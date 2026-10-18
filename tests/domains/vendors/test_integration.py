from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

import app.db.model_registration  # noqa: F401 - register every relationship
from app.db.connection_and_session import get_engine
from app.domains.accounts.models import Account
from app.domains.brokers.models import Broker
from app.domains.subscriptions.models import Subscription
from app.domains.transactions.models import Transaction
from app.domains.users.models import User
from app.domains.vendors.models import Vendor
from app.domains.vendors.schemas import VendorFilters
from app.domains.vendors.service import VendorService


@pytest.fixture
def db_session():
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
    """Netflix used 3 times, Spotify once, 100%_Natural never."""
    user = User(
        email="vendor-usage-integration@example.test",
        full_name="Vendor Usage Test",
        hashed_password="not-used",
    )
    db_session.add(user)
    db_session.flush()
    broker = Broker(user_id=user.id, name="Test Broker", colors=["#000000"])
    db_session.add(broker)
    db_session.flush()
    account = Account(
        user_id=user.id, broker_id=broker.id, name="Test Account", type="cash"
    )
    vendors = {
        name: Vendor(user_id=user.id, name=name)
        for name in ("Netflix", "Spotify", "100%_Natural")
    }
    db_session.add_all([account, *vendors.values()])
    db_session.flush()

    def expense(vendor):
        return Transaction(
            user_id=user.id,
            account_id=account.id,
            broker_id=broker.id,
            amount=Decimal("10.00"),
            description="Payment",
            date=datetime.utcnow(),
            movement_type="expense",
            vendor_id=vendor.id,
        )

    db_session.add_all(
        [
            expense(vendors["Netflix"]),
            expense(vendors["Netflix"]),
            expense(vendors["Spotify"]),
            Subscription(
                user_id=user.id,
                vendor_id=vendors["Netflix"].id,
                name="Netflix Family",
                amount=Decimal("55.90"),
                billing_cycle="monthly",
                next_due_date=date.today(),
            ),
        ]
    )
    db_session.commit()
    return SimpleNamespace(
        service=VendorService(db_session), user_id=user.id, vendors=vendors
    )


def test_usage_sort_puts_most_used_vendors_first(world):
    result = world.service.get_vendors(
        world.user_id, VendorFilters(sort_by="usage", sort_order="desc", per_page=2)
    )

    assert [(v.name, v.usage_count) for v in result.data] == [
        ("Netflix", 3),
        ("Spotify", 1),
    ]
    assert result.meta.total == 3
    assert result.meta.has_next is True


def test_search_is_case_insensitive_and_treats_wildcards_literally(world):
    def names(term):
        filters = VendorFilters(name_contains=term)
        return [v.name for v in world.service.get_vendors(world.user_id, filters).data]

    assert names("FLIX") == ["Netflix"]
    assert names("%_") == ["100%_Natural"]
    assert names("_") == ["100%_Natural"]


def test_plain_vendor_loads_do_not_compute_usage(world, db_session):
    db_session.expire_all()
    vendor = db_session.get(Vendor, world.vendors["Netflix"].id)

    assert "usage_count" in inspect(vendor).unloaded
