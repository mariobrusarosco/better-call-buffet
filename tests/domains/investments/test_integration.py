"""The monthly routine end to end, through the API: an investment account,
its closings and its income, then the monthly and portfolio views."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.db.model_registration  # noqa: F401 - register every relationship
from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session, get_engine
from app.domains.balance_points.models import BalancePoint
from app.domains.brokers.models import Broker
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
        email="investments-integration@example.test",
        full_name="Investments Test",
        hashed_password="not-used",
    )
    db_session.add(user)
    db_session.flush()
    broker = Broker(user_id=user.id, name="Itaú", colors=["#ec7000"])
    db_session.add(broker)
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_user_id] = lambda: user.id
    client = TestClient(app)

    def create_account(name, account_type, balance, opening_date=None):
        body = {
            "name": name,
            "type": account_type,
            "broker_id": str(broker.id),
            "balance": balance,
        }
        if opening_date:
            body["opening_date"] = opening_date
        response = client.post("/api/v1/accounts", json=body)
        assert response.status_code == 200, response.text
        return response.json()["id"]

    def add_transaction(account_id, movement_type, amount, day, **extra):
        response = client.post(
            "/api/v1/transactions",
            json={
                "account_id": account_id,
                "broker_id": str(broker.id),
                "is_paid": True,
                "date": f"{day}T12:00:00",
                "amount": amount,
                "description": f"{movement_type} {amount}",
                "movement_type": movement_type,
                **extra,
            },
        )
        assert response.status_code == 200, response.text

    def save_closing(account_id, day, balance):
        return client.put(
            f"/api/v1/balance_points/{account_id}/{day}", json={"balance": balance}
        )

    previdencia = create_account(
        "Previdência", "investment", 11036.00, opening_date="2022-12-31"
    )

    yield SimpleNamespace(
        client=client,
        db=db_session,
        previdencia=previdencia,
        create_account=create_account,
        add_transaction=add_transaction,
        save_closing=save_closing,
    )
    app.dependency_overrides.clear()


def monthly(world, account_id, first, last):
    response = world.client.get(
        f"/api/v1/investments/{account_id}/monthly",
        params={"from": first, "to": last},
    )
    assert response.status_code == 200, response.text
    return response.json()


def balance_of(world, account_id):
    response = world.client.get(f"/api/v1/accounts/{account_id}")
    assert response.status_code == 200, response.text
    return response.json()["balance"]


def test_monthly_routine_reproduces_the_spreadsheet(world):
    assert (
        world.save_closing(world.previdencia, "2023-01-31", "11196.00").status_code
        == 200
    )
    world.add_transaction(world.previdencia, "income", 1000.00, "2023-02-10")
    world.add_transaction(
        world.previdencia, "income", 999.00, "2023-02-11", ignored=True
    )
    assert (
        world.save_closing(world.previdencia, "2023-02-28", "12451.00").status_code
        == 200
    )

    jan, feb = monthly(world, world.previdencia, "2023-01", "2023-02")

    assert jan["started_with"] == "11036.00"
    assert jan["ended_with"] == "11196.00"
    assert jan["profit"] == "160.00"
    assert jan["profit_percentage"] == "1.45"
    assert feb["movement"] == "1000.00"  # the ignored income doesn't count
    assert feb["profit"] == "255.00"
    assert feb["profit_percentage"] == "2.28"


def test_balance_is_the_latest_closing_plus_later_transactions(world):
    world.save_closing(world.previdencia, "2023-01-31", "11196.00")
    world.add_transaction(world.previdencia, "income", 50.00, "2023-01-31")
    assert balance_of(world, world.previdencia) == 11196.00  # inside the closing

    world.add_transaction(world.previdencia, "income", 100.00, "2023-02-05")
    world.add_transaction(world.previdencia, "expense", 30.00, "2023-02-06")
    assert balance_of(world, world.previdencia) == 11266.00


def test_saving_a_closing_again_replaces_it(world):
    world.save_closing(world.previdencia, "2023-01-31", "11000.00")
    response = world.save_closing(world.previdencia, "2023-01-31", "11196.00")

    assert response.status_code == 200
    assert response.json()["balance"] == "11196.00"
    points = (
        world.db.query(BalancePoint)
        .filter(BalancePoint.account_id == world.previdencia)
        .all()
    )
    assert sorted(str(p.balance) for p in points) == ["11036.00", "11196.00"]


def test_deleting_a_closing_removes_that_month_and_the_opening_is_protected(world):
    world.save_closing(world.previdencia, "2023-01-31", "11196.00")

    deleted = world.client.delete(
        f"/api/v1/balance_points/{world.previdencia}/2023-01-31"
    )
    opening = world.client.delete(
        f"/api/v1/balance_points/{world.previdencia}/2022-12-31"
    )

    assert deleted.status_code == 204
    assert opening.status_code == 422
    (jan,) = monthly(world, world.previdencia, "2023-01", "2023-01")
    assert jan["has_data"] is False


def test_cash_accounts_keep_their_balance_and_take_no_closings(world):
    checking = world.create_account("Nu Conta", "cash", 1000.00)
    world.add_transaction(checking, "income", 200.00, "2023-01-10")
    world.add_transaction(checking, "expense", 50.00, "2023-01-11")

    response = world.save_closing(checking, "2023-01-31", "5000.00")
    monthly_response = world.client.get(
        f"/api/v1/investments/{checking}/monthly",
        params={"from": "2023-01", "to": "2023-01"},
    )

    assert response.status_code == 422
    assert monthly_response.status_code == 422
    assert balance_of(world, checking) == 1150.00


def test_portfolio_lists_investments_with_monthly_totals(world):
    world.create_account("Nu Conta", "cash", 1000.00)
    itau = world.create_account(
        "Itaú Renda Fixa", "investment", 251567.20, opening_date="2022-12-31"
    )
    world.save_closing(world.previdencia, "2023-01-31", "11196.00")
    world.add_transaction(itau, "income", 4000.00, "2023-01-15")
    world.save_closing(itau, "2023-01-31", "257523.00")

    response = world.client.get(
        "/api/v1/investments/portfolio", params={"from": "2023-01", "to": "2023-01"}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    profits = {
        account["name"]: account["months"][0]["profit"] for account in body["accounts"]
    }
    assert profits == {"Previdência": "160.00", "Itaú Renda Fixa": "1955.80"}
    (total,) = body["totals"]
    assert total["ended_with"] == "268719.00"
    assert total["movement"] == "4000.00"
    assert total["profit"] == "2115.80"
    assert total["profit_percentage"] == "0.79"  # 2115.80 ÷ 268719.00


def test_month_range_is_validated(world):
    backwards = world.client.get(
        f"/api/v1/investments/{world.previdencia}/monthly",
        params={"from": "2023-03", "to": "2023-01"},
    )
    malformed = world.client.get(
        "/api/v1/investments/portfolio", params={"from": "2023-13", "to": "2023-01"}
    )

    assert backwards.status_code == 422
    assert malformed.status_code == 422
