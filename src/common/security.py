"""
Security utilities for SENTINEL platform
- API key encryption & rotation
- Request signing & validation
- Data sanitization
- Rate limiting
"""
import hashlib
import hmac
import secrets
import time
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import re
import json

from src.common.config import settings
from src.common.logging import setup_logging

logger = setup_logging("security")


class SecurityManager:
    """Centralized security manager for all cryptographic operations"""
    
    def __init__(self):
        self._cipher = None
        self._init_encryption()
        self.rate_limits: Dict[str, list] = {}
        
    def _init_encryption(self):
        """Initialize encryption cipher with derived key"""
        try:
            salt = settings.encryption_salt.encode() if hasattr(settings, 'encryption_salt') and settings.encryption_salt else secrets.token_bytes(16)
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=600000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(settings.jwt_secret_key.encode()))
            self._cipher = Fernet(key)
            logger.info("Encryption initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for secure storage"""
        if not api_key:
            return ""
        try:
            encrypted = self._cipher.encrypt(api_key.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return api_key
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key for use"""
        if not encrypted_key:
            return ""
        try:
            decrypted = self._cipher.decrypt(encrypted_key.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_key
    
    def sign_request(self, payload: Dict[str, Any], secret: str) -> str:
        """Sign request payload with HMAC-SHA256"""
        message = json.dumps(payload, sort_keys=True).encode()
        signature = hmac.new(
            secret.encode(),
            message,
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_signature(self, payload: Dict[str, Any], signature: str, secret: str) -> bool:
        """Verify request signature"""
        expected = self.sign_request(payload, secret)
        return hmac.compare_digest(signature, expected)
    
    def generate_api_key(self, prefix: str = "sk") -> str:
        """Generate secure random API key"""
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}_{random_part}"
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data with SHA-256"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def sanitize_input(self, data: Any, field_name: str = "") -> Any:
        """Sanitize user input to prevent injection attacks"""
        if isinstance(data, str):
            # Remove SQL injection patterns
            data = re.sub(r"('|(--)|;|\/\*|\*\/|xp_|sp_)", "", data)
            # Remove XSS patterns
            data = re.sub(r"<script[^>]*>.*?</script>", "", data, flags=re.IGNORECASE)
            # Limit length
            data = data[:1000]
        elif isinstance(data, dict):
            return {k: self.sanitize_input(v, k) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_input(item) for item in data]
        return data
    
    def check_rate_limit(self, identifier: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
        """Check if identifier exceeds rate limit"""
        now = time.time()
        
        # Initialize or clean old entries
        if identifier not in self.rate_limits:
            self.rate_limits[identifier] = []
        
        # Remove old timestamps outside window
        self.rate_limits[identifier] = [
            ts for ts in self.rate_limits[identifier]
            if now - ts < window_seconds
        ]
        
        # Check limit
        if len(self.rate_limits[identifier]) >= max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False
        
        # Add current request
        self.rate_limits[identifier].append(now)
        return True
    
    def validate_api_key_format(self, api_key: str) -> bool:
        """Validate API key format"""
        if not api_key:
            return False
        # Check for common API key patterns
        patterns = [
            r'^sk_[A-Za-z0-9_\-]{32,}$',  # Stripe-style
            r'^[A-Za-z0-9]{32,}$',  # Simple hex
            r'^[A-Za-z0-9_\-]{40,}$',  # Generic long token
        ]
        return any(re.match(pattern, api_key) for pattern in patterns)
    
    def mask_sensitive_data(self, data: str, show_chars: int = 4) -> str:
        """Mask sensitive data for logging"""
        if not data or len(data) <= show_chars:
            return "***"
        return f"{data[:show_chars]}{'*' * (len(data) - show_chars)}"
    
    def validate_coordinates(self, lat: float, lon: float) -> bool:
        """Validate geographic coordinates"""
        return -90 <= lat <= 90 and -180 <= lon <= 180
    
    def validate_ip_address(self, ip: str) -> bool:
        """Validate IP address format"""
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)


class APIKeyRotation:
    """Manage API key rotation for enhanced security"""
    
    def __init__(self, rotation_hours: int = 24):
        self.rotation_hours = rotation_hours
        self.key_store: Dict[str, Dict] = {}
        
    def should_rotate(self, service_name: str) -> bool:
        """Check if API key should be rotated"""
        if service_name not in self.key_store:
            return True
        
        last_rotation = self.key_store[service_name].get("last_rotation")
        if not last_rotation:
            return True
        
        time_diff = datetime.utcnow() - last_rotation
        return time_diff > timedelta(hours=self.rotation_hours)
    
    def rotate_key(self, service_name: str, new_key: str):
        """Rotate API key for service"""
        self.key_store[service_name] = {
            "key": new_key,
            "last_rotation": datetime.utcnow(),
            "rotation_count": self.key_store.get(service_name, {}).get("rotation_count", 0) + 1
        }
        logger.info(f"API key rotated for {service_name}")
    
    def get_active_key(self, service_name: str) -> Optional[str]:
        """Get active API key for service"""
        return self.key_store.get(service_name, {}).get("key")


# Global security manager instance
_security_manager = SecurityManager()
_key_rotation = APIKeyRotation(rotation_hours=getattr(settings, 'api_key_rotation_hours', 24))


def get_security_manager() -> SecurityManager:
    """Get global security manager instance"""
    return _security_manager


def get_key_rotation() -> APIKeyRotation:
    """Get global key rotation manager"""
    return _key_rotation
