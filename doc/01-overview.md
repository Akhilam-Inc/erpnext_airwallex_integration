# Bank Integration App - Overview

## Introduction

The Bank Integration App is a Frappe/ERPNext application that integrates with Airwallex to synchronize bank transactions automatically. This app enables seamless financial data flow from Airwallex into ERPNext's Bank Transaction doctype.

## Key Features

- **Multi-Client Support**: Configure multiple Airwallex clients with different credentials and bank accounts
- **Automatic Scheduled Syncing**: Set up periodic syncs (Hourly, Daily, Weekly, Monthly)
- **Manual Historical Sync**: Sync old transactions within a specified date range
- **Smart Token Management**: Database-cached tokens with automatic refresh
- **Duplicate Prevention**: Intelligent duplicate detection to avoid redundant entries
- **Currency Matching**: Automatic bank account assignment based on currency match
- **Real-time Progress Tracking**: Live updates during sync operations
- **Comprehensive Error Handling**: Graceful error handling with detailed logging

## Sync Types

### 1. Scheduled Sync
Automatic periodic synchronization triggered by Frappe's scheduler based on configured schedule:
- **Hourly**: Syncs last 2 hours (or from last sync date)
- **Daily**: Syncs yesterday (or from last sync date)
- **Weekly**: Syncs last 7 days (or from last sync date)
- **Monthly**: Syncs last 30 days (or from last sync date)

### 2. Old Transactions Sync
Manual synchronization for historical transactions:
- User-defined date range (From/To dates)
- Runs in background job queue
- One-hour timeout for long-running operations
- Progress tracking via UI

## Architecture

```
bank_integration/
├── airwallex/
│   ├── api/
│   │   ├── base_api.py              # Base API class with auth & token management
│   │   ├── airwallex_authenticator.py  # Authentication handler
│   │   └── financial_transactions.py   # Financial transactions API
│   ├── scheduler.py                 # Cron job handlers
│   ├── transaction.py               # Sync logic
│   └── utils.py                     # Data mapping utilities
└── bank_integration/
    └── doctype/
        ├── bank_integration_setting/    # Main configuration doctype
        ├── airwallex_client/            # Client configuration (child table)
        └── bank_integration_log/        # Sync logs
```

## Data Flow

1. **Scheduler/User** triggers sync operation
2. **Sync Manager** orchestrates the sync process
3. **API Client** fetches transactions from Airwallex
4. **Token Manager** handles authentication automatically
5. **Data Mapper** transforms Airwallex data to ERPNext format
6. **Transaction Creator** inserts Bank Transaction records
7. **Progress Tracker** updates status and notifies user

## Next Steps

- [Configuration Guide](02-configuration.md) - How to set up the integration
- [Scheduled Sync Workflow](03-scheduled-sync-workflow.md) - Detailed scheduled sync process
- [Manual Sync Workflow](04-manual-sync-workflow.md) - Detailed manual sync process
- [Authentication & Token Management](05-authentication.md) - Token caching strategy
- [Data Mapping](06-data-mapping.md) - How Airwallex data is mapped to ERPNext
- [Error Handling](07-error-handling.md) - Error handling and recovery