from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.core.utils.date import add_months
from app.core.logging_config import get_logger
from app.domains.installments.models import Installment, InstallmentPlan, InstallmentStatus, InstallmentPlanStatus
from app.domains.installments.repository import InstallmentRepository
from app.domains.installments.schemas import (
    InstallmentFilters,
    InstallmentPlanCreate,
    InstallmentPlanListResponse,
    InstallmentPlanResponse,
    InstallmentPlanUpdate,
    InstallmentResponse,
    InstallmentPlanListMeta
)
from app.domains.vendors.service import VendorService
from app.domains.categories.service import CategoryService
from app.domains.credit_cards.service import CreditCardService
from app.domains.credit_cards.schemas import CreditCardFilters

logger = get_logger(__name__)


class InstallmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = InstallmentRepository(db)
        self.vendor_service = VendorService(db)
        self.category_service = CategoryService(db)
        self.credit_card_service = CreditCardService(db)

    def create_plan(self, plan_data: InstallmentPlanCreate, user_id: UUID) -> InstallmentPlan:
        """
        Atomically creates an Installment Plan and all its projected Installments.
        """
        # 1. Validate Ownership
        if plan_data.vendor_id:
            self.vendor_service.get_vendor(plan_data.vendor_id, user_id)
        
        if plan_data.category_id:
            category = self.category_service.repository.get_category_by_id(plan_data.category_id, user_id)
            if not category:
                raise NotFoundError(message="Category not found", error_code="CATEGORY_NOT_FOUND")

        if plan_data.credit_card_id:
            filters = CreditCardFilters(credit_card_id=plan_data.credit_card_id)
            self.credit_card_service.get_user_unique_credit_card_with_filters(user_id, filters)

        # 2. Create the Plan record
        plan = InstallmentPlan(
            user_id=user_id,
            name=plan_data.name,
            description=plan_data.description,
            total_amount=plan_data.total_amount,
            installment_count=plan_data.installment_count,
            start_date=plan_data.start_date,
            status=InstallmentPlanStatus.active,
            vendor_id=plan_data.vendor_id,
            category_id=plan_data.category_id,
            credit_card_id=plan_data.credit_card_id
        )
        
        created_plan = self.repository.create_plan(plan)

        # 3. Generate Installments
        installments = self._generate_installments(created_plan)
        self.repository.create_installments_bulk(installments)

        # Refresh to include the relationship
        return self.repository.get_plan_by_id(created_plan.id, user_id)

    def _generate_installments(self, plan: InstallmentPlan) -> List[Installment]:
        """
        Math engine to split the total amount and generate dates.
        Handles rounding remainders by adding the difference to the last installment.
        """
        installments = []
        count = plan.installment_count
        total = Decimal(str(plan.total_amount))
        
        # Calculate base amount (truncated to 2 decimal places)
        base_amount = (total / count).quantize(Decimal("0.01"), rounding="ROUND_DOWN")
        
        # Calculate remainder
        remainder = total - (base_amount * count)
        
        for i in range(1, count + 1):
            installment_amount = base_amount
            # Add remainder to the last installment
            if i == count:
                installment_amount += remainder
            
            # Date rollover logic: Each installment is 1 month after the previous
            # Starting from the purchase month (Installment 1 is usually in the month of purchase)
            due_date = add_months(plan.start_date, i - 1)
            
            installment = Installment(
                plan_id=plan.id,
                number=i,
                amount=installment_amount,
                due_date=due_date,
                status=InstallmentStatus.pending
            )
            installments.append(installment)
            
        return installments

    def get_plan(self, plan_id: UUID, user_id: UUID) -> InstallmentPlan:
        plan = self.repository.get_plan_by_id(plan_id, user_id)
        if not plan:
            raise NotFoundError(message="Installment Plan not found", error_code="INSTALLMENT_PLAN_NOT_FOUND")
        return plan

    def delete_plan(self, plan_id: UUID, user_id: UUID) -> None:
        plan = self.get_plan(plan_id, user_id)
        # SQLAlchemy Cascade handles the deletion of individual installments
        self.repository.delete_plan(plan)

    def list_plans(self, user_id: UUID, filters: Optional[InstallmentFilters] = None) -> InstallmentPlanListResponse:
        plans, total = self.repository.get_plans_with_filters(user_id, filters)
        
        # Calculate pagination metadata
        per_page = filters.per_page if filters else 20
        page = filters.page if filters else 1
        total_pages = (total + per_page - 1) // per_page
        
        meta = InstallmentPlanListMeta(
            total=total,
            page=page,
            per_page=per_page,
            has_next=page < total_pages,
            has_previous=page > 1
        )
        
        # Convert to responses (including eager relationships)
        data = [InstallmentPlanResponse.from_orm(p) for p in plans]
        
        return InstallmentPlanListResponse(data=data, meta=meta)
