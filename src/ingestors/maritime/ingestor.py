import asyncio
import re
import time
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import httpx
import numpy as np
from geopy.distance import distance

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics, track_latency
from src.common.kafka import kafka_client
from src.common.models import (
    VesselTrack, VesselType, NavStatus, AISClass,
)

logger = setup_logging("maritime-ingestor")


class AISParser:
    NMEA_RE = re.compile(r"!AIVDM,[0-9],[0-9],[A-Z]?,([^,]*),[0-9]-\*[0-9A-F]{2}")

    def parse_nmea(self, sentence: str) -> Optional[dict]:
        try:
            match = self.NMEA_RE.match(sentence)
            if not match:
                return None
            payload = match.group(1)
            return self._decode_payload(payload)
        except Exception as e:
            logger.error("NMEA parse error", extra={"error": str(e)})
            return None

    def _decode_payload(self, payload: str) -> Optional[dict]:
        bits = ""
        for c in payload:
            val = ord(c) - 48
            if val > 40:
                val -= 8
            bits += f"{val:06b}"
        if len(bits) < 38:
            return None
        msg_type = int(bits[0:6], 2)
        if msg_type in (1, 2, 3):
            return self._decode_position_report(bits)
        elif msg_type == 5:
            return self._decode_static_voyage(bits)
        elif msg_type == 18:
            return self._decode_class_b_position(bits)
        return None

    def _decode_position_report(self, bits: str) -> dict:
        mmsi = int(bits[8:38], 2)
        nav_status = int(bits[38:42], 2)
        sog = int(bits[50:60], 2) / 10.0
        lon = int(bits[61:89], 2) if bits[61] == "0" else -((1 << 28) - int(bits[61:89], 2))
        lon = lon / 600000.0
        lat = int(bits[89:116], 2) if bits[89] == "0" else -((1 << 27) - int(bits[89:116], 2))
        lat = lat / 600000.0
        cog = int(bits[116:128], 2) / 10.0
        heading = int(bits[128:137], 2) if bits[128:137] != "511" else None
        return {
            "mmsi": str(mmsi).zfill(9),
            "nav_status": ["underway", "at_anchor", "moored", "aground", "restricted", "unknown"][nav_status] if nav_status <= 5 else "unknown",
            "sog_knots": sog if sog < 102.3 else 0,
            "lon": lon if -180 <= lon <= 180 else 0,
            "lat": lat if -90 <= lat <= 90 else 0,
            "cog_deg": cog if cog <= 360 else 0,
            "heading_deg": heading,
            "ais_class": "A",
        }

    def _decode_static_voyage(self, bits: str) -> dict:
        mmsi = int(bits[8:38], 2)
        imo = int(bits[40:70], 2) if len(bits) > 70 else None
        vessel_name = self._decode_ascii6(bits[70:166]) if len(bits) > 166 else ""
        vessel_type = int(bits[166:174], 2) if len(bits) > 174 else 0
        return {
            "mmsi": str(mmsi).zfill(9),
            "imo": str(imo) if imo and imo != 0 else None,
            "vessel_name": vessel_name.strip(),
            "vessel_type": self._map_vessel_type(vessel_type),
        }

    def _decode_class_b_position(self, bits: str) -> dict:
        mmsi = int(bits[8:38], 2)
        sog = int(bits[46:56], 2) / 10.0
        lon = int(bits[57:85], 2) if bits[57] == "0" else -((1 << 28) - int(bits[57:85], 2))
        lon = lon / 600000.0
        lat = int(bits[85:112], 2) if bits[85] == "0" else -((1 << 27) - int(bits[85:112], 2))
        lat = lat / 600000.0
        cog = int(bits[112:124], 2) / 10.0
        heading = int(bits[124:133], 2) if len(bits) > 133 and bits[124:133] != "511" else None
        return {
            "mmsi": str(mmsi).zfill(9),
            "sog_knots": sog if sog < 102.3 else 0,
            "lon": lon if -180 <= lon <= 180 else 0,
            "lat": lat if -90 <= lat <= 90 else 0,
            "cog_deg": cog if cog <= 360 else 0,
            "heading_deg": heading,
            "ais_class": "B",
        }

    @staticmethod
    def _decode_ascii6(bits: str) -> str:
        chars = []
        for i in range(0, len(bits) - 5, 6):
            val = int(bits[i:i+6], 2)
            if 1 <= val <= 31:
                chars.append("@")
            elif 32 <= val <= 63:
                chars.append(chr(val + 32))
            elif 64 <= val <= 95:
                chars.append(chr(val + 64))
            elif 96 <= val <= 127:
                chars.append(" ")
        return "".join(chars)

    @staticmethod
    def _encode_ais_payload(msg_type: int, mmsi: int, nav_status: int, sog: int, lon: int, lat: int, cog: int, heading: int) -> str:
        bits = f"{msg_type:06b}{0:02b}{mmsi:030b}{nav_status:04b}{0:08b}{0:08b}{sog:010b}{0:01b}{lon:028b}{lat:027b}{cog:012b}{heading:09b}{0:06b}"
        payload = ""
        for i in range(0, len(bits) - 5, 6):
            val = int(bits[i:i+6], 2)
            c = val + 48
            if c > 88:
                c += 8
            payload += chr(c)
        return payload

    @staticmethod
    def _map_vessel_type(code: int) -> str:
        mapping = {
            70: "cargo", 71: "cargo", 72: "cargo", 73: "cargo", 74: "cargo", 75: "cargo", 76: "cargo", 77: "cargo", 78: "cargo", 79: "cargo",
            80: "tanker", 81: "tanker", 82: "tanker", 83: "tanker", 84: "tanker", 85: "tanker", 86: "tanker", 87: "tanker", 88: "tanker", 89: "tanker",
            60: "passenger", 61: "passenger", 62: "passenger", 63: "passenger",
            30: "fishing", 31: "fishing", 32: "fishing",
            35: "military", 36: "military",
            37: "pleasure",
        }
        return mapping.get(code, "unknown")


