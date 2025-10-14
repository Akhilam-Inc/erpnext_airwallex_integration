import frappe
import frappe.utils
from datetime import datetime, timedelta
from .base_api import AirwallexBase, AirwallexAPIError


class AirwallexAuthenticator(AirwallexBase):
    def __init__(self, client_id=None, api_key=None, api_url=None):
        """Initialize with specific client credentials for authentication"""
        super().__init__(
            client_id=client_id,
            api_key=api_key,
            api_url=api_url,
            use_auth_headers=True
        )

    def authenticate(self):
        """Authenticate with Airwallex API, checking database token first"""
        try:
            # First check if we have a valid token in the database
            cached_token = self._get_cached_token_from_db()
            if cached_token:
                return {"token": cached_token}

            # If no valid token, authenticate and get a new one
            response_data = self.post(
                endpoint="authentication/login",
                json=None
            )

            if response_data and response_data.get('token'):
                self._cache_token_to_db(response_data)
                return response_data
            else:
                # Short error log title
                error_title = f"Auth-{self.client_id[:6]}"
                frappe.log_error(
                    f"Authentication response missing token for client {self.client_id}: {response_data}",
                    error_title
                )
                return None

        except AirwallexAPIError as e:
            # Handle API errors with very short titles
            client_short = self.client_id[:6] if self.client_id else "unknown"
            error_title = f"Auth-{client_short}"

            # Truncate the error message if too long
            error_message = str(e.message)
            if len(error_message) > 300:
                error_message = error_message[:300] + "..."

            frappe.log_error(
                f"Authentication failed for client {self.client_id}: {error_message}",
                error_title
            )
            return None

        except Exception as e:
            # Very short error log title to avoid character limit
            client_short = self.client_id[:6] if self.client_id else "unknown"
            error_title = f"Auth-{client_short}"

            frappe.log_error(
                f"Unexpected authentication error for client {self.client_id}: {str(e)[:300]}",
                error_title
            )
            return None

    def _get_cached_token_from_db(self):
        """Get cached token from database if still valid"""
        try:
            # Get the Airwallex Client record for this client_id
            client_doc = self._get_client_doc()
            if not client_doc:
                return None

            # Check if token exists and is not expired
            if client_doc.token and client_doc.token_expiry:
                token_expiry = frappe.utils.get_datetime(client_doc.token_expiry)
                current_time = frappe.utils.now_datetime()

                # Add 5 minute buffer before expiry to avoid edge cases
                buffer_time = timedelta(minutes=5)
                if token_expiry > (current_time + buffer_time):
                    return client_doc.token

            return None

        except Exception as e:
            frappe.log_error(f"Failed to get cached token from database: {str(e)}", "Token DB Error")
            return None

    def _cache_token_to_db(self, token_data):
        """Cache the authentication token to database"""
        try:
            client_doc = self._get_client_doc()
            if not client_doc:
                frappe.log_error(f"Client document not found for client_id: {self.client_id}", "Token Cache Error")
                return

            # Calculate expiry time (typically 1 hour from now, with some buffer)
            expires_in = token_data.get('expires_in', 3600)  # Default to 1 hour
            expiry_time = frappe.utils.now_datetime() + timedelta(seconds=expires_in)

            # Update the client document
            client_doc.token = token_data.get('token')
            client_doc.token_expiry = expiry_time
            client_doc.save(ignore_permissions=True)
            frappe.db.commit()

        except Exception as e:
            frappe.log_error(f"Failed to cache token to database: {str(e)}", "Token Cache Error")

    def _get_client_doc(self):
        """Get the Airwallex Client document for this client_id"""
        try:
            # Get the Bank Integration Setting document
            settings = frappe.get_single("Bank Integration Setting")

            # Find the client with matching client_id
            for client in settings.airwallex_clients:
                if client.airwallex_client_id == self.client_id:
                    return client

            return None

        except Exception as e:
            frappe.log_error(f"Failed to get client document: {str(e)}", "Client Doc Error")
            return None

    def _cache_token(self, token_data):
        """Cache the authentication token (legacy method - now uses database)"""
        self._cache_token_to_db(token_data)

    def clear_cached_token(self):
        """Clear cached token for this client from database"""
        try:
            client_doc = self._get_client_doc()
            if client_doc:
                client_doc.token = None
                client_doc.token_expiry = None
                client_doc.save(ignore_permissions=True)
                frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Failed to clear cached token from database: {str(e)}", "Token Cache Error")

    def get_fresh_token(self):
        """Get a fresh token, bypassing cache"""
        self.clear_cached_token()
        auth_response = self.authenticate()
        if auth_response and auth_response.get('token'):
            return auth_response.get('token')
        return None

    def is_token_valid(self):
        """Check if the current token is still valid without authenticating"""
        cached_token = self._get_cached_token_from_db()
        return cached_token is not None

    def get_valid_token(self):
        """Get a valid token (from cache if available, otherwise authenticate)"""
        auth_response = self.authenticate()
        if auth_response and auth_response.get('token'):
            return auth_response.get('token')
        return None

    def handle_token_invalidation(self):
        """Handle when a token is found to be invalid - clear cache and get fresh token"""
        frappe.log_error(
            f"Token invalidated for client {self.client_id}, clearing cache and getting fresh token",
            f"Token-Invalid-{self.client_id[:6]}"
        )
        self.clear_cached_token()
        return self.get_valid_token()
