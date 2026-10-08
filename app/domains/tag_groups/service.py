from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.domains.tag_groups.constants import MAX_TAG_GROUP_DEPTH
from app.domains.tag_groups.models import TagGroup
from app.domains.tag_groups.repository import TagGroupRepository
from app.domains.tag_groups.schemas import (
    TagGroupCreate,
    TagGroupOverlapItem,
    TagGroupResponse,
    TagGroupSummaryItem,
    TagGroupUpdate,
)
from app.domains.tags.service import TagService
from app.domains.transactions.constants import MovementType


def ancestor_ids(group_id: UUID, parent_of: Dict[UUID, Optional[UUID]]) -> List[UUID]:
    """Ancestors from the root down to the direct parent."""
    chain: List[UUID] = []
    seen = {group_id}
    current = parent_of.get(group_id)
    while current is not None and current not in seen:
        chain.append(current)
        seen.add(current)
        current = parent_of.get(current)
    chain.reverse()
    return chain


def effective_tag_ids(
    group_id: UUID,
    parent_of: Dict[UUID, Optional[UUID]],
    own_tag_ids: Dict[UUID, List[UUID]],
) -> List[UUID]:
    """Inherited tags first (root down), then the group's own, without repeats."""
    result: List[UUID] = []
    for member in [*ancestor_ids(group_id, parent_of), group_id]:
        for tag_id in own_tag_ids.get(member, []):
            if tag_id not in result:
                result.append(tag_id)
    return result


def most_specific_groups(
    matched: Sequence[UUID], parent_of: Dict[UUID, Optional[UUID]]
) -> List[UUID]:
    """Drop every matched group that has a matched descendant.

    A child always matches wherever its parent does, so that pair is not an
    overlap. What remains are groups with no ancestor/descendant link between
    them: two or more of those means the transaction really is shared.
    """
    implied = {
        ancestor
        for group_id in matched
        for ancestor in ancestor_ids(group_id, parent_of)
    }
    return [group_id for group_id in matched if group_id not in implied]


