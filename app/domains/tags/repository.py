from typing import List, Optional, Sequence
from uuid import UUID

from sqlalchemy import asc, func
from sqlalchemy.orm import Session, joinedload

from app.domains.tags.models import (
    Tag,
    TagDimension,
    installment_plan_tags,
    subscription_tags,
    transaction_tags,
)


class TagRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_dimension(self, dimension: TagDimension) -> TagDimension:
        self.db.add(dimension)
        self.db.commit()
        self.db.refresh(dimension)
        return dimension

    def get_dimension(
        self, dimension_id: UUID, user_id: UUID
    ) -> Optional[TagDimension]:
        return (
            self.db.query(TagDimension)
            .filter(
                TagDimension.id == dimension_id,
                TagDimension.user_id == user_id,
            )
            .first()
        )

    def get_dimension_by_normalized_name(
        self, normalized_name: str, user_id: UUID
    ) -> Optional[TagDimension]:
        return (
            self.db.query(TagDimension)
            .filter(
                TagDimension.user_id == user_id,
                TagDimension.normalized_name == normalized_name,
            )
            .first()
        )

    def list_dimensions(
        self, user_id: UUID, include_inactive: bool = False
    ) -> List[TagDimension]:
        query = self.db.query(TagDimension).filter(TagDimension.user_id == user_id)
        if not include_inactive:
            query = query.filter(TagDimension.is_active.is_(True))
        return query.order_by(
            asc(TagDimension.display_order), asc(TagDimension.name)
        ).all()

    def save_dimension(self, dimension: TagDimension) -> TagDimension:
        self.db.commit()
        self.db.refresh(dimension)
        return dimension

    def dimension_has_active_tags(self, dimension_id: UUID) -> bool:
        return (
            self.db.query(Tag.id)
            .filter(Tag.dimension_id == dimension_id, Tag.is_active.is_(True))
            .first()
            is not None
        )

    def dimension_has_assignment_conflicts(self, dimension_id: UUID) -> bool:
        associations = (
            (transaction_tags, transaction_tags.c.transaction_id),
            (subscription_tags, subscription_tags.c.subscription_id),
            (installment_plan_tags, installment_plan_tags.c.installment_plan_id),
        )
        for association, entity_column in associations:
            conflict = (
                self.db.query(entity_column)
                .select_from(association)
                .join(Tag, association.c.tag_id == Tag.id)
                .filter(
                    Tag.dimension_id == dimension_id,
                    Tag.is_active.is_(True),
                )
                .group_by(entity_column)
                .having(func.count(Tag.id) > 1)
                .first()
            )
            if conflict is not None:
                return True
        return False

    def create_tag(self, tag: Tag) -> Tag:
        self.db.add(tag)
        self.db.commit()
        return self.get_tag(tag.id, tag.user_id)  # type: ignore[return-value]

    def get_tag(self, tag_id: UUID, user_id: UUID) -> Optional[Tag]:
        return (
            self.db.query(Tag)
            .options(joinedload(Tag.dimension))
            .filter(Tag.id == tag_id, Tag.user_id == user_id)
            .first()
        )

    def get_tag_by_normalized_name(
        self, normalized_name: str, user_id: UUID
    ) -> Optional[Tag]:
        return (
            self.db.query(Tag)
            .options(joinedload(Tag.dimension))
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
        query = (
            self.db.query(Tag)
            .options(joinedload(Tag.dimension))
            .filter(Tag.id.in_(tag_ids), Tag.user_id == user_id)
        )
        if active_only:
            query = query.filter(Tag.is_active.is_(True))
        return query.all()

    def list_tags(
        self,
        user_id: UUID,
        dimension_id: Optional[UUID] = None,
        include_inactive: bool = False,
    ) -> List[Tag]:
        query = (
            self.db.query(Tag)
            .options(joinedload(Tag.dimension))
            .filter(Tag.user_id == user_id)
        )
        if dimension_id is not None:
            query = query.filter(Tag.dimension_id == dimension_id)
        if not include_inactive:
            query = query.filter(Tag.is_active.is_(True))
        return query.order_by(asc(Tag.display_order), asc(Tag.name)).all()

    def save_tag(self, tag: Tag) -> Tag:
        self.db.commit()
        return self.get_tag(tag.id, tag.user_id)  # type: ignore[return-value]

    def tag_move_has_conflicts(self, tag_id: UUID, dimension_id: UUID) -> bool:
        associations = (
            (transaction_tags, transaction_tags.c.transaction_id),
            (subscription_tags, subscription_tags.c.subscription_id),
            (installment_plan_tags, installment_plan_tags.c.installment_plan_id),
        )
        for association, entity_column in associations:
            other = association.alias("other_assignment")
            conflict = (
                self.db.query(entity_column)
                .select_from(association)
                .join(other, other.c[entity_column.name] == entity_column)
                .join(Tag, other.c.tag_id == Tag.id)
                .filter(
                    association.c.tag_id == tag_id,
                    other.c.tag_id != tag_id,
                    Tag.dimension_id == dimension_id,
                    Tag.is_active.is_(True),
                )
                .first()
            )
            if conflict is not None:
                return True
        return False

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
