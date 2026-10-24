from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.error_handlers import ValidationError
from app.domains.cashflow.views.constants import MAX_GROUPS_PER_VIEW, MAX_TAGS_PER_GROUP
from app.domains.cashflow.views.schemas import (
    CashflowViewCreate,
    CashflowViewGroupCreate,
    CashflowViewUpdate,
)
from app.domains.cashflow.views.service import CashflowViewService


def build_service(existing_tag_ids=None):
    """Service with the database mocked out. Tags in `existing_tag_ids` count
    as existing, active and owned by the user; any other id does not."""
    service = CashflowViewService(MagicMock())
    service.repository = MagicMock()
    service.repository.save_view.side_effect = lambda view: view
    service.tag_repository = MagicMock()
    known = set(existing_tag_ids or [])
    service.tag_repository.get_tags_by_ids.side_effect = lambda ids, *_, **__: [
        SimpleNamespace(id=tag_id) for tag_id in ids if tag_id in known
    ]
    return service


def group(name="Family", tag_ids=None):
    return CashflowViewGroupCreate(name=name, tag_ids=tag_ids or [])


def message_of(excinfo):
    return excinfo.value.message


def test_create_keeps_group_and_tag_order():
    tags = [uuid4(), uuid4(), uuid4()]
    service = build_service(tags)

    view = service.create_view(
        CashflowViewCreate(
            name="  By person  ",
            groups=[group("Family", [tags[2], tags[0]]), group("Me", [tags[1]])],
        ),
        uuid4(),
    )

    assert view.name == "By person"
    assert [g.name for g in view.groups] == ["Family", "Me"]
    assert [g.position for g in view.groups] == [0, 1]
    assert view.groups[0].tag_ids == [tags[2], tags[0]]


def test_same_tag_may_appear_in_different_groups():
    tag = uuid4()
    service = build_service([tag])

    view = service.create_view(
        CashflowViewCreate(name="View", groups=[group("A", [tag]), group("B", [tag])]),
        uuid4(),
    )

    assert [g.tag_ids for g in view.groups] == [[tag], [tag]]


def test_view_without_groups_is_allowed():
    view = build_service().create_view(CashflowViewCreate(name="Empty"), uuid4())
    assert view.groups == []


@pytest.mark.parametrize(
    "payload, expected_message",
    [
        (dict(name="   "), "View name is required."),
        (dict(name="V", groups=[group(" ", [])]), "Every group needs a name."),
        (dict(name="V", groups=[group("Family", [])]), "needs at least one tag"),
        (
            dict(name="V", groups=[group("Family", [uuid4()] * 2)]),
            "same tag more than once",
        ),
        (
            dict(
                name="V",
                groups=[
                    group("Family", [uuid4()]) for _ in range(MAX_GROUPS_PER_VIEW + 1)
                ],
            ),
            f"at most {MAX_GROUPS_PER_VIEW} groups",
        ),
        (
            dict(
                name="V",
                groups=[
                    group("Family", [uuid4() for _ in range(MAX_TAGS_PER_GROUP + 1)])
                ],
            ),
            f"at most {MAX_TAGS_PER_GROUP} tags",
        ),
    ],
)
def test_create_rejects_invalid_payloads_with_readable_messages(
    payload, expected_message
):
    service = build_service()

    with pytest.raises(ValidationError) as excinfo:
        service.create_view(CashflowViewCreate(**payload), uuid4())

    assert expected_message in message_of(excinfo)
    service.repository.save_view.assert_not_called()


def test_create_rejects_unknown_inactive_or_foreign_tags():
    known = uuid4()
    service = build_service([known])

    with pytest.raises(ValidationError) as excinfo:
        service.create_view(
            CashflowViewCreate(name="V", groups=[group("Family", [known, uuid4()])]),
            uuid4(),
        )

    assert "no longer exist or are inactive" in message_of(excinfo)


def test_tags_are_checked_in_one_query_for_the_whole_view():
    tags = [uuid4(), uuid4()]
    service = build_service(tags)

    service.create_view(
        CashflowViewCreate(name="V", groups=[group("A", tags), group("B", [tags[0]])]),
        uuid4(),
    )

    service.tag_repository.get_tags_by_ids.assert_called_once()
    (tag_ids, _), kwargs = service.tag_repository.get_tags_by_ids.call_args
    assert sorted(tag_ids) == sorted(tags)
    assert kwargs == {"active_only": True}


# ---- PATCH --------------------------------------------------------------------


def existing_view(tag_id):
    view = build_service([tag_id]).create_view(
        CashflowViewCreate(name="Old", groups=[group("Family", [tag_id])]), uuid4()
    )
    view.display_order = 3
    return view


def test_update_changes_only_the_fields_sent():
    tag = uuid4()
    view = existing_view(tag)
    original_groups = view.groups
    service = build_service([tag])
    service.repository.get_view.return_value = view

    service.update_view(view.id, CashflowViewUpdate(name="New"), uuid4())

    assert view.name == "New"
    assert view.display_order == 3
    assert view.groups is original_groups


def test_update_with_groups_replaces_the_whole_list():
    tag, other = uuid4(), uuid4()
    view = existing_view(tag)
    service = build_service([tag, other])
    service.repository.get_view.return_value = view

    service.update_view(
        view.id,
        CashflowViewUpdate(groups=[group("Me", [other]), group("Family", [tag])]),
        uuid4(),
    )

    assert [(g.name, g.tag_ids) for g in view.groups] == [
        ("Me", [other]),
        ("Family", [tag]),
    ]


def test_update_rejects_null_name():
    tag = uuid4()
    service = build_service([tag])
    service.repository.get_view.return_value = existing_view(tag)

    with pytest.raises(ValidationError) as excinfo:
        service.update_view(uuid4(), CashflowViewUpdate(name=None), uuid4())

    assert message_of(excinfo) == "View name is required."
