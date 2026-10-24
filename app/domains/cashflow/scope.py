from datetime import date, datetime, time, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Query

from app.domains.transactions.models import Transaction


def cashflow_scope(
    query: Query,
    user_id: UUID,
    date_from: Optional[date],
    date_to: Optional[date],
) -> Query:
    """What counts as cashflow: the user's live, non-ignored transactions.

    The single definition shared by the monthly report and the views, so
    their numbers always agree. Both dates are inclusive whole days: `date_to`
    keeps everything up to the end of that day.
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
