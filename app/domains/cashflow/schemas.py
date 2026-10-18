from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---- Monthly cashflow -------------------------------------------------------


class MonthlyCashflow(BaseModel):
    month: str  # YYYY-MM
    income: Decimal
    expenses: Decimal
    savings: Decimal
    investments: Decimal


class CashflowSummary(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    net_cashflow: Decimal
    savings_rate: float
    monthly_data: List[MonthlyCashflow]


# ---- Cashflow views ---------------------------------------------------------
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


class CashflowViewTagSummary(BaseModel):
    tag_id: UUID
    total: Decimal
    count: int


class CashflowViewGroupSummary(BaseModel):
    group_id: UUID
    total: Decimal
    count: int
    tags: List[CashflowViewTagSummary]


class CashflowViewSummaryResponse(BaseModel):
    groups: List[CashflowViewGroupSummary]


class CashflowViewOverlapItem(BaseModel):
    transaction_id: UUID
    description: str
    amount: Decimal
    date: date
    group_ids: List[UUID]
