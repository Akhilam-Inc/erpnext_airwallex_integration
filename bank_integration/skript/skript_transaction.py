import frappe
from bank_integration.skript.api.skript_transactions_api import SkriptTransactions
from bank_integration.skript.api.skript_base_api import SkriptAPIError
from bank_integration.skript.skript_utils import map_skript_to_erpnext, format_datetime_for_skript_filter , parse_skript_to_system_timezone
from datetime import datetime , timedelta
import traceback


# def sync_skript_transactions(setting_name , from_date = None, to_date = None):
#     """
#     Sync Skript transactions for the configured consumer
#     """
#     settings = frappe.get_doc("Bank Integration Setting", setting_name)
    
#     if not settings.enable_skript:
#         frappe.logger().info("Skript integration is not enabled")
#         return
    
#     # Validate account mapping
#     unmapped = []
#     for row in settings.skript_accounts:
#         if not row.bank_account:
#             unmapped.append(row.display_name or row.account_id)
    
#     if unmapped:
#         error_msg = f"Cannot sync - unmapped accounts: {', '.join(unmapped)}"
#         frappe.logger().error(error_msg)
#         settings.update_skript_sync_progress(0, 0, "Failed", False)  # ← Changed
#         frappe.throw(error_msg)
#         return 0, 0
    
#     # Build account mapping dictionary
#     account_map = {}
#     for row in settings.skript_accounts:
#         account_map[row.account_id] = row.bank_account
    
#     try:
#         # Initialize API
#         api = SkriptTransactions(
#             consumer_id=settings.skript_consumer_id,
#             client_id=settings.get_password("skript_client_id"),
#             client_secret=settings.get_password("skript_client_secret"),
#             api_url=settings.skript_api_url,
#             api_scope=settings.skript_api_scope
#         )
        
#         # Format dates
#         from_date_str = format_datetime_for_skript_filter(from_date)
#         to_date_str = format_datetime_for_skript_filter(to_date)
#         filter_expr = f"postingDateTime BETWEEN {{ts '{from_date_str}'}} AND {{ts '{to_date_str}'}}"
        
#         frappe.logger().info(f"Skript sync starting: {from_date_str} to {to_date_str}")
        
#         # Fetch transactions
#         response = api.get_list_all(filter=filter_expr, size=100)
        
#         if isinstance(response, dict):
#             transactions = response.get('items', response.get('data', []))
#         else:
#             transactions = response if isinstance(response, list) else []
        
#         if not transactions:
#             frappe.logger().info("No Skript transactions found")
#             settings.update_skript_sync_progress(0, 0, "Completed" , False)  # ← Changed
#             return 0, 0
        
#         processed = 0
#         created = 0
#         skipped = 0
#         errors = 0
#         latest_modified = None
#         for txn in transactions:
#             try:
#                 pdt = parse_skript_to_system_timezone(txn.get('postingDateTime'))
#                 if not latest_modified or pdt > latest_modified:
#                     latest_modified = pdt
#                 frappe.log_error(title="Skript Transaction", message=f"{latest_modified}")

#                 transaction_id = txn.get('id')
#                 account_id = txn.get('accountId')
                
#                 if not account_id:
#                     skipped += 1
#                     processed += 1
#                     continue
                
#                 bank_account = account_map.get(account_id)
                
#                 if not bank_account:
#                     skipped += 1
#                     processed += 1
#                     continue
                
#                 if transaction_exists(transaction_id):
#                     skipped += 1
#                     processed += 1
#                     continue
                
#                 bank_txn = map_skript_to_erpnext(txn, bank_account)
#                 bank_txn_doc = frappe.get_doc(bank_txn)
#                 bank_txn_doc.insert()
#                 bank_txn_doc.submit()
                
#                 created += 1
#                 processed += 1
                
#                 # Update progress every 10 transactions
#                 if processed % 10 == 0:
#                     settings.update_skript_sync_progress(processed, len(transactions), "In Progress", False)  # ← Changed
            
#             except Exception as txn_error:
#                 errors += 1
#                 frappe.log_error(
#                     f"Failed to process Skript transaction {txn.get('id', 'unknown')}: {str(txn_error)}\n{traceback.format_exc()}",
#                     "Skript Transaction Error"
#                 )
#                 processed += 1
        
#         # Final update
#         final_status = "Completed" if errors == 0 else "Completed with Errors"
#         settings.update_skript_sync_progress(processed, len(transactions), final_status, False)  # ← Changed
#         if latest_modified:
#             settings.db_set('skript_last_sync_date', latest_modified.strftime("%Y-%m-%d %H:%M:%S"))  # ← Changed
        
#         frappe.logger().info(
#             f"Skript sync completed: Processed {processed}, Created {created}, "
#             f"Skipped {skipped}, Errors {errors}"
#         )
        
#         return processed, created
    
#     except Exception as e:
#         settings.update_skript_sync_progress(0, 0, "Failed", False)  # ← Changed
#         error_msg = f"Skript sync failed: {str(e)}"
#         frappe.log_error(f"{error_msg}\n{traceback.format_exc()}", "Skript Sync Error")
#         frappe.logger().error(error_msg)
#         return 0, 0

