from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.db.model_registration  # noqa: F401 - register every relationship
from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session, get_engine
from app.domains.accounts.models import Account
from app.domains.brokers.models import Broker
from app.domains.credit_cards.models import CreditCard
from app.domains.tags.schemas import TagCreate
from app.domains.tags.service import TagService
from app.domains.transactions.constants import MovementType
from app.domains.transactions.models import Transaction
from app.domains.users.models import User
from app.main import app


@pytest.fixture
def db_session():
    """A session inside a transaction that is always rolled back, so service
    commits never reach the database."""
    connection = get_engine().connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        if outer_transaction.is_active:
            outer_transaction.rollback()
        connection.close()


@pytest.fixture
def make_user(db_session):
    def make(email):
        user = User(email=email, full_name="Cashflow Test", hashed_password="not-used")
        db_session.add(user)
        db_session.flush()
        return user

    return make


@pytest.fixture
def ledger(db_session, make_user):
    """A user's transactions for today, plus an API client acting as them.

    Counted (expenses, today):
      Mother appointment  4000.00  [health, mother]            on the card
      Family pharmacy      100.00  [health, mother, personal]  13:00
      Gym                   50.00  [health, personal]
      Gift for mother      300.00  [mother]
      Untagged              30.00  []                          14:00
    Never counted: ignored, deleted, last year, and an income refund.

    Times are midday or later, not midnight: proves date_to includes the
    whole last day.
    """
    user = make_user("cashflow-integration@example.test")
    broker = Broker(user_id=user.id, name="Test Broker", colors=["#000000"])
    db_session.add(broker)
    db_session.flush()
    account = Account(
        user_id=user.id, broker_id=broker.id, name="Test Account", type="cash"
    )
    db_session.add(account)
    db_session.flush()
    card = CreditCard(
        user_id=user.id,
        broker_id=broker.id,
        account_id=account.id,
        name="Test Card",
        brand="visa",
    )
    db_session.add(card)
    db_session.commit()

    tag_service = TagService(db_session)
    tags = {
        name: tag_service.create_tag(TagCreate(name=name), user.id)
        for name in ("health", "mother", "personal", "unused")
    }

    today = date.today()
    noon = datetime.combine(today, time(12))

    def expense(description, amount, tag_names, **overrides):
        values = dict(
            user_id=user.id,
            account_id=account.id,
            broker_id=broker.id,
            amount=Decimal(amount),
            description=description,
            date=noon,
            movement_type=MovementType.EXPENSE.value,
            tags=[tags[name] for name in tag_names],
        )
        values.update(overrides)
        return Transaction(**values)

    on_card = dict(account_id=None, credit_card_id=card.id)
    db_session.add_all(
        [
            expense("Mother appointment", "4000.00", ["health", "mother"], **on_card),
            expense(
                "Family pharmacy",
                "100.00",
                ["health", "mother", "personal"],
                date=noon + timedelta(hours=1),
            ),
            expense("Gym", "50.00", ["health", "personal"]),
            expense("Gift for mother", "300.00", ["mother"]),
            expense("Untagged", "30.00", [], date=noon + timedelta(hours=2)),
            expense("Ignored", "500.00", ["health", "mother"], ignored=True),
            expense("Deleted", "600.00", ["health", "mother"], is_deleted=True),
            expense(
                "Last year",
                "700.00",
                ["health", "mother"],
                date=noon - timedelta(365),
            ),
            expense(
                "Refund",
                "20.00",
                ["health", "mother"],
                movement_type=MovementType.INCOME.value,
            ),
        ]
    )
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_user_id] = lambda: user.id

    yield SimpleNamespace(
        client=TestClient(app),
        user_id=user.id,
        tags={name: str(tag.id) for name, tag in tags.items()},
        account={"id": str(account.id), "name": "Test Account"},
        card={"id": str(card.id), "name": "Test Card"},
        period={"date_from": today.isoformat(), "date_to": today.isoformat()},
    )
    app.dependency_overrides.clear()
