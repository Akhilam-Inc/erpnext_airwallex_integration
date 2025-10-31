# Data Mapping

## Overview

This document describes how Airwallex transaction data is mapped to ERPNext Bank Transaction format.

## Mapping Function

The core mapping function is located in `bank_integration/airwallex/utils.py`:

```python
def map_airwallex_to_erpnext(txn, bank_account)
```

## Field Mapping

### Direct Mappings

| ERPNext Field | Airwallex Field | Transformation |
|---------------|-----------------|----------------|
| `date` | `created_at` | Extract date part (YYYY-MM-DD) |
| `currency` | `currency` | Direct mapping |
| `description` | `description` or `source_type` | Use description, fallback to source_type |
| `reference_number` | `batch_id` | Direct mapping |
| `transaction_id` | `id` | Direct mapping (used for duplicate detection) |
| `transaction_type` | `transaction_type` | Direct mapping |
| `airwallex_source_type` | `source_type` | Custom field |
| `airwallex_source_id` | `source_id` | Custom field |

### Conditional Mappings

#### Status Mapping

```python
def map_airwallex_status_to_erpnext(airwallex_status):
    status_mapping = {
        "PENDING": "Unreconciled",
        "SETTLED": "Settled",
        "CANCELLED": "Cancelled"
    }
    return status_mapping.get(airwallex_status.upper(), "Unreconciled")
```

| Airwallex Status | ERPNext Status |
|------------------|----------------|
| PENDING | Unreconciled |
| SETTLED | Settled |
| CANCELLED | Cancelled |
| *Other* | Unreconciled (default) |

#### Amount Mapping

```python
amount = txn.get("net", 0)
is_deposit = amount > 0

# In ERPNext format:
"deposit": amount if is_deposit else 0,
"withdrawal": abs(amount) if not is_deposit else 0
```

- **Positive amount**: Mapped to `deposit`
- **Negative amount**: Mapped to `withdrawal` (absolute value)

#### Bank Account Mapping

```python
# Get transaction currency
txn_currency = txn.get("currency", "")

# Check if bank account currency matches
mapped_bank_account = None
if bank_account and txn_currency:
    # Fetch the bank account's currency
    account = frappe.db.get_value("Bank Account", bank_account, "account")
    bank_account_currency = frappe.db.get_value("Account", account, "account_currency")

    # Only map if currencies match
    if bank_account_currency == txn_currency:
        mapped_bank_account = bank_account
    else:
        frappe.logger().info("Currency mismatch")
```

**Logic**:
1. Get transaction currency
2. Get bank account's linked GL account currency
3. Compare currencies
4. If match: assign bank account
5. If mismatch: leave bank account blank

**Rationale**: Prevents incorrectly assigning transactions to wrong-currency bank accounts.

## Sample Transformation

### Input (Airwallex)

```json
{
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
```

### Output (ERPNext Bank Transaction)

```python
{
  "doctype": "Bank Transaction",
  "date": "2021-03-22",
  "status": "Unreconciled",
  "bank_account": "HSBC Bank - CNY",  # Only if currency matches
  "currency": "CNY",
  "description": "deposit to",
  "reference_number": "bat_20201202_SGD_2",
  "transaction_id": "7f687fe6-dcf4-4462-92fa-80335301d9d2",
  "transaction_type": "PAYMENT",
  "deposit": 100.21,
  "withdrawal": 0,
  "airwallex_source_type": "PAYMENT_ATTEMPT",
  "airwallex_source_id": "9f687fe6-dcf4-4462-92fa-80335301d9d2"
}
```

## Custom Fields

The app adds custom fields to the Bank Transaction doctype:

| Field Name | Type | Purpose |
|------------|------|---------|
| `airwallex_source_type` | Data | Store Airwallex source type for reference |
| `airwallex_source_id` | Data | Store Airwallex source ID for traceability |

These fields are defined in `fixtures/custom_field.json`.

## Edge Cases

### Missing Description
```python
"description": txn.get("description") or txn.get("source_type", "")
```
Falls back to `source_type` if description is empty.

### Missing Net Amount
```python
amount = txn.get("net", 0)
```
Defaults to 0 if net amount is not provided.

### Negative Withdrawals
```python
"withdrawal": abs(amount) if not is_deposit else 0
```
Uses absolute value to ensure withdrawal is always positive.

### Missing Currency
```python
txn_currency = txn.get("currency", "")
if bank_account and txn_currency:
    # Only proceed if currency exists
```
Leaves bank account blank if transaction currency is missing.

## Testing Mapping

A test function is provided:

```python
def test_airwallex_mapping():
    # bench execute bank_integration.bank_integration.airwallex.utils.test_airwallex_mapping
    airwallex_txn = { /* sample transaction */ }

    erpnext_txn = map_airwallex_to_erpnext(airwallex_txn, "Your Bank Account Name")
    doc = frappe.get_doc(erpnext_txn)
    doc.insert()
    print(f"Created: {doc.name}")
```

Run via:
```bash
bench --site [site-name] execute bank_integration.bank_integration.airwallex.utils.test_airwallex_mapping
```

## Best Practices

1. **Verify Currency Mapping**: Ensure bank account currencies match transaction currencies
2. **Check Custom Fields**: Verify custom fields are created in Bank Transaction
3. **Test with Sample Data**: Use test function before production sync
4. **Review Logs**: Check for currency mismatch warnings
5. **Handle Nulls**: The mapping handles missing fields gracefully
6. **Preserve Source Data**: Original Airwallex IDs stored for audit trail
