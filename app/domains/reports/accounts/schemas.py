from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel
from app.domains.accounts.schemas import AccountType

class AccountsBalanceReportParams(BaseModel):
    type: AccountType
    start_date: date
    end_date: Optional[date] = None

    def get_start_datetime(self) -> datetime:
        dt = datetime.combine(self.start_date, datetime.min.time())
        # Return naive datetime for comparison with naive database dates
        return dt.replace(tzinfo=None)
    
    def get_end_datetime(self) -> Optional[datetime]:
        if self.end_date:
            dt = datetime.combine(self.end_date, datetime.max.time())
            # Return naive datetime for comparison with naive database dates
            return dt.replace(tzinfo=None)
        return None
