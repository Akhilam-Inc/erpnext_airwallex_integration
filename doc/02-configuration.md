# Configuration Guide

## Bank Integration Setting

The Bank Integration Setting is a Single DocType that holds all configuration for the Airwallex integration.

### Access

Navigate to: **Bank Integration** workspace → **Bank Integration Setting**

### Configuration Fields

#### Integration Settings

| Field | Type | Description |
|-------|------|-------------|
| `enable_airwallex` | Checkbox | Enable/disable the Airwallex integration |
| `api_url` | Data | Airwallex API base URL |
| `enable_log` | Checkbox | Enable detailed API logging |

#### Token Management (Auto-managed)

| Field | Type | Description |
|-------|------|-------------|
| `token` | Small Text | Cached authentication token (auto-populated) |
| `token_expiry` | Datetime | Token expiration time (auto-populated) |

#### Scheduled Sync Settings

| Field | Type | Description |
|-------|------|-------------|
| `sync_schedule` | Select | Schedule frequency: Hourly, Daily, Weekly, Monthly |
| `last_sync_date` | Datetime | Last successful sync timestamp (auto-updated) |

#### Manual Sync Settings

| Field | Type | Description |
|-------|------|-------------|
| `sync_old_transactions` | Checkbox | Enable manual sync for historical transactions |
| `from_date` | Datetime | Start date for manual sync |
| `to_date` | Datetime | End date for manual sync |

#### Sync Status (Auto-managed)

| Field | Type | Description |
|-------|------|-------------|
| `sync_status` | Select | Current sync status: Not Started, In Progress, Completed, Completed with Errors, Failed |
| `processed_records` | Int | Number of transactions processed (auto-updated) |
| `total_records` | Int | Total transactions to process (auto-updated) |
| `sync_progress` | Percent | Sync progress percentage (auto-updated) |

#### Airwallex Clients (Child Table)

| Field | Type | Description |
|-------|------|-------------|
| `airwallex_client_id` | Data | Client ID from Airwallex (required) |
| `airwallex_api_key` | Password | API Key from Airwallex (required) |
| `bank_account` | Link | ERPNext Bank Account to map transactions to (required) |
| `token` | Small Text | Client-specific cached token (auto-managed) |
| `token_expiry` | Datetime | Client-specific token expiry (auto-managed) |

## Setup Steps

### 1. Initial Configuration

1. Navigate to **Bank Integration Setting**
2. Set the **API URL** (e.g., `https://api.airwallex.com`)
3. Optionally enable **Enable Log** for detailed logging

### 2. Add Airwallex Clients

For each Airwallex account you want to sync:

1. Click **Add Row** in the Airwallex Clients table
2. Enter **Airwallex Client ID**
3. Enter **Airwallex API Key**
4. Select the corresponding **Bank Account** in ERPNext
5. Click **Save**

**Important**: The bank account currency should match the currencies of transactions from that Airwallex client.

### 3. Test Authentication

1. Click the **Test Authentication** button
2. The system will verify credentials for all configured clients
3. Green checkmarks indicate successful authentication
4. Red errors indicate failed authentication (fix credentials and try again)

### 4. Enable Integration

1. Check **Enable Airwallex**
2. Click **Save**

**Note**: The system automatically tests authentication when you enable the integration. If authentication fails, the integration will be automatically disabled.

### 5. Configure Scheduled Sync

1. Select **Sync Schedule** (Hourly/Daily/Weekly/Monthly)
2. Click **Save**

The scheduler will automatically start syncing based on your schedule.

### 6. Configure Manual Sync (Optional)

For syncing historical transactions:

1. Check **Sync Old Transactions**
2. Set **From Date** and **To Date**
3. Click **Save**
4. Click **Start Sync** button that appears

## Validation Rules

- At least one Airwallex client must be configured
- Client ID, API Key, and Bank Account are required for each client
- Authentication must succeed before enabling the integration
- From Date must be before To Date for manual sync
- Sync cannot start if another sync is in progress

## Best Practices

1. **Test Authentication First**: Always test authentication before enabling
2. **Match Currencies**: Ensure bank account currency matches transaction currencies
3. **Start Small**: Begin with a short date range for manual sync to test
4. **Monitor Progress**: Watch the sync progress percentage during operation
5. **Check Logs**: Review Bank Integration Logs for any errors
6. **Credential Security**: API keys are stored encrypted as password fields
