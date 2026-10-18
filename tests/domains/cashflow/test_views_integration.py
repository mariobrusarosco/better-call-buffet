from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.db.model_registration  # noqa: F401 - register every relationship
from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session, get_engine
from app.domains.accounts.models import Account
from app.domains.brokers.models import Broker
from app.domains.cashflow.models import CashflowViewGroup
from app.domains.tags.schemas import TagCreate
from app.domains.tags.service import TagService
from app.domains.transactions.constants import MovementType
from app.domains.transactions.models import Transaction
from app.domains.users.models import User
from app.main import app


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


def make_user(db_session, email):
    user = User(email=email, full_name="Cashflow Test", hashed_password="not-used")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def world(db_session):
    """One view, two groups:

    Family = [family, pharmacy]    Health = [health, unused]

    "Mother appointment" carries family + health, so it lands in both groups.
    "Pharmacy" carries family + pharmacy, so it matches Family through two
    tags but must be counted once.
    """
    user = make_user(db_session, "cashflow-views-integration@example.test")
    broker = Broker(user_id=user.id, name="Test Broker", colors=["#000000"])
    db_session.add(broker)
    db_session.flush()
    account = Account(
        user_id=user.id, broker_id=broker.id, name="Test Account", type="cash"
    )
    db_session.add(account)
    db_session.commit()

    tag_service = TagService(db_session)
    tags = {
        name: tag_service.create_tag(TagCreate(name=name), user.id)
        for name in ("family", "pharmacy", "health", "unused")
    }

    today = date.today()
    # Noon, not midnight: proves date_to includes the whole last day.
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

    db_session.add_all(
        [
            expense("Mother appointment", "4000.00", ["family", "health"]),
            expense("Pharmacy", "100.00", ["family", "pharmacy"]),
            expense("Gym", "50.00", ["health"]),
            expense("Untagged", "30.00", []),
            expense("Ignored", "500.00", ["family"], ignored=True),
            expense("Deleted", "600.00", ["family"], is_deleted=True),
            expense("Last year", "700.00", ["family"], date=noon - timedelta(365)),
            expense(
                "Refund",
                "20.00",
                ["family"],
                movement_type=MovementType.INCOME.value,
            ),
        ]
    )
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_user_id] = lambda: user.id
    client = TestClient(app)

    response = client.post(
        "/api/v1/cashflow/views",
        json={
            "name": "By person",
            "groups": [
                {
                    "name": "Family",
                    "tag_ids": [str(tags["family"].id), str(tags["pharmacy"].id)],
                },
                {
                    "name": "Health",
                    "tag_ids": [str(tags["health"].id), str(tags["unused"].id)],
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    view = response.json()

    yield SimpleNamespace(
        client=client,
        user_id=user.id,
        tags={name: str(tag.id) for name, tag in tags.items()},
        view=view,
        family=view["groups"][0]["id"],
        health=view["groups"][1]["id"],
        period={"date_from": today.isoformat(), "date_to": today.isoformat()},
    )
    app.dependency_overrides.clear()


# ---- CRUD ---------------------------------------------------------------------


def test_create_returns_the_contract_shape(world):
    view = world.view

    assert set(view) == {
        "id",
        "name",
        "display_order",
        "groups",
        "created_at",
        "updated_at",
    }
    assert view["name"] == "By person"
    assert view["display_order"] == 0
    assert [g["name"] for g in view["groups"]] == ["Family", "Health"]
    assert view["groups"][0]["tag_ids"] == [
        world.tags["family"],
        world.tags["pharmacy"],
    ]


def test_list_returns_a_bare_array_ordered_by_display_order_then_name(world):
    world.client.post(
        "/api/v1/cashflow/views", json={"name": "Alpha", "display_order": 1}
    )
    world.client.post("/api/v1/cashflow/views", json={"name": "Zulu"})

    response = world.client.get("/api/v1/cashflow/views")

    assert response.status_code == 200
    assert [v["name"] for v in response.json()] == ["By person", "Zulu", "Alpha"]


def test_patch_replaces_groups_and_keeps_omitted_fields(world, db_session):
    response = world.client.patch(
        f"/api/v1/cashflow/views/{world.view['id']}",
        json={"groups": [{"name": "Only health", "tag_ids": [world.tags["health"]]}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "By person"
    assert [(g["name"], g["tag_ids"]) for g in body["groups"]] == [
        ("Only health", [world.tags["health"]])
    ]
    # The replaced groups are gone from the database, not just detached.
    remaining = db_session.query(CashflowViewGroup).filter(
        CashflowViewGroup.view_id == world.view["id"]
    )
    assert remaining.count() == 1


def test_delete_returns_204_and_the_view_is_gone(world):
    url = f"/api/v1/cashflow/views/{world.view['id']}"

    response = world.client.delete(url)

    assert response.status_code == 204
    assert response.content == b""
    assert world.client.patch(url, json={"name": "x"}).status_code == 404


def test_views_of_another_user_are_not_found(world, db_session):
    intruder = make_user(db_session, "cashflow-views-intruder@example.test")
    app.dependency_overrides[get_current_user_id] = lambda: intruder.id
    view_url = f"/api/v1/cashflow/views/{world.view['id']}"

    assert world.client.get("/api/v1/cashflow/views").json() == []
    assert world.client.patch(view_url, json={"name": "x"}).status_code == 404
    assert world.client.delete(view_url).status_code == 404
    assert world.client.get(f"{view_url}/summary").status_code == 404
    assert world.client.get(f"{view_url}/overlaps").status_code == 404


def test_unknown_view_is_not_found(world):
    response = world.client.get(f"/api/v1/cashflow/views/{uuid4()}/summary")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Cashflow view not found"


def test_validation_errors_carry_a_readable_message(world):
    response = world.client.post(
        "/api/v1/cashflow/views",
        json={"name": "V", "groups": [{"name": "Family", "tag_ids": []}]},
    )

    assert response.status_code == 422
    assert (
        response.json()["error"]["message"] == 'Group "Family" needs at least one tag.'
    )


def test_another_users_tag_is_rejected(world, db_session):
    stranger = make_user(db_session, "cashflow-views-stranger@example.test")
    foreign_tag = TagService(db_session).create_tag(
        TagCreate(name="theirs"), stranger.id
    )

    response = world.client.post(
        "/api/v1/cashflow/views",
        json={"name": "V", "groups": [{"name": "G", "tag_ids": [str(foreign_tag.id)]}]},
    )

    assert response.status_code == 422


# ---- Summary and overlaps ---------------------------------------------------------


def test_summary_counts_each_expense_once_per_group(world):
    response = world.client.get(
        f"/api/v1/cashflow/views/{world.view['id']}/summary", params=world.period
    )

    assert response.status_code == 200
    family, health = response.json()["groups"]

    # Mother appointment + Pharmacy. Pharmacy matches through two tags but
    # counts once, so the group total is less than the sum of its tags.
    assert family == {
        "group_id": world.family,
        "total": "4100.00",
        "count": 2,
        "tags": [
            {"tag_id": world.tags["family"], "total": "4100.00", "count": 2},
            {"tag_id": world.tags["pharmacy"], "total": "100.00", "count": 1},
        ],
    }
    # Every tag is listed, even with no matches.
    assert health == {
        "group_id": world.health,
        "total": "4050.00",
        "count": 2,
        "tags": [
            {"tag_id": world.tags["health"], "total": "4050.00", "count": 2},
            {"tag_id": world.tags["unused"], "total": "0.00", "count": 0},
        ],
    }


def test_summary_respects_movement_type(world):
    response = world.client.get(
        f"/api/v1/cashflow/views/{world.view['id']}/summary",
        params={**world.period, "movement_type": "income"},
    )

    family = response.json()["groups"][0]
    assert (family["total"], family["count"]) == ("20.00", 1)


def test_summary_without_dates_covers_all_time(world):
    response = world.client.get(f"/api/v1/cashflow/views/{world.view['id']}/summary")

    family = response.json()["groups"][0]
    assert (family["total"], family["count"]) == ("4800.00", 3)  # + last year


def test_overlaps_list_expenses_in_two_or_more_groups(world):
    response = world.client.get(
        f"/api/v1/cashflow/views/{world.view['id']}/overlaps", params=world.period
    )

    assert response.status_code == 200
    [overlap] = response.json()
    assert overlap["description"] == "Mother appointment"
    assert overlap["amount"] == "4000.00"
    assert overlap["date"] == world.period["date_from"]
    assert overlap["group_ids"] == [world.family, world.health]


def test_overlaps_are_empty_when_groups_do_not_share_expenses(world):
    world.client.patch(
        f"/api/v1/cashflow/views/{world.view['id']}",
        json={"groups": [{"name": "Only health", "tag_ids": [world.tags["health"]]}]},
    )

    response = world.client.get(
        f"/api/v1/cashflow/views/{world.view['id']}/overlaps", params=world.period
    )

    assert response.json() == []


# ---- Monthly cashflow -------------------------------------------------------------


def test_monthly_cashflow_is_served_at_new_and_legacy_paths(world):
    new = world.client.get("/api/v1/cashflow", params=world.period)
    legacy = world.client.get("/api/v1/analytics/cashflow", params=world.period)

    assert new.status_code == legacy.status_code == 200
    assert new.json() == legacy.json()
    # Same scope as the views: ignored, deleted and last-year rows excluded.
    assert Decimal(new.json()["total_expenses"]) == Decimal("4180.00")