class DarkVesselDetector:
    def __init__(self):
        self.active_vessels: Dict[str, datetime] = {}
        self.thresholds = {
            VesselType.cargo: 10,
            VesselType.tanker: 6,
            VesselType.passenger: 3,
            VesselType.military: 15,
            VesselType.fishing: 30,
            VesselType.pleasure: 60,
            VesselType.unknown: 30,
        }

    def check(self, vessel: VesselTrack) -> bool:
        now = datetime.utcnow()
        self.active_vessels[vessel.mmsi] = now
        last_seen = vessel.last_seen_utc
        gap = (now - last_seen).total_seconds() / 60.0
        threshold = self.thresholds.get(vessel.vessel_type, 30)
        if gap > threshold:
            return True
        return False

    def cleanup(self):
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=24)
        self.active_vessels = {k: v for k, v in self.active_vessels.items() if v > cutoff}


class AnomalousBehaviorDetector:
    def __init__(self):
        self.historical_speeds: Dict[str, List[float]] = {}
        self.recent_positions: Dict[str, List[dict]] = {}

    def check_speed_anomaly(self, vessel: VesselTrack, area: str) -> Optional[str]:
        key = f"{vessel.vessel_type.value}_{area}"
        if key not in self.historical_speeds:
            self.historical_speeds[key] = []
            return None
        speeds = self.historical_speeds[key]
        if len(speeds) < 5:
            return None
        mean_sog = np.mean(speeds)
        std_sog = np.std(speeds) + 0.1
        z_score = (vessel.sog_knots - mean_sog) / std_sog
        self.historical_speeds[key].append(vessel.sog_knots)
        if len(self.historical_speeds[key]) > 100:
            self.historical_speeds[key] = self.historical_speeds[key][-100:]
        if abs(z_score) > 3:
            return f"speed_anomaly: z={z_score:.1f}, speed={vessel.sog_knots:.1f}kts, mean={mean_sog:.1f}kts"
        return None

    def check_course_change(self, vessel: VesselTrack) -> Optional[str]:
        mmsi = vessel.mmsi
        if mmsi not in self.recent_positions:
            self.recent_positions[mmsi] = []
            return None
        self.recent_positions[mmsi].append({
            "time": datetime.utcnow(),
            "cog": vessel.cog_deg,
        })
        positions = [p for p in self.recent_positions[mmsi] if (datetime.utcnow() - p["time"]).total_seconds() < 300]
        self.recent_positions[mmsi] = positions
        if len(positions) >= 2:
            head_change = abs(positions[-1]["cog"] - positions[0]["cog"])
            if head_change > 180:
                head_change = 360 - head_change
            time_span = (positions[-1]["time"] - positions[0]["time"]).total_seconds() / 60.0
            if head_change > 45 and time_span < 5:
                return f"rapid_course_change: {head_change:.0f}deg in {time_span:.1f}min"
        return None

    def check_loitering(self, vessel: VesselTrack) -> Optional[str]:
        mmsi = vessel.mmsi
        if mmsi not in self.recent_positions:
            self.recent_positions[mmsi] = []
        self.recent_positions[mmsi].append({
            "time": datetime.utcnow(),
            "lat": vessel.lat,
            "lon": vessel.lon,
        })
        positions = [p for p in self.recent_positions[mmsi] if (datetime.utcnow() - p["time"]).total_seconds() < 7200]
        self.recent_positions[mmsi] = positions
        if len(positions) >= 4 and vessel.nav_status != NavStatus.at_anchor:
            start = positions[0]
            start_point = (start["lat"], start["lon"])
            current_point = (vessel.lat, vessel.lon)
            dist_nm = distance(start_point, current_point).nm
            time_span = (datetime.utcnow() - start["time"]).total_seconds() / 3600.0
            if dist_nm < 2 and time_span > 2:
                return f"loitering: {dist_nm:.1f}NM radius for {time_span:.1f}hrs"
        return None

    def check_speed_draught(self, vessel: VesselTrack) -> Optional[str]:
        if vessel.draught_m and vessel.draught_m > 10 and vessel.sog_knots > 15:
            return f"speed_draught_mismatch: draught={vessel.draught_m}m, speed={vessel.sog_knots}kts"
        return None


