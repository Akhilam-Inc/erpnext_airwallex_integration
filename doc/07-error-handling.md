# Error Handling & Recovery

## Overview

The Bank Integration App implements comprehensive error handling at multiple levels to ensure robust operation and easy troubleshooting.

## Error Handling Layers

### 1. Configuration Validation

**Location**: `bank_integration_setting.py` - `validate()` method

**Checks**:
- At least one Airwallex client configured
- Required fields (Client ID, API Key, Bank Account) populated
- Authentication succeeds before enabling integration

**Behavior**:
```python
def validate(self):
    if self.enable_airwallex:
        if self._credentials_changed():
            if not self.test_authentication_silent():
                self.enable_airwallex = 0
                frappe.msgprint("❌ Authentication failed", indicator="red")
```

**User Experience**: Integration auto-disabled on validation failure.

### 2. API-Level Errors

**Location**: `base_api.py` - `_make_request()` method

#### Authentication Errors (401)

```python
if response.status_code == 401 and not self.is_auth_instance:
    # Clear auth header
    # Get fresh token
    # Retry request automatically
```

**Handling**: Automatic retry with fresh token

#### HTTP Errors (4xx, 5xx)

```python
if response.status_code >= 400:
    error_msg = f"HTTP {response.status_code}: {response.text}"
    frappe.throw(_("Airwallex API request failed: {0}").format(error_msg))
```

**Handling**: Throw error with detailed message

#### Network Errors

```python
except Exception as e:
    error_response = response.text if response else str(e)
    self.create_connection_log(status=500, ...)
    frappe.throw(_("Airwallex API request failed: {0}").format(str(e)))
```

**Handling**: Log error and throw exception

### 3. Transaction-Level Errors

**Location**: `transaction.py` - `sync_client_transactions()` function

#### Duplicate Transactions

```python
if transaction_exists(transaction_id):
    total_skipped += 1
    continue
```

**Handling**: Skip silently, increment counter

#### Duplicate Entry Errors

```python
except frappe.DuplicateEntryError:
    total_processed += 1
    total_skipped += 1
    existing_transaction_ids.add(txn.get('id'))
```

**Handling**: Catch database constraint violation, skip transaction

#### Mapping Errors

```python
if not erpnext_txn.get('transaction_id'):
    frappe.logger().warning("Transaction missing transaction_id")
    total_errors += 1
    total_processed += 1
    continue
```

**Handling**: Log warning, increment error counter, continue

#### General Transaction Errors

```python
except Exception as e:
    total_errors += 1
    total_processed += 1
    frappe.logger().error(f"Error processing transaction: {str(e)}")
    frappe.log_error(traceback.format_exc(), f"Transaction Sync Error")
```

**Handling**: Log error, continue with next transaction

### 4. Client-Level Errors

**Location**: `transaction.py` - `sync_transactions()` function

```python
for client in settings.airwallex_clients:
    try:
        processed, created = sync_client_transactions(...)
        total_processed += processed
        total_created += created
    except Exception as e:
        client_short = client.airwallex_client_id[:8]
        frappe.log_error(
            message=f"Failed to sync for client {client.airwallex_client_id}",
            title=f"Sync Error - {client_short}"
        )
```

**Handling**: Log error, continue with next client

### 5. Sync-Level Errors

**Location**: `transaction.py` - `sync_scheduled_transactions()` function

```python
try:
    sync_transactions(start_date, end_date, setting_name)
    setting.db_set('last_sync_date', frappe.utils.now())
except Exception as e:
    try:
        setting.db_set('sync_status', 'Failed')
    except:
        pass
    frappe.log_error(frappe.get_traceback(), f"Scheduled Sync Error")
```

**Handling**: Set status to Failed, log error, preserve state

## Error Logging

### Bank Integration Log

Custom logging via `bank_integration_log.py`:

```python
bi_log.create_log(
    message="Starting sync from X to Y",
    status="Info"  # or "Error"
)
```

