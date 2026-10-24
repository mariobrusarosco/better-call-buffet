from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Same pagination meta as the transactions list, so the frontend reads both
# the same way.
from app.domains.transactions.schemas import TransactionListMeta

# ---- Requests -----------------------------------------------------------------
# Request schemas only check types. Business rules (blank names, tag limits,
# duplicates, ownership) live in the service so their 422 carries a message
# the frontend can show as-is.


class CashflowViewGroupCreate(BaseModel):
    name: str
    tag_ids: List[UUID] = Field(default_factory=list)


class CashflowViewCreate(BaseModel):
    name: str
    groups: List[CashflowViewGroupCreate] = Field(default_factory=list)
    display_order: int = Field(default=0, ge=0)


class CashflowViewUpdate(BaseModel):
    """Partial update. `groups`, when sent, replaces the whole list."""

    name: Optional[str] = None
    groups: Optional[List[CashflowViewGroupCreate]] = None
    display_order: Optional[int] = Field(default=None, ge=0)


# ---- Views --------------------------------------------------------------------


class CashflowViewGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    tag_ids: List[UUID]


class CashflowViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    display_order: int
    groups: List[CashflowViewGroupResponse]
    created_at: datetime
    updated_at: datetime


# ---- Reporting ----------------------------------------------------------------


class CashflowViewGroupSummary(BaseModel):
    group_id: UUID
    total: Decimal
    count: int


class CashflowViewUngroupedSummary(BaseModel):
    total: Decimal
    count: int


class CashflowViewSummaryResponse(BaseModel):
    groups: List[CashflowViewGroupSummary]
    # Transactions that match none of the groups ("Not in any group").
    ungrouped: CashflowViewUngroupedSummary


class CashflowViewOverlapItem(BaseModel):
    transaction_id: UUID
    description: str
    amount: Decimal
    date: date
    group_ids: List[UUID]


class CashflowNamedRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class CashflowTransactionItem(BaseModel):
    id: UUID
    date: date
    description: str
    amount: Decimal
    account: Optional[CashflowNamedRef]
    credit_card: Optional[CashflowNamedRef]


class CashflowTransactionListResponse(BaseModel):
    """A page of the transactions behind a group's or the ungrouped total."""

    data: List[CashflowTransactionItem]
    meta: TransactionListMeta
