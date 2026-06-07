"""
Data Quality Validator
Ensures all incoming data meets accuracy and quality standards
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np

from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics

logger = setup_logging("data-quality")


class DataQualityValidator:
    """Validates and scores data quality across all domains"""
    
    def __init__(self):
        self.quality_thresholds = {
            "aviation": {
                "position_accuracy_m": 100,  # GPS accuracy
                "altitude_accuracy_ft": 250,
                "speed_variance_kts": 50,
                "timestamp_delay_s": 30
            },
            "maritime": {
                "position_accuracy_m": 500,
                "speed_variance_kts": 10,
                "timestamp_delay_s": 60
            },
            "cyber": {
                "timestamp_delay_s": 5,
                "confidence_min": 0.7
            },
            "seismic": {
                "magnitude_precision": 0.1,
                "location_accuracy_km": 10
            }
        }
        
        self.validation_history = {}
    
    def validate_aviation_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate aviation data quality"""
        quality_score = 1.0
        issues = []
        
        # Check required fields
        required_fields = ["lat", "lon", "altitude", "timestamp_utc"]
        for field in required_fields:
            if field not in data or data[field] is None:
                quality_score -= 0.2
                issues.append(f"missing_{field}")
        
        # Validate coordinates
        if not self._validate_coordinates(data.get("lat"), data.get("lon")):
            quality_score -= 0.3
            issues.append("invalid_coordinates")
        
        # Validate altitude (reasonable range for aircraft)
        altitude = data.get("altitude_ft", data.get("baro_altitude_m", 0))
        if altitude:
            if altitude < -1000 or altitude > 60000:
                quality_score -= 0.2
                issues.append("unrealistic_altitude")
        
        # Validate speed (reasonable for aircraft)
        speed = data.get("groundspeed_kts", data.get("velocity_ms", 0))
        if speed:
            if speed < 0 or speed > 600:
                quality_score -= 0.2
                issues.append("unrealistic_speed")
        
        # Check timestamp freshness
        timestamp = self._parse_timestamp(data.get("timestamp_utc"))
        if timestamp:
            age_seconds = (datetime.utcnow() - timestamp).total_seconds()
            if age_seconds > 300:  # Data older than 5 minutes
                quality_score -= 0.1
                issues.append("stale_data")
        
        # Check for duplicate data
        data_hash = self._hash_data(data)
        if self._is_duplicate(data_hash, "aviation"):
            quality_score -= 0.3
            issues.append("duplicate_data")
        
        return {
            "quality_score": max(quality_score, 0.0),
            "issues": issues,
            "validated": quality_score >= 0.6,
            "timestamp_validated": datetime.utcnow().isoformat()
        }
    
    def validate_maritime_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate maritime data quality"""
        quality_score = 1.0
        issues = []
        
        # Check required fields
        required_fields = ["mmsi", "lat", "lon", "timestamp_utc"]
        for field in required_fields:
            if field not in data or data[field] is None:
                quality_score -= 0.2
                issues.append(f"missing_{field}")
        
        # Validate MMSI format (9 digits)
        mmsi = str(data.get("mmsi", ""))
        if not mmsi.isdigit() or len(mmsi) != 9:
            quality_score -= 0.3
            issues.append("invalid_mmsi")
        
        # Validate coordinates
        if not self._validate_coordinates(data.get("lat"), data.get("lon")):
            quality_score -= 0.3
            issues.append("invalid_coordinates")
        
        # Validate speed (reasonable for vessels)
        speed = data.get("sog_knots", 0)
        if speed < 0 or speed > 50:  # Max ship speed ~40 knots
            quality_score -= 0.2
            issues.append("unrealistic_speed")
        
        # Check timestamp freshness
        timestamp = self._parse_timestamp(data.get("timestamp_utc"))
        if timestamp:
            age_seconds = (datetime.utcnow() - timestamp).total_seconds()
            if age_seconds > 600:  # Data older than 10 minutes
                quality_score -= 0.1
                issues.append("stale_data")
        
        return {
            "quality_score": max(quality_score, 0.0),
            "issues": issues,
            "validated": quality_score >= 0.6,
            "timestamp_validated": datetime.utcnow().isoformat()
        }
    
    def validate_cyber_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate cyber threat data quality"""
        quality_score = 1.0
        issues = []
        
        # Check IOC validity
        ioc_value = data.get("ioc_value", "")
        ioc_type = data.get("ioc_type", "")
        
        if ioc_type == "IPv4":
            if not self._validate_ipv4(ioc_value):
                quality_score -= 0.4
                issues.append("invalid_ip")
        
        # Check confidence score
        confidence = data.get("confidence", 0)
        if confidence < 0.5:
            quality_score -= 0.2
            issues.append("low_confidence")
        
        # Check source reputation
        source = data.get("source_feed", "")
        trusted_sources = ["otx_real", "abuseipdb_real", "virustotal_real", "threatfox_real"]
        if source not in trusted_sources:
            quality_score -= 0.1
            issues.append("untrusted_source")
        
        return {
            "quality_score": max(quality_score, 0.0),
            "issues": issues,
            "validated": quality_score >= 0.6,
            "timestamp_validated": datetime.utcnow().isoformat()
        }
    
    def validate_seismic_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate seismic data quality"""
        quality_score = 1.0
        issues = []
        
        # Validate magnitude range
        magnitude = data.get("magnitude", 0)
        if magnitude < 0 or magnitude > 10:
            quality_score -= 0.3
            issues.append("invalid_magnitude")
        
        # Validate depth (reasonable for earthquakes)
        depth = data.get("depth_km", 0)
        if depth < 0 or depth > 700:  # Max earthquake depth ~700km
            quality_score -= 0.2
            issues.append("unrealistic_depth")
        
        # Validate coordinates
        if not self._validate_coordinates(data.get("lat"), data.get("lon")):
            quality_score -= 0.3
            issues.append("invalid_coordinates")
        
        # Check source reliability
        source = data.get("source", "")
        if source not in ["usgs_real", "emsc_real"]:
            quality_score -= 0.2
            issues.append("non_authoritative_source")
        
        return {
            "quality_score": max(quality_score, 0.0),
            "issues": issues,
            "validated": quality_score >= 0.7,  # Higher threshold for seismic
            "timestamp_validated": datetime.utcnow().isoformat()
        }
    
    def _validate_coordinates(self, lat: Optional[float], lon: Optional[float]) -> bool:
        """Validate geographic coordinates"""
        if lat is None or lon is None:
            return False
        try:
            lat = float(lat)
            lon = float(lon)
            return -90 <= lat <= 90 and -180 <= lon <= 180
        except (ValueError, TypeError):
            return False
    
    def _validate_ipv4(self, ip: str) -> bool:
        """Validate IPv4 address"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            return all(0 <= int(part) <= 255 for part in parts)
        except (ValueError, AttributeError):
            return False
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp string"""
        if not timestamp_str:
            return None
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    def _hash_data(self, data: Dict[str, Any]) -> str:
        """Create hash of data for duplicate detection"""
        import hashlib
        key_fields = ["lat", "lon", "timestamp_utc", "mmsi", "icao24", "event_id"]
        hash_input = "|".join(str(data.get(k, "")) for k in key_fields if k in data)
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _is_duplicate(self, data_hash: str, domain: str) -> bool:
        """Check if data is duplicate"""
        key = f"{domain}_{data_hash}"
        
        # Clean old entries (older than 5 minutes)
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        self.validation_history = {
            k: v for k, v in self.validation_history.items()
            if v > cutoff
        }
        
        if key in self.validation_history:
            return True
        
        self.validation_history[key] = datetime.utcnow()
        return False
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """Get overall data quality metrics"""
        return {
            "total_validations": len(self.validation_history),
            "timestamp": datetime.utcnow().isoformat()
        }


# Global validator instance
_validator = DataQualityValidator()


def get_validator() -> DataQualityValidator:
    """Get global validator instance"""
    return _validator
