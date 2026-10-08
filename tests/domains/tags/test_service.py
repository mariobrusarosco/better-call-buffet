from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.error_handlers import ValidationError
from app.domains.tags.constants import MAX_TAGS_PER_ENTITY, TagSelectionMode
from app.domains.tags.service import TagService


def build_service():
    service = TagService(MagicMock())
    service.repository = MagicMock()
    return service


def build_tag(tag_id, dimension=None):
    return SimpleNamespace(
        id=tag_id,
        dimension_id=dimension.id if dimension else None,
        dimension=dimension,
    )


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


def test_assignment_rejects_two_tags_from_a_single_select_dimension():
    service = build_service()
    dimension = SimpleNamespace(
        id=uuid4(), selection_mode=TagSelectionMode.SINGLE.value
    )
    tag_ids = [uuid4(), uuid4()]
    service.repository.get_tags_by_ids.return_value = [
        build_tag(tag_ids[0], dimension),
        build_tag(tag_ids[1], dimension),
    ]

    with pytest.raises(ValidationError) as error:
        service.validate_tag_assignment(tag_ids, uuid4())

    assert error.value.error_code == "TAG_DIMENSION_ASSIGNMENT_CONFLICT"


def test_assignment_allows_health_and_mother_from_different_dimensions():
    service = build_service()
    topic = SimpleNamespace(id=uuid4(), selection_mode=TagSelectionMode.SINGLE.value)
    person = SimpleNamespace(id=uuid4(), selection_mode=TagSelectionMode.SINGLE.value)
    tag_ids = [uuid4(), uuid4()]
    tags = [build_tag(tag_ids[0], topic), build_tag(tag_ids[1], person)]
    service.repository.get_tags_by_ids.return_value = tags

    assert service.validate_tag_assignment(tag_ids, uuid4()) == tags
