import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Set
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.domains.cashflow.views.constants import (
    MAX_GROUP_NAME_LENGTH,
    MAX_GROUPS_PER_VIEW,
    MAX_TAGS_PER_GROUP,
    MAX_VIEW_NAME_LENGTH,
    GroupMatch,
)
from app.domains.cashflow.views.models import (
    CashflowView,
    CashflowViewGroup,
    CashflowViewGroupTag,
)
from app.domains.cashflow.views.repository import CashflowViewRepository, ReportFilters
from app.domains.cashflow.views.schemas import (
    CashflowTransactionItem,
    CashflowTransactionListResponse,
    CashflowViewCreate,
    CashflowViewGroupCreate,
    CashflowViewGroupSummary,
    CashflowViewOverlapItem,
    CashflowViewSummaryResponse,
    CashflowViewUngroupedSummary,
    CashflowViewUpdate,
)
from app.domains.tags.repository import TagRepository
from app.domains.transactions.constants import MovementType
from app.domains.transactions.models import Transaction
from app.domains.transactions.schemas import TransactionListMeta

CENTS = Decimal("0.01")
NOTHING = (Decimal("0"), 0)


def to_amount(value: Decimal) -> Decimal:
    """How every amount leaves this API: positive, two decimal places, so an
    empty total reads "0.00", not "0". Amounts are stored positive already;
    abs() keeps the contract even if one slips through."""
    return abs(Decimal(value)).quantize(CENTS)


def leaves_of(groups: Sequence[CashflowViewGroup]) -> List[CashflowViewGroup]:
    """The groups that hold tags, in display order: each group without
    sub-groups, or the sub-groups of one that has them. These are the only
    groups that match transactions directly."""
    leaves: List[CashflowViewGroup] = []
    for group in groups:
        leaves.extend(group.groups or [group])
    return leaves


