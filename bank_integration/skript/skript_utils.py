import frappe
import pytz
from datetime import datetime, timedelta


def map_skript_to_erpnext(skript_txn, bank_account):
    """
    Map Skript transaction to ERPNext Bank Transaction
    
    Args:
        skript_txn: Transaction dict from Skript API
        bank_account: ERPNext Bank Account name
    
    Returns:
        dict: Bank Transaction document dict
    """
    amount = float(skript_txn.get('amount', 0))
    
    return {
        "doctype": "Bank Transaction",
        "bank_account": bank_account,
        "transaction_id": skript_txn.get('id'),
        "date": parse_skript_date(skript_txn.get('postingDateTime')),
        "deposit": amount if amount > 0 else 0,
        "withdrawal": abs(amount) if amount < 0 else 0,
        "currency": skript_txn.get('currency', 'AUD'),
        "description": skript_txn.get('description', ''),
        "reference_number": skript_txn.get('reference', ''),
        "transaction_type": skript_txn.get('type', ''),
        # Note: If you add custom fields to Bank Transaction for Skript metadata,
        # uncomment and use these:
        # "skript_account_id": skript_txn.get('accountId'),
        # "skript_data_holder": skript_txn.get('dataHolderName'),
    }


def parse_skript_date(date_string):
    """
    Parse Skript date to ERPNext datetime (timezone-naive)
    Preserves the local date/time from the original timezone
    """
    if not date_string:
        return frappe.utils.now()
    
    try:
        # Parse the ISO8601 datetime with timezone
        dt_with_tz = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        
        # Simply remove timezone to preserve local date/time
        # DO NOT convert to UTC - this causes date shifts
        naive_dt = dt_with_tz.replace(tzinfo=None)
        
        return naive_dt
        
    except Exception as e:
        frappe.log_error(
            f"Date parse error for '{date_string}': {str(e)}", 
            "Skript Date Parse"
        )
        return frappe.utils.now()

def format_datetime_for_skript_filter(dt):
    """
    Format datetime for Skript SQL-like filter
    
    Args:
        dt: Python datetime or string
    
    Returns:
        str: Formatted datetime for filter like "2025-01-01 10:30:00"
    """
    if isinstance(dt, str):
        dt = frappe.utils.get_datetime(dt)
    
    system_tz = pytz.timezone(frappe.utils.get_system_timezone())
    # 1. If naive (no timezone), localize to System Timezone
    if dt.tzinfo is None:
        local_dt = system_tz.localize(dt)
    else:
        local_dt = dt
    
    # 2. Convert to UTC
    utc_dt = local_dt.astimezone(pytz.UTC)
    
    # 3. Format strictly for Skript API: YYYY-MM-DD HH:MM:SS
    return utc_dt.strftime('%Y-%m-%d %H:%M:%S')