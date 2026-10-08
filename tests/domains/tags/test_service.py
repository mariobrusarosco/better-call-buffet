from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.error_handlers import ValidationError
from app.domains.tags.constants import MAX_TAGS_PER_ENTITY, TagSort
from app.domains.tags.models import Tag
from app.domains.tags.service import TagService


def build_service():
    service = TagService(MagicMock())
    service.repository = MagicMock()
    return service


def build_tag(tag_id):
    return SimpleNamespace(id=tag_id)


def test_assignment_preserves_requested_tag_order():
    service = build_service()
    user_id = uuid4()
    first_id = uuid4()
    second_id = uuid4()
    first = build_tag(first_id)
    second = build_tag(second_id)
    service.repository.get_tags_by_ids.return_value = [second, first]

    result = service.validate_tag_assignment([first_id, second_id], user_id)

    assert result == [first, second]
    service.repository.get_tags_by_ids.assert_called_once_with(
        [first_id, second_id], user_id, active_only=True
    )


def test_assignment_rejects_more_than_the_tag_cap():
    service = build_service()

    with pytest.raises(ValidationError) as error:
        service.validate_tag_assignment(
            [uuid4() for _ in range(MAX_TAGS_PER_ENTITY + 1)], uuid4()
        )

    assert error.value.error_code == "TAG_LIMIT_EXCEEDED"
    service.repository.get_tags_by_ids.assert_not_called()


def test_assignment_allows_any_combination_of_flat_tags():
    # Formerly rejected by single-select dimensions; tags are flat now.
    service = build_service()
    tag_ids = [uuid4(), uuid4(), uuid4()]
    tags = [build_tag(tag_id) for tag_id in tag_ids]
    service.repository.get_tags_by_ids.return_value = tags

    assert service.validate_tag_assignment(tag_ids, uuid4()) == tags


def test_list_tags_normalizes_the_search_term():
    service = build_service()
    user_id = uuid4()

    service.list_tags(user_id, search="  StReAm ", sort=TagSort.USAGE, limit=10)

    service.repository.list_tags.assert_called_once_with(
        user_id, False, search="stream", sort=TagSort.USAGE, limit=10
    )


def test_list_tags_treats_a_blank_search_as_no_search():
    service = build_service()
    user_id = uuid4()

    service.list_tags(user_id, search="   ")

    service.repository.list_tags.assert_called_once_with(
        user_id, False, search=None, sort=TagSort.DISPLAY_ORDER, limit=None
    )


def test_usage_count_sums_links_from_every_taggable_entity():
    sql = str(Tag.usage_count.expression.compile())

    for association in (
        "transaction_tags",
        "subscription_tags",
        "installment_plan_tags",
    ):
        assert f"{association}.tag_id = tags.id" in sql
