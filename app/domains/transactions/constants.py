from enum import Enum

class MovementType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    INVESTMENT = "investment"
    TRANSFER = "transfer"
    OTHER = "other"  # For uncategorized movements from AI parsing
