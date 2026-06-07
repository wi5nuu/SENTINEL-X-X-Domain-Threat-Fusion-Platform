"""
Real-time Cyber Threat Intelligence Ingestor
Integrates with: AlienVault OTX, AbuseIPDB, Shodan, VirusTotal, ThreatFox
"""
import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import httpx

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics
from src.common.kafka import kafka_client
from src.common.security import get_security_manager, get_key_rotation

logger = setup_logging("threat-intel-ingestor")
security = get_security_manager()
key_rotation = get_key_rotation()


class ThreatIntelIngestor:
    """Real-time threat intelligence from multiple sources"""
    
    def __init__(self):
        self.running = False
        self.http_client: Optional[httpx.AsyncClient] = None
        self.seen_indicators = set()
        
        # API configurations with security
        self.otx_key = getattr(settings, 'otx_api_key', '')
        self.abuseipdb_key = getattr(settings, 'abuseipdb_key', '')
        self.shodan_key = getattr(settings, 'shodan_key', '')
        self.virustotal_key = getattr(settings, 'virustotal_api_key', '')
        self.threatfox_key = getattr(settings, 'threatfox_api_key', '')
        
        logger.info(f"Threat Intel sources configured: OTX={bool(self.otx_key)}, "
                   f"AbuseIPDB={bool(self.abuseipdb_key)}, Shodan={bool(self.shodan_key)}, "
                   f"VirusTotal={bool(self.virustotal_key)}")
    
    async def start(self):
        self.running = True
        self.http_client = httpx.AsyncClient(timeout=30.0)
        await kafka_client.start()
        logger.info("Threat Intelligence Ingestor started - REAL-TIME MODE")
        
        tasks = []
        if self.otx_key:
            tasks.append(self.poll_otx_pulses())
        if self.abuseipdb_key:
            tasks.append(self.poll_abuseipdb())
        if self.shodan_key:
            tasks.append(self.poll_shodan_alerts())
        if self.virustotal_key:
            tasks.append(self.poll_virustotal())
        
        tasks.append(self.poll_threatfox())  # Public API
        
        if not tasks:
            logger.warning("No threat intelligence sources configured!")
            return
        
        await asyncio.gather(*tasks)
    
    async def stop(self):
        self.running = False
        if self.http_client:
            await self.http_client.aclose()
        await kafka_client.stop()
    
    async def poll_otx_pulses(self):
        """Poll AlienVault OTX for threat pulses"""
        while self.running:
            # Check rate limit
            if not security.check_rate_limit("otx_api", max_requests=100, window_seconds=3600):
                await asyncio.sleep(60)
                continue
            
            try:
                headers = {
                    "X-OTX-API-KEY": self.otx_key,
                    "User-Agent": "SENTINEL-Platform/1.0"
                }
                
                # Get subscribed pulses
                resp = await self.http_client.get(
                    f"{getattr(settings, 'otx_api_url', 'https://otx.alienvault.com/api/v1')}/pulses/subscribed",
                    headers=headers,
                    params={"limit": 50, "page": 1}
                )
                
                if resp.status_code != 200:
                    logger.warning(f"OTX API error: {resp.status_code}")
                    await asyncio.sleep(300)
                    continue
                
                data = resp.json()
                pulses = data.get("results", [])
                
                for pulse in pulses:
                    await self._process_otx_pulse(pulse)
                
                logger.info(f"OTX poll complete: {len(pulses)} pulses")
                
            except Exception as e:
                logger.error(f"OTX poll error: {e}")
                metrics.errors_total.labels(service="threat_intel", error_type="otx_poll").inc()
            
            await asyncio.sleep(300)  # Poll every 5 minutes
    
    async def _process_otx_pulse(self, pulse: dict):
        """Process OTX threat pulse"""
        try:
            pulse_id = pulse.get("id", str(uuid.uuid4()))
            indicators = pulse.get("indicators", [])
            
            for indicator in indicators[:50]:  # Limit to prevent overload
                ioc_type = indicator.get("type", "unknown")
                ioc_value = security.sanitize_input(indicator.get("indicator", ""))
                
                if not ioc_value:
                    continue
                
                # Create unique identifier
                ioc_hash = hashlib.sha256(f"{ioc_type}:{ioc_value}".encode()).hexdigest()[:16]
                if ioc_hash in self.seen_indicators:
                    continue
                
                self.seen_indicators.add(ioc_hash)
                if len(self.seen_indicators) > 50000:
                    self.seen_indicators = set(list(self.seen_indicators)[-25000:])
                
                # Determine severity
                severity = self._calculate_severity(pulse, indicator)
                
                event = {
                    "event_id": f"otx_{ioc_hash}",
                    "domain": "cyber",
                    "timestamp_utc": pulse.get("created", datetime.utcnow().isoformat()),
                    "type": f"otx_{ioc_type}",
                    "technique": security.sanitize_input(pulse.get("attack_ids", ["unknown"])[0] if pulse.get("attack_ids") else "unknown"),
                    "src_ip": ioc_value if ioc_type in ["IPv4", "IPv6"] else "0.0.0.0",
                    "dst_ip": "0.0.0.0",
                    "src_port": 0,
                    "dst_port": 0,
                    "protocol": "INTEL",
                    "target_sector": security.sanitize_input(",".join(pulse.get("industries", [])[:3])) or None,
                    "severity": severity,
                    "source_feed": "otx_real",
                    "ioc_type": ioc_type,
                    "ioc_value": ioc_value,
                    "threat_name": security.sanitize_input(pulse.get("name", "Unknown")),
                    "adversary": security.sanitize_input(pulse.get("adversary", "")),
                    "malware_families": pulse.get("malware_families", [])[:5],
                    "tags": pulse.get("tags", [])[:10],
                    "threat_flags": [f"otx:{ioc_type}", "threat_intel_confirmed"]
                }
                
                # Validate IP if applicable
                if ioc_type in ["IPv4", "IPv6"] and not security.validate_ip_address(ioc_value):
                    continue
                
                await kafka_client.send_event("cyber-events", event, key=event["event_id"])
                metrics.events_ingested.labels(domain="cyber", source="otx_real").inc()
                
                # Emit alert for critical threats
                if severity in ["CRITICAL", "CATASTROPHIC"]:
                    await self._emit_alert(event)
                
        except Exception as e:
            logger.error(f"Error processing OTX pulse: {e}")
    
    async def poll_abuseipdb(self):
        """Poll AbuseIPDB for malicious IPs"""
        while self.running:
            if not security.check_rate_limit("abuseipdb_api", max_requests=1000, window_seconds=86400):
                await asyncio.sleep(300)
                continue
            
            try:
                headers = {
                    "Key": self.abuseipdb_key,
                    "Accept": "application/json"
                }
                
                # Get blacklist
                resp = await self.http_client.get(
                    f"{getattr(settings, 'abuseipdb_url', 'https://api.abuseipdb.com/api/v2')}/blacklist",
                    headers=headers,
                    params={"confidenceMinimum": 90, "limit": 100}
                )
                
                if resp.status_code != 200:
                    logger.warning(f"AbuseIPDB API error: {resp.status_code}")
                    await asyncio.sleep(600)
                    continue
                
                data = resp.json()
                ips = data.get("data", [])
                
                for ip_data in ips:
                    await self._process_abuseipdb_entry(ip_data)
                
                logger.info(f"AbuseIPDB poll complete: {len(ips)} IPs")
                
            except Exception as e:
                logger.error(f"AbuseIPDB poll error: {e}")
                metrics.errors_total.labels(service="threat_intel", error_type="abuseipdb_poll").inc()
            
            await asyncio.sleep(3600)  # Poll every hour
    
    async def _process_abuseipdb_entry(self, ip_data: dict):
        """Process AbuseIPDB malicious IP"""
        try:
            ip_address = ip_data.get("ipAddress", "")
            if not security.validate_ip_address(ip_address):
                return
            
            ioc_hash = hashlib.sha256(f"ipv4:{ip_address}".encode()).hexdigest()[:16]
            if ioc_hash in self.seen_indicators:
                return
            
            self.seen_indicators.add(ioc_hash)
            
            confidence_score = ip_data.get("abuseConfidenceScore", 0)
            
            # Determine severity based on confidence
            if confidence_score >= 95:
                severity = "CRITICAL"
            elif confidence_score >= 85:
                severity = "ELEVATED"
            else:
                severity = "SUSPICIOUS"
            
            event = {
                "event_id": f"abuseipdb_{ioc_hash}",
                "domain": "cyber",
                "timestamp_utc": datetime.utcnow().isoformat(),
                "type": "malicious_ip",
                "technique": "network_scanning",
                "src_ip": ip_address,
                "dst_ip": "0.0.0.0",
                "src_port": 0,
                "dst_port": 0,
                "protocol": "INTEL",
                "target_sector": None,
                "severity": severity,
                "source_feed": "abuseipdb_real",
                "ioc_type": "IPv4",
                "ioc_value": ip_address,
                "abuse_confidence_score": confidence_score,
                "country_code": ip_data.get("countryCode", ""),
                "threat_flags": ["abuseipdb_blacklist", "malicious_ip_confirmed"]
            }
            
            await kafka_client.send_event("cyber-events", event, key=event["event_id"])
            metrics.events_ingested.labels(domain="cyber", source="abuseipdb_real").inc()
            
        except Exception as e:
            logger.error(f"Error processing AbuseIPDB entry: {e}")
    
    async def poll_shodan_alerts(self):
        """Poll Shodan for network alerts"""
        while self.running:
            if not security.check_rate_limit("shodan_api", max_requests=100, window_seconds=3600):
                await asyncio.sleep(300)
                continue
            
            try:
                params = {"key": self.shodan_key}
                
                # Get network alerts
                resp = await self.http_client.get(
                    f"{getattr(settings, 'shodan_url', 'https://api.shodan.io')}/shodan/alert/info",
                    params=params
                )
                
                if resp.status_code == 200:
                    alerts = resp.json()
                    for alert in alerts[:50]:
                        await self._process_shodan_alert(alert)
                    
                    logger.info(f"Shodan poll complete: {len(alerts)} alerts")
                
            except Exception as e:
                logger.error(f"Shodan poll error: {e}")
                metrics.errors_total.labels(service="threat_intel", error_type="shodan_poll").inc()
            
            await asyncio.sleep(600)  # Poll every 10 minutes
    
    async def _process_shodan_alert(self, alert: dict):
        """Process Shodan network alert"""
        try:
            alert_id = alert.get("id", str(uuid.uuid4()))
            
            event = {
                "event_id": f"shodan_{alert_id}",
                "domain": "cyber",
                "timestamp_utc": datetime.utcnow().isoformat(),
                "type": "network_exposure",
                "technique": "reconnaissance",
                "src_ip": "0.0.0.0",
                "dst_ip": "0.0.0.0",
                "src_port": 0,
                "dst_port": 0,
                "protocol": "INTEL",
                "target_sector": None,
                "severity": "ELEVATED",
                "source_feed": "shodan_real",
                "alert_name": security.sanitize_input(alert.get("name", "Unknown")),
                "threat_flags": ["shodan_alert", "network_exposure"]
            }
            
            await kafka_client.send_event("cyber-events", event, key=event["event_id"])
            metrics.events_ingested.labels(domain="cyber", source="shodan_real").inc()
            
        except Exception as e:
            logger.error(f"Error processing Shodan alert: {e}")
    
    async def poll_virustotal(self):
        """Poll VirusTotal for file and URL intelligence"""
        while self.running:
            if not security.check_rate_limit("virustotal_api", max_requests=500, window_seconds=86400):
                await asyncio.sleep(600)
                continue
            
            try:
                headers = {
                    "x-apikey": self.virustotal_key,
                    "Accept": "application/json"
                }
                
                # Get recent files
                resp = await self.http_client.get(
                    f"{getattr(settings, 'virustotal_url', 'https://www.virustotal.com/api/v3')}/intelligence/search",
                    headers=headers,
                    params={"query": "type:file fs:2024-01-01+", "limit": 40}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    files = data.get("data", [])
                    
                    for file_data in files:
                        await self._process_virustotal_file(file_data)
                    
                    logger.info(f"VirusTotal poll complete: {len(files)} files")
                
            except Exception as e:
                logger.error(f"VirusTotal poll error: {e}")
                metrics.errors_total.labels(service="threat_intel", error_type="virustotal_poll").inc()
            
            await asyncio.sleep(900)  # Poll every 15 minutes
    
    async def _process_virustotal_file(self, file_data: dict):
        """Process VirusTotal file intelligence"""
        try:
            attributes = file_data.get("attributes", {})
            file_hash = attributes.get("sha256", str(uuid.uuid4()))
            
            ioc_hash = hashlib.sha256(f"hash:{file_hash}".encode()).hexdigest()[:16]
            if ioc_hash in self.seen_indicators:
                return
            
            self.seen_indicators.add(ioc_hash)
            
            stats = attributes.get("last_analysis_stats", {})
            malicious_count = stats.get("malicious", 0)
            
            if malicious_count < 5:
                return  # Skip low-confidence detections
            
            severity = "CRITICAL" if malicious_count > 40 else "ELEVATED" if malicious_count > 20 else "SUSPICIOUS"
            
            event = {
                "event_id": f"virustotal_{ioc_hash}",
                "domain": "cyber",
                "timestamp_utc": datetime.utcnow().isoformat(),
                "type": "malware_detected",
                "technique": "malware",
                "src_ip": "0.0.0.0",
                "dst_ip": "0.0.0.0",
                "src_port": 0,
                "dst_port": 0,
                "protocol": "INTEL",
                "target_sector": None,
                "severity": severity,
                "source_feed": "virustotal_real",
                "ioc_type": "hash",
                "ioc_value": file_hash,
                "malicious_detections": malicious_count,
                "file_type": security.sanitize_input(attributes.get("type_description", "Unknown")),
                "threat_flags": ["virustotal_detection", "malware_confirmed"]
            }
            
            await kafka_client.send_event("cyber-events", event, key=event["event_id"])
            metrics.events_ingested.labels(domain="cyber", source="virustotal_real").inc()
            
        except Exception as e:
            logger.error(f"Error processing VirusTotal file: {e}")
    
    async def poll_threatfox(self):
        """Poll ThreatFox for IOCs (public API)"""
        while self.running:
            try:
                # Get recent IOCs
                resp = await self.http_client.post(
                    f"{getattr(settings, 'threatfox_url', 'https://threatfox-api.abuse.ch/api/v1')}/",
                    json={"query": "get_iocs", "days": 1}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    iocs = data.get("data", [])
                    
                    for ioc in iocs[:100]:
                        await self._process_threatfox_ioc(ioc)
                    
                    logger.info(f"ThreatFox poll complete: {len(iocs)} IOCs")
                
            except Exception as e:
                logger.error(f"ThreatFox poll error: {e}")
            
            await asyncio.sleep(600)  # Poll every 10 minutes
    
    async def _process_threatfox_ioc(self, ioc: dict):
        """Process ThreatFox IOC"""
        try:
            ioc_value = security.sanitize_input(ioc.get("ioc", ""))
            ioc_type = ioc.get("ioc_type", "unknown")
            
            ioc_hash = hashlib.sha256(f"{ioc_type}:{ioc_value}".encode()).hexdigest()[:16]
            if ioc_hash in self.seen_indicators:
                return
            
            self.seen_indicators.add(ioc_hash)
            
            confidence = ioc.get("confidence_level", 50)
            severity = "CRITICAL" if confidence >= 80 else "ELEVATED" if confidence >= 50 else "SUSPICIOUS"
            
            event = {
                "event_id": f"threatfox_{ioc_hash}",
                "domain": "cyber",
                "timestamp_utc": ioc.get("first_seen", datetime.utcnow().isoformat()),
                "type": f"threatfox_{ioc_type}",
                "technique": security.sanitize_input(ioc.get("threat_type", "unknown")),
                "src_ip": ioc_value if ioc_type in ["ip:port", "ip"] else "0.0.0.0",
                "dst_ip": "0.0.0.0",
                "src_port": 0,
                "dst_port": 0,
                "protocol": "INTEL",
                "target_sector": None,
                "severity": severity,
                "source_feed": "threatfox_real",
                "ioc_type": ioc_type,
                "ioc_value": ioc_value,
                "malware": security.sanitize_input(ioc.get("malware", "")),
                "confidence_level": confidence,
                "threat_flags": ["threatfox_ioc", "active_threat"]
            }
            
            await kafka_client.send_event("cyber-events", event, key=event["event_id"])
            metrics.events_ingested.labels(domain="cyber", source="threatfox_real").inc()
            
        except Exception as e:
            logger.error(f"Error processing ThreatFox IOC: {e}")
    
    def _calculate_severity(self, pulse: dict, indicator: dict) -> str:
        """Calculate threat severity based on pulse and indicator data"""
        tags = pulse.get("tags", [])
        references = pulse.get("references", [])
        
        # High severity indicators
        if any(tag in tags for tag in ["apt", "ransomware", "critical", "zero-day", "exploit"]):
            return "CRITICAL"
        
        if any(tag in tags for tag in ["malware", "botnet", "phishing", "c2"]):
            return "ELEVATED"
        
        if len(references) > 5:
            return "ELEVATED"
        
        return "SUSPICIOUS"
    
    async def _emit_alert(self, event: dict):
        """Emit alert for critical threat intelligence"""
        alert = {
            "alert_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.utcnow().isoformat(),
            "threat_class": event["severity"],
            "confidence": 0.90,
            "domain": "cyber",
            "description": f"Critical threat intel: {event.get('threat_name', event['type'])} - IOC: {event.get('ioc_value', 'N/A')}",
            "source": "threat_intel_real",
            "ipfs_hash": f"Qm{abs(hash(event['event_id']))}{uuid.uuid4().hex[:16]}",
        }
        
        await kafka_client.send_event("alerts", alert, key=alert["alert_id"])
        metrics.events_ingested.labels(domain="alerts", source="threat_intel").inc()


if __name__ == "__main__":
    ingestor = ThreatIntelIngestor()
    asyncio.run(ingestor.start())
