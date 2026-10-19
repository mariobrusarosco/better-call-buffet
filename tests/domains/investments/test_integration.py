"""The four calls the frontend's Investments page makes, end to end, with the
payloads it sends (financial-app/src/domains/investments/api/investments.api.ts)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.db.model_registration  # noqa: F401 - register every relationship
from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session, get_engine
from app.domains.accounts.models import Account
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
    db_session.flush()
    # Created before opening balances existed: no balance point at all.
    previdencia = Account(
        user_id=user.id,
        broker_id=broker.id,
        name="Previdência - ITAÚ",
        type="investment",
    )
    db_session.add(previdencia)
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

    def save_balance(account_id, day, balance):
        # Exactly what the Data Input form sends.
        return client.put(
            f"/api/v1/balance_points/account/{account_id}/date/{day}",
            json={
                "balance": balance,
                "snapshot_type": "manual",
                "note": "from the form",
            },
        )

    yield SimpleNamespace(
        client=client,
        db=db_session,
        previdencia=str(previdencia.id),
        create_account=create_account,
        add_transaction=add_transaction,
        save_balance=save_balance,
    )
    app.dependency_overrides.clear()


def monthly_summary(world, account_id, year=2023, months=12):
    response = world.client.get(
        f"/api/v1/balance_points/account/{account_id}/monthly-summary",
        params={"year": year, "months": months},
    )
    assert response.status_code == 200, response.text
    return response.json()


def balance_of(world, account_id):
    response = world.client.get(f"/api/v1/accounts/{account_id}")
    assert response.status_code == 200, response.text
    return response.json()["balance"]


def fill_previdencia(world):
    for day, balance in [
        ("2022-12-31", 11036.00),  # first one becomes the opening
        ("2023-01-31", 11196.00),
        ("2023-02-28", 11451.00),
    ]:
        response = world.save_balance(world.previdencia, day, balance)
        assert response.status_code == 200, response.text


# ---- PUT /balance_points/account/{id}/date/{date} ------------------------------


def test_the_form_saves_balances_on_an_account_without_opening(world):
    response = world.save_balance(world.previdencia, "2022-12-31", 11036.00)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["account_id"] == world.previdencia
    assert body["date"] == "2022-12-31"
    assert body["balance"] == "11036.00"
    assert {"id", "created_at", "updated_at"} <= body.keys()
    assert balance_of(world, world.previdencia) == 11036.00


def test_saving_the_same_date_again_replaces_the_balance(world):
    world.save_balance(world.previdencia, "2022-12-31", 11036.00)
    world.save_balance(world.previdencia, "2023-01-31", 11000.00)
    world.save_balance(world.previdencia, "2023-01-31", 11196.00)

    points = (
        world.db.query(BalancePoint)
        .filter(BalancePoint.account_id == world.previdencia)
        .all()
    )
    assert sorted(str(p.balance) for p in points) == ["11036.00", "11196.00"]
    assert balance_of(world, world.previdencia) == 11196.00


def test_the_form_is_rejected_for_cash_accounts_and_bad_dates(world):
    checking = world.create_account("Nu Conta", "cash", 1000.00)
    world.save_balance(world.previdencia, "2022-12-31", 11036.00)

    assert world.save_balance(checking, "2023-01-31", 5000.00).status_code == 422
    assert world.save_balance(world.previdencia, "2022-12-30", 1.00).status_code == 422
    assert world.save_balance(world.previdencia, "2999-01-31", 1.00).status_code == 422
    assert world.save_balance(world.previdencia, "2023-01-31", -1.00).status_code == 422


def test_cash_account_balances_are_unchanged(world):
    checking = world.create_account("Nu Conta", "cash", 1000.00)
    world.add_transaction(checking, "income", 200.00, "2023-01-10")
    world.add_transaction(checking, "expense", 50.00, "2023-01-11")

    assert balance_of(world, checking) == 1150.00


# ---- GET /balance_points/account/{id}/monthly-summary ---------------------------


def test_monthly_summary_reproduces_the_spreadsheet(world):
    fill_previdencia(world)
    world.add_transaction(
        world.previdencia, "income", 999.00, "2023-02-11", ignored=True
    )

    months = monthly_summary(world, world.previdencia, months=3)

    assert [m["month_name"] for m in months] == ["Jan", "Feb", "Mar"]
    jan, feb, mar = months
    assert (jan["month"], jan["year"]) == (1, 2023)
    assert jan["started_with"] == "11036.00"
    assert jan["ended_with"] == "11196.00"
    assert jan["profit"] == "160.00"
    assert jan["profit_percentage"] == 1.45  # a number: the screen calls toFixed()
    assert feb["movement"] == "0.00"  # the ignored income doesn't count
    assert feb["profit"] == "255.00"
    assert feb["profit_percentage"] == 2.28
    assert mar["has_data"] is False


def test_income_is_taken_out_of_the_profit(world):
    itau = world.create_account(
        "Itaú Renda Fixa", "investment", 251567.20, opening_date="2022-12-31"
    )
    world.add_transaction(itau, "income", 4000.00, "2023-01-15")
    world.save_balance(itau, "2023-01-31", 257523.00)

    (jan,) = monthly_summary(world, itau, months=1)

    assert jan["movement"] == "4000.00"
    assert jan["profit"] == "1955.80"
    assert jan["profit_percentage"] == 0.78


def test_monthly_summary_is_only_for_investment_accounts(world):
    checking = world.create_account("Nu Conta", "cash", 1000.00)

    response = world.client.get(
        f"/api/v1/balance_points/account/{checking}/monthly-summary"
    )

    assert response.status_code == 422


# ---- GET /investments ---------------------------------------------------------------


def test_investments_list_shows_balance_invested_and_growth(world):
    fill_previdencia(world)
    world.add_transaction(world.previdencia, "income", 100.00, "2023-03-05")
    world.create_account("Nu Conta", "cash", 1000.00)

    response = world.client.get("/api/v1/investments")

    assert response.status_code == 200, response.text
    body = response.json()
    (investment,) = body["data"]
    assert investment["investment"]["id"] == world.previdencia
    assert investment["investment"]["name"] == "Previdência - ITAÚ"
    assert investment["current_balance"] == "11551.00"  # 11451 + 100 since
    assert investment["total_invested"] == "11136.00"  # 11036 opening + 100
    assert investment["total_growth"] == "415.00"  # 160 + 255
    assert investment["growth_percentage"] == 3.73
    assert investment["last_updated"] == "2023-02-28"
    assert body["meta"] == {
        "total": 1,
        "total_balance": "11551.00",
        "total_growth": "415.00",
        "overall_growth_percentage": 3.73,
    }


# ---- GET /investments/balances ------------------------------------------------------


def test_balance_history_has_the_spreadsheet_columns(world):
    fill_previdencia(world)
    world.add_transaction(world.previdencia, "income", 500.00, "2023-03-10")
    world.save_balance(world.previdencia, "2023-03-31", 11507.00)

    response = world.client.get(
        "/api/v1/investments/balances",
        params={"page": 1, "per_page": 20, "sort_by": "date", "sort_order": "desc"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    rows = [
        (
            r["date"],
            r["balance"],
            r["movement_amount"],
            r["diff_amount"],
            r["diff_percentage"],
        )
        for r in body["data"]
    ]
    assert rows == [
        ("2023-03-31", "11507.00", "500.00", "-444.00", -3.88),
        ("2023-02-28", "11451.00", None, "255.00", 2.28),
        ("2023-01-31", "11196.00", None, "160.00", 1.45),
        ("2022-12-31", "11036.00", None, "0.00", 0.0),  # the opening
    ]
    assert body["data"][0]["investment_id"] == world.previdencia
    assert body["meta"] == {
        "total": 4,
        "page": 1,
        "per_page": 20,
        "has_next": False,
        "has_previous": False,
    }


def test_balance_history_filters_and_pages(world):
    fill_previdencia(world)

    first_page = world.client.get(
        "/api/v1/investments/balances",
        params={
            "investment_id": world.previdencia,
            "date_from": "2023-01-01",
            "per_page": 1,
            "sort_order": "asc",
        },
    ).json()

    assert [r["date"] for r in first_page["data"]] == ["2023-01-31"]
    assert first_page["meta"]["total"] == 2
    assert first_page["meta"]["has_next"] is True
