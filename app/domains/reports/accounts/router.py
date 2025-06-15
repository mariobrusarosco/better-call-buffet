from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session  

from app.domains.reports.accounts.schemas import AccountsBalanceReportParams
from app.domains.reports.accounts.service import ReportAccountsService
from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session


router = APIRouter(tags=["account-reports"])


@router.get("/balance")
def get_balance_report(
    params: AccountsBalanceReportParams = Depends(),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get comprehensive balance report for a specific account type"""
    service = ReportAccountsService(db)
    
    start_datetime = params.get_start_datetime()
    end_datetime = params.get_end_datetime()
    
    try:
        return service.get_account_balance_report(
            user_id=current_user_id,
            account_type=params.type,
            start_date=start_datetime,
            end_date=end_datetime
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/trends")
def get_balance_trends(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get balance trends across all account types"""
    service = ReportAccountsService(db)
    
    return service.get_balance_trends_across_types(
        user_id=current_user_id,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/monthly-totals")
def get_monthly_totals(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get monthly totals grouped by account type"""
    service = ReportAccountsService(db)
    
    return service.get_monthly_totals_by_type(
        user_id=current_user_id,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/performance")
def get_performance_analysis(
    account_id: Optional[UUID] = Query(None, description="Specific account ID (optional)"),
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get detailed performance analysis for accounts"""
    service = ReportAccountsService(db)
    
    try:
        return service.get_account_performance_analysis(
            user_id=current_user_id,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/portfolio-overview")
def get_portfolio_overview(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get comprehensive portfolio overview with multiple analytics"""
    service = ReportAccountsService(db)
    
    return service.get_portfolio_overview(
        user_id=current_user_id,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/performance/account/{account_id}")
def get_account_specific_performance(
    account_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get performance analysis for a specific account"""
    service = ReportAccountsService(db)
    
    try:
        return service.get_account_performance_analysis(
            user_id=current_user_id,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Legacy endpoint for backward compatibility
@router.get("/balance-legacy")
def get_balance_points_legacy(
    params: AccountsBalanceReportParams = Depends(),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Legacy balance points endpoint for backward compatibility.
    DEPRECATED: Use /balance endpoint instead.
    """
    # This maintains the original functionality while using the new service
    from app.domains.accounts.service import AccountService
    from app.domains.balance_points.service import BalancePointService
    
    balance_point_service = BalancePointService(db)
    account_service = AccountService(db)
    report_service = ReportAccountsService(db)

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
            monthly_balances = report_service.get_account_monthly_balance(filtered_points)
            result.append({
                "account_id": account.id,
                "account_name": account.name,
                "monthly_balances": monthly_balances
            })
    
    return {
        "type": params.type,
        "start_date": params.start_date,
        "end_date": params.end_date,
        "accounts": result,
        "_deprecated": "This endpoint is deprecated. Use /balance instead."
    }



