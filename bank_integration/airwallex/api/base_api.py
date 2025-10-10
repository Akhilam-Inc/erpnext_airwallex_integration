import requests
import frappe
from urllib.parse import urljoin
from enum import Enum
from frappe import _
from frappe.utils.background_jobs import enqueue
from datetime import datetime, timedelta

class SupportedHTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"

class AirwallexBase:
    BASE_PATH = ""

    def __init__(self, client_id=None, api_key=None, api_url=None, use_auth_headers=False):
        """Initialize with specific client credentials"""
        if client_id and api_key:
            self.client_id = client_id
            self.api_key = api_key
            self.api_url = api_url or self._get_api_url()
        else:
            # Fallback to first client for backward compatibility
            settings = frappe.get_single("Bank Integration Setting")
            if settings.airwallex_clients:
                first_client = settings.airwallex_clients[0]
                self.client_id = first_client.airwallex_client_id
                self.api_key = first_client.airwallex_api_key
                self.api_url = settings.api_url
            else:
                frappe.throw("No Airwallex clients configured")

        self.base_url = self.api_url
        self.enable_api_log = True

        # Set headers based on whether this is for authentication or API calls
        if use_auth_headers:
            # Headers for authentication endpoint
            self.headers = {
                "x-api-key": self.api_key,
                "x-client-id": self.client_id,
                "Content-Type": "application/json"
            }
            self.is_auth_instance = True
        else:
            # Headers for API calls - token will be added when making requests
            self.headers = {
                "Content-Type": "application/json"
            }
            self.is_auth_instance = False

        self.log_data = {}

    def authenticate_and_cache_token(self, force_fresh=False):
        """Authenticate and cache the token"""
        from bank_integration.airwallex.api.airwallex_authenticator import AirwallexAuthenticator

        auth = AirwallexAuthenticator(
            client_id=self.client_id,
            api_key=self.api_key,
            api_url=self.api_url
        )

        if force_fresh:
            # Clear any existing cached token
            auth.clear_cached_token()

        auth_response = auth.authenticate()

        if not auth_response or not auth_response.get('token'):
            client_short = self.client_id[:8] if self.client_id else "unknown"
            frappe.log_error(
                f"Failed to authenticate with Airwallex API for client {self.client_id}",
                f"Auth Failed - {client_short}"
            )
            return None

        token = auth_response['token']
        expires_at = auth_response.get('expires_at')

        try:
            cache_key = f"airwallex_token_{self.client_id}"
            frappe.cache().set_value(cache_key, token, expires_in_sec=3500)
            if expires_at:
                frappe.cache().set_value(f"airwallex_expires_{self.client_id}", expires_at, expires_in_sec=3500)
        except Exception as e:
            frappe.log_error(f"Failed to cache token: {str(e)}", "Token Cache Error")

        return token

    def get_valid_token(self, force_fresh=False):
        """Get a valid bearer token, authenticate if needed"""
        if force_fresh:
            return self.authenticate_and_cache_token(force_fresh=True)

        # Check cached token first
        cache_key = f"airwallex_token_{self.client_id}"
        cached_token = frappe.cache().get_value(cache_key)
        expires_key = f"airwallex_expires_{self.client_id}"
        expires_at = frappe.cache().get_value(expires_key)

        if cached_token and expires_at:
            try:
                expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if datetime.now() < expires_datetime - timedelta(minutes=5):
                    return cached_token
            except:
                pass

        return self.authenticate_and_cache_token()

    def ensure_authenticated_headers(self, force_fresh=False):
        """Ensure headers have valid bearer token"""
        if force_fresh or "Authorization" not in self.headers:
            token = self.get_valid_token(force_fresh=force_fresh)
            if token:
                self.headers["Authorization"] = f"Bearer {token}"
            else:
                client_short = self.client_id[:8] if self.client_id else "unknown"
                raise AirwallexAPIError(f"Authentication failed for client {client_short}", 401)

    def get(self, endpoint=None, params=None, headers=None):
        # Ensure we have auth token for API calls (not auth endpoints)
        if not self.is_auth_instance:
            self.ensure_authenticated_headers()
        return self._make_request(SupportedHTTPMethod.GET, endpoint=endpoint, params=params, headers=headers)

    def delete(self, endpoint=None, params=None, headers=None):
        if not self.is_auth_instance:
            self.ensure_authenticated_headers()
        return self._make_request(SupportedHTTPMethod.DELETE, endpoint=endpoint, params=params, headers=headers)

    def post(self, endpoint, params=None, json=None, headers=None):
        if not self.is_auth_instance:
            self.ensure_authenticated_headers()
        return self._make_request(SupportedHTTPMethod.POST, endpoint, params=params, json=json, headers=headers)

    def put(self, endpoint=None, json=None, headers=None):
        if not self.is_auth_instance:
            self.ensure_authenticated_headers()
        return self._make_request(SupportedHTTPMethod.PUT, endpoint=endpoint, json=json, headers=headers)

    def _make_request(self, method: SupportedHTTPMethod, endpoint=None, params=None, json=None, headers=None):
        """Base method for making HTTP requests."""
        url = self._build_url(endpoint, method)
        request_headers = {**self.headers, **(headers or {})}

        params = params or {}
        self._prepare_log(url, params, json, request_headers)
        response = None

        try:
            response = requests.request(method.value, url, params=params, json=json, headers=request_headers)

            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text

            self.create_connection_log(
                status=str(response.status_code),
                message=str(response.text),
                response=response_data,
                method=method.value,
                payload=str(params) if json is None else str(json),
                url=url
            )

            # Check if the request was successful
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                # Instead of throwing, raise a custom exception that can be caught
                raise AirwallexAPIError(error_msg, response.status_code)

            return response_data if isinstance(response_data, dict) else {"error": response_data}

        except AirwallexAPIError:
            # Re-raise API errors
            raise
        except Exception as e:
            error_response = response.text if response else str(e)
            self.create_connection_log(
                status=response.status_code if response else 500,
                message="Error",
                response=error_response,
                method=method.value,
                payload=str(params) if json is None else str(json),
                url=url
            )
            # Raise a custom exception instead of using frappe.throw
            raise AirwallexAPIError(str(e).replace(self.api_key, "****"), getattr(response, 'status_code', 500))


    def _build_url(self, endpoint, method):
        """Generate full API URL ensuring correct formatting."""
        base_url = self.base_url+ "/"  # Ensure base_url has a trailing slash
        base_path = self.BASE_PATH  # Keep BASE_PATH as-is
        endpoint = endpoint # Remove leading slash from endpoint

        # Build full URL dynamically
        full_url = "/".join(filter(None, [base_url.rstrip("/"), base_path, endpoint]))

        return full_url


    def _prepare_log(self, url, params, json, headers):
        self.log_data = {
            "url": url,
            "params": params,
            "request_body": json,
            "headers": self._mask_sensitive_info(headers)
        }

    def _log_request(self):
        if "Shipstation Integration" not in self.log_data:
            self.log_data["integration_request_service"] = "Shipstation Integration"
        enqueue(self._enqueue_log, log_data=self.log_data)

    def _mask_sensitive_info(self, data):
        if not isinstance(data, dict):
            return data
        sensitive_fields = {"key", "password", "token", "auth", "secret"}
        return {k: "****" if any(s in k.lower() for s in sensitive_fields) else v for k, v in data.items()}

    def _enqueue_log(self, log_data):
        # Replace this with actual logging method if required
        frappe.logger().info(log_data)

    def create_connection_log(self, status, message, response=None, method=None, payload=None, url=None):
        """Create log entry for connection test"""
        try:
            status_string = "Success" if str(status).startswith("2") else "Error"
            log = frappe.get_doc({
                "doctype": "Bank Integration Log",
                "status": str(status_string),
                "message": str(message),
                "response_data": str(response) if response else "",
                "request_data": str(payload) if payload else "",
                "url": url or self.log_data.get("url", ""),  # Use passed URL or from log_data
                "method": str(method) if method else "",
                "status_code": str(status),
            })
            if self.enable_api_log:
                log.insert(ignore_permissions=True)
                return log

        except Exception as e:
            frappe.log_error(message=str(e), title="Bank Integration Log Creation Error")
            return None

    def _get_api_url(self):
        """Get API URL from settings"""
        try:
            settings = frappe.get_single("Bank Integration Setting")
            return settings.api_url or "https://api.airwallex.com"
        except:
            return "https://api.airwallex.com"


# Add a custom exception class
class AirwallexAPIError(Exception):
    def __init__(self, message, status_code=None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)
