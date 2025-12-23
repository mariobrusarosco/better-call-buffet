from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from app.domains.categories.models import UserCategory
from sqlalchemy import and_
from typing import Optional


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_categories(self, user_id: UUID) -> List[UserCategory]:
        query = self.db.query(UserCategory).filter(
            and_(UserCategory.user_id == user_id, UserCategory.is_active == True)
        )
        return query.order_by(UserCategory.display_order, UserCategory.name).all()

    def get_category_by_id(
        self, category_id: UUID, user_id: UUID
    ) -> Optional[UserCategory]:
        return (
            self.db.query(UserCategory)
            .filter(UserCategory.id == category_id, UserCategory.user_id == user_id)
            .first()
        )

    def get_first_level_category_by_id(
        self, category_id: UUID, user_id: UUID
    ) -> Optional[UserCategory]:
        return (
            self.db.query(UserCategory)
            .filter(
                UserCategory.id == category_id,
                UserCategory.user_id == user_id,
                UserCategory.parent_id is None,
            )
            .first()
        )

    def update_category(
        self, category: UserCategory, update_data: dict
    ) -> Optional[UserCategory]:
        for key, value in update_data.items():
            setattr(category, key, value)

        self.db.commit()
        self.db.refresh(category)
        return category

    def create_category(self, category_data: dict) -> UserCategory:
        db_category = UserCategory(**category_data)
        self.db.add(db_category)
        self.db.commit()
        self.db.refresh(db_category)

        return db_category

    def soft_delete_category(self, category_id: UUID, user_id: UUID) -> bool:
        query = (
            self.db.query(UserCategory)
            .filter(
                and_(UserCategory.id == category_id, UserCategory.user_id == user_id)
            )
            .first()
        )

        if not query:
            return False

        query.is_active = False
        self.db.commit()
        self.db.refresh(query)

        return True

    def check_duplicate_name(
        self,
        user_id: UUID,
        name: str,
        parent_category_id: UUID,
        exclude_category_id: Optional[UUID] = None,
    ) -> bool:
        query = self.db.query(UserCategory).filter(
            and_(
                UserCategory.user_id == user_id,
                UserCategory.name == name,
                UserCategory.parent_id == parent_category_id,
            )
        )

        if exclude_category_id:
            query = query.filter(UserCategory.id != exclude_category_id)

        return query.count() > 0
