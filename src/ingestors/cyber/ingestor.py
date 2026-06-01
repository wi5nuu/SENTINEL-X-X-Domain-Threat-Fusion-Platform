import asyncio
import json
import random
from datetime import datetime
from typing import Optional, Dict
import httpx

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics, track_latency
from src.common.kafka import kafka_client
from src.common.models import CyberEvent, ThreatLevel

logger = setup_logging("cyber-ingestor")

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
    def __init__(self):
        self.connections: Dict[str, list] = {}

    async def handle_connection(self, src_ip: str, dst_port: int, payload: str) -> CyberEvent:
        if dst_port not in ICS_PORTS:
            return None

        technique = None
        for tool, signatures in ICS_FINGERPRINTS.items():
            for sig in signatures:
                if sig.lower() in payload.lower():
                    technique = tool
                    break

        event = CyberEvent(
            src_ip=src_ip,
            src_port=random.randint(1024, 65535),
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
    FEEDS = {
        "alienvault_otx": {
            "poll_interval": 300,
        },
        "abuseipdb": {
            "poll_interval": 3600,
        },
    }

    def __init__(self):
        self.http_client: Optional[httpx.AsyncClient] = None
        self.running = False

    async def poll_otx(self):
        while self.running:
            await asyncio.sleep(self.FEEDS["alienvault_otx"]["poll_interval"])
            metrics.events_ingested.labels(domain="cyber", source="otx").inc()
            indicator = {
                "timestamp_utc": datetime.utcnow().isoformat(),
                "source": "alienvault_otx",
                "indicator": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
                "type": "IPv4",
                "confidence": random.randint(50, 100),
            }
            await kafka_client.send_event("cyber-events", indicator, key=indicator["indicator"])

    async def poll_abuseipdb(self):
        while self.running:
            await asyncio.sleep(self.FEEDS["abuseipdb"]["poll_interval"])
            metrics.events_ingested.labels(domain="cyber", source="abuseipdb").inc()
            entry = {
                "timestamp_utc": datetime.utcnow().isoformat(),
                "source": "abuseipdb",
                "ip": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
                "confidence": random.randint(90, 100),
            }
            await kafka_client.send_event("cyber-events", entry, key=entry["ip"])


class CyberDomainIngestor:
    def __init__(self):
        self.honeypot = ICSHoneypot()
        self.feed_ingestor = ThreatFeedIngestor()
        self.running = False

    async def start(self):
        self.running = True
        self.feed_ingestor.running = True
        self.feed_ingestor.http_client = httpx.AsyncClient(timeout=30.0)
        await kafka_client.start()
        logger.info("Cyber Domain Ingestor started")
        tasks = [
            self.simulate_ics_probes(),
            self.feed_ingestor.poll_otx(),
            self.feed_ingestor.poll_abuseipdb(),
        ]
        await asyncio.gather(*tasks)

    async def stop(self):
        self.running = False
        await kafka_client.stop()

    @track_latency("cyber")
    async def simulate_ics_probes(self):
        while self.running:
            await asyncio.sleep(random.uniform(3, 15))
            src_ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
            dst_port = random.choice(list(ICS_PORTS.keys()))
            payload = random.choice([
                "0300001611be0000000100010061010001000000",
                "01030000000a",
                "0564001400",
                "f0000000000103f0000000",
                "7ab500000000",
            ])
            event = await self.honeypot.handle_connection(src_ip, dst_port, payload)
            if event:
                metrics.events_ingested.labels(domain="cyber", source="honeypot").inc()
                await kafka_client.send_event("cyber-events", event.model_dump(), key=f"cyber-{datetime.utcnow().timestamp()}")
