from fastapi import APIRouter

from app.domains.accounts.router import router as accounts_router
from app.domains.balance_points.router import router as balance_points_router
api_router = APIRouter(prefix="/api/v1")    

api_router.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
api_router.include_router(balance_points_router, prefix="/balance_points", tags=["balance_points"])
