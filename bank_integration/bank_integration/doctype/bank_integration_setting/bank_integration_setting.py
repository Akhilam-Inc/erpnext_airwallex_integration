# Copyright (c) 2025, Akhilam Inc and contributors
# For license information, please see license.txt

from bank_integration.airwallex.api.airwallex_authenticator import AirwallexAuthenticator
import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from frappe.utils import add_days, add_months, get_datetime, now_datetime
from frappe.utils.scheduler import is_scheduler_inactive
from datetime import datetime

class BankIntegrationSetting(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from bank_integration.bank_integration.doctype.airwallex_client.airwallex_client import AirwallexClient
        from frappe.types import DF

        airwallex_clients: DF.Table[AirwallexClient]
        api_url: DF.Data | None
        enable_airwallex: DF.Check
        enable_log: DF.Check
        file_url: DF.Data | None
        from_date: DF.Datetime | None
        last_sync_date: DF.Datetime | None
        processed_records: DF.Int
        sync_old_transactions: DF.Check
        sync_progress: DF.Percent
        sync_schedule: DF.Literal["Hourly", "Daily", "Weekly", "Monthly"]
        sync_status: DF.Literal["Not Started", "In Progress", "Completed", "Completed with Errors", "Failed"]
        to_date: DF.Datetime | None
        total_records: DF.Int
    # end: auto-generated types

    def is_enabled(self):
        return bool(self.enable_airwallex)

    def _to_iso8601(self, dt):
        """Convert datetime to ISO8601 format in UTC timezone"""
        try:
            from frappe.utils import get_datetime
            import pytz

            if not dt:
                return None

            # Convert to datetime object if it's a string
            if isinstance(dt, str):
                dt = get_datetime(dt)

            # If datetime is naive (no timezone info), assume it's in system timezone
            if dt.tzinfo is None:
                # Get system timezone from Frappe settings
                system_tz = pytz.timezone(frappe.utils.get_system_timezone())
                dt = system_tz.localize(dt)

            # Convert to UTC
            utc_dt = dt.astimezone(pytz.UTC)

            # Format as ISO8601 with 'Z' suffix for UTC
            return utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        except Exception as e:
            frappe.log_error(f"Error converting datetime to ISO8601: {str(e)}", "ISO8601 Conversion Error")
            return None

    def _credentials_changed(self):
        """Check if any client credentials have changed"""
        if self.is_new():
            return True

        # Get the old document
        old_doc = self.get_doc_before_save()
        if not old_doc:
            return True

        # Check if API URL changed
        if self.api_url != old_doc.api_url:
            return True

        # Check if client credentials changed
        old_clients = {client.airwallex_client_id: client for client in old_doc.airwallex_clients}
        current_clients = {client.airwallex_client_id: client for client in self.airwallex_clients}

        # Check for new or removed clients
        if set(old_clients.keys()) != set(current_clients.keys()):
            return True

        # Check if any client credentials changed
        for client_id, client in current_clients.items():
            old_client = old_clients.get(client_id)
            if old_client:
                # Check if API key changed (comparing raw values)
                if (client.get_password("airwallex_api_key") !=
                    old_client.get_password("airwallex_api_key")):
                    return True
                # Check if bank account changed
                if client.bank_account != old_client.bank_account:
                    return True

        return False

    def validate(self):
        """Validate settings - only test authentication when credentials change"""
        if self.enable_airwallex:
            # Only test authentication if this is a new document or credentials have changed
            if self._credentials_changed():
                # Test authentication and disable if it fails
                authentication_successful = self.test_authentication_silent()
                if not authentication_successful:
                    self.enable_airwallex = 0
                    frappe.msgprint(
                        "❌ Authentication failed for one or more clients. Airwallex integration has been disabled.",
                        indicator="red",
                        alert=True
                    )

    def on_update(self):
        """Trigger sync job when sync_old_transactions is enabled"""
        if self.sync_old_transactions and self.sync_status == "Not Started":
            self.start_transaction_sync()

    # Add method to get client configurations
    def get_airwallex_clients(self):
        """Get all configured Airwallex clients"""
        return [client for client in self.airwallex_clients if client.airwallex_client_id and client.bank_account]

    def test_authentication_silent(self):
        """Test authentication without showing messages - returns True/False"""
        if not self.airwallex_clients:
            return False

        success_count = 0
        total_clients = len(self.airwallex_clients)

        for client in self.airwallex_clients:
            try:
                api = AirwallexAuthenticator(
                    client_id=client.airwallex_client_id,
                    api_key=client.get_password("airwallex_api_key"),
                    api_url=self.api_url
                )
                response = api.authenticate()

                if response and response.get('token'):
                    success_count += 1

            except Exception as e:
                # Log the error but don't show message - use short title
                client_short = client.airwallex_client_id[:6] if client.airwallex_client_id else "unknown"
                frappe.log_error(
                    f"Authentication failed for client {client.airwallex_client_id}: {str(e)}",
                    f"Auth-Test-{client_short}"
                )

        return success_count == total_clients

    def test_authentication(self):
        """Test authentication for all configured clients with user feedback"""
        if not self.airwallex_clients:
            frappe.throw("Please configure at least one Airwallex client")

        success_count = 0
        total_clients = len(self.airwallex_clients)
        failed_clients = []

        for client in self.airwallex_clients:
            try:
                api = AirwallexAuthenticator(
                    client_id=client.airwallex_client_id,
                    api_key=client.get_password("airwallex_api_key"),
                    api_url=self.api_url
                )
                response = api.authenticate()

                if response and response.get('token'):
                    success_count += 1
                    frappe.msgprint(
                        f"✅ Authentication successful for client {client.airwallex_client_id}",
                        indicator="green",
                        realtime=True,
                        alert=False
                    )
                else:
                    failed_clients.append(client.airwallex_client_id)
                    frappe.msgprint(
                        f"❌ Authentication failed for client {client.airwallex_client_id}",
                        indicator="red"
                    )
            except Exception as e:
                failed_clients.append(client.airwallex_client_id)
                frappe.msgprint(
                    f"❌ Authentication failed for client {client.airwallex_client_id}: {str(e)}",
                    indicator="red"
                )

        if success_count == total_clients:
            frappe.msgprint(
                f"🎉 All {total_clients} Airwallex clients authenticated successfully!",
                indicator="green",
                realtime=True,
                alert=False
            )
            return True
        else:
            error_message = f"⚠️ {success_count}/{total_clients} clients authenticated successfully"
            if failed_clients:
                error_message += f"\nFailed clients: {', '.join(failed_clients)}"

            frappe.msgprint(
                error_message,
                indicator="orange",
                realtime=True,
                alert=False
            )
            return False

    @frappe.whitelist()
    def start_transaction_sync(self):
        """Start background job for syncing transactions"""
        if not self.from_date or not self.to_date:
            frappe.throw("From and To dates are required for syncing old transactions")

        # Validate date range
        if self.from_date > self.to_date:
            frappe.throw("From date cannot be greater than To date")

        # Update status to indicate sync has started
        self.db_set('sync_status', 'In Progress')
        self.db_set('last_sync_date', frappe.utils.now())
        self.db_set('processed_records', 0)
        self.db_set('total_records', 0)
        self.db_set('sync_progress', 0)

        # Enqueue the sync job
        enqueue(
            'bank_integration.airwallex.transaction.sync_transactions',
            queue='long',
            timeout=3600,  # 1 hour timeout
            from_date=str(self.from_date),
            to_date=str(self.to_date),
            setting_name=self.name
        )

        frappe.msgprint(
            "Transaction sync job has been started. You can monitor the progress from this page.",
            indicator="blue", alert=False
        )

    @frappe.whitelist()
    def restart_transaction_sync(self):
        """Restart transaction sync by resetting status and starting new job"""
        if not self.from_date or not self.to_date:  # Changed from self.from to self.from_date
            frappe.throw("From and To dates are required for syncing old transactions")

        # Reset sync status and counters
        self.db_set('sync_status', 'Not Started')
        self.db_set('processed_records', 0)
        self.db_set('total_records', 0)
        self.db_set('sync_progress', 0)

        # Start the sync
        return self.start_transaction_sync()

    @frappe.whitelist()
    def stop_transaction_sync(self):
        """Stop the current transaction sync"""
        try:
            # Update status to stopped
            self.db_set('sync_status', 'Stopped')

            frappe.msgprint(
                "Transaction sync has been marked as stopped. The background job may take a moment to complete.",
                indicator="orange", alert=False
            )

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Failed to stop sync job")
            frappe.throw(f"Failed to stop sync job: {str(e)}")

    def update_sync_progress(self, processed, total, status="In Progress"):
        """Update sync progress"""
        progress = (processed / total * 100) if total > 0 else 0

        self.db_set('processed_records', processed)
        self.db_set('total_records', total)
        self.db_set('sync_progress', progress)
        self.db_set('sync_status', status)
        self.db_set('last_sync_date', frappe.utils.now())

        frappe.publish_realtime(
            'transaction_sync_progress',
            {
                'processed': processed,
                'total': total,
                'progress': progress,
                'status': status
            },
            user=frappe.session.user
        )
