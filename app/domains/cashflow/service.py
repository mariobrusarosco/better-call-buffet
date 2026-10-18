from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.domains.cashflow.constants import (
    MAX_GROUP_NAME_LENGTH,
    MAX_GROUPS_PER_VIEW,
    MAX_TAGS_PER_GROUP,
    MAX_VIEW_NAME_LENGTH,
)
from app.domains.cashflow.models import (
    CashflowView,
    CashflowViewGroup,
    CashflowViewGroupTag,
)
from app.domains.cashflow.repository import CashflowRepository
from app.domains.cashflow.schemas import (
    CashflowSummary,
    CashflowViewCreate,
    CashflowViewGroupCreate,
    CashflowViewGroupSummary,
    CashflowViewOverlapItem,
    CashflowViewSummaryResponse,
    CashflowViewTagSummary,
    CashflowViewUpdate,
    MonthlyCashflow,
)
from app.domains.tags.repository import TagRepository
from app.domains.transactions.constants import MovementType

CENTS = Decimal("0.01")


def to_money(amount: Decimal) -> Decimal:
    """Two decimal places, so an empty total serializes as "0.00", not "0"."""
    return Decimal(amount).quantize(CENTS)


class CashflowService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = CashflowRepository(db)
        self.tag_repository = TagRepository(db)

    # ---- Monthly cashflow ---------------------------------------------------

    def get_cashflow_analytics(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
        account_id: Optional[UUID] = None,
    ) -> CashflowSummary:
        """
        Orchestrates the retrieval and calculation of cashflow analytics.
        """
        monthly_data_raw = self.repository.get_monthly_cashflow(
            user_id, date_from, date_to, account_id
        )

        monthly_data = []
        total_income = Decimal(0)
        total_expenses = Decimal(0)
        total_investments = Decimal(0)

        for item in monthly_data_raw:
            income = Decimal(item["income"])
            expenses = Decimal(item["expenses"])
            investments = Decimal(item["investments"])

            # Savings = Income - Expenses
            # Note: This assumes Investments are tracked separately or are just informational in this context.
            # If investments are outflows (expenses), they might be included in expenses if movement_type='expense'
            # But if movement_type='investment', they are summed separately here.
            # The calculation `Savings = Income - Expenses` aligns with the user's example where
            # Income (10k) - Expenses (6k) = Savings (4k).
            savings = income - expenses

            monthly_data.append(
                MonthlyCashflow(
                    month=item["month"],
                    income=income,
                    expenses=expenses,
                    savings=savings,
                    investments=investments,
                )
            )

            total_income += income
            total_expenses += expenses
            total_investments += investments

        # Net cashflow over the entire period
        net_cashflow = total_income - total_expenses

        # Savings Rate = (Net Cashflow / Total Income) * 100
        savings_rate = 0.0
        if total_income > 0:
            savings_rate = (float(net_cashflow) / float(total_income)) * 100

        return CashflowSummary(
            total_income=total_income,
            total_expenses=total_expenses,
            net_cashflow=net_cashflow,
            savings_rate=round(savings_rate, 2),
            monthly_data=monthly_data,
        )

    # ---- Views: CRUD --------------------------------------------------------

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

    # ---- Views: reporting ---------------------------------------------------

    def get_view_summary(
        self,
        view_id: UUID,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        movement_type: MovementType = MovementType.EXPENSE,
    ) -> CashflowViewSummaryResponse:
        """Every group and every tag of the view, zero when nothing matches.

        A tag's total covers every transaction carrying it. A group's total
        covers every transaction carrying ANY of its tags, counted once, so
        it can be less than the sum of its tags.
        """
        view = self.get_view(view_id, user_id)
        group_ids = [group.id for group in view.groups]
        tag_ids = list({tag_id for group in view.groups for tag_id in group.tag_ids})
        by_tag = self.repository.totals_by_tag(
            user_id, tag_ids, date_from, date_to, movement_type.value
        )
        by_group = self.repository.totals_by_group(
            user_id, group_ids, date_from, date_to, movement_type.value
        )
        nothing = (Decimal("0"), 0)

        return CashflowViewSummaryResponse(
            groups=[
                CashflowViewGroupSummary(
                    group_id=group.id,
                    total=to_money(by_group.get(group.id, nothing)[0]),
                    count=by_group.get(group.id, nothing)[1],
                    tags=[
                        CashflowViewTagSummary(
                            tag_id=tag_id,
                            total=to_money(by_tag.get(tag_id, nothing)[0]),
                            count=by_tag.get(tag_id, nothing)[1],
                        )
                        for tag_id in group.tag_ids
                    ],
                )
                for group in view.groups
            ]
        )

    def get_view_overlaps(
        self,
        view_id: UUID,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        movement_type: MovementType = MovementType.EXPENSE,
    ) -> List[CashflowViewOverlapItem]:
        """Transactions that land in two or more groups of the view, newest
        first. group_ids follow the view's group order."""
        view = self.get_view(view_id, user_id)
        group_order = {group.id: index for index, group in enumerate(view.groups)}

        rows = self.repository.list_group_matches(
            user_id, list(group_order), date_from, date_to, movement_type.value
        )
        # Rows arrive newest first; dicts keep that order.
        groups_of: Dict[UUID, List[UUID]] = {}
        first_row: Dict[UUID, Tuple[str, Decimal, datetime]] = {}
        for group_id, transaction_id, description, amount, when in rows:
            groups_of.setdefault(transaction_id, []).append(group_id)
            first_row.setdefault(transaction_id, (description, amount, when))

        overlaps = []
        for transaction_id, group_ids in groups_of.items():
            if len(group_ids) < 2:
                continue
            description, amount, when = first_row[transaction_id]
            overlaps.append(
                CashflowViewOverlapItem(
                    transaction_id=transaction_id,
                    description=description,
                    amount=to_money(abs(amount)),
                    date=when.date(),
                    group_ids=sorted(group_ids, key=group_order.__getitem__),
                )
            )
        return overlaps

    # ---- Views: validation --------------------------------------------------
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

    def _check_tags_usable(self, tag_ids: set, user_id: UUID) -> None:
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
