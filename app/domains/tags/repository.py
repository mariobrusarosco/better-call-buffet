from typing import List, Optional, Sequence
from uuid import UUID

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, undefer

from app.domains.tags.constants import TagSort
from app.domains.tags.models import Tag


class TagRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_tag(self, tag: Tag) -> Tag:
        self.db.add(tag)
        self.db.commit()
        return self.get_tag(tag.id, tag.user_id)  # type: ignore[return-value]

    def get_tag(self, tag_id: UUID, user_id: UUID) -> Optional[Tag]:
        return (
            self.db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == user_id).first()
        )

    def get_tag_by_normalized_name(
        self, normalized_name: str, user_id: UUID
    ) -> Optional[Tag]:
        return (
            self.db.query(Tag)
            .filter(
                Tag.user_id == user_id,
                Tag.normalized_name == normalized_name,
            )
            .first()
        )

    def get_tags_by_ids(
        self,
        tag_ids: Sequence[UUID],
        user_id: UUID,
        active_only: bool = False,
    ) -> List[Tag]:
        if not tag_ids:
            return []
        query = self.db.query(Tag).filter(Tag.id.in_(tag_ids), Tag.user_id == user_id)
        if active_only:
            query = query.filter(Tag.is_active.is_(True))
        return query.all()

    def list_tags(
        self,
        user_id: UUID,
        include_inactive: bool = False,
        search: Optional[str] = None,
        sort: TagSort = TagSort.DISPLAY_ORDER,
        limit: Optional[int] = None,
    ) -> List[Tag]:
        query = (
            self.db.query(Tag)
            .options(undefer(Tag.usage_count))
            .filter(Tag.user_id == user_id)
        )
        if not include_inactive:
            query = query.filter(Tag.is_active.is_(True))
        if search:
            # `search` arrives normalized; autoescape keeps % and _ literal.
            query = query.filter(Tag.normalized_name.contains(search, autoescape=True))

        if sort == TagSort.USAGE:
            query = query.order_by(desc(Tag.usage_count), asc(Tag.name))
        else:
            query = query.order_by(asc(Tag.display_order), asc(Tag.name))

        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def save_tag(self, tag: Tag) -> Tag:
        self.db.commit()
        return self.get_tag(tag.id, tag.user_id)  # type: ignore[return-value]

    def find_or_create_tag(self, user_id: UUID, name: str) -> Tag:
        normalized_name = name.strip().casefold()
        existing = self.get_tag_by_normalized_name(normalized_name, user_id)
        if existing:
            return existing
        tag = Tag(
            user_id=user_id,
            name=name.strip(),
            normalized_name=normalized_name,
            is_active=True,
        )
        self.db.add(tag)
        self.db.flush()
        return tag
