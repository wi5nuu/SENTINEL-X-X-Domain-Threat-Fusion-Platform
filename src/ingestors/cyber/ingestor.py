"""
Cyber Domain Ingestor - Real-Time Threat Intelligence
Pulls from real threat intelligence feeds: OTX, AbuseIPDB, ThreatFox
ICS Honeypot logic retained for local probe detection
"""
import asyncio
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict
import httpx

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics, track_latency
from src.common.kafka import kafka_client
from src.common.models import CyberEvent, ThreatLevel
from src.common.security import get_security_manager

logger = setup_logging("cyber-ingestor")
security = get_security_manager()

ICS_PORTS = {
    102: "S7comm (Siemens SCADA)",
    502: "Modbus TCP (PLC)",
    20000: "DNP3 (RTU Substation)",
    44818: "EtherNet/IP (Rockwell)",
}

ICS_FINGERPRINTS = {
    "Shodan": ["Shodan", "Mozilla/5.0 Shodan", "shodan"],
    "Nmap": ["Nmap", "nmap", "masscan"],
    "Metasploit": ["Metasploit", "meterpreter", "reverse_tcp"],
}


class ICSHoneypot:
    """Local ICS honeypot for detecting real probe attempts"""

    def __init__(self):
        self.connections: Dict[str, list] = {}

    async def handle_connection(self, src_ip: str, dst_port: int, payload: str) -> Optional[CyberEvent]:
        if dst_port not in ICS_PORTS:
            return None
        if not security.validate_ip(src_ip):
            return None

        technique = None
        for tool, signatures in ICS_FINGERPRINTS.items():
            for sig in signatures:
                if sig.lower() in payload.lower():
                    technique = tool
                    break

        event = CyberEvent(
            src_ip=src_ip,
            dst_port=dst_port,
            protocol=ICS_PORTS.get(dst_port, "unknown"),
            payload_hex=payload,
            technique=technique,
            target_sector="power_grid" if dst_port in (502, 20000) else "industrial_control",
            source_feed="honeypot",
            severity=ThreatLevel.suspicious,
        )

        if src_ip not in self.connections:
            self.connections[src_ip] = []
        self.connections[src_ip].append({
            "timestamp": datetime.utcnow().isoformat(),
            "port": dst_port,
            "payload": payload[:64],
        })

        return event


