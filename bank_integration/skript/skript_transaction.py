import frappe
from bank_integration.skript.api.skript_transactions_api import SkriptTransactions
from bank_integration.skript.api.skript_base_api import SkriptAPIError
from bank_integration.skript.skript_utils import map_skript_to_erpnext, format_datetime_for_skript_filter
from datetime import datetime
import traceback


def sync_skript_transactions(from_date, to_date, setting_name):
    """
    Sync Skript transactions for the configured consumer
    """
    settings = frappe.get_doc("Bank Integration Setting", setting_name)
    
    if not settings.enable_skript:
        frappe.logger().info("Skript integration is not enabled")
        return
    
    # Validate account mapping
    unmapped = []
    for row in settings.skript_accounts:
        if not row.bank_account:
            unmapped.append(row.display_name or row.account_id)
    
    if unmapped:
        error_msg = f"Cannot sync - unmapped accounts: {', '.join(unmapped)}"
        frappe.logger().error(error_msg)
        settings.update_skript_sync_progress(0, 0, "Failed")  # ← Changed
        frappe.throw(error_msg)
        return 0, 0
    
    # Build account mapping dictionary
    account_map = {}
    for row in settings.skript_accounts:
        account_map[row.account_id] = row.bank_account
    
    try:
        # Initialize API
        api = SkriptTransactions(
            consumer_id=settings.skript_consumer_id,
            client_id=settings.get_password("skript_client_id"),
            client_secret=settings.get_password("skript_client_secret"),
            api_url=settings.skript_api_url,
            api_scope=settings.skript_api_scope
        )
        
        # Format dates
        from_date_str = format_datetime_for_skript_filter(from_date)
        to_date_str = format_datetime_for_skript_filter(to_date)
        filter_expr = f"postingDateTime BETWEEN {{ts '{from_date_str}'}} AND {{ts '{to_date_str}'}}"
        
        frappe.logger().info(f"Skript sync starting: {from_date_str} to {to_date_str}")
        
        # Fetch transactions
        response = api.get_list_all(filter=filter_expr, size=100)
        
        if isinstance(response, dict):
            transactions = response.get('items', response.get('data', []))
        else:
            transactions = response if isinstance(response, list) else []
        
        if not transactions:
            frappe.logger().info("No Skript transactions found")
            settings.update_skript_sync_progress(0, 0, "Completed")  # ← Changed
            return 0, 0
        
        processed = 0
        created = 0
        skipped = 0
        errors = 0
        
        for txn in transactions:
            try:
                transaction_id = txn.get('id')
                account_id = txn.get('accountId')
                
                if not account_id:
                    skipped += 1
                    processed += 1
                    continue
                
                bank_account = account_map.get(account_id)
                
                if not bank_account:
                    skipped += 1
                    processed += 1
                    continue
                
                if transaction_exists(transaction_id):
                    skipped += 1
                    processed += 1
                    continue
                
                bank_txn = map_skript_to_erpnext(txn, bank_account)
                bank_txn_doc = frappe.get_doc(bank_txn)
                bank_txn_doc.insert()
                bank_txn_doc.submit()
                
                created += 1
                processed += 1
                
                # Update progress every 10 transactions
                if processed % 10 == 0:
                    settings.update_skript_sync_progress(processed, len(transactions))  # ← Changed
            
            except Exception as txn_error:
                errors += 1
                frappe.log_error(
                    f"Failed to process Skript transaction {txn.get('id', 'unknown')}: {str(txn_error)}\n{traceback.format_exc()}",
                    "Skript Transaction Error"
                )
                processed += 1
        
        # Final update
        final_status = "Completed" if errors == 0 else "Completed with Errors"
        settings.update_skript_sync_progress(processed, len(transactions), final_status)  # ← Changed
        settings.db_set('skript_last_sync_date', frappe.utils.now())  # ← Changed
        
        frappe.logger().info(
            f"Skript sync completed: Processed {processed}, Created {created}, "
            f"Skipped {skipped}, Errors {errors}"
        )
        
        return processed, created
    
    except Exception as e:
        settings.update_skript_sync_progress(0, 0, "Failed")  # ← Changed
        error_msg = f"Skript sync failed: {str(e)}"
        frappe.log_error(f"{error_msg}\n{traceback.format_exc()}", "Skript Sync Error")
        frappe.logger().error(error_msg)
        return 0, 0


def sync_scheduled_transactions_skript(setting_name, schedule_type):
    """Sync transactions based on schedule type"""
    from datetime import datetime, timedelta
    
    try:
        setting = frappe.get_single("Bank Integration Setting")
        
        # Check if sync is already in progress
        if setting.skript_sync_status == "In Progress":  # ← Changed
            frappe.logger().info(f"Skript sync already in progress")
            return
        
        if not setting.enable_skript:
            frappe.logger().info("Skript integration disabled")
            return
        
        # Check if schedule matches
        if setting.skript_sync_schedule != schedule_type:  # ← Changed
            return
        
        # Set status
        setting.db_set('skript_sync_status', 'In Progress')  # ← Changed
        
        # Calculate date range
        end_date = frappe.utils.now_datetime()
        
        if setting.skript_last_sync_date:  # ← Changed
            start_date = frappe.utils.get_datetime(setting.skript_last_sync_date)
        else:
            if schedule_type == "Hourly":
                start_date = end_date - timedelta(hours=2)
            elif schedule_type == "Daily":
                start_date = end_date - timedelta(days=1)
            elif schedule_type == "Weekly":
                start_date = end_date - timedelta(days=7)
            elif schedule_type == "Monthly":
                start_date = end_date - timedelta(days=30)
            else:
                setting.db_set('skript_sync_status', 'Failed')  # ← Changed
                return
        
        frappe.logger().info(f"Scheduled Skript {schedule_type} sync: {start_date} to {end_date}")
        
        # Sync
        sync_skript_transactions(start_date, end_date, "Bank Integration Setting")
        
    except Exception as e:
        try:
            setting = frappe.get_single("Bank Integration Setting")
            setting.db_set('skript_sync_status', 'Failed')  # ← Changed
        except:
            pass
        
        error_msg = f"Scheduled Skript {schedule_type} sync failed: {str(e)}"
        frappe.log_error(f"{error_msg}\n{traceback.format_exc()}", f"Skript Scheduled Sync Error")

def transaction_exists(transaction_id):
    """
    Check if a Bank Transaction with the given transaction ID already exists
    """
    return frappe.db.exists("Bank Transaction", {"transaction_id": transaction_id})


