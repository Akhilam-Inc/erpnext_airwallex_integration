import frappe
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
        """Authenticate with Airwallex API using base class post method"""
        try:
            response_data = self.post(
                endpoint="authentication/login",
                json=None
            )

            if response_data and response_data.get('token'):
                self._cache_token(response_data)
                return response_data
            else:
                # Short error log title
                error_title = f"Auth Failed - {self.client_id[:8]}"
                frappe.log_error(
                    f"Authentication response missing token for client {self.client_id}: {response_data}",
                    error_title
                )
                return None

        except AirwallexAPIError as e:
            # Handle API errors without character length issues
            client_short = self.client_id[:8] if self.client_id else "unknown"
            error_title = f"Auth Error - {client_short}"

            # Truncate the error message if too long
            error_message = str(e.message)
            if len(error_message) > 500:
                error_message = error_message[:500] + "..."

            frappe.log_error(
                f"Authentication failed for client {self.client_id}: {error_message}",
                error_title
            )
            return None

        except Exception as e:
            # Very short error log title to avoid character limit
            client_short = self.client_id[:8] if self.client_id else "unknown"
            error_title = f"Auth Error - {client_short}"

            frappe.log_error(
                f"Unexpected authentication error for client {self.client_id}: {str(e)[:500]}",
                error_title
            )
            return None

    def _cache_token(self, token_data):
        """Cache the authentication token"""
        try:
            cache_key = f"airwallex_token_{self.client_id}"
            frappe.cache().set_value(cache_key, token_data, expires_in_sec=3500)
        except Exception as e:
            frappe.log_error(f"Failed to cache token: {str(e)}", "Token Cache Error")

    def clear_cached_token(self):
        """Clear cached token for this client"""
        try:
            cache_key = f"airwallex_token_{self.client_id}"
            frappe.cache().delete_value(cache_key)
        except Exception as e:
            frappe.log_error(f"Failed to clear cached token: {str(e)}", "Token Cache Error")

    def get_fresh_token(self):
        """Get a fresh token, bypassing cache"""
        self.clear_cached_token()
        auth_response = self.authenticate()
        if auth_response and auth_response.get('token'):
            return auth_response.get('token')
        return None
