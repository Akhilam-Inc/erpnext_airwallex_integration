import frappe
import requests
from datetime import datetime, timedelta
from .skript_base_api import SkriptBase, SkriptAPIError


class SkriptAuthenticator(SkriptBase):
    """OAuth 2.0 authenticator for Skript"""
    
    def __init__(self, consumer_id, client_id, client_secret, api_url):
        super().__init__(consumer_id, client_id, client_secret, api_url)
        self.is_auth_instance = True
    
    def authenticate(self):
        """Authenticate using OAuth 2.0 client credentials"""
        try:
            # Check cached token first
            cached_token = self._get_cached_token_from_db()
            if cached_token:
                frappe.logger().info("Using cached Skript token")
                return {"access_token": cached_token}
            
            # Get token URL from settings
            settings = frappe.get_single("Bank Integration Setting")
            token_url = settings.skript_access_token_url
            
            if not token_url:
                raise SkriptAPIError("Token URL not configured", 400)
            
            # OAuth request with form-encoded data
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "skript/ob-products skript/ob-direct-data"
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            frappe.logger().info(f"Requesting new Skript token from {token_url}")
            
            response = requests.post(token_url, data=data, headers=headers, timeout=30)
            
            # LOG THE TOKEN REQUEST
            try:
                response_data = response.json() if response.status_code == 200 else response.text
            except:
                response_data = response.text
            
            # Mask sensitive data for logging
            masked_data = {
                "grant_type": data["grant_type"],
                "client_id": data["client_id"],
                "client_secret": "****",  # Masked
                "scope": "skript/ob-products skript/ob-direct-data"
            }
            
            # Create log entry
            self._create_token_log(
                status=response.status_code,
                message="Token Request",
                response=response_data,
                url=token_url,
                request_data=masked_data
            )
            
            if response.status_code != 200:
                error_msg = f"OAuth failed ({response.status_code}): {response.text}"
                frappe.log_error(error_msg, "Skript Auth Error")
                raise SkriptAPIError(error_msg, response.status_code)
            
            token_data = response.json()
            
            if token_data.get('access_token'):
                self._cache_token_to_db(token_data)
                frappe.logger().info("Skript token obtained and cached successfully")
                return token_data
            else:
                raise SkriptAPIError("No access token in response", 400)
        
        except SkriptAPIError:
            raise
        except Exception as e:
            frappe.log_error(f"Skript authentication error: {str(e)}", "Skript Auth Error")
            raise SkriptAPIError(str(e), 500)

    def _create_token_log(self, status, message, response=None, url=None, request_data=None):
        """Create log entry for token requests"""
        try:
            settings = frappe.get_single("Bank Integration Setting")
            if not settings.enable_log:
                return
            
            import json
            
            status_string = "Success" if str(status).startswith("2") else "Error"
            
            # Format response
            response_str = ""
            if response:
                if isinstance(response, (dict, list)):
                    # Mask access_token in response for security
                    if isinstance(response, dict) and 'access_token' in response:
                        masked_response = response.copy()
                        masked_response['access_token'] = f"{response['access_token'][:10]}...{response['access_token'][-10:]}"
                        response_str = json.dumps(masked_response, indent=2, default=str)
                    else:
                        response_str = json.dumps(response, indent=2, default=str)
                else:
                    response_str = str(response)
            
            # Format request
            request_str = ""
            if request_data:
                if isinstance(request_data, (dict, list)):
                    request_str = json.dumps(request_data, indent=2, default=str)
                else:
                    request_str = str(request_data)
            
            log = frappe.get_doc({
                "doctype": "Bank Integration Log",
                "status": status_string,
                "message": f"Skript OAuth Token: {message}",
                "response_data": response_str,
                "request_data": request_str,
                "url": url or "",
                "method": "POST",
                "status_code": str(status)
            })
            log.insert(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Token log creation error: {str(e)}", "Skript Token Log Error")
    
    def _get_cached_token_from_db(self):
        """Get cached token from Bank Integration Setting"""
        try:
            settings = frappe.get_single("Bank Integration Setting")
            
            if settings.skript_access_token and settings.skript_token_expiry:
                token_expiry = frappe.utils.get_datetime(settings.skript_token_expiry)
                current_time = frappe.utils.now_datetime()
                
                # 5-minute buffer
                buffer = timedelta(minutes=5)
                if token_expiry > (current_time + buffer):
                    return settings.skript_access_token
            
            return None
        
        except Exception as e:
            frappe.log_error(f"Token cache retrieval error: {str(e)}", "Skript Token Cache")
            return None
    
    def _cache_token_to_db(self, token_data):
        """Cache token to Bank Integration Setting"""
        try:
            settings = frappe.get_single("Bank Integration Setting")
            
            # Calculate expiry
            expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
            expiry_time = frappe.utils.now_datetime() + timedelta(seconds=expires_in)
            
            # Update settings
            settings.db_set('skript_access_token', token_data.get('access_token'))
            settings.db_set('skript_token_expiry', expiry_time)
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"Token cache save error: {str(e)}", "Skript Token Cache")
    
    def clear_cached_token(self):
        """Clear cached token"""
        try:
            settings = frappe.get_single("Bank Integration Setting")
            settings.db_set('skript_access_token', None)
            settings.db_set('skript_token_expiry', None)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Token clear error: {str(e)}", "Skript Token")
    
    def get_valid_token(self):
        """Get valid token (cached or new)"""
        auth_response = self.authenticate()
        if auth_response and auth_response.get('access_token'):
            return auth_response.get('access_token')
        return None
    
    def get_fresh_token(self):
        """Get a fresh token, bypassing cache"""
        self.clear_cached_token()
        return self.get_valid_token()
