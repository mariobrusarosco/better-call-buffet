"""
CSV Handler for Financial Data Export/Import

Manages CSV generation, parsing, and data type conversions.
Handles the CSV schema and field mappings for all financial entities.
"""

import csv
import io
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class MovementType(str, Enum):
    """Transaction movement types"""
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"


class AccountType(str, Enum):
    """Account types"""
    SAVINGS = "SAVINGS"
    CREDIT = "CREDIT"
    CASH = "CASH"
    INVESTMENT = "INVESTMENT"
    OTHER = "OTHER"


class BillingCycle(str, Enum):
    """Subscription billing cycles"""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


# CSV Column Definitions
CSV_HEADERS = [
    # Transaction columns
    "transaction_date",
    "transaction_amount",
    "transaction_description",
    "transaction_movement_type",
    "transaction_is_paid",
    "transaction_ignored",

    # Account columns
    "account_name",
    "account_type",
    "account_currency",
    "account_description",

    # Credit Card columns
    "credit_card_name",
    "credit_card_brand",
    "credit_card_last_four",
    "credit_card_limit",
    "credit_card_due_date",

    # Category columns
    "category_name",
    "category_parent",

    # Vendor columns
    "vendor_name",
    "vendor_website",

    # Broker columns
    "broker_name",
    "broker_description",

    # Subscription columns
    "subscription_name",
    "subscription_amount",
    "subscription_billing_cycle",
    "subscription_next_due_date",

    # Installment columns
    "installment_plan_name",
    "installment_number",
    "installment_total_amount",
    "installment_count",

    # Transfer columns
    "from_account_name",
    "to_account_name",
]

# Required columns for valid import
REQUIRED_COLUMNS = {
    "transaction_date",
    "transaction_amount",
    "transaction_description",
    "transaction_movement_type",
}