class PortArrivalPredictor:
    PORTS = [
        {"name": "Port of Singapore", "lat": 1.2789, "lon": 103.8390},
        {"name": "Port of Shanghai", "lat": 31.2304, "lon": 121.4737},
        {"name": "Port of Rotterdam", "lat": 51.9606, "lon": 4.0451},
        {"name": "Port of New York/New Jersey", "lat": 40.6413, "lon": -74.0445},
    ]

    def predict(self, vessel: VesselTrack) -> Optional[dict]:
        if not vessel.destination:
            return None
        port = next((p for p in self.PORTS if p["name"].lower().startswith(vessel.destination.lower()[:6])), None)
        if not port:
            return None
        dist_nm = distance((vessel.lat, vessel.lon), (port["lat"], port["lon"])).nm
        if vessel.sog_knots < 0.1 or dist_nm < 1:
            return {
                "predicted_arrival_utc": datetime.utcnow().isoformat(),
                "predicted_berth": port["name"],
                "confidence": 0.99,
            }
        hours_to_go = dist_nm / vessel.sog_knots
        return {
            "predicted_arrival_utc": (datetime.utcnow() + timedelta(hours=hours_to_go)).isoformat(),
            "predicted_berth": port["name"],
            "confidence": min(0.95, 0.5 + 0.4 * (1 - hours_to_go / 168)),
        }


