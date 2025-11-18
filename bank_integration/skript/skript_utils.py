import frappe
from datetime import datetime


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
    
    Args:
        date_string: ISO8601 datetime string from Skript
                    Examples: '2025-10-23T11:00:09+11:00' or '2025-10-23T00:00:09Z'
    
    Returns:
        datetime: Timezone-naive datetime object for ERPNext
    """
    if not date_string:
        return frappe.utils.now()
    
    try:
        # Method 1: Use Frappe's built-in parser (handles timezones automatically)
        dt = frappe.utils.get_datetime(date_string)
        
        # Ensure it's timezone-naive (ERPNext requirement)
        if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
            # Convert to UTC first, then remove timezone
            import pytz
            utc_dt = dt.astimezone(pytz.UTC)
            dt = utc_dt.replace(tzinfo=None)
        
        return dt
        
    except Exception as e:
        # Fallback: Manual parsing
        try:
            # Remove 'Z' and replace with '+00:00' for UTC
            clean_date = date_string.replace('Z', '+00:00')
            
            # Parse with timezone
            from datetime import datetime
            dt_with_tz = datetime.fromisoformat(clean_date)
            
            # Remove timezone info (make naive)
            if dt_with_tz.tzinfo is not None:
                import pytz
                utc_dt = dt_with_tz.astimezone(pytz.UTC)
                dt = utc_dt.replace(tzinfo=None)
            else:
                dt = dt_with_tz
            
            return dt
            
        except Exception as parse_error:
            frappe.log_error(
                f"Date parse error for '{date_string}': {str(e)}\nFallback error: {str(parse_error)}", 
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
    
    # Return in format: YYYY-MM-DD HH:MM:SS (no timezone)
    return dt.strftime('%Y-%m-%d %H:%M:%S')