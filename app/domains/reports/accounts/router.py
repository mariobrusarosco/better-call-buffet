from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  

from app.domains.accounts.service import AccountService
from app.domains.balance_points.service import BalancePointService
from app.domains.reports.accounts.schemas import AccountsBalanceReportParams
from app.domains.reports.accounts.service import ReportAccountsService
from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session


router = APIRouter(tags=["accounts"])

@router.get("/balance")
def get_balance_points(
    params: AccountsBalanceReportParams = Depends(),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    balance_point_service = BalancePointService(db)
    report_accounts_service = ReportAccountsService(db)
    account_service = AccountService(db)

    accounts = account_service.get_accounts_by_type(current_user_id, params.type)
    
    result = []
    start_datetime = params.get_start_datetime()
    end_datetime = params.get_end_datetime()
    
    for account in accounts:
        balance_points = balance_point_service.get_balance_points_by_account_id(
            account_id=account.id, 
            user_id=current_user_id
        )
        
        filtered_points = [
            bp for bp in balance_points 
            if start_datetime <= bp.date and (end_datetime is None or bp.date <= end_datetime)
        ]
        

        if filtered_points:
            monthly_balances = report_accounts_service.get_account_monthly_balance(filtered_points)
            result.append({
                "account_id": account.id,
                "account_name": account.name,
                "monthly_balances": monthly_balances
            })
    
    return {
        "type": params.type,
        "start_date": params.start_date,
        "end_date": params.end_date,
        "accounts": result
    }


    # result = []
    # for account in accounts:
    #     balance_points = balance_point_service.get_balance_points_by_account_id(
    #         account_id=account.id, 
    #         user_id=current_user_id
    #     )
        
    #     # Filter by date range
    #     filtered_points = [
    #         bp for bp in balance_points 
    #         if start_date <= bp.date <= end_date
    #     ]
        
    #     result.append({
    #         "account_id": account.id,
    #         "account_name": account.name,
    #         "balance_points": filtered_points
    #     })



