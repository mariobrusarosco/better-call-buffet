from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

import app.db.model_registration  # noqa: F401 - register every relationship
from app.db.connection_and_session import get_engine
from app.domains.accounts.models import Account
from app.domains.aggregations.schemas import (
    AggregationConditionCreate,
    AggregationNodeCreate,
    AggregationViewCreate,
)
from app.domains.aggregations.service import AggregationService
from app.domains.brokers.models import Broker
from app.domains.tags.constants import TagSelectionMode
from app.domains.tags.schemas import TagCreate, TagDimensionCreate
from app.domains.tags.service import TagService
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


def test_health_view_aggregates_mother_and_myself_transactions(db_session):
    user = User(
        email="tag-aggregation-integration@example.test",
        full_name="Tag Aggregation Test",
        hashed_password="not-used",
    )
    db_session.add(user)
    db_session.flush()
    broker = Broker(
        user_id=user.id,
        name="Test Broker",
        colors=["#000000"],
    )
    db_session.add(broker)
    db_session.flush()
    account = Account(
        user_id=user.id,
        broker_id=broker.id,
        name="Test Account",
        type="cash",
    )
    db_session.add(account)
    db_session.commit()

    tag_service = TagService(db_session)
    topic = tag_service.create_dimension(
        TagDimensionCreate(name="Topic", selection_mode=TagSelectionMode.SINGLE),
        user.id,
    )
    person = tag_service.create_dimension(
        TagDimensionCreate(name="Person", selection_mode=TagSelectionMode.SINGLE),
        user.id,
    )
    health = tag_service.create_tag(
        TagCreate(name="Health", dimension_id=topic.id), user.id
    )
    mother = tag_service.create_tag(
        TagCreate(name="Mother", dimension_id=person.id), user.id
    )
    myself = tag_service.create_tag(
        TagCreate(name="Myself", dimension_id=person.id), user.id
    )

    db_session.add_all(
        [
            Transaction(
                user_id=user.id,
                account_id=account.id,
                broker_id=broker.id,
                amount=Decimal("100.00"),
                description="Mother appointment",
                date=datetime.utcnow(),
                movement_type="expense",
                is_paid=True,
                tags=[health, mother],
            ),
            Transaction(
                user_id=user.id,
                account_id=account.id,
                broker_id=broker.id,
                amount=Decimal("50.00"),
                description="My appointment",
                date=datetime.utcnow(),
                movement_type="expense",
                is_paid=True,
                tags=[health, myself],
            ),
        ]
    )
    db_session.commit()

    aggregation_service = AggregationService(db_session)
    view = aggregation_service.create_view(
        AggregationViewCreate(name="Health Expenses"), user.id
    )
    root_response = aggregation_service.create_node(
        view.id,
        AggregationNodeCreate(
            name="Health Expenses",
            conditions=[AggregationConditionCreate(tag_id=health.id)],
        ),
        user.id,
    )
    root_id = root_response.nodes[0].id
    aggregation_service.create_node(
        view.id,
        AggregationNodeCreate(
            name="Health and Mother",
            parent_id=root_id,
            conditions=[AggregationConditionCreate(tag_id=mother.id)],
        ),
        user.id,
    )
    aggregation_service.create_node(
        view.id,
        AggregationNodeCreate(
            name="Health and Myself",
            parent_id=root_id,
            conditions=[AggregationConditionCreate(tag_id=myself.id)],
        ),
        user.id,
    )

    result = aggregation_service.get_results(view.id, user.id)

    assert result.nodes[0].total == Decimal("150.00")
    assert result.nodes[0].transaction_count == 2
    children = {child.name: child for child in result.nodes[0].children}
    assert children["Health and Mother"].total == Decimal("100.00")
    assert children["Health and Mother"].transaction_count == 1
    assert children["Health and Myself"].total == Decimal("50.00")
    assert children["Health and Myself"].transaction_count == 1