**Purpose**: User-friendly sync history

### Frappe Error Log

Standard error logging:

```python
frappe.log_error(
    message="Detailed error message",
    title="Short Error Title"
)
```

**Purpose**: Developer-level debugging

### Application Logger

```python
frappe.logger().info("Info message")
frappe.logger().warning("Warning message")
frappe.logger().error("Error message")
```

**Purpose**: Console/file logging for monitoring

## Error Recovery Strategies

### Automatic Recovery

| Error Type | Recovery Method |
|------------|-----------------|
| 401 Unauthorized | Auto-refresh token and retry |
| Duplicate transaction | Skip and continue |
| Single transaction error | Log and continue with next |
| Network timeout | Fail and log (retry next scheduled run) |

### Manual Recovery

| Error Scenario | Recovery Steps |
|----------------|----------------|
| Authentication failure | 1. Check credentials<br/>2. Click "Test Authentication"<br/>3. Re-enable if successful |
| Sync stuck "In Progress" | 1. Wait for timeout<br/>2. Click "Restart Sync" |
| Missing transactions | 1. Note date range<br/>2. Use manual sync to backfill |
| Currency mismatch | 1. Review bank account configuration<br/>2. Ensure currencies match<br/>3. Re-sync affected period |

## Concurrent Sync Prevention

```python
if setting.sync_status == "In Progress":
    frappe.logger().info("Sync already in progress, skipping")
    return
```

**Purpose**: Prevent multiple simultaneous syncs that could cause:
- Duplicate transactions
- Database locks
- Resource contention

## Error Notification

### Real-time Notifications

```python
frappe.publish_realtime(
    'transaction_sync_complete',
    {
        'processed': total_processed,
        'created': total_created,
        'skipped': total_skipped,
        'errors': total_errors,
        'status': final_status,
        'message': "Summary message"
    },
    user=frappe.session.user
)
```

**Delivery**: Immediately to active user session

### Status Updates

```python
def update_sync_progress(self, processed, total, status="In Progress"):
    self.db_set('sync_status', status)
    self.db_set('processed_records', processed)
    self.db_set('total_records', total)
    # ... publish realtime update
```

**Purpose**: Keep UI informed of current state

## Common Error Messages

### "No Airwallex clients configured"
**Cause**: No clients in Airwallex Clients table
**Fix**: Add at least one client with valid credentials

### "Authentication failed for one or more clients"
**Cause**: Invalid Client ID or API Key
**Fix**: Verify credentials, test authentication

### "From and To dates are required"
**Cause**: Missing dates for manual sync
**Fix**: Set both From Date and To Date

### "Sync already in progress"
**Cause**: Another sync is running
**Fix**: Wait for completion or reset status

### "Transaction sync failed: [error details]"
**Cause**: Various (network, API, data issues)
**Fix**: Check Error Log for details, address root cause

## Debugging Tools

### Check Sync Status
```python
frappe.get_single("Bank Integration Setting").sync_status
```

### View Recent Errors
```sql
SELECT * FROM `tabError Log`
WHERE creation > DATE_SUB(NOW(), INTERVAL 1 DAY)
AND error LIKE '%airwallex%'
ORDER BY creation DESC;
```

### Count Synced Transactions
```sql
SELECT COUNT(*) FROM `tabBank Transaction`
WHERE transaction_id IS NOT NULL
AND transaction_id != '';
```

### Find Duplicates
```sql
SELECT transaction_id, COUNT(*) as count
FROM `tabBank Transaction`
GROUP BY transaction_id
HAVING count > 1;
```

## Best Practices

1. **Monitor Error Logs**: Review regularly for patterns
2. **Test Credentials**: After any configuration change
3. **Start Small**: Test with short date ranges first
4. **Review Logs**: Check Bank Integration Log after each sync
5. **Handle Errors Gracefully**: Don't panic - most errors are recoverable
6. **Document Issues**: Note error patterns for future reference
7. **Update Regularly**: Keep app updated for bug fixes
