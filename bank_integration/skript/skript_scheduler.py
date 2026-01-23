import frappe
from bank_integration.skript.skript_transaction import sync_scheduled_transactions_skript


def run_hourly_skript_sync():
    """Run hourly sync for Skript if enabled"""
    try:
        setting = frappe.get_single("Bank Integration Setting")
        
        if (setting.enable_skript and 
            setting.skript_sync_schedule == "Hourly" and  # ← Changed
            setting.skript_sync_status != "In Progress"):  # ← Changed
            
            sync_scheduled_transactions_skript("Bank Integration Setting", "Hourly")
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Skript Hourly Sync Error")


def run_daily_skript_sync():
    """Run daily sync for Skript if enabled"""
    try:
        setting = frappe.get_single("Bank Integration Setting")
        
        if (setting.enable_skript and 
            setting.skript_sync_schedule == "Daily" and 
            setting.skript_sync_status != "In Progress"):
            
            sync_scheduled_transactions_skript("Bank Integration Setting", "Daily")
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Skript Daily Sync Error")


def run_weekly_skript_sync():
    """Run weekly sync for Skript if enabled"""
    try:
        setting = frappe.get_single("Bank Integration Setting")
        
        if (setting.enable_skript and 
            setting.skript_sync_schedule == "Weekly" and 
            setting.skript_sync_status != "In Progress"):
            
            sync_scheduled_transactions_skript("Bank Integration Setting", "Weekly")
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Skript Weekly Sync Error")


def run_monthly_skript_sync():
    """Run monthly sync for Skript if enabled"""
    try:
        setting = frappe.get_single("Bank Integration Setting")
        
        if (setting.enable_skript and 
            setting.skript_sync_schedule == "Monthly" and 
            setting.skript_sync_status != "In Progress"):
            
            sync_scheduled_transactions_skript("Bank Integration Setting", "Monthly")
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Skript Monthly Sync Error")

def complete_skript_sync():
    """Find START scheduler jobs and mark them completed"""

    try:
        setting = frappe.get_single("Bank Integration Setting")

        if not (setting.enable_skript and setting.skript_sync_status == "In Progress"):
            frappe.log("Skript sync not in progress or not enabled; skipping completion.")
            return

        # Get all START jobs (latest first)
        jobs = frappe.db.get_all(
            "Scheduled Job Log",
            filters={
                "scheduled_job_type": "skript_scheduler.run_hourly_skript_sync",
                "status": "Start",
            },
            fields=["name", "creation"],
            order_by="creation desc",
        )

        # Nothing to process
        if not jobs:
            return

        for job in jobs:
            # Mark scheduler job as completed
            frappe.db.set_value(
                "Scheduled Job Log",
                job.name,
                {
                    "status": "Complete",
                },
                update_modified=False,
            )

        # Mark Skript sync as completed (only once)
        setting.skript_sync_status = "Completed"
        setting.skript_last_sync_date = frappe.utils.now()
        setting.save(ignore_permissions=True)

        frappe.db.commit()

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Skript Sync Completion Error"
        )
