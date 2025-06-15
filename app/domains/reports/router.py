from fastapi import APIRouter

from app.domains.reports.accounts.router import router as accounts_router

router = APIRouter()
router.include_router(accounts_router, prefix="/accounts", tags=["account-reports"])
