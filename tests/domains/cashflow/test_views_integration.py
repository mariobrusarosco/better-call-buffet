from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

import app.db.model_registration  # noqa: F401 - register every relationship
from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session, get_engine
from app.domains.accounts.models import Account
from app.domains.brokers.models import Broker
from app.domains.cashflow.models import CashflowViewGroup
from app.domains.credit_cards.models import CreditCard
from app.domains.tags.models import Tag
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
    """One view, three groups. A group matches expenses carrying ALL its tags:

    Mother Health = [health, mother]       Personal Health = [health, personal]
    Unused        = [unused]

    "Family pharmacy" carries health + mother + personal, so it lands in both
    health groups. "Gift for mother" has mother but not health: no match.
    """
    user = make_user(db_session, "cashflow-views-integration@example.test")
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
    # Midday, not midnight: proves date_to includes the whole last day.
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
    client = TestClient(app)

    def tag_ids(*names):
        return [str(tags[name].id) for name in names]

    response = client.post(
        "/api/v1/cashflow/views",
        json={
            "name": "By person",
            "groups": [
                {"name": "Mother Health", "tag_ids": tag_ids("health", "mother")},
                {"name": "Personal Health", "tag_ids": tag_ids("health", "personal")},
                {"name": "Unused", "tag_ids": tag_ids("unused")},
            ],
        },
    )
    assert response.status_code == 201, response.text
    view = response.json()
    mother, personal, unused = (group["id"] for group in view["groups"])

    yield SimpleNamespace(
        client=client,
        user_id=user.id,
        tags={name: str(tag.id) for name, tag in tags.items()},
        account={"id": str(account.id), "name": "Test Account"},
        card={"id": str(card.id), "name": "Test Card"},
        view=view,
        view_url=f"/api/v1/cashflow/views/{view['id']}",
        mother=mother,
        personal=personal,
        unused=unused,
        period={"date_from": today.isoformat(), "date_to": today.isoformat()},
    )
    app.dependency_overrides.clear()