class MaritimeDomainIngestor:
    def __init__(self):
        self.parser = AISParser()
        self.dark_vessel = DarkVesselDetector()
        self.anomaly = AnomalousBehaviorDetector()
        self.predictor = PortArrivalPredictor()
        self.running = False
        self.http_client: Optional[httpx.AsyncClient] = None
        self.active_vessels: Dict[str, VesselTrack] = {}

    async def start(self):
        self.running = True
        self.http_client = httpx.AsyncClient(timeout=30.0)
        await kafka_client.start()
        logger.info("Maritime Domain Ingestor started")
        tasks = [
            self.poll_ais_stream(),
            self.simulated_ais_generator(),
        ]
        await asyncio.gather(*tasks)

    async def stop(self):
        self.running = False
        if self.http_client:
            await self.http_client.aclose()
        await kafka_client.stop()

    @track_latency("maritime")
    async def poll_ais_stream(self):
        while self.running:
            await asyncio.sleep(10)
            try:
                nmea_samples = self._generate_nmea_samples(5)
                for sentence in nmea_samples:
                    parsed = self.parser.parse_nmea(sentence)
                    if parsed:
                        vessel = self._build_vessel(parsed)
                        await self._process_vessel(vessel)
            except Exception as e:
                metrics.errors_total.labels(service="maritime_ingestor", error_type="ais_poll").inc()
                logger.error("AIS poll error", extra={"error": str(e)})

    async def simulated_ais_generator(self):
        while self.running:
            await asyncio.sleep(2)
            vessel = self._create_simulated_vessel()
            await self._process_vessel(vessel)

    async def _process_vessel(self, vessel: VesselTrack):
        metrics.events_ingested.labels(domain="maritime", source="ais").inc()
        self.active_vessels[vessel.mmsi] = vessel
        vessel.dark_vessel_suspect = self.dark_vessel.check(vessel)
        anomaly_flags = []
        speed_anom = self.anomaly.check_speed_anomaly(vessel, "global")
        if speed_anom:
            anomaly_flags.append(speed_anom)
        course_anom = self.anomaly.check_course_change(vessel)
        if course_anom:
            anomaly_flags.append(course_anom)
        loiter = self.anomaly.check_loitering(vessel)
        if loiter:
            anomaly_flags.append(loiter)
        draught = self.anomaly.check_speed_draught(vessel)
        if draught:
            anomaly_flags.append(draught)
        vessel.anomaly_flags = anomaly_flags
        vessel.ais_gap_minutes = 0.0

        await kafka_client.send_event("maritime-positions", vessel.model_dump(), key=vessel.mmsi)

    def _build_vessel(self, parsed: dict) -> VesselTrack:
        mmsi = parsed.get("mmsi", "000000000")
        existing = self.active_vessels.get(mmsi)
        return VesselTrack(
            mmsi=mmsi,
            imo=parsed.get("imo", getattr(existing, "imo", None)),
            vessel_name=parsed.get("vessel_name", getattr(existing, "vessel_name", "")),
            vessel_type=VesselType(parsed.get("vessel_type", "unknown")) if parsed.get("vessel_type", "unknown") in [t.value for t in VesselType] else VesselType.unknown,
            flag_state=getattr(existing, "flag_state", ""),
            lat=parsed.get("lat", 0.0),
            lon=parsed.get("lon", 0.0),
            sog_knots=parsed.get("sog_knots", 0.0),
            cog_deg=parsed.get("cog_deg", 0.0),
            heading_deg=parsed.get("heading_deg"),
            nav_status=NavStatus(parsed.get("nav_status", "unknown")) if parsed.get("nav_status", "unknown") in [s.value for s in NavStatus] else NavStatus.unknown,
            ais_class=AISClass(parsed.get("ais_class", "A")),
        )

    def _create_simulated_vessel(self) -> VesselTrack:
        mmsi = f"{random.randint(100000000, 999999999)}"
        vessel_type = random.choice(list(VesselType))
        return VesselTrack(
            mmsi=mmsi,
            imo=f"IMO{random.randint(9000000, 9999999)}" if random.random() > 0.5 else None,
            vessel_name=f"MV {random.choice(['SENTINEL', 'ODYSSEY', 'HORIZON', 'ARCTIC', 'PACIFIC'])}-{random.randint(1, 99)}",
            vessel_type=vessel_type,
            flag_state=random.choice(["USA", "PAN", "LBR", "MHL", "SGP", "HKG"]),
            lat=random.uniform(-60, 60),
            lon=random.uniform(-180, 180),
            sog_knots=random.uniform(0, 25),
            cog_deg=random.uniform(0, 360),
            heading_deg=random.uniform(0, 360) if random.random() > 0.2 else None,
            nav_status=random.choice(list(NavStatus)),
            destination=random.choice(["Singapore", "Shanghai", "Rotterdam", "New York", None]),
            draught_m=random.uniform(3, 18) if random.random() > 0.3 else None,
            cargo_hazmat_class=random.choice(["1", "2.1", "3", "4.1", None, None]),
            ais_class=random.choice(["A", "B"]),
        )

    def _generate_nmea_samples(self, count: int) -> list:
        samples = []
        for _ in range(count):
            mmsi = random.randint(200000000, 999999999)
            lat = random.uniform(-60, 60)
            lon = random.uniform(-180, 180)
            sog = random.randint(0, 300)
            cog = random.randint(0, 3600)
            heading = random.randint(0, 511)
            nav_status = random.randint(0, 7)
            lat_min = int(abs(lat) * 60000)
            lon_min = int(abs(lon) * 60000)
            lat_enc = lat_min + (0 if lat >= 0 else (1 << 27))
            lon_enc = lon_min + (0 if lon >= 0 else (1 << 28))
            payload = AISParser._encode_ais_payload(1, mmsi, nav_status, sog, lon_enc, lat_enc, cog, heading)
            samples.append(payload)
        return samples




class MarineTrafficAPIAdapter:
    def __init__(self):
        self.base_url = "https://marine-traffic-api.example.com"

    async def fetch_vessel(self, mmsi: str) -> Optional[dict]:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/vessels/{mmsi}",
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass
            return None
