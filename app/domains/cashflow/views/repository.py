from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import Select, asc, func, or_, select
from sqlalchemy.orm import Query, Session, joinedload, selectinload

from app.domains.cashflow.scope import cashflow_scope
from app.domains.cashflow.views.constants import GroupMatch
from app.domains.cashflow.views.models import (
    CashflowView,
    CashflowViewGroup,
    CashflowViewGroupTag,
)
from app.domains.tags.models import transaction_tags
from app.domains.transactions.models import Transaction

# (total, count)
Aggregate = Tuple[Decimal, int]
# (leaf group id, transaction id, description, amount, date)
LeafMatchRow = Tuple[UUID, UUID, str, Decimal, datetime]


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
        groups = selectinload(CashflowView.groups)
        sub_groups = groups.selectinload(CashflowViewGroup.groups)
        return self.db.query(CashflowView).options(
            groups.selectinload(CashflowViewGroup.tag_links),
            sub_groups.selectinload(CashflowViewGroup.tag_links),
            # Always empty, but loading it here keeps serializing a view
            # from issuing one query per sub-group.
            sub_groups.selectinload(CashflowViewGroup.groups),
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
        # Reload with the whole tree eagerly, as get_view does.
        saved = self.get_view(view.id, view.user_id)
        assert saved is not None
        return saved

    def delete_view(self, view: CashflowView) -> None:
        # Groups, sub-groups and their tag links go with it (ON DELETE CASCADE).
        self.db.delete(view)
        self.db.commit()

    # ---- Matching -------------------------------------------------------------
    # Only groups that hold tags ("leaves": a top-level group without
    # sub-groups, or a sub-group) match transactions directly. A parent's
    # matches are the union of its sub-groups'.
    #
    # Totals sum abs(amount): amounts are stored positive (the API rejects
    # amount <= 0), and the frontend contract promises positive values.

    def _scoped(self, query: Query, filters: ReportFilters) -> Query:
        query = cashflow_scope(
            query, filters.user_id, filters.date_from, filters.date_to
        )
        return query.filter(Transaction.movement_type == filters.movement_type)

    def _leaf_matches(self, leaf_ids: Sequence[UUID], filters: ReportFilters) -> Query:
        """One row per (leaf, transaction) where the transaction matches the
        leaf: carries ANY of its tags, or ALL of them, per the leaf's match.

        Joining a leaf's tags to a transaction's tags gives one row per tag
        they share. Both links are unique pairs, so the transaction carries
        every tag of the leaf exactly when that shared count equals the
        leaf's size; any shared row at all is enough for "any". A leaf left
        with no tags (its tags were deleted) has no rows to join and matches
        nothing, rather than everything.
        """
        leaf_sizes = (
            self.db.query(
                CashflowViewGroupTag.group_id.label("group_id"),
                func.count().label("size"),
            )
            .filter(CashflowViewGroupTag.group_id.in_(leaf_ids))
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
            .join(leaf_sizes, leaf_sizes.c.group_id == CashflowViewGroupTag.group_id)
            .join(
                CashflowViewGroup, CashflowViewGroup.id == CashflowViewGroupTag.group_id
            )
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
                CashflowViewGroupTag.group_id,
                Transaction.id,
                CashflowViewGroup.match,
                leaf_sizes.c.size,
            ).having(
                or_(
                    CashflowViewGroup.match == GroupMatch.ANY.value,
                    func.count() == leaf_sizes.c.size,
                )
            )
        )

    def _matching_any_leaf(
        self, leaf_ids: Sequence[UUID], filters: ReportFilters
    ) -> Select:
        """Ids of the transactions matching at least one of the leaves."""
        matches = self._leaf_matches(leaf_ids, filters).subquery()
        return select(matches.c.transaction_id)

    def _ungrouped(self, leaf_ids: Sequence[UUID], filters: ReportFilters) -> Query:
        """Transactions that match no leaf of the view, untagged ones
        included. With no groups, every transaction is ungrouped."""
        query = self._scoped(self.db.query(Transaction), filters)
        if leaf_ids:
            query = query.filter(
                ~Transaction.id.in_(self._matching_any_leaf(leaf_ids, filters))
            )
        return query

    # ---- Totals ---------------------------------------------------------------

    def totals_by_group(
        self, leaf_ids: Sequence[UUID], filters: ReportFilters
    ) -> Dict[UUID, Aggregate]:
        """Totals for the given leaves and for every parent above them. A
        parent counts each transaction once, even when several of its
        sub-groups match it."""
        if not leaf_ids:
            return {}
        leaf_matches = self._leaf_matches(leaf_ids, filters).subquery()
        by_leaf = self.db.query(
            leaf_matches.c.group_id,
            func.sum(func.abs(leaf_matches.c.amount)),
            func.count(),
        ).group_by(leaf_matches.c.group_id)

        parent_matches = (
            self.db.query(
                CashflowViewGroup.parent_id.label("group_id"),
                leaf_matches.c.transaction_id,
                leaf_matches.c.amount,
            )
            .join(CashflowViewGroup, CashflowViewGroup.id == leaf_matches.c.group_id)
            .filter(CashflowViewGroup.parent_id.isnot(None))
            .distinct()
            .subquery()
        )
        by_parent = self.db.query(
            parent_matches.c.group_id,
            func.sum(func.abs(parent_matches.c.amount)),
            func.count(),
        ).group_by(parent_matches.c.group_id)

        return {
            group_id: (Decimal(total), int(count))
            for group_id, total, count in by_leaf.union_all(by_parent).all()
        }

    def totals_ungrouped(
        self, leaf_ids: Sequence[UUID], filters: ReportFilters
    ) -> Aggregate:
        total, count = (
            self._ungrouped(leaf_ids, filters)
            .with_entities(
                func.coalesce(func.sum(func.abs(Transaction.amount)), 0),
                func.count(Transaction.id),
            )
            .one()
        )
        return Decimal(total), int(count)

    # ---- Lists ----------------------------------------------------------------

    def list_leaf_matches(
        self, leaf_ids: Sequence[UUID], filters: ReportFilters
    ) -> List[LeafMatchRow]:
        if not leaf_ids:
            return []
        rows = (
            self._leaf_matches(leaf_ids, filters)
            .order_by(Transaction.date.desc(), Transaction.id)
            .all()
        )
        return [tuple(row) for row in rows]  # type: ignore[misc]

    def list_matching_transactions(
        self,
        leaf_ids: Sequence[UUID],
        filters: ReportFilters,
        page: int,
        per_page: int,
    ) -> Tuple[List[Transaction], int]:
        """Transactions matching any of the leaves, each once: one leaf for a
        group that holds tags, its sub-groups for a parent. Same match as
        totals_by_group, so the total equals that group's summary count."""
        query = self.db.query(Transaction).filter(
            Transaction.id.in_(self._matching_any_leaf(leaf_ids, filters))
        )
        return self._page_of_transactions(query, page, per_page)

    def list_ungrouped_transactions(
        self,
        leaf_ids: Sequence[UUID],
        filters: ReportFilters,
        page: int,
        per_page: int,
    ) -> Tuple[List[Transaction], int]:
        """Same set as totals_ungrouped, so the total here always equals the
        ungrouped count in the summary."""
        query = self._ungrouped(leaf_ids, filters)
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
