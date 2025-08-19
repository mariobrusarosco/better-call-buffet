from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.domains.accounts.router import router as accounts_router
from app.domains.balance_points.router import router as balance_points_router
from app.domains.brokers.router import router as brokers_router
from app.domains.credit_cards.router import router as credit_cards_router
from app.domains.invoices.router import router as invoices_router
from app.domains.reports.router import router as reports_router
from app.domains.statements.router import router as statements_router
from app.domains.transactions.router import router as transactions_router
from app.domains.users.router import router as users_router

api_router = APIRouter(prefix="/api/v1")

# Authentication routes (no auth required)
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])

# User management routes  
api_router.include_router(users_router, prefix="/users", tags=["users"])

# Protected routes
api_router.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
api_router.include_router(
    balance_points_router, prefix="/balance_points", tags=["balance_points"]
)
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(invoices_router, prefix="/invoices", tags=["invoices"])
api_router.include_router(brokers_router, prefix="/brokers", tags=["brokers"])
api_router.include_router(
    credit_cards_router, prefix="/credit_cards", tags=["credit_cards"]
)
api_router.include_router(
    statements_router, prefix="/statements", tags=["statements"]
)
api_router.include_router(
    transactions_router, prefix="/transactions", tags=["transactions"]
)