class TagGroupService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = TagGroupRepository(db)
        self.tag_service = TagService(db)

    # ---- CRUD ---------------------------------------------------------------

    def list_groups(self, user_id: UUID) -> List[TagGroup]:
        return self.repository.list_groups(user_id)

    def get_group(self, group_id: UUID, user_id: UUID) -> TagGroup:
        group = self.repository.get_group(group_id, user_id)
        if not group:
            raise NotFoundError(
                message="Tag group not found", error_code="TAG_GROUP_NOT_FOUND"
            )
        return group

    def create_group(self, data: TagGroupCreate, user_id: UUID) -> TagGroup:
        tags = self.tag_service.validate_tag_assignment(data.tag_ids, user_id)
        parent_of = self._parent_map(user_id)
        if data.parent_id is not None:
            self._ensure_parent_exists(data.parent_id, parent_of)
            depth = len(ancestor_ids(data.parent_id, parent_of)) + 2
            self._ensure_depth(depth)

        group = TagGroup(
            user_id=user_id,
            parent_id=data.parent_id,
            name=data.name,
            display_order=data.display_order,
            tags=tags,
        )
        return self.repository.save(group)

    def update_group(
        self, group_id: UUID, data: TagGroupUpdate, user_id: UUID
    ) -> TagGroup:
        group = self.get_group(group_id, user_id)
        fields = data.model_fields_set

        if "parent_id" in fields and data.parent_id != group.parent_id:
            self._validate_move(group.id, data.parent_id, self._parent_map(user_id))
            group.parent_id = data.parent_id
        if "tag_ids" in fields and data.tag_ids is not None:
            group.tags = self.tag_service.validate_tag_assignment(data.tag_ids, user_id)
        if "name" in fields and data.name is not None:
            group.name = data.name
        if "display_order" in fields and data.display_order is not None:
            group.display_order = data.display_order

        return self.repository.save(group)

    def delete_group(self, group_id: UUID, user_id: UUID) -> None:
        self.repository.delete(self.get_group(group_id, user_id))

    # ---- Responses ----------------------------------------------------------

    def build_responses(self, groups: Sequence[TagGroup]) -> List[TagGroupResponse]:
        parent_of = {group.id: group.parent_id for group in groups}
        own_tags = {group.id: [tag.id for tag in group.tags] for group in groups}
        return [
            TagGroupResponse(
                id=group.id,
                name=group.name,
                parent_id=group.parent_id,
                tag_ids=own_tags[group.id],
                effective_tag_ids=effective_tag_ids(group.id, parent_of, own_tags),
                display_order=group.display_order,
                created_at=group.created_at,
                updated_at=group.updated_at,
            )
            for group in groups
        ]

    def get_group_response(self, group_id: UUID, user_id: UUID) -> TagGroupResponse:
        # effective_tag_ids needs the ancestors, so build from the full list.
        self.get_group(group_id, user_id)
        responses = self.build_responses(self.list_groups(user_id))
        return next(response for response in responses if response.id == group_id)

    # ---- Reporting ----------------------------------------------------------

    def get_summary(
        self,
        user_id: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        movement_type: MovementType = MovementType.EXPENSE,
    ) -> List[TagGroupSummaryItem]:
        summary = []
        for group in self.build_responses(self.list_groups(user_id)):
            if not group.effective_tag_ids:
                # Without tags the ALL-of filter would match every transaction.
                summary.append(
                    TagGroupSummaryItem(group_id=group.id, total=Decimal("0"), count=0)
                )
                continue
            total, count = self.repository.sum_transactions_with_all_tags(
                user_id,
                group.effective_tag_ids,
                date_from,
                date_to,
                movement_type.value,
            )
            summary.append(
                TagGroupSummaryItem(group_id=group.id, total=total, count=count)
            )
        return summary

    def get_overlaps(
        self,
        user_id: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        movement_type: MovementType = MovementType.EXPENSE,
    ) -> List[TagGroupOverlapItem]:
        groups = self.build_responses(self.list_groups(user_id))
        parent_of = {group.id: group.parent_id for group in groups}
        required = {group.id: set(group.effective_tag_ids) for group in groups}
        all_tag_ids = sorted({tag for tags in required.values() for tag in tags})

        overlaps = []
        for row in self.repository.list_transactions_with_any_tag(
            user_id, all_tag_ids, date_from, date_to, movement_type.value
        ):
            transaction_id, description, amount, date, tag_ids = row
            carried = set(tag_ids)
            matched = [
                group.id
                for group in groups
                if required[group.id] and required[group.id] <= carried
            ]
            shared_by = most_specific_groups(matched, parent_of)
            if len(shared_by) >= 2:
                overlaps.append(
                    TagGroupOverlapItem(
                        transaction_id=transaction_id,
                        description=description,
                        amount=amount,
                        date=date,
                        group_ids=shared_by,
                    )
                )
        return overlaps

    # ---- Tree rules ---------------------------------------------------------

    def _parent_map(self, user_id: UUID) -> Dict[UUID, Optional[UUID]]:
        return {group.id: group.parent_id for group in self.list_groups(user_id)}

    @staticmethod
    def _ensure_parent_exists(
        parent_id: UUID, parent_of: Dict[UUID, Optional[UUID]]
    ) -> None:
        # parent_of only holds this user's groups, so this is also the
        # ownership check.
        if parent_id not in parent_of:
            raise ValidationError(
                message="Parent group not found",
                error_code="INVALID_TAG_GROUP_PARENT",
            )

    @staticmethod
    def _ensure_depth(depth: int) -> None:
        if depth > MAX_TAG_GROUP_DEPTH:
            raise ValidationError(
                message=f"Groups cannot be nested more than {MAX_TAG_GROUP_DEPTH} levels",
                error_code="TAG_GROUP_DEPTH_EXCEEDED",
            )

    def _validate_move(
        self,
        group_id: UUID,
        new_parent_id: Optional[UUID],
        parent_of: Dict[UUID, Optional[UUID]],
    ) -> None:
        if new_parent_id is None:
            return
        self._ensure_parent_exists(new_parent_id, parent_of)
        if new_parent_id == group_id or group_id in ancestor_ids(
            new_parent_id, parent_of
        ):
            raise ValidationError(
                message="A group cannot be moved under itself or its own subgroups",
                error_code="TAG_GROUP_CYCLE",
            )

        # The whole subtree moves, so its deepest member sets the new depth.
        children: Dict[UUID, List[UUID]] = {}
        for child_id, parent_id in parent_of.items():
            if parent_id is not None:
                children.setdefault(parent_id, []).append(child_id)

        def subtree_height(node_id: UUID) -> int:
            return 1 + max(
                (subtree_height(child) for child in children.get(node_id, [])),
                default=0,
            )

        new_parent_depth = len(ancestor_ids(new_parent_id, parent_of)) + 1
        self._ensure_depth(new_parent_depth + subtree_height(group_id))
