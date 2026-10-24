"""GET /transactions?has_installment, end to end. The frontend's Link a payment
drawer uses has_installment=false to list the transactions still available to
link, whatever their is_paid (users can mark a transaction paid by hand)."""

from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.db.model_registration  # noqa: F401 - register every relationship
from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session, get_engine
from app.domains.accounts.models import Account
from app.domains.brokers.models import Broker
from app.domains.installments.models import Installment, InstallmentPlan
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
def world(db_session):
    user = User(
        email="has-installment-filter@example.test",
        full_name="Installments Test",
        hashed_password="not-used",
    )
    db_session.add(user)
    db_session.flush()
    broker = Broker(user_id=user.id, name="Nubank", colors=["#820ad1"])
    db_session.add(broker)
    db_session.flush()
    account = Account(
        user_id=user.id, broker_id=broker.id, name="Nu Conta", type="savings"
    )
    db_session.add(account)
    db_session.flush()
    plan = InstallmentPlan(
        user_id=user.id,
        name="Dental Treatment",
        total_amount=18000,
        installment_count=10,
        start_date=date(2026, 8, 1),
    )
    db_session.add(plan)
    db_session.flush()
    installment = Installment(
        plan_id=plan.id, number=1, amount=1800, due_date=date(2026, 8, 1)
    )
    db_session.add(installment)
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_user_id] = lambda: user.id
    client = TestClient(app)

    def add_expense(description, is_paid):
        response = client.post(
            "/api/v1/transactions",
            json={
                "account_id": str(account.id),
                "broker_id": str(broker.id),
                "is_paid": is_paid,
                "date": "2026-08-01T12:00:00",
                "amount": 1800,
                "description": description,
                "movement_type": "expense",
            },
        )
        assert response.status_code == 200, response.text
        return response.json()["id"]

    def link(transaction_id):
        response = client.post(
            f"/api/v1/installments/{installment.id}/link-transaction",
            json={"transaction_id": transaction_id},
        )
        assert response.status_code == 200, response.text

    def descriptions(**params):
        response = client.get("/api/v1/transactions", params=params)
        assert response.status_code == 200, response.text
        return sorted(item["description"] for item in response.json()["data"])

    yield SimpleNamespace(add_expense=add_expense, link=link, descriptions=descriptions)
    app.dependency_overrides.clear()


def test_has_installment_splits_linked_from_unlinked(world):
    linked = world.add_expense("Parcela 1/10", is_paid=False)
    world.add_expense("Parcela 2/10", is_paid=True)  # marked paid by hand
    world.add_expense("Parcela 3/10", is_paid=False)
    world.link(linked)

    assert world.descriptions(has_installment="false") == [
        "Parcela 2/10",
        "Parcela 3/10",
    ]
    assert world.descriptions(has_installment="true") == ["Parcela 1/10"]
    assert len(world.descriptions()) == 3


def test_has_installment_ignores_is_paid(world):
    world.add_expense("Parcela 2/10", is_paid=True)

    # The old way (is_paid=false) misses it; has_installment=false finds it.
    assert world.descriptions(is_paid="false") == []
    assert world.descriptions(has_installment="false") == ["Parcela 2/10"]