def sync_skript_transactions(setting_name, from_date=None, to_date=None):
    """
    Sync Skript transactions iteratively until no more records are found.
    Uses a 'Watermark' strategy: fetch > last_sync_date.
    """
    settings = frappe.get_doc("Bank Integration Setting", setting_name)
    
    if not settings.enable_skript:
        frappe.logger().info("Skript integration is not enabled")
        return 0, 0
    
    # --- 1. Validate Mapping ---
    unmapped = []
    for row in settings.skript_accounts:
        if not row.bank_account:
            unmapped.append(row.display_name or row.account_id)
    
    if unmapped:
        error_msg = f"Cannot sync - unmapped accounts: {', '.join(unmapped)}"
        frappe.logger().error(error_msg)
        settings.update_skript_sync_progress(0, 0, "Failed", False)
        frappe.throw(error_msg)
        return 0, 0
    
    account_map = {row.account_id: row.bank_account for row in settings.skript_accounts}
    
    try:
        # --- 2. Initialize API ---
        api = SkriptTransactions(
            consumer_id=settings.skript_consumer_id,
            client_id=settings.get_password("skript_client_id"),
            client_secret=settings.get_password("skript_client_secret"),
            api_url=settings.skript_api_url,
            api_scope=settings.skript_api_scope
        )

        total_processed = 0
        total_created = 0
        total_errors = 0
        
        # Determine the initial start time for the sync loop
        # Priority: 1. DB Last Sync, 2. Manual from_date, 3. Default (30 days ago)
        current_cursor = None
        
        if settings.skript_last_sync_date:
            current_cursor = frappe.utils.get_datetime(from_date)
        elif from_date:
            current_cursor = frappe.utils.get_datetime(from_date)
        else:
            # Fallback: If never synced, look back 30 days
            current_cursor = frappe.utils.add_days(frappe.utils.now(), -30)

        loop_count = 0
        MAX_LOOPS = 100  # Safety break to prevent infinite loops

        # --- 3. Sync Loop ---
        while True:
            loop_count += 1
            if loop_count > MAX_LOOPS:
                frappe.logger().warning("Skript Sync hit max loop limit (100 batches). Stopping safely.")
                break

            # Format the filter date
            filter_date_str = format_datetime_for_skript_filter(current_cursor)
            
            # Construct Filter: postingDateTime > Last Sync
            filter_expr = f"postingDateTime > {{ts '{filter_date_str}'}}"
            
            frappe.logger().info(f"Skript Sync Batch {loop_count}: Fetching > {filter_date_str}")
            
            # Fetch transactions
            response = api.get_list_all(filter=filter_expr, size=100)
            
            # Normalize response
            if isinstance(response, dict):
                transactions = response.get('items', response.get('data', []))
            else:
                transactions = response if isinstance(response, list) else []
            
            # --- EXIT CONDITION: No more data ---
            if not transactions:
                frappe.logger().info("No more Skript transactions found. Sync complete.")
                break
            
            batch_processed = 0
            batch_max_date = None
            
            for txn in transactions:
                try:
                    # Track the latest date in this batch for the next loop
                    # Using parse_skript_date from utils (assuming it returns datetime)
                    txn_dt = parse_skript_to_system_timezone(txn.get('postingDateTime'))
                    
                    # Update local batch max
                    if not batch_max_date or (txn_dt and txn_dt > batch_max_date):
                        batch_max_date = txn_dt + timedelta(seconds=1)

                    # Business Logic
                    transaction_id = txn.get('id')
                    account_id = txn.get('accountId')
                    
                    if not account_id or not account_map.get(account_id):
                        total_processed += 1
                        continue
                        
                    if transaction_exists(transaction_id):
                        total_processed += 1
                        continue
                    
                    bank_account = account_map.get(account_id)
                    bank_txn = map_skript_to_erpnext(txn, bank_account)
                    
                    bank_txn_doc = frappe.get_doc(bank_txn)
                    bank_txn_doc.insert()
                    bank_txn_doc.submit()
                    
                    total_created += 1
                    total_processed += 1
                    batch_processed += 1

                except Exception as txn_error:
                    total_errors += 1
                    frappe.log_error(
                        f"Skript Txn Error {txn.get('id')}: {str(txn_error)}",
                        "Skript Transaction Error"
                    )
            
            # --- 4. Update Watermark & Save Progress ---
            # If we found a newer date in this batch, update settings immediately
            if batch_max_date and batch_max_date > current_cursor:
                current_cursor = batch_max_date
                settings.db_set('skript_last_sync_date', current_cursor.strftime("%Y-%m-%d %H:%M:%S"))
                settings.save()
                frappe.db.commit() # Commit explicitly to save progress
            # Update Progress Bar (optional)
            settings.update_skript_sync_progress(total_processed, total_processed + 100, "In Progress", False)

        # Final Status Update
        final_status = "Completed" if total_errors == 0 else "Completed with Errors"
        settings.update_skript_sync_progress(total_processed, total_processed, final_status, False)
        
        return total_processed, total_created
    
    except Exception as e:
        settings.update_skript_sync_progress(0, 0, "Failed", False)
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
        if setting.skript_sync_status == "In Progress":
            # Safety check: if stuck in progress for > 1 hour, reset it
            if setting.modified and (frappe.utils.now_datetime() - frappe.utils.get_datetime(setting.modified)).total_seconds() > 3600:
                 frappe.logger().info("Resetting stuck Skript sync status")
                 setting.db_set('skript_sync_status', 'Not Started')  # ← Changed
            else:
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
                start_date = end_date - timedelta(hours=1)
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
        sync_skript_transactions( "Bank Integration Setting", start_date, end_date)
        
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


