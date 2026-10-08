from collections import Counter
from typing import List, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.domains.tags.constants import MAX_TAGS_PER_ENTITY, TagSelectionMode
from app.domains.tags.models import Tag, TagDimension
from app.domains.tags.repository import TagRepository
from app.domains.tags.schemas import (
    TagCreate,
    TagDimensionCreate,
    TagDimensionUpdate,
    TagUpdate,
)


class TagService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = TagRepository(db)

    @staticmethod
    def normalize_name(name: str) -> str:
        return name.strip().casefold()

    def create_dimension(self, data: TagDimensionCreate, user_id: UUID) -> TagDimension:
        normalized_name = self.normalize_name(data.name)
        if self.repository.get_dimension_by_normalized_name(normalized_name, user_id):
            raise ValidationError(
                message=f"Tag dimension '{data.name}' already exists",
                error_code="TAG_DIMENSION_ALREADY_EXISTS",
            )
        dimension = TagDimension(
            user_id=user_id,
            name=data.name,
            normalized_name=normalized_name,
            selection_mode=data.selection_mode.value,
            display_order=data.display_order,
        )
        return self.repository.create_dimension(dimension)

    def list_dimensions(
        self, user_id: UUID, include_inactive: bool = False
    ) -> List[TagDimension]:
        return self.repository.list_dimensions(user_id, include_inactive)

    def get_dimension(self, dimension_id: UUID, user_id: UUID) -> TagDimension:
        dimension = self.repository.get_dimension(dimension_id, user_id)
        if not dimension:
            raise NotFoundError(
                message="Tag dimension not found",
                error_code="TAG_DIMENSION_NOT_FOUND",
            )
        return dimension

    def update_dimension(
        self,
        dimension_id: UUID,
        data: TagDimensionUpdate,
        user_id: UUID,
    ) -> TagDimension:
        dimension = self.get_dimension(dimension_id, user_id)
        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data:
            normalized_name = self.normalize_name(update_data["name"])
            duplicate = self.repository.get_dimension_by_normalized_name(
                normalized_name, user_id
            )
            if duplicate and duplicate.id != dimension.id:
                raise ValidationError(
                    message=f"Tag dimension '{update_data['name']}' already exists",
                    error_code="TAG_DIMENSION_ALREADY_EXISTS",
                )
            dimension.name = update_data["name"]
            dimension.normalized_name = normalized_name

        if "selection_mode" in update_data:
            mode = update_data["selection_mode"]
            mode_value = mode.value if isinstance(mode, TagSelectionMode) else mode
            is_single_mode = mode_value == TagSelectionMode.SINGLE.value
            was_not_single = dimension.selection_mode != TagSelectionMode.SINGLE.value
            if is_single_mode and was_not_single:
                if self.repository.dimension_has_assignment_conflicts(dimension.id):
                    raise ValidationError(
                        message=(
                            "Dimension cannot become single-select while an entity "
                            "has multiple tags from it"
                        ),
                        error_code="TAG_DIMENSION_ASSIGNMENT_CONFLICT",
                    )
            dimension.selection_mode = mode_value

        if "display_order" in update_data:
            dimension.display_order = update_data["display_order"]

        return self.repository.save_dimension(dimension)

    def delete_dimension(self, dimension_id: UUID, user_id: UUID) -> None:
        dimension = self.get_dimension(dimension_id, user_id)
        if self.repository.dimension_has_active_tags(dimension.id):
            raise ValidationError(
                message="Deactivate or move the dimension's tags first",
                error_code="TAG_DIMENSION_NOT_EMPTY",
            )
        dimension.is_active = False
        self.repository.save_dimension(dimension)

    def create_tag(self, data: TagCreate, user_id: UUID) -> Tag:
        normalized_name = self.normalize_name(data.name)
        if self.repository.get_tag_by_normalized_name(normalized_name, user_id):
            raise ValidationError(
                message=f"Tag '{data.name}' already exists",
                error_code="TAG_ALREADY_EXISTS",
            )
        dimension = None
        if data.dimension_id:
            dimension = self.get_dimension(data.dimension_id, user_id)
            if not dimension.is_active:
                raise ValidationError(
                    message="Cannot add a tag to an inactive dimension",
                    error_code="TAG_DIMENSION_INACTIVE",
                )
        tag = Tag(
            user_id=user_id,
            name=data.name,
            normalized_name=normalized_name,
            dimension_id=dimension.id if dimension else None,
            display_order=data.display_order,
        )
        return self.repository.create_tag(tag)

    def list_tags(
        self,
        user_id: UUID,
        dimension_id: UUID | None = None,
        include_inactive: bool = False,
    ) -> List[Tag]:
        if dimension_id is not None:
            self.get_dimension(dimension_id, user_id)
        return self.repository.list_tags(user_id, dimension_id, include_inactive)

    def get_tag(self, tag_id: UUID, user_id: UUID) -> Tag:
        tag = self.repository.get_tag(tag_id, user_id)
        if not tag:
            raise NotFoundError(message="Tag not found", error_code="TAG_NOT_FOUND")
        return tag

    def update_tag(self, tag_id: UUID, data: TagUpdate, user_id: UUID) -> Tag:
        tag = self.get_tag(tag_id, user_id)
        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data:
            normalized_name = self.normalize_name(update_data["name"])
            duplicate = self.repository.get_tag_by_normalized_name(
                normalized_name, user_id
            )
            if duplicate and duplicate.id != tag.id:
                raise ValidationError(
                    message=f"Tag '{update_data['name']}' already exists",
                    error_code="TAG_ALREADY_EXISTS",
                )
            tag.name = update_data["name"]
            tag.normalized_name = normalized_name

        if "dimension_id" in update_data:
            dimension_id = update_data["dimension_id"]
            if dimension_id is not None:
                dimension = self.get_dimension(dimension_id, user_id)
                if not dimension.is_active:
                    raise ValidationError(
                        message="Cannot move a tag to an inactive dimension",
                        error_code="TAG_DIMENSION_INACTIVE",
                    )
                if dimension.selection_mode == TagSelectionMode.SINGLE.value:
                    if self.repository.tag_move_has_conflicts(tag.id, dimension.id):
                        raise ValidationError(
                            message=(
                                "Moving this tag would violate single-select "
                                "assignments"
                            ),
                            error_code="TAG_DIMENSION_ASSIGNMENT_CONFLICT",
                        )
            tag.dimension_id = dimension_id

        if "display_order" in update_data:
            tag.display_order = update_data["display_order"]

        return self.repository.save_tag(tag)

    def delete_tag(self, tag_id: UUID, user_id: UUID) -> None:
        tag = self.get_tag(tag_id, user_id)
        tag.is_active = False
        self.repository.save_tag(tag)

    def validate_tag_assignment(
        self, tag_ids: Sequence[UUID], user_id: UUID
    ) -> List[Tag]:
        if len(tag_ids) > MAX_TAGS_PER_ENTITY:
            raise ValidationError(
                message=f"At most {MAX_TAGS_PER_ENTITY} tags may be assigned",
                error_code="TAG_LIMIT_EXCEEDED",
            )
        if len(set(tag_ids)) != len(tag_ids):
            raise ValidationError(
                message="tag_ids must not contain duplicates",
                error_code="DUPLICATE_TAG_IDS",
            )

        tags = self.repository.get_tags_by_ids(tag_ids, user_id, active_only=True)
        if len(tags) != len(tag_ids):
            raise ValidationError(
                message="One or more tags do not exist, are inactive, or are not owned by the user",
                error_code="INVALID_TAG_ASSIGNMENT",
            )

        single_dimension_ids = []
        for tag in tags:
            if tag.dimension is None:
                continue
            if tag.dimension.selection_mode == TagSelectionMode.SINGLE.value:
                single_dimension_ids.append(tag.dimension_id)
        conflicts = [
            dimension_id
            for dimension_id, count in Counter(single_dimension_ids).items()
            if count > 1
        ]
        if conflicts:
            raise ValidationError(
                message="Only one tag may be selected from a single-select dimension",
                error_code="TAG_DIMENSION_ASSIGNMENT_CONFLICT",
                details={"dimension_ids": [str(value) for value in conflicts]},
            )

        tags_by_id = {tag.id: tag for tag in tags}
        return [tags_by_id[tag_id] for tag_id in tag_ids]
