from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import asc, func, select
from sqlalchemy.orm import Query, Session, joinedload, selectinload

from app.domains.cashflow.scope import cashflow_scope
from app.domains.cashflow.views.models import (
    CashflowView,
    CashflowViewGroup,
    CashflowViewGroupTag,
)
from app.domains.tags.models import transaction_tags
from app.domains.transactions.models import Transaction

# (total, count)
Aggregate = Tuple[Decimal, int]
# (group id, transaction id, description, amount, date)
GroupMatchRow = Tuple[UUID, UUID, str, Decimal, datetime]


@dataclass(frozen=True)
class ReportFilters:
    """Which transactions a report looks at: cashflow scope plus one
    movement type. Shared by the summary and every list behind it, so their
    totals and counts always agree."""

    user_id: UUID
    date_from: Optional[date]
    date_to: Optional[date]
    movement_type: str


class CashflowViewRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---- Views ----------------------------------------------------------------

    def _views(self) -> Query:
        return self.db.query(CashflowView).options(
            selectinload(CashflowView.groups).selectinload(CashflowViewGroup.tag_links)
        )

    def list_views(self, user_id: UUID) -> List[CashflowView]:
        return (
            self._views()
            .filter(CashflowView.user_id == user_id)
            .order_by(asc(CashflowView.display_order), asc(CashflowView.name))
            .all()
        )

    def get_view(self, view_id: UUID, user_id: UUID) -> Optional[CashflowView]:
        return (
            self._views()
            .filter(CashflowView.id == view_id, CashflowView.user_id == user_id)
            .first()
        )

    def save_view(self, view: CashflowView) -> CashflowView:
        self.db.add(view)
        self.db.commit()
        self.db.refresh(view)
        return view

    def delete_view(self, view: CashflowView) -> None:
        # Groups and their tag links go with it (ON DELETE CASCADE).
        self.db.delete(view)
        self.db.commit()

    # ---- Matching -------------------------------------------------------------
    # Totals sum abs(amount): amounts are stored positive (the API rejects
    # amount <= 0), and the frontend contract promises positive values.

    def _scoped(self, query: Query, filters: ReportFilters) -> Query:
        query = cashflow_scope(
            query, filters.user_id, filters.date_from, filters.date_to
        )
        return query.filter(Transaction.movement_type == filters.movement_type)

    def _group_matches(
        self, group_ids: Sequence[UUID], filters: ReportFilters
    ) -> Query:
        """One row per (group, transaction) where the transaction carries ALL
        of the group's tags.

        Joining a group's tags to a transaction's tags gives one row per tag
        they share. Both links are unique pairs, so the transaction carries
        every tag of the group exactly when that shared count equals the
        group's size. A group left with no tags (its tags were deleted) has
        no rows to join and matches nothing, rather than everything.
        """
        group_sizes = (
            self.db.query(
                CashflowViewGroupTag.group_id.label("group_id"),
                func.count().label("size"),
            )
            .filter(CashflowViewGroupTag.group_id.in_(group_ids))
            .group_by(CashflowViewGroupTag.group_id)
            .subquery()
        )
        query = (
            self.db.query(
                CashflowViewGroupTag.group_id.label("group_id"),
                Transaction.id.label("transaction_id"),
                Transaction.description.label("description"),
                Transaction.amount.label("amount"),
                Transaction.date.label("date"),
            )
            .join(group_sizes, group_sizes.c.group_id == CashflowViewGroupTag.group_id)
            .join(
                transaction_tags,
                transaction_tags.c.tag_id == CashflowViewGroupTag.tag_id,
            )
            .join(Transaction, Transaction.id == transaction_tags.c.transaction_id)
        )
        return (
            self._scoped(query, filters)
            # Grouping by the primary key lets Postgres select the other
            # transaction columns without listing them here.
            .group_by(
                CashflowViewGroupTag.group_id, Transaction.id, group_sizes.c.size
            ).having(func.count() == group_sizes.c.size)
        )

    def _ungrouped(self, group_ids: Sequence[UUID], filters: ReportFilters) -> Query:
        """Transactions that match none of the groups, untagged ones included.
        With no groups, every transaction is ungrouped."""
        query = self._scoped(self.db.query(Transaction), filters)
        if group_ids:
            matches = self._group_matches(group_ids, filters).subquery()
            query = query.filter(~Transaction.id.in_(select(matches.c.transaction_id)))
        return query

    # ---- Totals ---------------------------------------------------------------

    def totals_by_group(
        self, group_ids: Sequence[UUID], filters: ReportFilters
    ) -> Dict[UUID, Aggregate]:
        if not group_ids:
            return {}
        matches = self._group_matches(group_ids, filters).subquery()
        rows = (
            self.db.query(
                matches.c.group_id,
                func.sum(func.abs(matches.c.amount)),
                func.count(matches.c.transaction_id),
            )
            .group_by(matches.c.group_id)
            .all()
        )
        return {
            group_id: (Decimal(total), int(count)) for group_id, total, count in rows
        }

    def totals_ungrouped(
        self, group_ids: Sequence[UUID], filters: ReportFilters
    ) -> Aggregate:
        total, count = (
            self._ungrouped(group_ids, filters)
            .with_entities(
                func.coalesce(func.sum(func.abs(Transaction.amount)), 0),
                func.count(Transaction.id),
            )
            .one()
        )
        return Decimal(total), int(count)

    # ---- Lists ----------------------------------------------------------------

    def list_group_matches(
        self, group_ids: Sequence[UUID], filters: ReportFilters
    ) -> List[GroupMatchRow]:
        if not group_ids:
            return []
        rows = (
            self._group_matches(group_ids, filters)
            .order_by(Transaction.date.desc(), Transaction.id)
            .all()
        )
        return [tuple(row) for row in rows]  # type: ignore[misc]

    def list_group_transactions(
        self, group_id: UUID, filters: ReportFilters, page: int, per_page: int
    ) -> Tuple[List[Transaction], int]:
        """Same match as totals_by_group, so the total here always equals the
        group's count in the summary."""
        matches = self._group_matches([group_id], filters).subquery()
        query = self.db.query(Transaction).filter(
            Transaction.id.in_(select(matches.c.transaction_id))
        )
        return self._page_of_transactions(query, page, per_page)

    def list_ungrouped_transactions(
        self,
        group_ids: Sequence[UUID],
        filters: ReportFilters,
        page: int,
        per_page: int,
    ) -> Tuple[List[Transaction], int]:
        """Same set as totals_ungrouped, so the total here always equals the
        ungrouped count in the summary."""
        query = self._ungrouped(group_ids, filters)
        return self._page_of_transactions(query, page, per_page)

    @staticmethod
    def _page_of_transactions(
        query: Query, page: int, per_page: int
    ) -> Tuple[List[Transaction], int]:
        """One page, newest first, with account and card names loaded in the
        same query; plus the total across all pages."""
        total = query.count()
        transactions = (
            query.options(
                joinedload(Transaction.account), joinedload(Transaction.credit_card)
            )
            .order_by(Transaction.date.desc(), Transaction.id)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return transactions, total
