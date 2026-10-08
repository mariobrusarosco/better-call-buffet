from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

import app.db.model_registration  # noqa: F401 - register every relationship
from app.db.connection_and_session import get_engine
from app.domains.accounts.models import Account
from app.domains.brokers.models import Broker
from app.domains.tag_groups.models import TagGroup
from app.domains.tag_groups.schemas import TagGroupCreate
from app.domains.tag_groups.service import TagGroupService
from app.domains.tags.schemas import TagCreate
from app.domains.tags.service import TagService
from app.domains.transactions.constants import MovementType
from app.domains.transactions.models import Transaction
from app.domains.users.models import User


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
    """Health > {Mother Health, Personal Health}, plus a few expenses."""
    user = User(
        email="tag-groups-integration@example.test",
        full_name="Tag Groups Test",
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
    db_session.add(account)
    db_session.commit()

    tag_service = TagService(db_session)
    tags = {
        name: tag_service.create_tag(TagCreate(name=name), user.id)
        for name in ("health", "mother", "personal")
    }

    now = datetime.utcnow()

    def expense(description, amount, tag_names, **overrides):
        values = dict(
            user_id=user.id,
            account_id=account.id,
            broker_id=broker.id,
            amount=Decimal(amount),
            description=description,
            date=now,
            movement_type="expense",
            tags=[tags[name] for name in tag_names],
        )
        values.update(overrides)
        return Transaction(**values)

    db_session.add_all(
        [
            expense("Mother appointment", "100.00", ["health", "mother"]),
            expense("Gym", "40.00", ["health", "personal"]),
            expense("Family pharmacy", "30.00", ["health", "mother", "personal"]),
            expense("Gift for mother", "999.00", ["mother"]),  # no health tag
            expense("Ignored", "500.00", ["health", "mother"], ignored=True),
            expense(
                "Last year", "700.00", ["health", "mother"], date=now - timedelta(365)
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

    service = TagGroupService(db_session)
    health = service.create_group(
        TagGroupCreate(name="Health", tag_ids=[tags["health"].id]), user.id
    )
    mother = service.create_group(
        TagGroupCreate(
            name="Mother Health", tag_ids=[tags["mother"].id], parent_id=health.id
        ),
        user.id,
    )
    personal = service.create_group(
        TagGroupCreate(
            name="Personal Health", tag_ids=[tags["personal"].id], parent_id=health.id
        ),
        user.id,
    )
    return SimpleNamespace(
        service=service,
        user_id=user.id,
        tags=tags,
        groups={"health": health, "mother": mother, "personal": personal},
        since=now - timedelta(days=30),
    )


def test_child_group_exposes_inherited_tags(world):
    responses = {
        response.id: response
        for response in world.service.build_responses(
            world.service.list_groups(world.user_id)
        )
    }
    mother = responses[world.groups["mother"].id]

    assert mother.tag_ids == [world.tags["mother"].id]
    assert mother.effective_tag_ids == [
        world.tags["health"].id,
        world.tags["mother"].id,
    ]


def test_summary_matches_all_effective_tags_within_cashflow_scope(world):
    summary = {
        item.group_id: (item.total, item.count)
        for item in world.service.get_summary(world.user_id, date_from=world.since)
    }

    # Ignored, last-year, income and health-less expenses never count.
    assert summary[world.groups["health"].id] == (Decimal("170.00"), 3)
    assert summary[world.groups["mother"].id] == (Decimal("130.00"), 2)
    assert summary[world.groups["personal"].id] == (Decimal("70.00"), 2)


def test_overlaps_list_only_transactions_shared_by_unrelated_groups(world):
    overlaps = world.service.get_overlaps(world.user_id, date_from=world.since)

    assert [item.description for item in overlaps] == ["Family pharmacy"]
    assert set(overlaps[0].group_ids) == {
        world.groups["mother"].id,
        world.groups["personal"].id,
    }


def test_deleting_a_parent_deletes_its_children(world, db_session):
    world.service.delete_group(world.groups["health"].id, world.user_id)
    db_session.expire_all()

    remaining = db_session.query(TagGroup).filter(TagGroup.user_id == world.user_id)
    assert remaining.count() == 0
