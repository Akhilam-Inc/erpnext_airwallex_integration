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
        "PENDING": "Pending",
        "SETTLED": "Settled",
        "CANCELLED": "Cancelled"
    }

    return status_mapping.get(airwallex_status.upper(), "Pending")

def map_airwallex_to_erpnext(txn, bank_account):
    """
    Maps an Airwallex transaction to ERPNext Bank Transaction format.

    Args:
        txn (dict): Airwallex transaction payload.
        bank_account_lookup (dict): Mapping of funding_source_id to ERPNext Bank Account name.

    Returns:
        dict: ERPNext Bank Transaction dictionary.
    """
    # Get the amount first
    amount = txn.get("net", 0)

    # Determine transaction direction
    is_deposit = amount > 0

    return {
        "doctype": "Bank Transaction",
        "date": txn.get("created_at", "")[:10],  # YYYY-MM-DD
        "status": map_airwallex_status_to_erpnext(txn.get("status", "PENDING")),
        # "bank_account": bank_account,
        "currency": txn.get("currency", "USD"),
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
    # bench execute bank_integration.bank_integration.airwallex.utils test_airwallex_mapping
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

	erpnext_txn = map_airwallex_to_erpnext(airwallex_txn)
	import frappe
	doc = frappe.get_doc(erpnext_txn)
	doc.insert()
	print(f"Created: {doc.name}")

