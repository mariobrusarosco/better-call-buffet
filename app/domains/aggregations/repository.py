from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import asc, func
from sqlalchemy.orm import Session, joinedload

from app.domains.aggregations.models import (
    AggregationNode,
    AggregationNodeCondition,
    AggregationView,
)
from app.domains.tags.models import Tag
from app.domains.transactions.models import Transaction


class AggregationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_view(self, view_id: UUID, user_id: UUID) -> Optional[AggregationView]:
        return (
            self.db.query(AggregationView)
            .options(
                joinedload(AggregationView.nodes)
                .joinedload(AggregationNode.conditions)
                .joinedload(AggregationNodeCondition.tag)
                .joinedload(Tag.dimension)
            )
            .filter(
                AggregationView.id == view_id,
                AggregationView.user_id == user_id,
            )
            .first()
        )

    def get_view_by_normalized_name(
        self, normalized_name: str, user_id: UUID
    ) -> Optional[AggregationView]:
        return (
            self.db.query(AggregationView)
            .filter(
                AggregationView.user_id == user_id,
                AggregationView.normalized_name == normalized_name,
            )
            .first()
        )

    def list_views(self, user_id: UUID) -> List[AggregationView]:
        return (
            self.db.query(AggregationView)
            .filter(AggregationView.user_id == user_id)
            .order_by(asc(AggregationView.name))
            .all()
        )

    def aggregate_transactions(
        self,
        user_id: UUID,
        effective_conditions: Dict[UUID, str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        movement_types: Sequence[str],
    ) -> Tuple[Decimal, int]:
        query = self.db.query(
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(Transaction.id),
        ).filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.ignored.is_(False),
            Transaction.movement_type.in_(movement_types),
        )

        if date_from is not None:
            query = query.filter(Transaction.date >= date_from)
        if date_to is not None:
            query = query.filter(Transaction.date <= date_to)

        for tag_id, operator in effective_conditions.items():
            predicate = Transaction.tags.any(Tag.id == tag_id)
            query = query.filter(predicate if operator == "include" else ~predicate)

        total, transaction_count = query.one()
        return Decimal(total), int(transaction_count)