class ThreatFeedIngestor:
    """Real-time threat intelligence feed ingestion"""

    def __init__(self):
        self.http_client: Optional[httpx.AsyncClient] = None
        self.running = False
        self.seen_indicators: set = set()

    def _dedup(self, indicator: str) -> bool:
        """Returns True if new (not seen before)"""
        h = hashlib.sha256(indicator.encode()).hexdigest()[:16]
        if h in self.seen_indicators:
            return False
        self.seen_indicators.add(h)
        if len(self.seen_indicators) > 50000:
            self.seen_indicators = set(list(self.seen_indicators)[-25000:])
        return True

    @track_latency("cyber")
    async def poll_otx(self):
        """Poll AlienVault OTX for real threat indicators"""
        api_key = getattr(settings, 'otx_api_key', '')
        base_url = getattr(settings, 'otx_api_url', 'https://otx.alienvault.com/api/v1')

        if not api_key:
            logger.warning("OTX API key not configured - skipping")
            while self.running:
                await asyncio.sleep(3600)
            return

        headers = {"X-OTX-API-KEY": api_key}

        while self.running:
            if not security.check_rate_limit("otx", max_requests=100, window_seconds=3600):
                await asyncio.sleep(60)
                continue

            try:
                resp = await self.http_client.get(
                    f"{base_url}/pulses/subscribed",
                    headers=headers,
                    params={"limit": 50, "page": 1}
                )

                if resp.status_code == 200:
                    data = resp.json()
                    pulses = data.get("results", [])
                    count = 0

                    for pulse in pulses:
                        for indicator in pulse.get("indicators", [])[:20]:
                            ioc_value = indicator.get("indicator", "")
                            ioc_type = indicator.get("type", "")

                            if not ioc_value or not self._dedup(ioc_value):
                                continue

                            event = {
                                "event_id": str(uuid.uuid4()),
                                "timestamp_utc": datetime.utcnow().isoformat(),
                                "source_feed": "otx_real",
                                "indicator": security.sanitize_input(ioc_value),
                                "indicator_type": ioc_type,
                                "pulse_name": security.sanitize_input(pulse.get("name", "")),
                                "pulse_id": pulse.get("id", ""),
                                "tlp": pulse.get("tlp", "white"),
                                "tags": pulse.get("tags", [])[:5],
                                "confidence": indicator.get("confidence", 50),
                                "malware_families": pulse.get("malware_families", [])[:3],
                                "domain": "cyber",
                            }

                            await kafka_client.send_event("cyber-events", event, key=ioc_value)
                            metrics.events_ingested.labels(domain="cyber", source="otx_real").inc()
                            count += 1

                    logger.info(f"OTX poll complete: {count} real indicators")
                else:
                    logger.warning(f"OTX API error: {resp.status_code}")

            except Exception as e:
                logger.error(f"OTX poll error: {e}")
                metrics.errors_total.labels(service="cyber", error_type="otx_poll").inc()

            await asyncio.sleep(300)  # poll every 5 minutes

    async def poll_abuseipdb(self):
        """Poll AbuseIPDB for real malicious IP reports"""
        api_key = getattr(settings, 'abuseipdb_key', '')
        base_url = getattr(settings, 'abuseipdb_url', 'https://api.abuseipdb.com/api/v2')

        if not api_key:
            logger.warning("AbuseIPDB API key not configured - skipping")
            while self.running:
                await asyncio.sleep(3600)
            return

        headers = {
            "Key": api_key,
            "Accept": "application/json"
        }

        while self.running:
            if not security.check_rate_limit("abuseipdb", max_requests=20, window_seconds=86400):
                await asyncio.sleep(3600)
                continue

            try:
                resp = await self.http_client.get(
                    f"{base_url}/blacklist",
                    headers=headers,
                    params={
                        "confidenceMinimum": 90,
                        "limit": 100
                    }
                )

                if resp.status_code == 200:
                    data = resp.json()
                    entries = data.get("data", [])
                    count = 0

                    for entry in entries:
                        ip = entry.get("ipAddress", "")
                        if not ip or not self._dedup(ip):
                            continue
                        if not security.validate_ip(ip):
                            continue

                        event = {
                            "event_id": str(uuid.uuid4()),
                            "timestamp_utc": datetime.utcnow().isoformat(),
                            "source_feed": "abuseipdb_real",
                            "indicator": ip,
                            "indicator_type": "IPv4",
                            "abuse_confidence": entry.get("abuseConfidenceScore", 0),
                            "country_code": entry.get("countryCode", ""),
                            "usage_type": entry.get("usageType", ""),
                            "isp": entry.get("isp", ""),
                            "total_reports": entry.get("totalReports", 0),
                            "last_reported": entry.get("lastReportedAt", ""),
                            "domain": "cyber",
                        }

                        await kafka_client.send_event("cyber-events", event, key=ip)
                        metrics.events_ingested.labels(domain="cyber", source="abuseipdb_real").inc()
                        count += 1

                    logger.info(f"AbuseIPDB poll complete: {count} real malicious IPs")
                else:
                    logger.warning(f"AbuseIPDB API error: {resp.status_code}")

            except Exception as e:
                logger.error(f"AbuseIPDB poll error: {e}")
                metrics.errors_total.labels(service="cyber", error_type="abuseipdb_poll").inc()

            await asyncio.sleep(3600)  # poll every hour (rate limit)

    async def poll_threatfox(self):
        """Poll ThreatFox for real malware IOCs (no key required)"""
        base_url = getattr(settings, 'threatfox_url', 'https://threatfox-api.abuse.ch/api/v1')

        while self.running:
            if not security.check_rate_limit("threatfox", max_requests=50, window_seconds=3600):
                await asyncio.sleep(300)
                continue

            try:
                resp = await self.http_client.post(
                    base_url,
                    json={"query": "get_iocs", "days": 1}
                )

                if resp.status_code == 200:
                    data = resp.json()
                    iocs = data.get("data", [])
                    count = 0

                    for ioc in (iocs or [])[:100]:
                        ioc_val = ioc.get("ioc", "")
                        if not ioc_val or not self._dedup(ioc_val):
                            continue

                        event = {
                            "event_id": str(uuid.uuid4()),
                            "timestamp_utc": datetime.utcnow().isoformat(),
                            "source_feed": "threatfox_real",
                            "indicator": security.sanitize_input(ioc_val),
                            "indicator_type": ioc.get("ioc_type", ""),
                            "malware": ioc.get("malware", ""),
                            "malware_printable": ioc.get("malware_printable", ""),
                            "confidence": ioc.get("confidence_level", 50),
                            "tags": ioc.get("tags", [])[:5],
                            "first_seen": ioc.get("first_seen", ""),
                            "threat_type": ioc.get("threat_type", ""),
                            "domain": "cyber",
                        }

                        await kafka_client.send_event("cyber-events", event, key=ioc_val)
                        metrics.events_ingested.labels(domain="cyber", source="threatfox_real").inc()
                        count += 1

                    logger.info(f"ThreatFox poll complete: {count} real IOCs")
                else:
                    logger.warning(f"ThreatFox API error: {resp.status_code}")

            except Exception as e:
                logger.error(f"ThreatFox poll error: {e}")
                metrics.errors_total.labels(service="cyber", error_type="threatfox_poll").inc()

            await asyncio.sleep(300)


class CyberDomainIngestor:
    """Main cyber domain ingestor - all real threat feeds"""

    def __init__(self):
        self.honeypot = ICSHoneypot()
        self.feed_ingestor = ThreatFeedIngestor()
        self.running = False

    async def start(self):
        self.running = True
        self.feed_ingestor.running = True
        self.feed_ingestor.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "SENTINEL-ThreatIntel/1.0"}
        )
        await kafka_client.start()
        logger.info("Cyber Domain Ingestor started - REAL THREAT FEEDS ONLY")

        tasks = [
            self.feed_ingestor.poll_otx(),
            self.feed_ingestor.poll_abuseipdb(),
            self.feed_ingestor.poll_threatfox(),
        ]
        await asyncio.gather(*tasks)

    async def stop(self):
        self.running = False
        self.feed_ingestor.running = False
        if self.feed_ingestor.http_client:
            await self.feed_ingestor.http_client.aclose()
        await kafka_client.stop()
