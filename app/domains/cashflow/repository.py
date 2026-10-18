from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import asc, case, func
from sqlalchemy.orm import Query, Session, selectinload

from app.domains.cashflow.models import (
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


def cashflow_scope(
    query: Query,
    user_id: UUID,
    date_from: Optional[date],
    date_to: Optional[date],
) -> Query:
    """What counts as cashflow: the user's live, non-ignored transactions.

    The single definition shared by the monthly report and the view
    summaries, so their numbers always agree. Both dates are inclusive whole
    days: `date_to` keeps everything up to the end of that day.
    """
    query = query.filter(
        Transaction.user_id == user_id,
        Transaction.is_deleted.is_(False),
        Transaction.ignored.is_(False),
    )
    if date_from is not None:
        query = query.filter(Transaction.date >= datetime.combine(date_from, time.min))
    if date_to is not None:
        next_day = datetime.combine(date_to + timedelta(days=1), time.min)
        query = query.filter(Transaction.date < next_day)
    return query


class CashflowRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---- Monthly cashflow ---------------------------------------------------

    def get_monthly_cashflow(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
        account_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates transaction data by month to calculate income, expenses, and investments.
        """
        # Truncate date to month: TO_CHAR(date, 'YYYY-MM')
        month_col = func.to_char(Transaction.date, "YYYY-MM").label("month")

        # Aggregations
        income_sum = func.sum(
            case((Transaction.movement_type == "income", Transaction.amount), else_=0)
        ).label("income")

        expense_sum = func.sum(
            case((Transaction.movement_type == "expense", Transaction.amount), else_=0)
        ).label("expenses")

        investment_sum = func.sum(
            case(
                (Transaction.movement_type == "investment", Transaction.amount), else_=0
            )
        ).label("investments")

        query = self.db.query(month_col, income_sum, expense_sum, investment_sum)
        query = cashflow_scope(query, user_id, date_from, date_to)

        if account_id:
            query = query.filter(Transaction.account_id == account_id)

        results = query.group_by(month_col).order_by(month_col).all()

        # Format results as dicts
        return [
            {
                "month": r.month,
                "income": r.income or 0,
                "expenses": r.expenses or 0,
                "investments": r.investments or 0,
            }
            for r in results
        ]

    # ---- Views --------------------------------------------------------------

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

    # ---- View reporting -----------------------------------------------------

    def totals_by_tag(
        self,
        user_id: UUID,
        tag_ids: Sequence[UUID],
        date_from: Optional[date],
        date_to: Optional[date],
        movement_type: str,
    ) -> Dict[UUID, Aggregate]:
        """Every transaction carrying the tag. A (transaction, tag) link is
        unique, so nothing is counted twice within one tag."""
        if not tag_ids:
            return {}
        query = self.db.query(
            transaction_tags.c.tag_id,
            func.sum(func.abs(Transaction.amount)),
            func.count(Transaction.id),
        ).join(Transaction, Transaction.id == transaction_tags.c.transaction_id)
        query = cashflow_scope(query, user_id, date_from, date_to)
        rows = (
            query.filter(
                Transaction.movement_type == movement_type,
                transaction_tags.c.tag_id.in_(tag_ids),
            )
            .group_by(transaction_tags.c.tag_id)
            .all()
        )
        return {tag_id: (Decimal(total), int(count)) for tag_id, total, count in rows}

    def _group_matches(
        self,
        user_id: UUID,
        group_ids: Sequence[UUID],
        date_from: Optional[date],
        date_to: Optional[date],
        movement_type: str,
    ) -> Query:
        """One row per (group, transaction) where the transaction carries ANY
        of the group's tags. DISTINCT collapses a transaction that matches a
        group through several tags into a single row."""
        query = (
            self.db.query(
                CashflowViewGroupTag.group_id.label("group_id"),
                Transaction.id.label("transaction_id"),
                Transaction.description.label("description"),
                Transaction.amount.label("amount"),
                Transaction.date.label("date"),
            )
            .join(
                transaction_tags,
                transaction_tags.c.tag_id == CashflowViewGroupTag.tag_id,
            )
            .join(Transaction, Transaction.id == transaction_tags.c.transaction_id)
        )
        query = cashflow_scope(query, user_id, date_from, date_to)
        return query.filter(
            Transaction.movement_type == movement_type,
            CashflowViewGroupTag.group_id.in_(group_ids),
        ).distinct()

    def totals_by_group(
        self,
        user_id: UUID,
        group_ids: Sequence[UUID],
        date_from: Optional[date],
        date_to: Optional[date],
        movement_type: str,
    ) -> Dict[UUID, Aggregate]:
        if not group_ids:
            return {}
        matches = self._group_matches(
            user_id, group_ids, date_from, date_to, movement_type
        ).subquery()
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

    def list_group_matches(
        self,
        user_id: UUID,
        group_ids: Sequence[UUID],
        date_from: Optional[date],
        date_to: Optional[date],
        movement_type: str,
    ) -> List[GroupMatchRow]:
        if not group_ids:
            return []
        rows = (
            self._group_matches(user_id, group_ids, date_from, date_to, movement_type)
            .order_by(Transaction.date.desc(), Transaction.id)
            .all()
        )
        return [tuple(row) for row in rows]  # type: ignore[misc]
