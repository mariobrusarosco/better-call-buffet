"""
Service layer for Data Transfer domain

Orchestrates export and import operations, managing business logic
and coordinating between repository, CSV handler, and other components.
"""

import logging
import tempfile
import os
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy.orm import Session

from app.domains.data_transfer.repository import DataTransferRepository
from app.domains.data_transfer.csv_handler import CSVHandler
from app.domains.data_transfer.schemas import (
    ExportRequest,
    ExportResponse,
    ExportStatus,
    ImportRequest,
    ImportResponse,
    ImportStatus,
    ImportStatistics,
    EntityCreationStats,
    ImportValidationResult
)

logger = logging.getLogger(__name__)


class DataTransferService:
    """
    Service for handling data export and import operations.
    Orchestrates the business logic for financial data transfer.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = DataTransferRepository(db)
        self.csv_handler = CSVHandler()
        # Temporary storage for export files
        self.export_dir = Path(tempfile.gettempdir()) / "data_exports"
        self.export_dir.mkdir(exist_ok=True)

    # ==================== EXPORT METHODS ====================

    def export_user_data(
        self,
        user_id: UUID,
        request: ExportRequest
    ) -> ExportResponse:
        """
        Export user's financial data to CSV.

        Args:
            user_id: User UUID
            request: Export request parameters

        Returns:
            Export response with file details
        """
        export_id = str(uuid4())
        start_time = datetime.utcnow()

        try:
            logger.info(f"Starting export {export_id} for user {user_id}")

            # Fetch all user data
            data = self.repository.fetch_user_financial_data(
                user_id=user_id,
                date_from=request.date_from,
                date_to=request.date_to,
                include_deleted=request.include_deleted
            )

            # Transform data to CSV format
            csv_rows = self._transform_data_for_export(data)

            # Generate CSV content
            csv_content = self.csv_handler.generate_csv(csv_rows)

            # Save to temporary file
            export_file = self.export_dir / f"export_{export_id}.csv"
            export_file.write_text(csv_content, encoding="utf-8")

            # Calculate statistics
            file_size = len(csv_content.encode("utf-8"))
            row_count = len(csv_rows)

            logger.info(
                f"Export {export_id} completed: {row_count} rows, {file_size} bytes"
            )

            return ExportResponse(
                export_id=export_id,
                status=ExportStatus.COMPLETED,
                file_size=file_size,
                row_count=row_count,
                download_url=f"/api/v1/data_transfer/export/{export_id}/download",
                created_at=start_time,
                completed_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Export {export_id} failed: {str(e)}")
            return ExportResponse(
                export_id=export_id,
                status=ExportStatus.FAILED,
                created_at=start_time,
                completed_at=datetime.utcnow(),
                error_message=str(e)
            )

    def get_export_file(self, export_id: str, user_id: UUID) -> Optional[Tuple[str, str]]:
        """
        Get exported file content.

        Args:
            export_id: Export job ID
            user_id: User ID for verification

        Returns:
            Tuple of (content, filename) or None if not found
        """
        export_file = self.export_dir / f"export_{export_id}.csv"

        if not export_file.exists():
            logger.warning(f"Export file not found: {export_id}")
            return None

        try:
            content = export_file.read_text(encoding="utf-8")
            filename = f"financial_data_export_{datetime.now().strftime('%Y%m%d')}.csv"
            return content, filename
        except Exception as e:
            logger.error(f"Error reading export file {export_id}: {e}")
            return None

    def _transform_data_for_export(self, data: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        Transform database entities to CSV rows.

        Args:
            data: Dictionary of entity lists

        Returns:
            List of CSV row dictionaries
        """
        rows = []

        # Build lookup maps for relationship resolution
        broker_map = {b.id: b.name for b in data.get("brokers", [])}
        account_map = {a.id: a for a in data.get("accounts", [])}
        card_map = {c.id: c for c in data.get("credit_cards", [])}
        category_map = {c.id: c for c in data.get("categories", [])}
        vendor_map = {v.id: v.name for v in data.get("vendors", [])}
        subscription_map = {s.id: s for s in data.get("subscriptions", [])}

        # Build installment lookup
        installment_map = {}
        for plan in data.get("installment_plans", []):
            for installment in plan.installments:
                installment_map[installment.id] = {
                    "plan": plan,
                    "installment": installment
                }

        # Process transactions
        for transaction in data.get("transactions", []):
            row = {
                # Transaction fields
                "transaction_date": transaction.date,
                "transaction_amount": transaction.amount,
                "transaction_description": transaction.description,
                "transaction_movement_type": transaction.movement_type,
                "transaction_is_paid": transaction.is_paid,
                "transaction_ignored": transaction.ignored,
            }

            # Add broker name
            row["broker_name"] = broker_map.get(transaction.broker_id, "")

            # Add account information
            if transaction.account_id and transaction.account_id in account_map:
                account = account_map[transaction.account_id]
                row["account_name"] = account.name
                row["account_type"] = account.type
                row["account_currency"] = account.currency
                row["account_description"] = account.description

            # Add credit card information
            if transaction.credit_card_id and transaction.credit_card_id in card_map:
                card = card_map[transaction.credit_card_id]
                row["credit_card_name"] = card.name
                row["credit_card_brand"] = card.brand
                row["credit_card_last_four"] = card.last_four_digits
                row["credit_card_limit"] = card.credit_limit
                row["credit_card_due_date"] = card.due_date

            # Add transfer information
            if transaction.from_account_id and transaction.from_account_id in account_map:
                row["from_account_name"] = account_map[transaction.from_account_id].name
            if transaction.to_account_id and transaction.to_account_id in account_map:
                row["to_account_name"] = account_map[transaction.to_account_id].name

            # Add category information
            if transaction.category_id and transaction.category_id in category_map:
                category = category_map[transaction.category_id]
                row["category_name"] = category.name
                # Add parent category if exists
                if category.parent_id and category.parent_id in category_map:
                    row["category_parent"] = category_map[category.parent_id].name

            # Add vendor information
            if transaction.vendor_id:
                row["vendor_name"] = vendor_map.get(transaction.vendor_id, "")
                # Get vendor website if available
                vendor = next(
                    (v for v in data.get("vendors", []) if v.id == transaction.vendor_id),
                    None
                )
                if vendor:
                    row["vendor_website"] = vendor.website

            # Add subscription information
            if transaction.subscription_id and transaction.subscription_id in subscription_map:
                subscription = subscription_map[transaction.subscription_id]
                row["subscription_name"] = subscription.name
                row["subscription_amount"] = subscription.amount
                # Extract enum value (not the enum object itself)
                row["subscription_billing_cycle"] = subscription.billing_cycle.value if hasattr(subscription.billing_cycle, 'value') else subscription.billing_cycle
                row["subscription_next_due_date"] = subscription.next_due_date

            # Add installment information
            if transaction.installment_id and transaction.installment_id in installment_map:
                inst_data = installment_map[transaction.installment_id]
                plan = inst_data["plan"]
                installment = inst_data["installment"]
                row["installment_plan_name"] = plan.name
                row["installment_number"] = installment.number
                row["installment_total_amount"] = plan.total_amount
                row["installment_count"] = plan.installment_count

            rows.append(row)

        return rows

    # ==================== IMPORT METHODS ====================

    def validate_csv(
        self,
        user_id: UUID,
        csv_content: str
    ) -> ImportValidationResult:
        """
        Validate CSV content without importing.

        Args:
            user_id: User UUID
            csv_content: CSV file content

        Returns:
            Validation result with errors and warnings
        """
        try:
            # Parse CSV
            rows, parse_errors = self.csv_handler.parse_csv(csv_content)

            if parse_errors:
                return ImportValidationResult(
                    valid=False,
                    row_count=len(rows),
                    errors=parse_errors
                )

            # Extract unique entities
            entities = self.csv_handler.extract_unique_entities(rows)

            # Estimate entity counts
            estimated = {
                "brokers": len(entities.get("brokers", set())),
                "accounts": len(entities.get("accounts", set())),
                "credit_cards": len(entities.get("credit_cards", set())),
                "categories": len(entities.get("categories", set())),
                "vendors": len(entities.get("vendors", set())),
                "subscriptions": len(entities.get("subscriptions", set())),
                "transactions": len(rows)
            }

            # Check for potential issues
            warnings = []
            if len(rows) > 10000:
                warnings.append(
                    f"Large import: {len(rows)} transactions may take several minutes"
                )

            return ImportValidationResult(
                valid=True,
                row_count=len(rows),
                estimated_entities=estimated,
                warnings=warnings,
                errors=[]
            )

        except Exception as e:
            logger.error(f"CSV validation failed: {e}")
            return ImportValidationResult(
                valid=False,
                row_count=0,
                errors=[str(e)]
            )

    def import_user_data(
        self,
        user_id: UUID,
        csv_content: str,
        request: ImportRequest
    ) -> ImportResponse:
        """
        Import financial data from CSV.

        Args:
            user_id: User UUID
            csv_content: CSV file content
            request: Import request parameters

        Returns:
            Import response with statistics
        """
        import_id = str(uuid4())
        start_time = datetime.utcnow()

        try:
            logger.info(f"Starting import {import_id} for user {user_id}")

            # Validate first if requested
            if request.validate_only:
                validation = self.validate_csv(user_id, csv_content)
                return ImportResponse(
                    import_id=import_id,
                    status=ImportStatus.COMPLETED if validation.valid else ImportStatus.FAILED,
                    created_at=start_time,
                    completed_at=datetime.utcnow(),
                    errors=validation.errors,
                    warnings=validation.warnings
                )

            # Parse CSV
            rows, parse_errors = self.csv_handler.parse_csv(csv_content)

            if parse_errors and not request.skip_errors:
                return ImportResponse(
                    import_id=import_id,
                    status=ImportStatus.FAILED,
                    created_at=start_time,
                    completed_at=datetime.utcnow(),
                    errors=parse_errors
                )

            # Extract unique entities
            entities = self.csv_handler.extract_unique_entities(rows)

            # Create entities in dependency order
            entity_map = self._create_entities(user_id, entities)

            # Import transactions
            import_stats = self._import_transactions(
                user_id,
                rows,
                entity_map,
                request.skip_errors
            )

            # Commit all changes
            self.repository.commit_import()

            logger.info(
                f"Import {import_id} completed: {import_stats.processed_rows} rows processed"
            )

            return ImportResponse(
                import_id=import_id,
                status=ImportStatus.COMPLETED,
                statistics=import_stats,
                entities_created=entity_map["stats"],
                created_at=start_time,
                completed_at=datetime.utcnow(),
                errors=parse_errors if request.skip_errors else [],
                warnings=[]
            )

        except Exception as e:
            logger.error(f"Import {import_id} failed: {str(e)}")
            self.repository.rollback_import()

            return ImportResponse(
                import_id=import_id,
                status=ImportStatus.FAILED,
                created_at=start_time,
                completed_at=datetime.utcnow(),
                errors=[str(e)]
            )

    def _create_entities(
        self,
        user_id: UUID,
        entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create all entities in dependency order.

        Args:
            user_id: User UUID
            entities: Dictionary of entity sets

        Returns:
            Dictionary mapping entity names to IDs
        """
        entity_map = {
            "brokers": {},
            "accounts": {},
            "credit_cards": {},
            "categories": {},
            "vendors": {},
            "subscriptions": {},
            "installment_plans": {},
            "stats": EntityCreationStats()
        }

        # Create brokers
        for broker_name in entities.get("brokers", set()):
            broker = self.repository.find_or_create_broker(user_id, broker_name)
            entity_map["brokers"][broker_name] = broker.id
            if self.db.new and broker in self.db.new:
                entity_map["stats"].brokers += 1

        # Create accounts
        for account_name, broker_name, account_type, currency in entities.get("accounts", set()):
            broker_id = entity_map["brokers"].get(broker_name)
            if not broker_id:
                # Create broker if not found
                broker = self.repository.find_or_create_broker(user_id, broker_name or "Unknown")
                broker_id = broker.id
                entity_map["brokers"][broker_name or "Unknown"] = broker_id

            account = self.repository.find_or_create_account(
                user_id,
                broker_id,
                account_name,
                account_type,
                currency
            )
            entity_map["accounts"][(account_name, broker_name)] = account.id
            if self.db.new and account in self.db.new:
                entity_map["stats"].accounts += 1

        # Create credit cards
        for card_name, account_name, broker_name in entities.get("credit_cards", set()):
            account_key = (account_name, broker_name)
            account_id = entity_map["accounts"].get(account_key)

            if not account_id:
                logger.warning(f"Account not found for credit card: {card_name}")
                continue

            broker_id = entity_map["brokers"].get(broker_name)
            card = self.repository.find_or_create_credit_card(
                user_id,
                broker_id,
                account_id,
                card_name
            )
            entity_map["credit_cards"][card_name] = card.id
            if self.db.new and card in self.db.new:
                entity_map["stats"].credit_cards += 1

        # Create categories (parents first)
        for cat_name, parent_name in entities.get("categories", set()):
            if parent_name is None:  # Parent category
                category = self.repository.find_or_create_category(
                    user_id,
                    cat_name,
                    None
                )
                entity_map["categories"][cat_name] = category.id
                if self.db.new and category in self.db.new:
                    entity_map["stats"].categories += 1

        # Create child categories
        for cat_name, parent_name in entities.get("categories", set()):
            if parent_name is not None and cat_name not in entity_map["categories"]:
                parent_id = entity_map["categories"].get(parent_name)
                category = self.repository.find_or_create_category(
                    user_id,
                    cat_name,
                    parent_id
                )
                entity_map["categories"][cat_name] = category.id
                if self.db.new and category in self.db.new:
                    entity_map["stats"].categories += 1

        # Create vendors
        for vendor_name in entities.get("vendors", set()):
            vendor = self.repository.find_or_create_vendor(user_id, vendor_name)
            entity_map["vendors"][vendor_name] = vendor.id
            if self.db.new and vendor in self.db.new:
                entity_map["stats"].vendors += 1

        # Create subscriptions
        for sub_data in entities.get("subscriptions", set()):
            # Unpack subscription tuple: (name, vendor_name, amount, billing_cycle, next_due_date)
            sub_name = sub_data[0]
            vendor_name = sub_data[1] if len(sub_data) > 1 else ""
            sub_amount_str = sub_data[2] if len(sub_data) > 2 else "0"
            sub_cycle = sub_data[3] if len(sub_data) > 3 else "monthly"
            sub_next_due_str = sub_data[4] if len(sub_data) > 4 else None

            vendor_id = entity_map["vendors"].get(vendor_name) if vendor_name else None

            # Parse amount
            try:
                sub_amount = Decimal(sub_amount_str)
            except (ValueError, InvalidOperation):
                sub_amount = Decimal("0")
                logger.warning(f"Invalid subscription amount for '{sub_name}', using 0")

            # Parse next_due_date
            sub_next_due = None
            if sub_next_due_str:
                try:
                    if isinstance(sub_next_due_str, str):
                        sub_next_due = datetime.fromisoformat(sub_next_due_str).date()
                    else:
                        sub_next_due = sub_next_due_str
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Invalid subscription next_due_date for '{sub_name}': {e}")

            subscription = self.repository.find_or_create_subscription(
                user_id,
                sub_name,
                vendor_id=vendor_id,
                amount=sub_amount,
                billing_cycle=sub_cycle,
                next_due_date=sub_next_due
            )
            entity_map["subscriptions"][sub_name] = subscription.id
            if self.db.new and subscription in self.db.new:
                entity_map["stats"].subscriptions += 1

        return entity_map

    def _import_transactions(
        self,
        user_id: UUID,
        rows: List[Dict[str, Any]],
        entity_map: Dict[str, Any],
        skip_errors: bool
    ) -> ImportStatistics:
        """
        Import transaction rows.

        Args:
            user_id: User UUID
            rows: Parsed CSV rows
            entity_map: Dictionary mapping entity names to IDs
            skip_errors: Whether to skip rows with errors

        Returns:
            Import statistics
        """
        stats = ImportStatistics(
            total_rows=len(rows),
            processed_rows=0,
            skipped_rows=0,
            error_rows=0
        )

        for row_num, row in enumerate(rows, start=1):
            try:
                # Resolve entity references
                broker_name = row.get("broker_name", "Unknown")
                broker_id = entity_map["brokers"].get(broker_name)

                if not broker_id:
                    # Create default broker if not found
                    broker = self.repository.find_or_create_broker(user_id, broker_name)
                    broker_id = broker.id
                    entity_map["brokers"][broker_name] = broker_id

                # Resolve account
                account_id = None
                if account_name := row.get("account_name"):
                    account_key = (account_name, broker_name)
                    account_id = entity_map["accounts"].get(account_key)

                # Resolve credit card
                credit_card_id = None
                if card_name := row.get("credit_card_name"):
                    credit_card_id = entity_map["credit_cards"].get(card_name)

                # Resolve transfer accounts
                from_account_id = None
                to_account_id = None
                if from_account := row.get("from_account_name"):
                    from_key = (from_account, broker_name)
                    from_account_id = entity_map["accounts"].get(from_key)
                if to_account := row.get("to_account_name"):
                    to_key = (to_account, broker_name)
                    to_account_id = entity_map["accounts"].get(to_key)

                # Resolve category
                category_id = None
                if cat_name := row.get("category_name"):
                    category_id = entity_map["categories"].get(cat_name)

                # Resolve vendor
                vendor_id = None
                if vendor_name := row.get("vendor_name"):
                    vendor_id = entity_map["vendors"].get(vendor_name)

                # Resolve subscription
                subscription_id = None
                if sub_name := row.get("subscription_name"):
                    subscription_id = entity_map["subscriptions"].get(sub_name)

                # Create transaction
                transaction = self.repository.create_transaction(
                    user_id=user_id,
                    broker_id=broker_id,
                    date=row["transaction_date"],
                    amount=row["transaction_amount"],
                    description=row["transaction_description"],
                    movement_type=row["transaction_movement_type"],
                    account_id=account_id,
                    credit_card_id=credit_card_id,
                    from_account_id=from_account_id,
                    to_account_id=to_account_id,
                    category_id=category_id,
                    vendor_id=vendor_id,
                    subscription_id=subscription_id,
                    is_paid=row.get("transaction_is_paid", True),
                    ignored=row.get("transaction_ignored", False)
                )

                if transaction:
                    stats.processed_rows += 1
                    entity_map["stats"].transactions += 1
                else:
                    stats.skipped_rows += 1  # Duplicate transaction

            except Exception as e:
                logger.error(f"Error processing row {row_num}: {e}")
                stats.error_rows += 1
                if not skip_errors:
                    raise

        return stats