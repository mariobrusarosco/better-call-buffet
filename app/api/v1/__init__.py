from fastapi import APIRouter

from app.domains.accounts.router import router as accounts_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
