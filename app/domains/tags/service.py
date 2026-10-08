from typing import List, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.domains.tags.constants import MAX_TAGS_PER_ENTITY, TagSort
from app.domains.tags.models import Tag
from app.domains.tags.repository import TagRepository
from app.domains.tags.schemas import TagCreate, TagUpdate


class TagService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = TagRepository(db)

    @staticmethod
    def normalize_name(name: str) -> str:
        return name.strip().casefold()

    def create_tag(self, data: TagCreate, user_id: UUID) -> Tag:
        normalized_name = self.normalize_name(data.name)
        if self.repository.get_tag_by_normalized_name(normalized_name, user_id):
            raise ValidationError(
                message=f"Tag '{data.name}' already exists",
                error_code="TAG_ALREADY_EXISTS",
            )
        tag = Tag(
            user_id=user_id,
            name=data.name,
            normalized_name=normalized_name,
            display_order=data.display_order,
        )
        return self.repository.create_tag(tag)

    def list_tags(
        self,
        user_id: UUID,
        include_inactive: bool = False,
        search: str | None = None,
        sort: TagSort = TagSort.DISPLAY_ORDER,
        limit: int | None = None,
    ) -> List[Tag]:
        normalized_search = self.normalize_name(search) if search else None
        return self.repository.list_tags(
            user_id,
            include_inactive,
            search=normalized_search or None,
            sort=sort,
            limit=limit,
        )

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

        tags_by_id = {tag.id: tag for tag in tags}
        return [tags_by_id[tag_id] for tag_id in tag_ids]
