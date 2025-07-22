from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session

from app.domains.statements.models import Statement
from app.domains.statements.schemas import StatementFilters


class StatementRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, statement_data: dict) -> Statement:
        """Create a new statement"""
        try:
            statement = Statement(**statement_data)
            self.db.add(statement)
            self.db.commit()
            self.db.refresh(statement)
            return statement
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_id(self, statement_id: UUID, user_id: UUID) -> Optional[Statement]:
        """Get statement by ID and user"""
        return (
            self.db.query(Statement)
            .filter(
                and_(
                    Statement.id == statement_id,
                    Statement.user_id == user_id,
                    Statement.is_deleted == False,
                )
            )
            .first()
        )

    def get_account_statements_with_filters(
        self,
        account_id: UUID,
        user_id: UUID,
        filters: Optional[StatementFilters] = None,
    ) -> Tuple[List[Statement], int]:
        """Get account statements with filtering and pagination"""
        
        # Base query
        query = self.db.query(Statement).filter(
            and_(
                Statement.account_id == account_id,
                Statement.user_id == user_id,
                Statement.is_deleted == False,
            )
        )

        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)
            query = self._apply_sorting(query, filters)

            # Get total count before pagination
            total_count = query.count()
            
            # Apply pagination
            query = self._apply_pagination(query, filters)
        else:
            total_count = query.count()

        return query.all(), total_count

    def get_user_statements_with_filters(
        self,
        user_id: UUID,
        filters: Optional[StatementFilters] = None,
    ) -> Tuple[List[Statement], int]:
        """Get all user statements with filtering and pagination"""
        
        # Base query
        query = self.db.query(Statement).filter(
            and_(
                Statement.user_id == user_id,
                Statement.is_deleted == False,
            )
        )

        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)
            query = self._apply_sorting(query, filters)

            # Get total count before pagination
            total_count = query.count()
            
            # Apply pagination
            query = self._apply_pagination(query, filters)
        else:
            total_count = query.count()

        return query.all(), total_count

    def _apply_filters(self, query, filters: StatementFilters):
        """Apply filters to query"""
        
        # Account filter
        if filters.account_id:
            query = query.filter(Statement.account_id == filters.account_id)
        
        # Status filters
        if filters.is_processed is not None:
            query = query.filter(Statement.is_processed == filters.is_processed)
        
        # Date range filters
        if filters.date_from:
            query = query.filter(Statement.created_at >= filters.date_from)
        if filters.date_to:
            query = query.filter(Statement.created_at <= filters.date_to)

        return query

    def _apply_sorting(self, query, filters: StatementFilters):
        """Apply sorting to query"""
        sort_fields = {
            "created_at": Statement.created_at,
            "updated_at": Statement.updated_at,
            "due_date": Statement.due_date,
            "period_start": Statement.period_start,
            "period_end": Statement.period_end,
        }

        field = sort_fields.get(filters.sort_by or "created_at", Statement.created_at)

        if filters.sort_order == "asc":
            query = query.order_by(asc(field))
        else:
            # Default to desc, with secondary sort by created_at desc
            query = query.order_by(desc(field), desc(Statement.created_at))

        return query

    def _apply_pagination(self, query, filters: StatementFilters):
        """Apply pagination to query"""
        page = max(1, filters.page)
        per_page = min(100, max(1, filters.per_page))

        offset = (page - 1) * per_page
        return query.offset(offset).limit(per_page)

    def update(self, statement_id: UUID, user_id: UUID, update_data: dict) -> Optional[Statement]:
        """Update statement"""
        try:
            statement = self.get_by_id(statement_id, user_id)
            if not statement:
                return None

            for key, value in update_data.items():
                setattr(statement, key, value)
            
            statement.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(statement)
            return statement
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, statement_id: UUID, user_id: UUID) -> bool:
        """Soft delete statement"""
        try:
            statement = self.get_by_id(statement_id, user_id)
            if not statement:
                return False

            statement.is_deleted = True
            statement.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e