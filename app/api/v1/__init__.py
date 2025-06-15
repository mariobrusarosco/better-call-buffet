from fastapi import APIRouter

from app.domains.accounts.router import router as accounts_router
from app.domains.balance_points.router import router as balance_points_router
from app.domains.reports.router import router as reports_router
from app.domains.invoices.router import router as invoices_router
from app.domains.brokers.router import router as brokers_router
from app.domains.credit_cards.router import router as credit_cards_router

api_router = APIRouter(prefix="/api/v1")

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
