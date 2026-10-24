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


def to_amount(value: Decimal) -> Decimal:
    """How every amount leaves this API: positive, two decimal places, so an
    empty total reads "0.00", not "0". Amounts are stored positive already;
    abs() keeps the contract even if one slips through."""
    return abs(Decimal(value)).quantize(CENTS)


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
        view = CashflowView(
            user_id=user_id,
            name=self._clean_view_name(data.name),
            display_order=data.display_order,
            groups=self._build_groups(data.groups, user_id),
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
            # Wholesale replace: old groups are deleted (delete-orphan) and
            # the new ones get fresh ids.
            view.groups = self._build_groups(data.groups, user_id)
        if "display_order" in fields and data.display_order is not None:
            view.display_order = data.display_order

        # onupdate only fires when a column of this row changes; a groups-only
        # edit touches other tables, so stamp it explicitly.
        view.updated_at = datetime.utcnow()
        return self.repository.save_view(view)

    def delete_view(self, view_id: UUID, user_id: UUID) -> None:
        self.repository.delete_view(self.get_view(view_id, user_id))

    # ---- Reporting ------------------------------------------------------------
    # A group matches the transactions carrying ALL of its tags, each counted
    # once. "Ungrouped" is everything in scope that matches no group.

    def get_summary(
        self,
        view_id: UUID,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        movement_type: MovementType = MovementType.EXPENSE,
    ) -> CashflowViewSummaryResponse:
        """Every group of the view (zero when nothing matches), plus what fell
        outside all of them."""
        view = self.get_view(view_id, user_id)
        group_ids = [group.id for group in view.groups]
        filters = ReportFilters(user_id, date_from, date_to, movement_type.value)

        by_group = self.repository.totals_by_group(group_ids, filters)
        ungrouped_total, ungrouped_count = self.repository.totals_ungrouped(
            group_ids, filters
        )

        groups = []
        for group in view.groups:
            total, count = by_group.get(group.id, (Decimal("0"), 0))
            groups.append(
                CashflowViewGroupSummary(
                    group_id=group.id, total=to_amount(total), count=count
                )
            )
        return CashflowViewSummaryResponse(
            groups=groups,
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
        """Transactions that land in two or more groups, newest first.
        group_ids follow the view's group order."""
        view = self.get_view(view_id, user_id)
        group_order = {group.id: index for index, group in enumerate(view.groups)}
        filters = ReportFilters(user_id, date_from, date_to, movement_type.value)

        # Rows arrive newest first, one per (group, transaction); dicts keep
        # that order.
        by_transaction: Dict[UUID, CashflowViewOverlapItem] = {}
        for (
            group_id,
            transaction_id,
            description,
            amount,
            when,
        ) in self.repository.list_group_matches(list(group_order), filters):
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
            item.group_ids.append(group_id)

        overlaps = [item for item in by_transaction.values() if len(item.group_ids) > 1]
        for item in overlaps:
            item.group_ids.sort(key=group_order.__getitem__)
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
        """The transactions behind a group's summary total, newest first."""
        view = self.get_view(view_id, user_id)
        if group_id not in {group.id for group in view.groups}:
            raise NotFoundError(
                message="Cashflow view group not found",
                error_code="CASHFLOW_VIEW_GROUP_NOT_FOUND",
            )
        filters = ReportFilters(user_id, date_from, date_to, movement_type.value)

        transactions, total = self.repository.list_group_transactions(
            group_id, filters, page, per_page
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
            [group.id for group in view.groups], filters, page, per_page
        )
        return self._transaction_page(transactions, total, page, per_page)

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

    # ---- Validation -----------------------------------------------------------
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
        self, groups_in: Sequence[CashflowViewGroupCreate], user_id: UUID
    ) -> List[CashflowViewGroup]:
        if len(groups_in) > MAX_GROUPS_PER_VIEW:
            raise ValidationError(
                message=f"A view can have at most {MAX_GROUPS_PER_VIEW} groups.",
                error_code="CASHFLOW_VIEW_TOO_MANY_GROUPS",
            )

        groups = []
        for position, group_in in enumerate(groups_in):
            name = self._clean_group_name(group_in.name)
            self._check_group_tags(name, group_in.tag_ids)
            groups.append(
                CashflowViewGroup(
                    name=name,
                    position=position,
                    tag_links=[
                        CashflowViewGroupTag(tag_id=tag_id, position=tag_position)
                        for tag_position, tag_id in enumerate(group_in.tag_ids)
                    ],
                )
            )

        self._check_tags_usable(
            {tag_id for group_in in groups_in for tag_id in group_in.tag_ids},
            user_id,
        )
        return groups

    @staticmethod
    def _clean_group_name(name: Optional[str]) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValidationError(
                message="Every group needs a name.",
                error_code="CASHFLOW_GROUP_NAME_REQUIRED",
            )
        if len(cleaned) > MAX_GROUP_NAME_LENGTH:
            raise ValidationError(
                message=f"Group names must be at most {MAX_GROUP_NAME_LENGTH} characters.",
                error_code="CASHFLOW_GROUP_NAME_TOO_LONG",
            )
        return cleaned

    @staticmethod
    def _check_group_tags(group_name: str, tag_ids: Sequence[UUID]) -> None:
        if not tag_ids:
            raise ValidationError(
                message=f'Group "{group_name}" needs at least one tag.',
                error_code="CASHFLOW_GROUP_NEEDS_TAGS",
            )
        if len(tag_ids) > MAX_TAGS_PER_GROUP:
            raise ValidationError(
                message=f'Group "{group_name}" can have at most {MAX_TAGS_PER_GROUP} tags.',
                error_code="CASHFLOW_GROUP_TOO_MANY_TAGS",
            )
        # Within one group only; the same tag may appear in other groups.
        if len(set(tag_ids)) != len(tag_ids):
            raise ValidationError(
                message=f'Group "{group_name}" has the same tag more than once.',
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
