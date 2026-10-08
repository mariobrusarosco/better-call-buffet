from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.error_handlers import ValidationError
from app.domains.tag_groups.constants import MAX_TAG_GROUP_DEPTH
from app.domains.tag_groups.schemas import TagGroupCreate, TagGroupUpdate
from app.domains.tag_groups.service import (
    TagGroupService,
    effective_tag_ids,
    most_specific_groups,
)


def build_group(parent=None, tag_ids=None):
    now = datetime.utcnow()
    return SimpleNamespace(
        id=uuid4(),
        parent_id=parent.id if parent else None,
        name="Group",
        display_order=0,
        created_at=now,
        updated_at=now,
        tags=[SimpleNamespace(id=tag_id) for tag_id in (tag_ids or [uuid4()])],
    )


def build_service(groups=()):
    service = TagGroupService(MagicMock())
    service.repository = MagicMock()
    service.repository.list_groups.return_value = list(groups)
    service.repository.save.side_effect = lambda group: group
    by_id = {group.id: group for group in groups}
    service.repository.get_group.side_effect = lambda group_id, _: by_id.get(group_id)
    service.tag_service = MagicMock()
    service.tag_service.validate_tag_assignment.side_effect = lambda ids, _: [
        SimpleNamespace(id=tag_id) for tag_id in ids
    ]
    return service


def build_chain(length):
    groups = [build_group()]
    for _ in range(length - 1):
        groups.append(build_group(parent=groups[-1]))
    return groups


# ---- Inheritance and overlap rules -------------------------------------------


def test_effective_tags_inherit_from_every_ancestor_root_first():
    health, mother = uuid4(), uuid4()
    root, child = uuid4(), uuid4()
    parent_of = {root: None, child: root}
    own = {root: [health], child: [mother, health]}

    assert effective_tag_ids(child, parent_of, own) == [health, mother]
    assert effective_tag_ids(root, parent_of, own) == [health]


def test_parent_and_child_matching_together_is_not_an_overlap():
    root, child = uuid4(), uuid4()
    parent_of = {root: None, child: root}

    assert most_specific_groups([root, child], parent_of) == [child]


def test_siblings_matching_together_are_an_overlap():
    root, mother, personal = uuid4(), uuid4(), uuid4()
    parent_of = {root: None, mother: root, personal: root}

    assert most_specific_groups([root, mother, personal], parent_of) == [
        mother,
        personal,
    ]


# ---- Create / update rules ---------------------------------------------------


def test_create_rejects_a_parent_the_user_does_not_own():
    service = build_service()

    with pytest.raises(ValidationError) as error:
        service.create_group(
            TagGroupCreate(name="Mother", tag_ids=[uuid4()], parent_id=uuid4()),
            uuid4(),
        )

    assert error.value.error_code == "INVALID_TAG_GROUP_PARENT"
    service.repository.save.assert_not_called()


def test_create_rejects_nesting_deeper_than_the_limit():
    chain = build_chain(MAX_TAG_GROUP_DEPTH)
    service = build_service(chain)

    with pytest.raises(ValidationError) as error:
        service.create_group(
            TagGroupCreate(name="Too deep", tag_ids=[uuid4()], parent_id=chain[-1].id),
            uuid4(),
        )

    assert error.value.error_code == "TAG_GROUP_DEPTH_EXCEEDED"


def test_update_rejects_moving_a_group_under_its_own_descendant():
    root, child, grandchild = build_chain(3)
    service = build_service([root, child, grandchild])

    with pytest.raises(ValidationError) as error:
        service.update_group(root.id, TagGroupUpdate(parent_id=grandchild.id), uuid4())

    assert error.value.error_code == "TAG_GROUP_CYCLE"
    assert root.parent_id is None


def test_update_rejects_making_a_group_its_own_parent():
    group = build_group()
    service = build_service([group])

    with pytest.raises(ValidationError) as error:
        service.update_group(group.id, TagGroupUpdate(parent_id=group.id), uuid4())

    assert error.value.error_code == "TAG_GROUP_CYCLE"


def test_update_with_null_parent_moves_group_to_the_top_level():
    root, child = build_chain(2)
    service = build_service([root, child])

    result = service.update_group(child.id, TagGroupUpdate(parent_id=None), uuid4())

    assert result.parent_id is None


def test_update_rejects_a_move_that_pushes_the_subtree_too_deep():
    deep_chain = build_chain(MAX_TAG_GROUP_DEPTH - 1)
    moving_root, moving_child = build_chain(2)
    service = build_service([*deep_chain, moving_root, moving_child])

    with pytest.raises(ValidationError) as error:
        service.update_group(
            moving_root.id, TagGroupUpdate(parent_id=deep_chain[-1].id), uuid4()
        )

    assert error.value.error_code == "TAG_GROUP_DEPTH_EXCEEDED"


def test_update_without_tag_ids_keeps_tags_and_skips_validation():
    group = build_group()
    original_tags = group.tags
    service = build_service([group])

    result = service.update_group(group.id, TagGroupUpdate(name="Renamed"), uuid4())

    assert result.tags is original_tags
    assert result.name == "Renamed"
    service.tag_service.validate_tag_assignment.assert_not_called()


# ---- Request validation ------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Health", "tag_ids": []},
        {"name": "   ", "tag_ids": ["00000000-0000-0000-0000-000000000001"]},
        {
            "name": "Health",
            "tag_ids": [
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000001",
            ],
        },
    ],
    ids=["no-tags", "blank-name", "duplicate-tags"],
)
def test_create_payload_validation(payload):
    with pytest.raises(PydanticValidationError):
        TagGroupCreate(**payload)


@pytest.mark.parametrize("field", ["name", "tag_ids"])
def test_update_payload_rejects_null_for_required_fields(field):
    with pytest.raises(PydanticValidationError):
        TagGroupUpdate(**{field: None})


# ---- Reporting ---------------------------------------------------------------


def test_summary_never_matches_everything_for_a_group_without_tags():
    group = build_group(tag_ids=[])
    group.tags = []
    service = build_service([group])

    [item] = service.get_summary(uuid4())

    assert (item.total, item.count) == (Decimal("0"), 0)
    service.repository.sum_transactions_with_all_tags.assert_not_called()


def test_overlaps_report_siblings_but_not_parent_child_pairs():
    health, mother, personal = uuid4(), uuid4(), uuid4()
    root = build_group(tag_ids=[health])
    mother_group = build_group(parent=root, tag_ids=[mother])
    personal_group = build_group(parent=root, tag_ids=[personal])
    service = build_service([root, mother_group, personal_group])
    only_mother = (
        uuid4(),
        "Doctor",
        Decimal("50"),
        datetime.utcnow(),
        [health, mother],
    )
    shared = (
        uuid4(),
        "Pharmacy",
        Decimal("100"),
        datetime.utcnow(),
        [health, mother, personal],
    )
    service.repository.list_transactions_with_any_tag.return_value = [
        only_mother,
        shared,
    ]

    [overlap] = service.get_overlaps(uuid4())

    assert overlap.transaction_id == shared[0]
    assert overlap.group_ids == [mother_group.id, personal_group.id]