class CashflowViewService:
    def __init__(self, db: Session):
        self.repository = CashflowViewRepository(db)
        self.tag_repository = TagRepository(db)

    # ---- CRUD -----------------------------------------------------------------

    def list_views(self, user_id: UUID) -> List[CashflowView]:
        return self.repository.list_views(user_id)

    def get_view(self, view_id: UUID, user_id: UUID) -> CashflowView:
        view = self.repository.get_view(view_id, user_id)
        if not view:
            raise NotFoundError(
                message="Cashflow view not found",
                error_code="CASHFLOW_VIEW_NOT_FOUND",
            )
        return view

    def create_view(self, data: CashflowViewCreate, user_id: UUID) -> CashflowView:
        # Known up front: sub-groups carry the view id too, and they are not
        # in view.groups for the ORM to fill it in.
        view_id = uuid.uuid4()
        view = CashflowView(
            id=view_id,
            user_id=user_id,
            name=self._clean_view_name(data.name),
            display_order=data.display_order,
            groups=self._build_groups(data.groups, view_id, user_id),
        )
        return self.repository.save_view(view)

    def update_view(
        self, view_id: UUID, data: CashflowViewUpdate, user_id: UUID
    ) -> CashflowView:
        view = self.get_view(view_id, user_id)
        fields = data.model_fields_set

        if "name" in fields:
            view.name = self._clean_view_name(data.name)
        if "groups" in fields and data.groups is not None:
            # Wholesale replace: old groups are deleted (delete-orphan, and
            # their sub-groups by cascade) and the new ones get fresh ids.
            view.groups = self._build_groups(data.groups, view.id, user_id)
        if "display_order" in fields and data.display_order is not None:
            view.display_order = data.display_order

        # onupdate only fires when a column of this row changes; a groups-only
        # edit touches other tables, so stamp it explicitly.
        view.updated_at = datetime.utcnow()
        return self.repository.save_view(view)

    def delete_view(self, view_id: UUID, user_id: UUID) -> None:
        self.repository.delete_view(self.get_view(view_id, user_id))

    # ---- Reporting ------------------------------------------------------------
    # Groups that hold tags match transactions carrying ANY or ALL of their
    # tags, per their match. A parent matches what any of its sub-groups
    # match. Every group counts each transaction once. "Ungrouped" is
    # everything in scope that no group matches.

    def get_summary(
        self,
        view_id: UUID,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        movement_type: MovementType = MovementType.EXPENSE,
    ) -> CashflowViewSummaryResponse:
        """Every group and sub-group of the view (zero when nothing matches),
        plus what fell outside all of them."""
        view = self.get_view(view_id, user_id)
        leaf_ids = [leaf.id for leaf in leaves_of(view.groups)]
        filters = ReportFilters(user_id, date_from, date_to, movement_type.value)

        totals = self.repository.totals_by_group(leaf_ids, filters)
        ungrouped_total, ungrouped_count = self.repository.totals_ungrouped(
            leaf_ids, filters
        )

        def summarize(group: CashflowViewGroup) -> CashflowViewGroupSummary:
            total, count = totals.get(group.id, NOTHING)
            return CashflowViewGroupSummary(
                group_id=group.id,
                total=to_amount(total),
                count=count,
                groups=[summarize(sub_group) for sub_group in group.groups],
            )

        return CashflowViewSummaryResponse(
            groups=[summarize(group) for group in view.groups],
            ungrouped=CashflowViewUngroupedSummary(
                total=to_amount(ungrouped_total), count=ungrouped_count
            ),
        )

    def get_overlaps(
        self,
        view_id: UUID,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        movement_type: MovementType = MovementType.EXPENSE,
    ) -> List[CashflowViewOverlapItem]:
        """Transactions that land in two or more groups holding tags, newest
        first. A parent is never compared with its own sub-groups (it always
        shares their transactions). group_ids follow the view's order."""
        view = self.get_view(view_id, user_id)
        leaf_order = {
            leaf.id: index for index, leaf in enumerate(leaves_of(view.groups))
        }
        filters = ReportFilters(user_id, date_from, date_to, movement_type.value)

        # Rows arrive newest first, one per (leaf, transaction); dicts keep
        # that order.
        by_transaction: Dict[UUID, CashflowViewOverlapItem] = {}
        for (
            leaf_id,
            transaction_id,
            description,
            amount,
            when,
        ) in self.repository.list_leaf_matches(list(leaf_order), filters):
            item = by_transaction.setdefault(
                transaction_id,
                CashflowViewOverlapItem(
                    transaction_id=transaction_id,
                    description=description,
                    amount=to_amount(amount),
                    date=when.date(),
                    group_ids=[],
                ),
            )
            item.group_ids.append(leaf_id)

        overlaps = [item for item in by_transaction.values() if len(item.group_ids) > 1]
        for item in overlaps:
            item.group_ids.sort(key=leaf_order.__getitem__)
        return overlaps

    def list_group_transactions(
        self,
        view_id: UUID,
        group_id: UUID,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        movement_type: MovementType = MovementType.EXPENSE,
        page: int = 1,
        per_page: int = 20,
    ) -> CashflowTransactionListResponse:
        """The transactions behind a group's summary total, newest first. For
        a parent: everything its sub-groups match, each once."""
        view = self.get_view(view_id, user_id)
        group = self._find_group(view, group_id)
        filters = ReportFilters(user_id, date_from, date_to, movement_type.value)

        transactions, total = self.repository.list_matching_transactions(
            [leaf.id for leaf in leaves_of([group])], filters, page, per_page
        )
        return self._transaction_page(transactions, total, page, per_page)

    def list_ungrouped_transactions(
        self,
        view_id: UUID,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        movement_type: MovementType = MovementType.EXPENSE,
        page: int = 1,
        per_page: int = 20,
    ) -> CashflowTransactionListResponse:
        """The transactions behind the summary's ungrouped total, newest
        first."""
        view = self.get_view(view_id, user_id)
        filters = ReportFilters(user_id, date_from, date_to, movement_type.value)

        transactions, total = self.repository.list_ungrouped_transactions(
            [leaf.id for leaf in leaves_of(view.groups)], filters, page, per_page
        )
        return self._transaction_page(transactions, total, page, per_page)

    @staticmethod
    def _find_group(view: CashflowView, group_id: UUID) -> CashflowViewGroup:
        for group in view.groups:
            for candidate in (group, *group.groups):
                if candidate.id == group_id:
                    return candidate
        raise NotFoundError(
            message="Cashflow view group not found",
            error_code="CASHFLOW_VIEW_GROUP_NOT_FOUND",
        )

    @staticmethod
    def _transaction_page(
        transactions: Sequence[Transaction], total: int, page: int, per_page: int
    ) -> CashflowTransactionListResponse:
        return CashflowTransactionListResponse(
            data=[
                CashflowTransactionItem(
                    id=transaction.id,
                    date=transaction.date.date(),
                    description=transaction.description,
                    amount=to_amount(transaction.amount),
                    account=transaction.account,
                    credit_card=transaction.credit_card,
                )
                for transaction in transactions
            ],
            meta=TransactionListMeta(
                total=total,
                page=page,
                per_page=per_page,
                has_next=page * per_page < total,
                has_previous=page > 1,
            ),
        )

    # ---- Validation and building ------------------------------------------------
    # Raised as ValidationError (422) with messages the frontend shows as-is.

    @staticmethod
    def _clean_view_name(name: Optional[str]) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValidationError(
                message="View name is required.",
                error_code="CASHFLOW_VIEW_NAME_REQUIRED",
            )
        if len(cleaned) > MAX_VIEW_NAME_LENGTH:
            raise ValidationError(
                message=f"View name must be at most {MAX_VIEW_NAME_LENGTH} characters.",
                error_code="CASHFLOW_VIEW_NAME_TOO_LONG",
            )
        return cleaned

    def _build_groups(
        self,
        groups_in: Sequence[CashflowViewGroupCreate],
        view_id: UUID,
        user_id: UUID,
    ) -> List[CashflowViewGroup]:
        """The view's group tree, validated, ready to save."""
        every_group_in = [
            group_in
            for top_level in groups_in
            for group_in in (top_level, *top_level.groups)
        ]
        if len(every_group_in) > MAX_GROUPS_PER_VIEW:
            raise ValidationError(
                message=(
                    f"A view can have at most {MAX_GROUPS_PER_VIEW} groups, "
                    "counting sub-groups."
                ),
                error_code="CASHFLOW_VIEW_TOO_MANY_GROUPS",
            )

        groups = [
            self._build_group(group_in, position, view_id, is_sub_group=False)
            for position, group_in in enumerate(groups_in)
        ]
        self._check_tags_usable(
            {tag_id for group_in in every_group_in for tag_id in group_in.tag_ids},
            user_id,
        )
        return groups

    def _build_group(
        self,
        group_in: CashflowViewGroupCreate,
        position: int,
        view_id: UUID,
        is_sub_group: bool,
    ) -> CashflowViewGroup:
        label = "Sub-group" if is_sub_group else "Group"
        name = self._clean_group_name(label, group_in.name)

        if group_in.groups:
            if is_sub_group:
                raise ValidationError(
                    message=f'Sub-group "{name}" can\'t hold sub-groups.',
                    error_code="CASHFLOW_GROUP_TOO_DEEP",
                )
            if group_in.tag_ids:
                raise ValidationError(
                    message=f'Group "{name}" can hold tags or sub-groups, not both.',
                    error_code="CASHFLOW_GROUP_TAGS_AND_SUBGROUPS",
                )
            # A parent matches through its sub-groups; any match sent for it
            # is ignored.
            return CashflowViewGroup(
                view_id=view_id,
                name=name,
                position=position,
                match=None,
                groups=[
                    self._build_group(sub_group_in, index, view_id, is_sub_group=True)
                    for index, sub_group_in in enumerate(group_in.groups)
                ],
            )

        if not group_in.tag_ids:
            raise ValidationError(
                message=(
                    f'Sub-group "{name}" needs at least one tag.'
                    if is_sub_group
                    else f'Group "{name}" needs tags or sub-groups.'
                ),
                error_code="CASHFLOW_GROUP_NEEDS_TAGS_OR_SUBGROUPS",
            )
        match = self._clean_match(label, name, group_in.match)
        self._check_group_tags(label, name, group_in.tag_ids)
        return CashflowViewGroup(
            view_id=view_id,
            name=name,
            position=position,
            match=match,
            tag_links=[
                CashflowViewGroupTag(tag_id=tag_id, position=tag_position)
                for tag_position, tag_id in enumerate(group_in.tag_ids)
            ],
        )

    @staticmethod
    def _clean_group_name(label: str, name: Optional[str]) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValidationError(
                message=f"Every {label.lower()} needs a name.",
                error_code="CASHFLOW_GROUP_NAME_REQUIRED",
            )
        if len(cleaned) > MAX_GROUP_NAME_LENGTH:
            raise ValidationError(
                message=f"{label} names must be at most {MAX_GROUP_NAME_LENGTH} characters.",
                error_code="CASHFLOW_GROUP_NAME_TOO_LONG",
            )
        return cleaned

    @staticmethod
    def _clean_match(label: str, name: str, match: Optional[str]) -> str:
        if match is None:
            return GroupMatch.ANY.value
        try:
            return GroupMatch(match).value
        except ValueError:
            raise ValidationError(
                message=f'{label} "{name}" must match "any" or "all" of its tags.',
                error_code="CASHFLOW_GROUP_INVALID_MATCH",
            )

    @staticmethod
    def _check_group_tags(label: str, name: str, tag_ids: Sequence[UUID]) -> None:
        if len(tag_ids) > MAX_TAGS_PER_GROUP:
            raise ValidationError(
                message=f'{label} "{name}" can have at most {MAX_TAGS_PER_GROUP} tags.',
                error_code="CASHFLOW_GROUP_TOO_MANY_TAGS",
            )
        # Within one group only; the same tag may appear in other groups.
        if len(set(tag_ids)) != len(tag_ids):
            raise ValidationError(
                message=f'{label} "{name}" has the same tag more than once.',
                error_code="CASHFLOW_GROUP_DUPLICATE_TAG",
            )

    def _check_tags_usable(self, tag_ids: Set[UUID], user_id: UUID) -> None:
        """Every tag must exist, be active and belong to the user. One query
        for the whole view, not one per group."""
        found = self.tag_repository.get_tags_by_ids(
            list(tag_ids), user_id, active_only=True
        )
        if len(found) != len(tag_ids):
            raise ValidationError(
                message="Some tags no longer exist or are inactive. Refresh and try again.",
                error_code="CASHFLOW_GROUP_INVALID_TAGS",
            )
