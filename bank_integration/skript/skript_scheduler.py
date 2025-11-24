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
