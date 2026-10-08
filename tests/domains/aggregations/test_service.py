from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.error_handlers import ValidationError
from app.domains.aggregations.service import AggregationService


def condition(tag_id, operator="include"):
    return SimpleNamespace(tag_id=tag_id, operator=operator)


def node(name, *, parent_id=None, conditions=None, display_order=0):
    return SimpleNamespace(
        id=uuid4(),
        parent_id=parent_id,
        name=name,
        conditions=conditions or [],
        display_order=display_order,
    )


def build_service():
    service = AggregationService(MagicMock())
    service.repository = MagicMock()
    return service


def test_results_combine_parent_and_child_conditions():
    service = build_service()
    user_id = uuid4()
    health_tag_id = uuid4()
    mother_tag_id = uuid4()
    health = node("Health Expenses", conditions=[condition(health_tag_id)])
    mother = node(
        "Mother Health",
        parent_id=health.id,
        conditions=[condition(mother_tag_id)],
    )
    view = SimpleNamespace(id=uuid4(), name="My Budget", nodes=[mother, health])
    service.repository.get_view.return_value = view
    service.repository.aggregate_transactions.side_effect = [
        (Decimal("150.00"), 3),
        (Decimal("60.00"), 1),
    ]

    result = service.get_results(view.id, user_id)

    assert result.nodes[0].name == "Health Expenses"
    assert result.nodes[0].total == Decimal("150.00")
    assert result.nodes[0].children[0].name == "Mother Health"
    assert result.nodes[0].children[0].total == Decimal("60.00")
    calls = service.repository.aggregate_transactions.call_args_list
    assert calls[0].args[1] == {health_tag_id: "include"}
    assert calls[1].args[1] == {
        health_tag_id: "include",
        mother_tag_id: "include",
    }


def test_tree_rejects_include_exclude_contradiction_in_one_path():
    service = build_service()
    health_tag_id = uuid4()
    root = node("Health", conditions=[condition(health_tag_id, "include")])
    child = node(
        "Not Health",
        parent_id=root.id,
        conditions=[condition(health_tag_id, "exclude")],
    )

    with pytest.raises(ValidationError) as error:
        service._validate_tree([root, child])

    assert error.value.error_code == "CONTRADICTORY_AGGREGATION_CONDITIONS"


def test_tree_rejects_parent_cycles():
    service = build_service()
    first = node("First")
    second = node("Second", parent_id=first.id)
    first.parent_id = second.id

    with pytest.raises(ValidationError) as error:
        service._validate_tree([first, second])

    assert error.value.error_code == "AGGREGATION_NODE_CYCLE"


def test_tree_rejects_duplicate_sibling_names_case_insensitively():
    service = build_service()

    with pytest.raises(ValidationError) as error:
        service._validate_tree([node("Health"), node(" health ")])

    assert error.value.error_code == "DUPLICATE_AGGREGATION_NODE_NAME"
