from app.db.connection_and_session import Base

# Import all models here
from app.domains.users.models import User
from app.domains.accounts.models import Account
from app.domains.broker.model import Broker
from app.domains.balance_points.models import BalancePoint

# Make sure all models are imported before initializing the metadata 