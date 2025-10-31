# Bank Integration - Airwallex to ERPNext

Seamless integration between Airwallex and ERPNext for automatic financial transaction synchronization.

## Overview

The Bank Integration App provides comprehensive integration between Airwallex and ERPNext, enabling automatic synchronization of financial transactions. This app supports multiple Airwallex clients, scheduled syncing, intelligent currency matching, and robust error handling.

## Features

- ✅ **Multi-Client Support**: Manage multiple Airwallex clients from a single setting
- ✅ **Scheduled Syncing**: Automatic hourly, daily, weekly, or monthly transaction sync
- ✅ **Manual Sync**: Sync historical transactions for specific date ranges
- ✅ **Smart Token Caching**: Database-backed token storage with automatic refresh
- ✅ **Currency Matching**: Intelligent bank account assignment based on currency
- ✅ **Duplicate Prevention**: Automatic detection and skipping of existing transactions
- ✅ **Real-time Progress**: Live updates during sync operations
- ✅ **Comprehensive Logging**: Detailed error logs with privacy protection
- ✅ **Background Processing**: Long-running syncs handled by background jobs
- ✅ **Paginated API Calls**: Efficient handling of large transaction volumes

## Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/Akhilam-Inc/erpnext_airwallex_integration --branch develop
bench install-app bank_integration
```

### Post-Installation Setup

1. Navigate to **Bank Integration Setting** in your ERPNext instance
2. Configure your Airwallex API URL (e.g., `https://api.airwallex.com/api/v1`)
3. Add your Airwallex clients with their credentials and bank accounts
4. Enable the integration and set up your sync schedule
5. Test authentication to verify connectivity

For detailed setup instructions, see the [Configuration Guide](doc/02-configuration.md).

## Quick Start

### Basic Configuration

1. Go to **Bank Integration Setting**
2. Enable Airwallex Integration
3. Set API URL: `https://api.airwallex.com/api/v1`
4. Add Airwallex Client:
   - Client ID
   - API Key
   - Linked Bank Account (must match currency)
5. Click **Test Authentication**
6. Set Sync Schedule (Hourly/Daily/Weekly/Monthly)
7. Save

### Sync Transactions

**Scheduled Sync** (Automatic):
- Runs based on your configured schedule
- Syncs from last sync date to current time
- No user intervention required

**Manual Sync** (Historical):
1. Enable "Sync Old Transactions"
2. Set From Date and To Date
3. Click **Start Sync**
4. Monitor progress in real-time

## Documentation

Complete documentation is available in the [`doc/`](doc/) directory:

### Getting Started
- **[Overview](doc/01-overview.md)** - Introduction and key features
- **[Configuration Guide](doc/02-configuration.md)** - Detailed setup instructions

### Workflow Documentation
- **[Scheduled Sync Workflow](doc/03-scheduled-sync-workflow.md)** - Automatic periodic syncing
- **[Manual Sync Workflow](doc/04-manual-sync-workflow.md)** - Historical data sync
- **[Common Sync Process](doc/08-common-sync-process.md)** - Core sync logic

### Technical Details
- **[Authentication & Token Management](doc/05-authentication.md)** - Token caching and security
- **[Data Mapping](doc/06-data-mapping.md)** - Field transformations
- **[Error Handling & Recovery](doc/07-error-handling.md)** - Troubleshooting guide

📖 **Start here**: [doc/README.md](doc/README.md)

## Architecture

### Core Components

1. **Bank Integration Setting** - Global configuration and multi-client management
2. **Scheduler** - Cron-triggered sync functions for scheduled operations
3. **Transaction Sync** - Main orchestration and client-specific processing
4. **API Layer** - Base API client with authentication and token management
5. **Data Mapping** - Airwallex to ERPNext field transformation

### Code Structure

```
bank_integration/
├── airwallex/                          # Airwallex integration logic
│   ├── api/                           # API client layer
│   │   ├── base_api.py               # Base API client
│   │   ├── airwallex_authenticator.py # Authentication
│   │   └── financial_transactions.py  # Transactions API
│   ├── scheduler.py                   # Cron job functions
│   ├── transaction.py                 # Sync orchestration
│   └── utils.py                       # Data mapping utilities
├── bank_integration/                   # Main module
│   └── doctype/                       # DocTypes
│       ├── bank_integration_setting/  # Settings DocType
│       ├── bank_integration_log/      # Log DocType
│       └── airwallex_client/          # Client child table
└── fixtures/                          # Custom field definitions
```

