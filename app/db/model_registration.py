from app.db.connection_and_session import Base
from app.domains.accounts.models import Account
from app.domains.balance_points.models import BalancePoint
from app.domains.brokers.models import Broker
from app.domains.credit_cards.models import CreditCard

# Import all models here
from app.domains.users.models import User

# Make sure all models are imported before initializing the metadata
