"""
SENTINEL Platform - Configuration Validator
Validates system configuration and prerequisites

NOTE: This is a simplified version for demonstration.
Production deployments require additional security measures.
"""
import os
import sys
import hashlib
import json
from datetime import datetime
from pathlib import Path


class ConfigValidator:
    """
    Validates system configuration and prerequisites.
    Ensures all required components are properly configured.
    """
    
    CONFIG_FILE = ".sentinel_config"
    
    def __init__(self):
        self.config_valid = False
        self.warnings = []
        self.errors = []
        
    def check_environment(self) -> bool:
        """
        Check if environment is properly configured.
        Returns True if basic requirements are met.
        """
        print("\n" + "="*60)
        print("SENTINEL PLATFORM - CONFIGURATION VALIDATOR")
        print("="*60)
        
        # Check .env file
        if not os.path.exists('.env'):
            self.errors.append(".env file not found")
            print("❌ ERROR: .env file not found!")
            print("   Copy .env.example to .env and configure all parameters.")
        else:
            print("✓ .env file found")
        
        # Check required environment variables
        required_vars = [
            'JWT_SECRET_KEY',
            'DATABASE_URL',
            'KAFKA_BOOTSTRAP_SERVERS',
            'REDIS_URL',
            'ELASTICSEARCH_URL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.errors.append(f"Missing environment variables: {', '.join(missing_vars)}")
            print("❌ ERROR: Missing required environment variables:")
            for var in missing_vars:
                print(f"   - {var}")
        else:
            print("✓ Required environment variables configured")
        
        # Check API keys for data sources
        api_keys_optional = [
            'OPENSKY_USERNAME',
            'NASA_API_KEY',
            'OTX_API_KEY',
            'ABUSEIPDB_KEY',
            'AEROAPI_KEY',
            'OPENWEATHER_API_KEY'
        ]
        
        missing_keys = []
        for key in api_keys_optional:
            if not os.getenv(key):
                missing_keys.append(key)
        
        if missing_keys:
            self.warnings.append(f"Missing optional API keys: {', '.join(missing_keys)}")
            print(f"\n⚠️  WARNING: Missing optional API keys:")
            for key in missing_keys:
                print(f"   - {key}")
            print("   Platform will run with limited data sources.")
        
        # Summary
        print("\n" + "="*60)
        if self.errors:
            print("❌ CONFIGURATION INCOMPLETE")
            print(f"\nFound {len(self.errors)} error(s):")
            for error in self.errors:
                print(f"  - {error}")
            print("\nPlatform may not function correctly.")
            print("Please fix configuration issues above.")
        elif self.warnings:
            print("⚠️  CONFIGURATION WARNINGS")
            print(f"\nFound {len(self.warnings)} warning(s):")
            for warning in self.warnings:
                print(f"  - {warning}")
            print("\nPlatform will run with limited functionality.")
        else:
            print("✓ CONFIGURATION VALID")
            self.config_valid = True
        
        print("="*60 + "\n")
        
        return len(self.errors) == 0
    
    def validate_on_startup(self):
        """
        Run validation on startup.
        Shows warnings but allows platform to start.
        """
        if not self.check_environment():
            print("⚠️  WARNING: Configuration issues detected.")
            print("Platform will attempt to start, but may not function correctly.")
            print("Please review the errors above and update your .env file.\n")


# Global validator instance
_validator = None


def get_validator() -> ConfigValidator:
    """Get singleton validator instance"""
    global _validator
    if _validator is None:
        _validator = ConfigValidator()
    return _validator


def validate_config():
    """
    Validate configuration on module import.
    This runs automatically when the module is loaded.
    """
    validator = get_validator()
    validator.validate_on_startup()


if __name__ == "__main__":
    # Test configuration validation
    validator = ConfigValidator()
    validator.validate_on_startup()