def summary_of(world, **params):
    response = world.client.get(f"{world.view_url}/summary", params=params)
    assert response.status_code == 200, response.text
    return {group["group_id"]: group for group in response.json()["groups"]}


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
    assert [g["name"] for g in view["groups"]] == [
        "Mother Health",
        "Personal Health",
        "Unused",
    ]
    assert view["groups"][0]["tag_ids"] == [
        world.tags["health"],
        world.tags["mother"],
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
        world.view_url,
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
    response = world.client.delete(world.view_url)

    assert response.status_code == 204
    assert response.content == b""
    assert world.client.patch(world.view_url, json={"name": "x"}).status_code == 404


def test_views_of_another_user_are_not_found(world, db_session):
    intruder = make_user(db_session, "cashflow-views-intruder@example.test")
    app.dependency_overrides[get_current_user_id] = lambda: intruder.id
    group_url = f"{world.view_url}/groups/{world.mother}/transactions"

    assert world.client.get("/api/v1/cashflow/views").json() == []
    assert world.client.patch(world.view_url, json={"name": "x"}).status_code == 404
    assert world.client.delete(world.view_url).status_code == 404
    assert world.client.get(f"{world.view_url}/summary").status_code == 404
    assert world.client.get(f"{world.view_url}/overlaps").status_code == 404
    assert world.client.get(group_url).status_code == 404
    ungrouped_url = f"{world.view_url}/ungrouped/transactions"
    assert world.client.get(ungrouped_url).status_code == 404


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


# ---- Summary ------------------------------------------------------------------


def test_summary_matches_expenses_carrying_all_of_a_groups_tags(world):
    response = world.client.get(f"{world.view_url}/summary", params=world.period)

    # Gift for mother (mother only) stays out of Mother Health. Family
    # pharmacy is in both health groups and counted once in each.
    # Ignored, deleted, last-year and income rows never count.
    assert response.json() == {
        "groups": [
            {"group_id": world.mother, "total": "4100.00", "count": 2},
            {"group_id": world.personal, "total": "150.00", "count": 2},
            {"group_id": world.unused, "total": "0.00", "count": 0},
        ],
        # Gift for mother + Untagged.
        "ungrouped": {"total": "330.00", "count": 2},
    }


def test_in_a_view_without_groups_every_expense_is_ungrouped(world):
    view = world.client.post("/api/v1/cashflow/views", json={"name": "Empty"}).json()

    response = world.client.get(
        f"/api/v1/cashflow/views/{view['id']}/summary", params=world.period
    )

    assert response.json() == {
        "groups": [],
        "ungrouped": {"total": "4480.00", "count": 5},
    }


def test_ungrouped_is_zero_when_groups_cover_everything(world):
    world.client.patch(
        world.view_url,
        json={"groups": [{"name": "Health", "tag_ids": [world.tags["health"]]}]},
    )

    response = world.client.get(
        f"{world.view_url}/summary", params={**world.period, "movement_type": "income"}
    )

    assert response.json()["ungrouped"] == {"total": "0.00", "count": 0}


def test_summary_respects_movement_type(world):
    summary = summary_of(world, **world.period, movement_type="income")

    assert (summary[world.mother]["total"], summary[world.mother]["count"]) == (
        "20.00",
        1,
    )


def test_summary_without_dates_covers_all_time(world):
    summary = summary_of(world)

    # + Last year
    assert (summary[world.mother]["total"], summary[world.mother]["count"]) == (
        "4800.00",
        3,
    )


def test_group_whose_tags_were_all_deleted_matches_nothing(world, db_session):
    # Deleting a tag removes it from groups (ON DELETE CASCADE). An empty
    # ALL-of rule must not turn into "every transaction".
    db_session.execute(delete(Tag).where(Tag.id == world.tags["unused"]))
    db_session.commit()

    summary = summary_of(world, **world.period)

    assert (summary[world.unused]["total"], summary[world.unused]["count"]) == (
        "0.00",
        0,
    )


# ---- Overlaps -----------------------------------------------------------------


def test_overlaps_list_expenses_in_two_or_more_groups(world):
    response = world.client.get(f"{world.view_url}/overlaps", params=world.period)

    assert response.status_code == 200
    [overlap] = response.json()
    assert overlap["description"] == "Family pharmacy"
    assert overlap["amount"] == "100.00"
    assert overlap["date"] == world.period["date_from"]
    assert overlap["group_ids"] == [world.mother, world.personal]


def test_overlaps_are_empty_when_groups_do_not_share_expenses(world):
    world.client.patch(
        world.view_url,
        json={"groups": [{"name": "Only health", "tag_ids": [world.tags["health"]]}]},
    )

    response = world.client.get(f"{world.view_url}/overlaps", params=world.period)

    assert response.json() == []


# ---- Group transactions -------------------------------------------------------


def test_group_transactions_list_what_is_behind_the_total(world):
    response = world.client.get(
        f"{world.view_url}/groups/{world.mother}/transactions", params=world.period
    )

    assert response.status_code == 200
    body = response.json()
    family_pharmacy, mother_appointment = body["data"]  # newest first
    assert family_pharmacy == {
        "id": family_pharmacy["id"],
        "date": world.period["date_from"],
        "description": "Family pharmacy",
        "amount": "100.00",
        "account": world.account,
        "credit_card": None,
    }
    assert mother_appointment["description"] == "Mother appointment"
    assert mother_appointment["account"] is None
    assert mother_appointment["credit_card"] == world.card
    # Same rule as the summary, so the numbers line up.
    assert (
        body["meta"]["total"]
        == summary_of(world, **world.period)[world.mother]["count"]
    )
    assert body["meta"]["has_next"] is False


def test_group_transactions_are_paginated(world):
    url = f"{world.view_url}/groups/{world.mother}/transactions"

    first = world.client.get(url, params={**world.period, "per_page": 1}).json()
    second = world.client.get(
        url, params={**world.period, "per_page": 1, "page": 2}
    ).json()

    assert [t["description"] for t in first["data"]] == ["Family pharmacy"]
    assert first["meta"] == {
        "total": 2,
        "page": 1,
        "per_page": 1,
        "has_next": True,
        "has_previous": False,
    }
    assert [t["description"] for t in second["data"]] == ["Mother appointment"]
    assert second["meta"]["has_next"] is False


def test_group_transactions_reject_per_page_above_100(world):
    response = world.client.get(
        f"{world.view_url}/groups/{world.mother}/transactions",
        params={"per_page": 101},
    )

    assert response.status_code == 422


def test_group_of_another_view_or_unknown_is_not_found(world):
    other = world.client.post(
        "/api/v1/cashflow/views",
        json={
            "name": "Other",
            "groups": [{"name": "G", "tag_ids": [world.tags["health"]]}],
        },
    ).json()
    other_group = other["groups"][0]["id"]

    for group_id in (other_group, str(uuid4())):
        response = world.client.get(f"{world.view_url}/groups/{group_id}/transactions")
        assert response.status_code == 404
        assert response.json()["error"]["message"] == "Cashflow view group not found"


# ---- Monthly cashflow -----------------------------------------------------------


def test_monthly_cashflow_is_served_at_new_and_legacy_paths(world):
    new = world.client.get("/api/v1/cashflow", params=world.period)
    legacy = world.client.get("/api/v1/analytics/cashflow", params=world.period)

    assert new.status_code == legacy.status_code == 200
    assert new.json() == legacy.json()
    # Same scope as the views: ignored, deleted and last-year rows excluded.
    assert Decimal(new.json()["total_expenses"]) == Decimal("4480.00")


# ---- Ungrouped transactions -----------------------------------------------------


def test_ungrouped_transactions_list_what_is_behind_the_ungrouped_total(world):
    response = world.client.get(
        f"{world.view_url}/ungrouped/transactions", params=world.period
    )

    assert response.status_code == 200
    body = response.json()
    assert [t["description"] for t in body["data"]] == [
        "Untagged",
        "Gift for mother",
    ]
    assert body["data"][0]["account"] == world.account
    ungrouped = world.client.get(
        f"{world.view_url}/summary", params=world.period
    ).json()["ungrouped"]
    assert body["meta"]["total"] == ungrouped["count"]


def test_ungrouped_transactions_are_paginated(world):
    url = f"{world.view_url}/ungrouped/transactions"

    second = world.client.get(
        url, params={**world.period, "per_page": 1, "page": 2}
    ).json()

    assert [t["description"] for t in second["data"]] == ["Gift for mother"]
    assert second["meta"] == {
        "total": 2,
        "page": 2,
        "per_page": 1,
        "has_next": False,
        "has_previous": True,
    }
