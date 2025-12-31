from typing import List, Optional, Tuple
from uuid import UUID
from datetime import date
from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session, joinedload

from app.domains.installments.models import InstallmentPlan, Installment, InstallmentPlanStatus
from app.domains.installments.schemas import InstallmentFilters


class InstallmentRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Installment Plan Operations ---

    def create_plan(self, plan: InstallmentPlan) -> InstallmentPlan:
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def get_plan_by_id(self, plan_id: UUID, user_id: UUID) -> Optional[InstallmentPlan]:
        return (
            self.db.query(InstallmentPlan)
            .options(
                joinedload(InstallmentPlan.vendor),
                joinedload(InstallmentPlan.category),
                joinedload(InstallmentPlan.credit_card),
                joinedload(InstallmentPlan.installments)
            )
            .filter(and_(InstallmentPlan.id == plan_id, InstallmentPlan.user_id == user_id))
            .first()
        )

    def get_plans_with_filters(
        self, user_id: UUID, filters: Optional[InstallmentFilters] = None
    ) -> Tuple[List[InstallmentPlan], int]:
        query = (
            self.db.query(InstallmentPlan)
            .options(
                joinedload(InstallmentPlan.vendor),
                joinedload(InstallmentPlan.category),
                joinedload(InstallmentPlan.credit_card)
            )
            .filter(InstallmentPlan.user_id == user_id)
        )

        if filters:
            if filters.status:
                query = query.filter(InstallmentPlan.status == filters.status)
            if filters.vendor_id:
                query = query.filter(InstallmentPlan.vendor_id == filters.vendor_id)
            if filters.category_id:
                query = query.filter(InstallmentPlan.category_id == filters.category_id)
            if filters.credit_card_id:
                query = query.filter(InstallmentPlan.credit_card_id == filters.credit_card_id)

            total_count = query.count()
            
            # Pagination
            page = max(1, filters.page)
            per_page = min(100, max(1, filters.per_page))
            offset = (page - 1) * per_page
            query = query.order_by(desc(InstallmentPlan.created_at)).offset(offset).limit(per_page)
        else:
            total_count = query.count()
            query = query.order_by(desc(InstallmentPlan.created_at))

        return query.all(), total_count

    def update_plan(self, plan: InstallmentPlan) -> InstallmentPlan:
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def delete_plan(self, plan: InstallmentPlan) -> None:
        self.db.delete(plan)
        self.db.commit()

    # --- Individual Installment Operations ---

    def create_installments_bulk(self, installments: List[Installment]) -> None:
        self.db.add_all(installments)
        self.db.commit()

    def get_installment_by_id(self, installment_id: UUID, user_id: UUID) -> Optional[Installment]:
        return (
            self.db.query(Installment)
            .join(InstallmentPlan)
            .filter(and_(Installment.id == installment_id, InstallmentPlan.user_id == user_id))
            .first()
        )

    def get_installments_by_plan_id(self, plan_id: UUID) -> List[Installment]:
        return (
            self.db.query(Installment)
            .filter(Installment.plan_id == plan_id)
            .order_by(asc(Installment.number))
            .all()
        )

    def update_installment(self, installment: Installment) -> Installment:
        self.db.commit()
        self.db.refresh(installment)
        return installment

    def get_pending_installments_in_range(
        self, user_id: UUID, start_date: date, end_date: date
    ) -> List[Installment]:
        """Fetches all pending installments within a date range for a specific user."""
        from app.domains.installments.models import InstallmentStatus
        
        return (
            self.db.query(Installment)
            .join(InstallmentPlan)
            .options(joinedload(Installment.plan).joinedload(InstallmentPlan.vendor))
            .filter(
                and_(
                    InstallmentPlan.user_id == user_id,
                    Installment.status == InstallmentStatus.pending,
                    Installment.due_date >= start_date,
                    Installment.due_date <= end_date,
                )
            )
            .order_by(asc(Installment.due_date))
            .all()
        )
