# Router (API Layer)
@router.post("/", response_model=User)
def create_user(...)

# Service (Business Logic)
class UserService:
    def create(self, user_in: UserCreate) -> User

# Models (Data Layer)
class User(Base):
    __tablename__ = "users"
