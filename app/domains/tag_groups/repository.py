from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import asc, func
from sqlalchemy.orm import Query, Session, selectinload

from app.domains.tag_groups.models import TagGroup
from app.domains.tags.models import Tag, transaction_tags
from app.domains.transactions.models import Transaction

# (transaction id, description, amount, date, ids of every tag it carries)
TaggedTransactionRow = Tuple[UUID, str, Decimal, datetime, List[UUID]]


class TagGroupRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_groups(self, user_id: UUID) -> List[TagGroup]:
        return (
            self.db.query(TagGroup)
            .options(selectinload(TagGroup.tags))
            .filter(TagGroup.user_id == user_id)
            .order_by(asc(TagGroup.display_order), asc(TagGroup.name))
            .all()
        )

    def get_group(self, group_id: UUID, user_id: UUID) -> Optional[TagGroup]:
        return (
            self.db.query(TagGroup)
            .options(selectinload(TagGroup.tags))
            .filter(TagGroup.id == group_id, TagGroup.user_id == user_id)
            .first()
        )

    def save(self, group: TagGroup) -> TagGroup:
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group

    def delete(self, group: TagGroup) -> None:
        # Children go with it through the parent_id ON DELETE CASCADE.
        self.db.delete(group)
        self.db.commit()

    def _scoped_transactions(
        self,
        query: Query,
        user_id: UUID,
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        movement_type: str,
    ) -> Query:
        """Same scope as Cashflow: the user's live, non-ignored transactions.
        Date bounds are inclusive, like the transactions list filters."""
        query = query.filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.ignored.is_(False),
            Transaction.movement_type == movement_type,
        )
        if date_from is not None:
            query = query.filter(Transaction.date >= date_from)
        if date_to is not None:
            query = query.filter(Transaction.date <= date_to)
        return query

    def sum_transactions_with_all_tags(
        self,
        user_id: UUID,
        tag_ids: Sequence[UUID],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        movement_type: str,
    ) -> Tuple[Decimal, int]:
        query = self.db.query(
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(Transaction.id),
        )
        query = self._scoped_transactions(
            query, user_id, date_from, date_to, movement_type
        )
        # One EXISTS per tag: a transaction is counted once, however many
        # tags it carries, so totals never double up.
        for tag_id in tag_ids:
            query = query.filter(Transaction.tags.any(Tag.id == tag_id))

        total, count = query.one()
        return Decimal(total), int(count)

    def list_transactions_with_any_tag(
        self,
        user_id: UUID,
        tag_ids: Sequence[UUID],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        movement_type: str,
    ) -> List[TaggedTransactionRow]:
        """Candidate transactions for overlap detection, each with all of its
        tag ids, so matching against groups can happen in one pass."""
        if not tag_ids:
            return []
        query = self.db.query(
            Transaction.id,
            Transaction.description,
            Transaction.amount,
            Transaction.date,
            func.array_agg(transaction_tags.c.tag_id),
        ).join(transaction_tags, transaction_tags.c.transaction_id == Transaction.id)
        query = self._scoped_transactions(
            query, user_id, date_from, date_to, movement_type
        )
        rows = (
            query.group_by(Transaction.id)
            .having(func.bool_or(transaction_tags.c.tag_id.in_(tag_ids)))
            .order_by(Transaction.date.desc(), Transaction.id)
            .all()
        )
        return [tuple(row) for row in rows]  # type: ignore[misc]