class CSVHandler:
    """Handles CSV generation and parsing for financial data"""

    def __init__(self):
        self.headers = CSV_HEADERS
        self.required_columns = REQUIRED_COLUMNS

    def generate_csv(self, data: List[Dict[str, Any]]) -> str:
        """
        Generate CSV content from a list of data rows.

        Args:
            data: List of dictionaries representing rows

        Returns:
            CSV content as string
        """
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=self.headers,
            extrasaction='ignore'  # Ignore extra fields not in headers
        )

        writer.writeheader()

        for row in data:
            # Sanitize and write row
            sanitized_row = self._sanitize_row(row)
            writer.writerow(sanitized_row)

        return output.getvalue()

    def parse_csv(self, content: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parse CSV content into list of dictionaries.

        Args:
            content: CSV content as string

        Returns:
            Tuple of (parsed rows, list of errors)
        """
        errors = []
        rows = []

        try:
            reader = csv.DictReader(io.StringIO(content))

            # Validate headers
            if reader.fieldnames:
                header_errors = self._validate_headers(reader.fieldnames)
                if header_errors:
                    errors.extend(header_errors)
                    # Continue parsing even with header warnings

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    validated_row = self._validate_and_parse_row(row, row_num)
                    if validated_row:
                        rows.append(validated_row)
                except ValueError as e:
                    errors.append(f"Row {row_num}: {str(e)}")

        except csv.Error as e:
            errors.append(f"CSV parsing error: {str(e)}")

        return rows, errors

    def _sanitize_row(self, row: Dict[str, Any]) -> Dict[str, str]:
        """
        Sanitize a row for CSV export.

        Args:
            row: Dictionary representing a row

        Returns:
            Sanitized row with all values as strings
        """
        sanitized = {}

        for key in self.headers:
            value = row.get(key, "")

            # Convert None to empty string
            if value is None:
                sanitized[key] = ""
            # Convert boolean to string
            elif isinstance(value, bool):
                sanitized[key] = str(value).lower()
            # Convert date/datetime to ISO format
            elif isinstance(value, (date, datetime)):
                sanitized[key] = value.isoformat()
            # Convert Decimal to string
            elif isinstance(value, Decimal):
                sanitized[key] = str(value)
            # Prevent CSV injection
            elif isinstance(value, str) and value and value[0] in ['=', '+', '-', '@']:
                sanitized[key] = "'" + value
            else:
                sanitized[key] = str(value)

        return sanitized

    def _validate_headers(self, headers: List[str]) -> List[str]:
        """
        Validate CSV headers.

        Args:
            headers: List of header names

        Returns:
            List of error messages
        """
        errors = []

        # Check for required columns
        missing = self.required_columns - set(headers)
        if missing:
            errors.append(f"Missing required columns: {', '.join(sorted(missing))}")

        # Warn about unknown columns
        known = set(self.headers)
        unknown = set(headers) - known
        if unknown:
            logger.warning(f"Unknown columns will be ignored: {', '.join(sorted(unknown))}")

        return errors

    def _validate_and_parse_row(
        self,
        row: Dict[str, str],
        row_num: int
    ) -> Optional[Dict[str, Any]]:
        """
        Validate and parse a CSV row.

        Args:
            row: Raw row data from CSV
            row_num: Row number for error reporting

        Returns:
            Parsed row with proper data types, or None if invalid

        Raises:
            ValueError: If validation fails
        """
        parsed = {}

        # Validate required fields
        for field in self.required_columns:
            if not row.get(field):
                raise ValueError(f"Missing required field: {field}")

        # Parse transaction date
        date_str = row.get("transaction_date", "").strip()
        parsed["transaction_date"] = self._parse_date(date_str)

        # Parse transaction amount
        amount_str = row.get("transaction_amount", "").strip()
        parsed["transaction_amount"] = self._parse_decimal(amount_str, "transaction_amount")

        # Parse transaction description
        parsed["transaction_description"] = row.get("transaction_description", "").strip()

        # Parse movement type
        movement_type = row.get("transaction_movement_type", "").strip().upper()
        if movement_type not in [mt.value for mt in MovementType]:
            raise ValueError(
                f"Invalid movement type: {movement_type}. "
                f"Must be one of: {', '.join([mt.value for mt in MovementType])}"
            )
        parsed["transaction_movement_type"] = movement_type

        # Parse boolean fields
        parsed["transaction_is_paid"] = self._parse_boolean(
            row.get("transaction_is_paid", "true")
        )
        parsed["transaction_ignored"] = self._parse_boolean(
            row.get("transaction_ignored", "false")
        )

        # Parse optional fields
        for field in row:
            if field not in parsed and field in self.headers:
                value = row[field].strip()
                if value:  # Only include non-empty values
                    # Special parsing for specific field types
                    if "amount" in field or "limit" in field:
                        try:
                            parsed[field] = self._parse_decimal(value, field)
                        except ValueError:
                            logger.warning(f"Row {row_num}: Invalid decimal for {field}: {value}")
                    elif "date" in field and field != "transaction_date":
                        try:
                            parsed[field] = self._parse_date(value)
                        except ValueError:
                            logger.warning(f"Row {row_num}: Invalid date for {field}: {value}")
                    elif field == "account_type":
                        if value.upper() in [at.value for at in AccountType]:
                            parsed[field] = value.upper()
                        else:
                            logger.warning(f"Row {row_num}: Invalid account type: {value}")
                    elif field == "subscription_billing_cycle":
                        if value.lower() in [bc.value for bc in BillingCycle]:
                            parsed[field] = value.lower()
                        else:
                            logger.warning(f"Row {row_num}: Invalid billing cycle: {value}")
                    elif field == "credit_card_due_date":
                        try:
                            due_date = int(value)
                            if 1 <= due_date <= 31:
                                parsed[field] = due_date
                            else:
                                logger.warning(f"Row {row_num}: Due date must be 1-31: {value}")
                        except ValueError:
                            logger.warning(f"Row {row_num}: Invalid due date: {value}")
                    else:
                        parsed[field] = value

        # Validate transfer consistency
        if parsed.get("transaction_movement_type") == "TRANSFER":
            if not (parsed.get("from_account_name") and parsed.get("to_account_name")):
                raise ValueError(
                    "Transfer transactions must have both from_account_name and to_account_name"
                )
            if parsed.get("from_account_name") == parsed.get("to_account_name"):
                raise ValueError("Transfer cannot be between the same account")

        return parsed

    def _parse_date(self, date_str: str) -> date:
        """
        Parse date string in various formats.

        Args:
            date_str: Date string to parse

        Returns:
            Parsed date object

        Raises:
            ValueError: If date format is invalid
        """
        if not date_str:
            raise ValueError("Date cannot be empty")

        # Try different date formats
        formats = [
            "%Y-%m-%d",      # ISO format
            "%m/%d/%Y",      # US format
            "%d/%m/%Y",      # EU format
            "%Y/%m/%d",      # Alternative
            "%Y-%m-%dT%H:%M:%S",  # ISO datetime
            "%Y-%m-%dT%H:%M:%S.%f",  # ISO datetime with microseconds
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Invalid date format: {date_str}")

    def _parse_decimal(self, value_str: str, field_name: str) -> Decimal:
        """
        Parse decimal string.

        Args:
            value_str: Decimal string to parse
            field_name: Field name for error reporting

        Returns:
            Parsed Decimal object

        Raises:
            ValueError: If decimal format is invalid
        """
        if not value_str:
            raise ValueError(f"{field_name} cannot be empty")

        try:
            # Remove common formatting characters
            cleaned = value_str.replace(",", "").replace("$", "").strip()
            amount = Decimal(cleaned)

            # Check range (15 digits total, 2 decimal places)
            if abs(amount) > Decimal("9999999999999.99"):
                raise ValueError(f"{field_name} exceeds maximum value")

            # Check precision
            if amount.as_tuple().exponent < -2:
                # Round to 2 decimal places
                amount = amount.quantize(Decimal("0.01"))

            return amount

        except (InvalidOperation, ValueError) as e:
            raise ValueError(f"Invalid decimal for {field_name}: {value_str}")

    def _parse_boolean(self, value_str: str) -> bool:
        """
        Parse boolean string.

        Args:
            value_str: Boolean string to parse

        Returns:
            Parsed boolean value
        """
        value_lower = value_str.strip().lower()
        return value_lower in ["true", "yes", "1", "t", "y"]

    def extract_unique_entities(
        self,
        rows: List[Dict[str, Any]]
    ) -> Dict[str, Set[Any]]:
        """
        Extract unique entities from parsed CSV rows.

        Args:
            rows: List of parsed CSV rows

        Returns:
            Dictionary of entity types to sets of unique values
        """
        entities = {
            "brokers": set(),
            "accounts": set(),  # (name, broker_name, type, currency)
            "credit_cards": set(),  # (name, account_name, broker_name)
            "categories": set(),  # (name, parent_name)
            "vendors": set(),
            "subscriptions": set(),  # (name, vendor_name)
            "installment_plans": set(),  # (name, total_amount, count)
        }

        for row in rows:
            # Extract brokers
            if broker_name := row.get("broker_name"):
                entities["brokers"].add(broker_name)

            # Extract accounts
            if account_name := row.get("account_name"):
                entities["accounts"].add((
                    account_name,
                    row.get("broker_name", ""),
                    row.get("account_type", "OTHER"),
                    row.get("account_currency", "USD")
                ))

            # Extract from/to accounts for transfers
            if from_account := row.get("from_account_name"):
                entities["accounts"].add((
                    from_account,
                    row.get("broker_name", ""),
                    "OTHER",  # Default type for transfer accounts
                    "USD"
                ))

            if to_account := row.get("to_account_name"):
                entities["accounts"].add((
                    to_account,
                    row.get("broker_name", ""),
                    "OTHER",
                    "USD"
                ))

            # Extract credit cards
            if card_name := row.get("credit_card_name"):
                entities["credit_cards"].add((
                    card_name,
                    row.get("account_name", ""),
                    row.get("broker_name", "")
                ))

            # Extract categories (handle hierarchy)
            if parent_cat := row.get("category_parent"):
                entities["categories"].add((parent_cat, None))

            if cat_name := row.get("category_name"):
                parent = row.get("category_parent")
                entities["categories"].add((cat_name, parent))

            # Extract vendors
            if vendor_name := row.get("vendor_name"):
                entities["vendors"].add(vendor_name)

            # Extract subscriptions
            if sub_name := row.get("subscription_name"):
                entities["subscriptions"].add((
                    sub_name,
                    row.get("vendor_name", "")
                ))

            # Extract installment plans
            if plan_name := row.get("installment_plan_name"):
                entities["installment_plans"].add((
                    plan_name,
                    row.get("installment_total_amount", "0"),
                    row.get("installment_count", "1")
                ))

        return entities