import frappe
from datetime import datetime

def map_airwallex_status_to_erpnext(airwallex_status):
    """
    Maps Airwallex transaction status to ERPNext Bank Transaction status.

    Args:
        airwallex_status (str): Airwallex transaction status

    Returns:
        str: ERPNext Bank Transaction status
    """
    status_mapping = {
        "PENDING": "Unreconciled",
        "SETTLED": "Settled",
        "CANCELLED": "Cancelled"
    }

    return status_mapping.get(airwallex_status.upper(), "Unreconciled")

def map_airwallex_to_erpnext(txn, bank_account):
    """
    Maps an Airwallex transaction to ERPNext Bank Transaction format.

    Args:
        txn (dict): Airwallex transaction payload.
        bank_account (str): ERPNext Bank Account name.

    Returns:
        dict: ERPNext Bank Transaction dictionary.
    """
    # Get the amount first
    amount = txn.get("net", 0)

    # Determine transaction direction
    is_deposit = amount > 0

    # Get transaction currency
    txn_currency = txn.get("currency", "")

    # Check if bank account currency matches transaction currency
    mapped_bank_account = None
    if bank_account and txn_currency:
        try:
            # Fetch the bank account currency from the database
            account = frappe.db.get_value("Bank Account", bank_account, "account")
            bank_account_currency = frappe.db.get_value("Account", account, "account_currency")

            # Only map if currencies match
            if bank_account_currency == txn_currency:
                mapped_bank_account = bank_account
            else:
                frappe.logger().info(
                    f"Currency mismatch: Transaction {txn.get('id')} currency {txn_currency} "
                    f"doesn't match Bank Account {bank_account} currency {bank_account_currency}"
                )
        except Exception as e:
            frappe.log_error(f"Error fetching bank account currency: {str(e)}")

    return {
        "doctype": "Bank Transaction",
        "date": txn.get("created_at", "")[:10],  # YYYY-MM-DD
        "status": map_airwallex_status_to_erpnext(txn.get("status", "PENDING")),
        "bank_account": mapped_bank_account,
        "currency": txn_currency,
        "description": txn.get("description") or txn.get("source_type", ""),
        "reference_number": txn.get("batch_id", ""),
        "transaction_id": txn.get("id"),
        "transaction_type": txn.get("transaction_type", ""),
        "deposit": amount if is_deposit else 0,
        "withdrawal": abs(amount) if not is_deposit else 0,  # Use abs() for withdrawal amounts
        "airwallex_source_type": txn.get("source_type", ""),
        "airwallex_source_id": txn.get("source_id", "")
    }

def test_airwallex_mapping():
    # bench execute bank_integration.bank_integration.airwallex.utils.test_airwallex_mapping
    airwallex_txn = {
    "amount": 200.21,
    "batch_id": "bat_20201202_SGD_2",
    "client_rate": 6.93,
    "created_at": "2021-03-22T16:08:02",
    "currency": "CNY",
    "currency_pair": "AUDUSD",
    "description": "deposit to",
    "estimated_settled_at": "2021-03-22T16:08:02",
    "fee": 0,
    "funding_source_id": "99d23411-234-22dd-23po-13sd7c267b9e",
    "id": "7f687fe6-dcf4-4462-92fa-80335301d9d2",
    "net": 100.21,
    "settled_at": "2021-03-22T16:08:02",
    "source_id": "9f687fe6-dcf4-4462-92fa-80335301d9d2",
    "source_type": "PAYMENT_ATTEMPT",
    "status": "PENDING",
    "transaction_type": "PAYMENT"
    }

    erpnext_txn = map_airwallex_to_erpnext(airwallex_txn, "Your Bank Account Name")
    doc = frappe.get_doc(erpnext_txn)
    doc.insert()
    print(f"Created: {doc.name}")