## Key Concepts

### Sync Types

**Scheduled Sync**:
- Automatic, incremental, triggered by cron
- Date range calculated from last sync date
- Runs in background without user intervention

**Manual Sync**:
- User-initiated, specific date range
- Background job with real-time progress
- Useful for historical data import

### Authentication

- Database-cached tokens with automatic refresh
- Multi-client support with individual credentials
- Automatic retry on authentication failures (401)
- 5-minute buffer before token expiry

### Data Mapping

- **Currency Matching**: Bank account only assigned if transaction currency matches account currency
- **Auto-Classification**: Deposit vs withdrawal based on amount sign
- **Duplicate Prevention**: Checks `transaction_id` field before creating
- **Comprehensive Mapping**: All relevant Airwallex fields mapped to ERPNext

### Sync Status States

| Status | Description |
|--------|-------------|
| Not Started | Initial state, no sync has been initiated |
| In Progress | Sync is currently running |
| Completed | Sync finished successfully with no errors |
| Completed with Errors | Sync finished but some transactions had errors |
| Failed | Sync failed completely |

## API Reference

### Main Functions

#### `sync_transactions(from_date, to_date, setting_name)`
Main sync orchestrator that processes all configured clients.

**Parameters:**
- `from_date` (str/datetime): Start date for transaction sync
- `to_date` (str/datetime): End date for transaction sync
- `setting_name` (str): Name of Bank Integration Setting document

#### `sync_client_transactions(client, from_date_iso, to_date_iso, settings)`
Syncs transactions for a specific Airwallex client.

**Parameters:**
- `client` (AirwallexClient): Client configuration object
- `from_date_iso` (str): ISO8601 formatted start date
- `to_date_iso` (str): ISO8601 formatted end date
- `settings` (BankIntegrationSetting): Settings document

#### `map_airwallex_to_erpnext(txn, bank_account)`
Maps Airwallex transaction to ERPNext Bank Transaction format.

**Parameters:**
- `txn` (dict): Airwallex transaction payload
- `bank_account` (str): ERPNext Bank Account name

**Returns:**
- `dict`: ERPNext Bank Transaction document dictionary

For detailed API documentation, see [Data Mapping](doc/06-data-mapping.md).

## Troubleshooting

### Common Issues

**Authentication Failed**
- Verify Client ID and API Key are correct
- Check API URL is set to `https://api.airwallex.com/api/v1`
- Ensure credentials have proper permissions in Airwallex

**Transactions Not Syncing**
- Check sync status in Bank Integration Setting
- Review Bank Integration Log for errors
- Verify date range is correct
- Ensure scheduler is running: `bench enable-scheduler`

**Bank Account Not Set**
- Check transaction currency matches bank account currency
- Verify bank account is properly configured in ERPNext
- Review Data Mapping documentation

**Duplicate Transactions**
- App automatically prevents duplicates based on `transaction_id`
- Check Bank Transaction list for existing transactions
- Review error logs for duplicate entry errors

For comprehensive troubleshooting, see [Error Handling & Recovery](doc/07-error-handling.md).

## Development

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/bank_integration
pre-commit install
```

Pre-commit is configured to use the following tools:
- **ruff** - Python linting and formatting
- **eslint** - JavaScript linting
- **prettier** - Code formatting
- **pyupgrade** - Python syntax modernization

### Running Tests

```bash
# Run all tests
bench --site your-site run-tests --app bank_integration

# Run specific test file
bench --site your-site run-tests --app bank_integration --module bank_integration.tests.test_transaction
```

### CI/CD

This app uses GitHub Actions for continuous integration:

- **CI**: Installs this app and runs unit tests on every push to `develop` branch
- **Linters**: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request

## Support

For issues, questions, or contributions:
- **GitHub Issues**: [Report an issue](https://github.com/Akhilam-Inc/erpnext_airwallex_integration/issues)
- **Documentation**: Review the guides in the [`doc/`](doc/) directory
- **Troubleshooting**: See [Error Handling & Recovery](doc/07-error-handling.md)

## Roadmap

- [ ] Support for additional payment gateways
- [ ] Enhanced transaction filtering
- [ ] Automatic bank reconciliation
- [ ] Multi-currency conversion support
- [ ] Advanced reporting and analytics
- [ ] Webhook support for real-time updates

## License

MIT License

Copyright (c) 2025 Akhilam Inc

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

**Made with ❤️ by [Akhilam Inc](https://github.com/Akhilam-Inc)**
