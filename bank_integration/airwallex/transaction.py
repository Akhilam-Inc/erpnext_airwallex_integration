import frappe
from bank_integration.airwallex.api.financial_transactions import FinancialTransactions
from bank_integration.airwallex.api.base_api import AirwallexAPIError  # Add this import
from bank_integration.airwallex.utils import map_airwallex_to_erpnext
from bank_integration.bank_integration.doctype.bank_integration_log import bank_integration_log as bi_log
from datetime import datetime
import traceback


def sync_transactions(from_date, to_date, setting_name):
    """Sync transactions for all configured clients"""
    settings = frappe.get_doc("Bank Integration Setting", setting_name)

    if not settings.airwallex_clients:
        frappe.throw("No Airwallex clients configured")

    total_processed = 0
    total_created = 0

    for client in settings.airwallex_clients:
        try:
            # Sync transactions for this specific client
            processed, created = sync_client_transactions(
                client, from_date, to_date, settings
            )
            total_processed += processed
            total_created += created

        except Exception as e:
            # Shorten the error message for the log title
            client_short = client.airwallex_client_id[:8] if client.airwallex_client_id else "unknown"
            error_title = f"Sync Error - Client {client_short}"

            # Create detailed error message (truncated to avoid length issues)
            error_message = f"Failed to sync transactions for client {client.airwallex_client_id}: {str(e)[:500]}"

            frappe.log_error(error_message, error_title)

            # Also log to Bank Integration Log
            try:
                bi_log.create_log(
                    f"Sync failed for client {client.airwallex_client_id}: {str(e)[:200]}",
                    status="Error"
                )
            except Exception as log_error:
                frappe.logger().error(f"Failed to create integration log: {str(log_error)}")

    # Update final status
    settings.update_sync_progress(total_processed, total_processed, "Completed")


def sync_client_transactions(client, from_date, to_date, settings):
    """Sync transactions for a specific client"""
    try:
        # Check how FinancialTransactions should be initialized
        # Option 1: If it accepts no parameters
        api = FinancialTransactions()

        # Set credentials manually
        api.client_id = client.airwallex_client_id
        api.api_key = client.get_password("airwallex_api_key")
        api.api_url = settings.api_url

        # Initialize headers if needed
        if hasattr(api, '_initialize_headers'):
            api._initialize_headers()

        # OR Option 2: If it accepts different parameters, check the constructor:
        # api = FinancialTransactions(
        #     api_url=settings.api_url,
        #     client_credentials={
        #         'client_id': client.airwallex_client_id,
        #         'api_key': client.get_password("airwallex_api_key")
        #     }
        # )

        # Force fresh authentication for sync operations
        if hasattr(api, 'ensure_authenticated_headers'):
            api.ensure_authenticated_headers(force_fresh=True)

        transactions = api.get_list(from_created_at=from_date, to_created_at=to_date)
        processed = 0
        created = 0

        if not transactions:
            return 0, 0

        # Handle different response formats
        if isinstance(transactions, dict):
            # If the response is paginated or wrapped
            transactions = transactions.get('items', transactions.get('data', []))

        for txn in transactions:
            try:
                if not transaction_exists(txn.get('id')) and txn.get('currency') == "AUD": # Only sync AUD transactions temporarily
                    # Map transaction to client's bank account
                    bank_txn = map_airwallex_to_erpnext(txn, client.bank_account)
                    bank_txn_doc = frappe.get_doc(bank_txn)
                    bank_txn_doc.insert()
                    created += 1

                processed += 1

                # Update progress periodically (every 10 transactions)
                if processed % 10 == 0:
                    settings.update_sync_progress(processed, len(transactions))

            except Exception as txn_error:
                client_short = client.airwallex_client_id[:8]
                frappe.log_error(
                    f"Failed to process transaction {txn.get('id', 'unknown')}: {str(txn_error)[:300]}",
                    f"Txn Error - {client_short}"
                )
                processed += 1  # Still count as processed even if failed

        # Final progress update
        if hasattr(settings, 'update_sync_progress'):
            settings.update_sync_progress(processed, len(transactions))

        return processed, created

    except AirwallexAPIError as e:
        client_short = client.airwallex_client_id[:8] if client.airwallex_client_id else "unknown"
        frappe.log_error(
            f"API Error for client {client.airwallex_client_id}: {str(e.message)[:300]}",
            f"API Error - {client_short}"
        )
        return 0, 0

    except Exception as e:
        client_short = client.airwallex_client_id[:8] if client.airwallex_client_id else "unknown"
        frappe.log_error(
            f"Sync failed for client {client.airwallex_client_id}: {str(e)[:300]}",
            f"Sync Error - {client_short}"
        )
        return 0, 0


def transaction_exists(transaction_id):
    """
    Check if a Bank Transaction with the given Airwallex source ID already exists
    """
    # Check using the custom field we added for Airwallex source ID
    return frappe.db.exists("Bank Transaction", {"transaction_id": transaction_id})


def sync_scheduled_transactions(setting_name, schedule_type):
    """
    Sync transactions based on schedule type
    """
    from datetime import datetime, timedelta

    try:
        # For single doctype, use get_single instead of get_doc
        setting = frappe.get_single("Bank Integration Setting")

        # Check if sync is already in progress
        if setting.sync_status == "In Progress":
            frappe.logger().info(f"Sync already in progress, skipping {schedule_type} sync")
            return

        if not setting.is_enabled():
            frappe.logger().info(f"Airwallex integration disabled")
            return

        # Set status to prevent concurrent runs
        setting.db_set('sync_status', 'In Progress')
        setting.db_set('last_sync_date', frappe.utils.now())

        # Calculate date range based on schedule type
        end_date = datetime.now().date()

        if schedule_type == "Hourly":
            # Sync last 2 hours
            start_date = (datetime.now() - timedelta(hours=2)).date()
        elif schedule_type == "Daily":
            # Sync yesterday
            start_date = end_date - timedelta(days=1)
        elif schedule_type == "Weekly":
            # Sync last 7 days
            start_date = end_date - timedelta(days=7)
        elif schedule_type == "Monthly":
            # Sync last 30 days
            start_date = end_date - timedelta(days=30)
        else:
            frappe.logger().error(f"Unknown schedule type: {schedule_type}")
            setting.db_set('sync_status', 'Failed')
            return

        bi_log.create_log(f"Starting scheduled {schedule_type} sync from {start_date} to {end_date}")
        frappe.logger().info(f"Starting scheduled {schedule_type} sync from {start_date} to {end_date}")

        # Use the existing sync function with calculated dates
        # Pass the doctype name since it's a single doctype
        sync_transactions(str(start_date), str(end_date), "Bank Integration Setting")

    except Exception as e:
        # Make sure to reset status on error
        try:
            setting = frappe.get_single("Bank Integration Setting")
            setting.db_set('sync_status', 'Failed')
        except:
            pass

        error_msg = f"Scheduled {schedule_type} sync failed: {str(e)}"
        bi_log.create_log(error_msg, status="Error")
        frappe.log_error(frappe.get_traceback(), f"Scheduled Sync Error - {schedule_type}")
        frappe.logger().error(error_msg)
