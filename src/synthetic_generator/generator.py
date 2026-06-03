import asyncio
import math
import random
import uuid
import time
from datetime import datetime
from typing import Optional

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.kafka import kafka_client
from src.common.metrics import _metrics as metrics

logger = setup_logging("synthetic-generator")

AIRLINES = ["UAL", "AAL", "DAL", "SWA", "BAW", "AFR", "KLM", "CPA", "SIA", "JAL"]
COUNTRIES = ["US", "UK", "DE", "FR", "JP", "SG", "AE", "BR", "IN", "AU"]
VESSEL_NAMES = ["SENTINEL", "ODYSSEY", "HORIZON", "ARCTIC", "PACIFIC", "GUARDIAN", "WATCHER"]
VESSEL_TYPES = ["cargo", "tanker", "passenger", "military", "fishing", "pleasure"]
NAV_STATUSES = ["underway", "at_anchor", "moored", "unknown"]
SECTORS = ["power_grid", "water", "transportation", "finance", "government", "healthcare"]

GLOBAL_HUBS = [
    (-6.2, 106.8, "ID"), (1.3, 103.8, "SG"), (13.8, 100.5, "TH"), (21.0, 105.8, "VN"),
    (14.6, 121.0, "PH"), (5.5, 100.4, "MY"), (3.1, 101.7, "MY"), (22.3, 114.2, "HK"),
    (25.0, 121.5, "TW"), (31.2, 121.5, "CN"), (35.7, 139.7, "JP"), (37.6, 127.0, "KR"),
    (40.7, -74.0, "US"), (34.1, -118.2, "US"), (25.8, -80.3, "US"), (33.9, -84.4, "US"),
    (41.9, -87.6, "US"), (51.5, -0.1, "UK"), (48.9, 2.3, "FR"), (52.5, 13.4, "DE"),
    (55.8, 37.6, "RU"), (28.6, 77.2, "IN"), (19.4, -99.1, "MX"), (-23.6, -46.6, "BR"),
    (-33.9, 151.2, "AU"), (-26.1, 28.2, "ZA"), (30.0, 31.2, "EG"), (25.2, 55.3, "AE"),
    (1.5, 104.0, "MY"), (3.0, 98.7, "ID"), (-8.5, 115.2, "ID"), (-5.1, 119.4, "ID"),
]
BASE_LAT, BASE_LON, _ = GLOBAL_HUBS[0]


class SyntheticGenerator:
    def __init__(self):
        self.running = False
        self.icao24_pool = [f"{random.randint(0, 0xFFFFFF):06x}" for _ in range(50)]
        self.mmsi_pool = [f"{random.randint(100000000, 999999999)}" for _ in range(30)]
        self.air_positions = {}
        self.maritime_positions = {}

    async def start(self):
        self.running = True
        await kafka_client.start()
        logger.info("Synthetic data generator started")

        tasks = [
            self.generate_air_tracks(),
            self.generate_maritime_positions(),
            self.generate_rf_anomalies(),
            self.generate_cyber_events(),
            self.generate_seismic_events(),
            self.generate_missile_tracks(),
            self.generate_compound_trigger_bursts(),
        ]
        await asyncio.gather(*tasks)

    async def stop(self):
        self.running = False
        await kafka_client.stop()

    async def generate_air_tracks(self):
        while self.running:
            icao = random.choice(self.icao24_pool)
            if icao not in self.air_positions:
                hub = random.choice(GLOBAL_HUBS)
                self.air_positions[icao] = {
                    "lat": hub[0] + random.uniform(-5, 5),
                    "lon": hub[1] + random.uniform(-5, 5),
                    "alt": random.uniform(3000, 12000),
                    "vx": random.uniform(100, 280),
                    "heading": random.uniform(0, 360),
                }
            pos = self.air_positions[icao]
            pos["lat"] += random.uniform(-0.05, 0.05)
            pos["lon"] += random.uniform(-0.05, 0.05)
            pos["alt"] += random.uniform(-50, 50)
            pos["alt"] = max(0, min(15000, pos["alt"]))

            is_unidentified = random.random() < 0.1
            track = {
                "track_id": str(uuid.uuid4()),
                "domain": "air",
                "icao24": icao,
                "callsign": f"{random.choice(AIRLINES)}{random.randint(100,999)}" if not is_unidentified else None,
                "origin_country": random.choice(COUNTRIES),
                "timestamp_utc": datetime.utcnow().isoformat(),
                "lat": pos["lat"],
                "lon": pos["lon"],
                "baro_altitude_m": pos["alt"],
                "geo_altitude_m": pos["alt"] + random.uniform(-50, 50),
                "velocity_ms": pos["vx"],
                "true_track_deg": pos["heading"],
                "vertical_rate_ms": random.uniform(-5, 5),
                "on_ground": False,
                "source": "simulated",
                "classification": "unidentified" if is_unidentified else random.choice(["commercial", "military", "private"]),
                "threat_flags": [],
                "anomaly_flags": [],
            }
            if is_unidentified:
                self._maybe_add_threat_flag(track, ["squawk_unknown", "no_flight_plan", "erratic_pattern"])

            await kafka_client.send_event("air-tracks", track, key=icao)
            metrics.events_ingested.labels(domain="air", source="synthetic").inc()
            await asyncio.sleep(random.uniform(0.05, 0.3))

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    @staticmethod
    def _great_circle_interp(lat1, lon1, lat2, lon2, f):
        if f <= 0: return lat1, lon1
        if f >= 1: return lat2, lon2
        r1, r2 = map(math.radians, [lat1, lat2])
        dl = math.radians(lon2 - lon1)
        d = math.acos(min(1, max(-1, math.sin(r1)*math.sin(r2) + math.cos(r1)*math.cos(r2)*math.cos(dl))))
        if d < 1e-10: return lat1, lon1
        a, b = math.sin((1-f)*d)/math.sin(d), math.sin(f*d)/math.sin(d)
        x = a*math.cos(r1)*math.cos(math.radians(lon1)) + b*math.cos(r2)*math.cos(math.radians(lon2))
        y = a*math.cos(r1)*math.sin(math.radians(lon1)) + b*math.cos(r2)*math.sin(math.radians(lon2))
        z = a*math.sin(r1) + b*math.sin(r2)
        return math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))

    # Global strategic military bases (both launch sites and targets)
    STRATEGIC_BASES = [
        # Americas
        ("US-MALMSTROM", 47.5, -111.0, "US"), ("US-MINOT", 48.4, -101.3, "US"),
        ("US-WARREN", 41.1, -104.9, "US"), ("US-VANDENBERG", 34.7, -120.6, "US"),
        ("US-CANAVERAL", 28.4, -80.6, "US"), ("US-NORFOLK", 36.9, -76.3, "US"),
        ("US-SANDIEGO", 32.7, -117.2, "US"), ("US-PEARL", 21.3, -157.9, "US"),
        ("US-KITSAP", 47.6, -122.7, "US"), ("US-KINGSBAY", 30.8, -81.5, "US"),
        # Russia
        ("RU-PLESETSK", 62.9, 40.7, "RU"), ("RU-DOMBAROVSKY", 51.1, 59.8, "RU"),
        ("RU-KAPUSTINYAR", 48.5, 45.8, "RU"), ("RU-MURMANSK", 69.0, 33.1, "RU"),
        ("RU-SEVEROMORSK", 69.1, 33.4, "RU"), ("RU-KALININGRAD", 54.7, 20.5, "RU"),
        ("RU-SEVASTOPOL", 44.6, 33.5, "RU"), ("RU-VLADIVOSTOK", 43.1, 131.9, "RU"),
        ("RU-PETROPAVLOVSK", 53.0, 158.7, "RU"), ("RU-KHABAROVSK", 48.5, 135.1, "RU"),
        # North Korea
        ("KP-SOHAE", 39.7, 124.7, "KP"), ("KP-MUSUDAN", 40.9, 129.7, "KP"),
        ("KP-WONSAN", 39.2, 127.4, "KP"), ("KP-SINPO", 40.1, 128.3, "KP"),
        # China
        ("CN-JIUQUAN", 40.9, 100.3, "CN"), ("CN-TAIYUAN", 38.8, 111.6, "CN"),
        ("CN-XICHANG", 28.3, 102.0, "CN"), ("CN-HAINAN", 19.1, 108.6, "CN"),
        ("CN-QINGDAO", 36.1, 120.4, "CN"), ("CN-ZHANJIANG", 21.2, 110.4, "CN"),
        ("CN-SHANGHAI", 31.2, 121.5, "CN"), ("CN-DALIAN", 38.9, 121.6, "CN"),
        ("CN-SANYA", 18.2, 109.5, "CN"),
        # Iran
        ("IR-SHAHRUD", 36.4, 55.0, "IR"), ("IR-ISFAHAN", 32.7, 51.7, "IR"),
        ("IR-BANDARABBAS", 27.2, 56.3, "IR"), ("IR-BUSHEHR", 29.0, 50.8, "IR"),
        ("IR-TEHRAN", 35.7, 51.4, "IR"),
        # India
        ("IN-WHEELER", 20.8, 87.1, "IN"), ("IN-SRIHARIKOTA", 13.7, 80.2, "IN"),
        ("IN-MUMBAI", 18.9, 72.8, "IN"), ("IN-VISAKHAPATNAM", 17.7, 83.3, "IN"),
        ("IN-KARWAR", 14.8, 74.1, "IN"), ("IN-PORTBLAIR", 11.7, 92.8, "IN"),
        # Pakistan
        ("PK-TILLA", 33.5, 72.8, "PK"), ("PK-SONMIANI", 25.1, 66.8, "PK"),
        ("PK-SARGODHA", 32.0, 72.7, "PK"), ("PK-KARACHI", 24.9, 67.0, "PK"),
        ("PK-GWADAR", 25.1, 62.3, "PK"),
        # Israel
        ("IL-PALMACHIM", 31.9, 34.7, "IL"), ("IL-HAIFA", 32.8, 35.0, "IL"),
        ("IL-EILAT", 29.6, 35.0, "IL"),
        # Middle East
        ("AE-ALDHARA", 24.3, 54.5, "AE"), ("YE-ADEN", 12.8, 45.0, "YE"),
        ("SY-TARTUS", 34.9, 35.9, "SY"), ("IQ-BAGHDAD", 33.3, 44.4, "IQ"),
        ("TR-INCRLIK", 37.0, 35.4, "TR"),
        # Europe
        ("UK-FASLANE", 56.1, -4.8, "UK"), ("UK-PORTSMOUTH", 50.8, -1.1, "UK"),
        ("FR-TOULON", 43.1, 5.9, "FR"), ("FR-BREST", 48.4, -4.5, "FR"),
        ("DE-RAMSTEIN", 49.4, 7.6, "DE"), ("IT-AVIANO", 46.0, 12.6, "IT"),
        ("IT-SIGONELLA", 37.4, 14.9, "IT"), ("GR-SOUDA", 35.5, 24.2, "GR"),
        ("ES-ROTA", 36.6, -6.3, "ES"),
        # East Asia / Oceania
        ("KR-JINHAE", 35.2, 128.7, "KR"), ("KR-JEJU", 33.5, 126.5, "KR"),
        ("JP-YOKOTA", 35.7, 139.3, "JP"), ("JP-KADENA", 26.4, 127.8, "JP"),
        ("JP-MISAWA", 40.7, 141.4, "JP"), ("JP-SASEBO", 33.2, 129.7, "JP"),
        ("JP-YOKOSUKA", 35.3, 139.7, "JP"), ("GU-ANDERSEN", 13.6, 144.9, "GU"),
        ("AU-DARWIN", -12.4, 130.9, "AU"), ("AU-PERTH", -31.9, 115.8, "AU"),
        ("AU-SYDNEY", -33.9, 151.2, "AU"),
        # Southeast Asia
        ("SG-CHANGI", 1.3, 104.0, "SG"), ("MY-BUTTERWORTH", 5.5, 100.4, "MY"),
        ("MY-LUMUT", 4.2, 100.6, "MY"), ("TH-SATTAHIP", 12.6, 100.9, "TH"),
        ("VN-CAMRANH", 12.0, 109.2, "VN"), ("VN-HAIPHONG", 20.9, 106.7, "VN"),
        ("PH-SUBIC", 14.8, 120.3, "PH"), ("ID-SURABAYA", -7.2, 112.7, "ID"),
        ("ID-JAKARTA", -6.3, 106.8, "ID"), ("ID-MAKASSAR", -5.1, 119.4, "ID"),
        ("ID-SABANG", 5.9, 95.3, "ID"), ("ID-BITUNG", 1.4, 125.2, "ID"),
        ("ID-AMBON", -3.7, 128.2, "ID"), ("ID-MERAUKE", -8.5, 140.4, "ID"),
        # Africa
        ("EG-ALEXANDRIA", 31.2, 29.9, "EG"), ("EG-CAIRO", 30.0, 31.2, "EG"),
        ("ZA-PRETORIA", -25.7, 28.2, "ZA"), ("ZA-SIMONSTOWN", -34.2, 18.4, "ZA"),
        ("DJ-DJIBOUTI", 11.6, 43.2, "DJ"), ("KE-MOMBASA", -4.1, 39.7, "KE"),
        ("NG-LAGOS", 6.5, 3.4, "NG"),
        # Americas (non-US)
        ("CU-HAVANA", 23.1, -82.4, "CU"), ("VE-PUERTOCABELLO", 10.5, -68.0, "VE"),
        ("BR-RIO", -22.9, -43.2, "BR"), ("AR-BUENOSAIRES", -34.6, -58.4, "AR"),
        ("CL-VALPARAISO", -33.0, -71.6, "CL"),
    ]

    STRATEGIC_CITIES = [
        ("NEW YORK", 40.7, -74.0, "US"), ("WASHINGTON DC", 38.9, -77.0, "US"),
        ("MOSCOW", 55.8, 37.6, "RU"), ("LONDON", 51.5, -0.1, "UK"),
        ("PARIS", 48.9, 2.3, "FR"), ("BERLIN", 52.5, 13.4, "DE"),
        ("BEIJING", 39.9, 116.4, "CN"), ("TOKYO", 35.7, 139.7, "JP"),
        ("DELHI", 28.6, 77.2, "IN"), ("PYONGYANG", 39.0, 125.7, "KP"),
        ("SEOUL", 37.6, 127.0, "KR"), ("TEHRAN", 35.7, 51.4, "IR"),
        ("TEL AVIV", 32.1, 34.8, "IL"), ("CANBERRA", -35.3, 149.1, "AU"),
        ("JAKARTA", -6.2, 106.8, "ID"), ("MANILA", 14.6, 121.0, "PH"),
        ("BANGKOK", 13.8, 100.5, "TH"), ("HANOI", 21.0, 105.8, "VN"),
        ("ISLAMABAD", 33.7, 73.1, "PK"), ("KABUL", 34.5, 69.2, "AF"),
        ("BAGHDAD", 33.3, 44.4, "IQ"), ("CAIRO", 30.0, 31.2, "EG"),
        ("ADDIS ABABA", 9.0, 38.7, "ET"), ("NAIROBI", -1.3, 36.8, "KE"),
        ("BRASILIA", -15.8, -47.9, "BR"), ("SANTIAGO", -33.5, -70.7, "CL"),
        ("LIMA", -12.0, -77.0, "PE"), ("MEXICO CITY", 19.4, -99.1, "MX"),
        ("SINGAPORE", 1.3, 103.8, "SG"),
    ]

    # Pre-compute all strategic points as targets
    _ALL_TARGETS = STRATEGIC_BASES + STRATEGIC_CITIES

    async def generate_missile_tracks(self):
        MISSILE_TYPES = [
            {"type": "SRBM", "speed_mach": (3, 5), "max_range_km": 500, "accuracy_m": (50, 200), "peak_alt_km": 80},
            {"type": "MRBM", "speed_mach": (5, 8), "max_range_km": 1500, "accuracy_m": (100, 500), "peak_alt_km": 200},
            {"type": "IRBM", "speed_mach": (8, 12), "max_range_km": 4000, "accuracy_m": (150, 600), "peak_alt_km": 600},
            {"type": "ICBM", "speed_mach": (15, 22), "max_range_km": 14000, "accuracy_m": (200, 800), "peak_alt_km": 1200},
            {"type": "Cruise", "speed_mach": (0.7, 0.9), "max_range_km": 1000, "accuracy_m": (5, 30), "peak_alt_km": 0.1},
            {"type": "Hypersonic", "speed_mach": (5, 12), "max_range_km": 2000, "accuracy_m": (10, 50), "peak_alt_km": 50},
            {"type": "Anti-Ship", "speed_mach": (0.8, 2.5), "max_range_km": 300, "accuracy_m": (3, 15), "peak_alt_km": 5},
        ]
        bases = [(b[0], {"name": b[0], "lat": b[1], "lon": b[2], "country": b[3]}) for b in self.STRATEGIC_BASES]
        target_dicts = [{"name": t[0], "lat": t[1], "lon": t[2], "country": t[3]} for t in self._ALL_TARGETS]
        missile_states = {}

        while self.running:
            if random.random() < 0.15 or len(missile_states) < 2:
                name1, launcher = random.choice(bases)
                mtype = random.choice(MISSILE_TYPES)
                valid = [t for t in target_dicts if t["name"] != name1 and self._haversine(
                    launcher["lat"], launcher["lon"], t["lat"], t["lon"]) <= mtype["max_range_km"] * 1.2]
                if not valid:
                    continue
                target = random.choice(valid)
                mid = f"MSSL-{uuid.uuid4().hex[:8].upper()}"
                speed_mach = random.uniform(*mtype["speed_mach"])
                speed_ms = speed_mach * 343
                dist_km = self._haversine(launcher["lat"], launcher["lon"], target["lat"], target["lon"])
                flight_time_s = max(dist_km * 1000 / speed_ms, 0.1) # Prevent division by zero
                start_time = time.time()
                missile_states[mid] = {
                    "id": mid, "launcher": launcher, "target": target,
                    "mtype": mtype, "speed_mach": speed_mach, "speed_ms": speed_ms,
                    "distance_km": dist_km, "flight_time_s": flight_time_s,
                    "start_time": start_time, "progress": 0.0, "is_threat": True,
                }

            dead_missiles = []
            for mid, state in missile_states.items():
                elapsed = time.time() - state["start_time"]
                state["progress"] = min(elapsed / state["flight_time_s"], 1.0)
                progress = state["progress"]
                launcher, target = state["launcher"], state["target"]

                lat, lon = self._great_circle_interp(launcher["lat"], launcher["lon"], target["lat"], target["lon"], progress)
                peak_m = state["mtype"]["peak_alt_km"] * 1000
                alt = peak_m * math.sin(progress * math.pi)
                heading = math.degrees(math.atan2(
                    math.sin(math.radians(target["lon"] - launcher["lon"])) * math.cos(math.radians(target["lat"])),
                    math.cos(math.radians(launcher["lat"])) * math.sin(math.radians(target["lat"])) -
                    math.sin(math.radians(launcher["lat"])) * math.cos(math.radians(target["lat"])) *
                    math.cos(math.radians(target["lon"] - launcher["lon"]))
                )) % 360

                track = {
                    "track_id": mid, "domain": "air", "callsign": mid,
                    "origin_country": launcher["country"],
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "lat": lat, "lon": lon, "baro_altitude_m": alt,
                    "geo_altitude_m": alt + random.uniform(-100, 100),
                    "velocity_ms": state["speed_ms"], "true_track_deg": heading,
                    "vertical_rate_ms": random.uniform(-100, 100),
                    "on_ground": False, "source": "synthetic", "classification": "military",
                    "is_missile": True, "missile_type": state["mtype"]["type"],
                    "threat_status": random.choice(["PREDICTED", "CONFIRMED"]),
                    "missile_id": mid, "origin_lat": launcher["lat"],
                    "origin_lon": launcher["lon"], "origin_name": launcher["name"],
                    "target_lat": target["lat"], "target_lon": target["lon"],
                    "target_name": target["name"],
                    "speed_mach": round(state["speed_mach"], 1),
                    "accuracy_cep_m": random.uniform(*state["mtype"]["accuracy_m"]),
                    "launch_time": datetime.utcfromtimestamp(state["start_time"]).isoformat(),
                    "eta_seconds": round(state["flight_time_s"] * (1 - progress)),
                    "distance_km": round(state["distance_km"], 1),
                    "flight_progress_pct": round(progress * 100, 1),
                    "threat_flags": ["missile_launch_detected", "ballistic_trajectory"],
                    "anomaly_flags": [],
                }
                await kafka_client.send_event("air-tracks", track, key=mid)
                metrics.events_ingested.labels(domain="air", source="synthetic").inc()

                if progress >= 1.0:
                    dead_missiles.append(mid)
                    alert = {
                        "alert_id": str(uuid.uuid4()),
                        "timestamp_utc": datetime.utcnow().isoformat(),
                        "threat_class": "CRITICAL", "confidence": 0.95, "domain": "air",
                        "description": f"Missile impact: {mid} ({state['mtype']['type']}) from {launcher['name']} ({launcher['country']}) struck {target['name']} ({target['country']}). Dist: {dist_km:.0f}km, Speed: {state['speed_mach']} Mach",
                        "source": "synthetic_missile",
                        "ipfs_hash": f"Qm{abs(hash(mid))}{uuid.uuid4().hex[:16]}",
                    }
                    await kafka_client.send_event("alerts", alert, key=alert["alert_id"])
                    metrics.events_ingested.labels(domain="alerts", source="synthetic").inc()

            for mid in dead_missiles:
                del missile_states[mid]
            await asyncio.sleep(random.uniform(0.2, 0.5))

    async def generate_maritime_positions(self):
        while self.running:
            mmsi = random.choice(self.mmsi_pool)
            if mmsi not in self.maritime_positions:
                self.maritime_positions[mmsi] = {
                    "lat": random.uniform(-60, 60),
                    "lon": random.uniform(-180, 180),
                }
            pos = self.maritime_positions[mmsi]
            pos["lat"] += random.uniform(-0.1, 0.1)
            pos["lon"] += random.uniform(-0.1, 0.1)

            is_dark = random.random() < 0.08
            is_loitering = random.random() < 0.05
            sog = random.uniform(0, 25) if not is_loitering else random.uniform(0, 1)

            vessel = {
                "mmsi": mmsi,
                "domain": "maritime",
                "vessel_name": f"MV {random.choice(VESSEL_NAMES)}-{random.randint(1, 99)}",
                "vessel_type": random.choice(VESSEL_TYPES),
                "flag_state": random.choice(["USA", "PAN", "LBR", "MHL", "SGP", "HKG"]),
                "timestamp_utc": datetime.utcnow().isoformat(),
                "lat": pos["lat"],
                "lon": pos["lon"],
                "sog_knots": sog,
                "cog_deg": random.uniform(0, 360),
                "heading_deg": random.uniform(0, 360),
                "nav_status": random.choice(NAV_STATUSES),
                "destination": random.choice(["Singapore", "Shanghai", "Rotterdam", "New York", None]),
                "dark_vessel_suspect": is_dark,
                "anomaly_flags": [],
                "threat_flags": [],
            }
            if is_loitering:
                vessel["anomaly_flags"].append("loitering")
            if is_dark:
                vessel["anomaly_flags"].append("dark_vessel_suspect")
            if random.random() < 0.05:
                vessel["anomaly_flags"].append("course_change")

            await kafka_client.send_event("maritime-positions", vessel, key=mmsi)
            metrics.events_ingested.labels(domain="maritime", source="synthetic").inc()
            await asyncio.sleep(random.uniform(0.1, 0.5))

    async def generate_rf_anomalies(self):
        while self.running:
            anomaly_types = ["gps_jamming", "gps_spoofing", "radar_anomaly", "comms_interference", "unknown"]
            atype = random.choice(anomaly_types)

            rf_event = {
                "event_id": str(uuid.uuid4()),
                "domain": "rf",
                "timestamp_utc": datetime.utcnow().isoformat(),
                "type": atype,
                "anomaly_type": atype,
                "freq_mhz": random.choice([1575.42, 1227.6, 162.0, 406.0, 1090.0, 243.0]),
                "bandwidth_hz": random.uniform(1000, 5000000),
                "signal_strength_dbm": random.uniform(-120, -30),
                "confidence": random.uniform(0.5, 0.99),
                "protocol_guess": random.choice(["DJI", "unknown", None]),
                "estimated_lat": random.uniform(-90, 90),
                "estimated_lon": random.uniform(-180, 180),
            }

            await kafka_client.send_event("rf-signals", rf_event, key=f"rf-{time.time_ns()}")
            metrics.events_ingested.labels(domain="rf", source="synthetic").inc()
            await asyncio.sleep(random.uniform(0.2, 0.8))

    async def generate_cyber_events(self):
        while self.running:
            techniques = ["port_scan", "sql_injection", "phishing", "ddos", "comms_blackout", "malware", "ransomware"]
            technique = random.choice(techniques)

            cyber_event = {
                "event_id": str(uuid.uuid4()),
                "domain": "cyber",
                "timestamp_utc": datetime.utcnow().isoformat(),
                "type": technique,
                "technique": technique,
                "src_ip": f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 255)}",
                "src_port": random.randint(1024, 65535),
                "dst_port": random.choice([22, 80, 443, 3389, 8080, 8443]),
                "protocol": random.choice(["TCP", "UDP", "HTTP", "HTTPS", "MQTT"]),
                "target_sector": random.choice(SECTORS) if random.random() < 0.3 else None,
                "severity": random.choice(["INFORMATIONAL", "SUSPICIOUS", "ELEVATED", "CRITICAL"]),
                "source_feed": "synthetic",
            }

            await kafka_client.send_event("cyber-events", cyber_event, key=f"cyber-{time.time_ns()}")
            metrics.events_ingested.labels(domain="cyber", source="synthetic").inc()
            await asyncio.sleep(random.uniform(0.3, 1.0))

    async def generate_seismic_events(self):
        while self.running:
            mag = random.choices(
                [random.uniform(2.0, 4.5), random.uniform(4.5, 6.5), random.uniform(6.5, 8.5)],
                weights=[70, 25, 5],
            )[0]

            event = {
                "event_id": str(uuid.uuid4()),
                "domain": "seismic",
                "timestamp_utc": datetime.utcnow().isoformat(),
                "lat": random.uniform(-90, 90),
                "lon": random.uniform(-180, 180),
                "depth_km": random.uniform(1, 100),
                "magnitude": mag,
                "magnitude_type": "ml",
                "location_description": f"Region {random.randint(1, 100)}",
                "tsunami_warning": mag > 7.0 and random.random() < 0.3,
            }

            await kafka_client.send_event("seismic-events", event, key=f"seismic-{time.time_ns()}")
            metrics.events_ingested.labels(domain="seismic", source="synthetic").inc()
            await asyncio.sleep(random.uniform(1.0, 3.0))

    async def generate_compound_trigger_bursts(self):
        while self.running:
            await asyncio.sleep(random.uniform(15, 30))
            logger.info("Emitting compound pattern trigger burst")
            # Generate periodic alerts for all domains
            for domain_name, threat_class, confidence, desc in [
                ("air", "SUSPICIOUS", 0.65, f"Unidentified aerial contact — {random.choice(GLOBAL_HUBS)} sector — no flight plan, squawk unknown"),
                ("maritime", "ELEVATED", 0.78, f"Dark vessel loitering near strategic waterway — AIS transponder off, suspected spoofing"),
                ("cyber", "CRITICAL", 0.92, f"Coordinated cyber intrusion detected — multiple IOC indicators across {random.randint(2,5)} kill chain phases"),
                ("rf", "ELEVATED", 0.81, f"Anomalous RF emission in {random.choice(['L','S','C','X','Ku'])}-band — geolocated to {random.choice(GLOBAL_HUBS)} elevation {random.randint(1,15)}°"),
                ("seismic", "INFORMATIONAL", 0.45, f"Seismic event M{random.uniform(3,7):.1f} — depth {random.randint(5,60)}km — monitoring for aftershock sequence"),
            ]:
                alert_item = {
                    "alert_id": str(uuid.uuid4()),
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "threat_class": threat_class,
                    "confidence": confidence,
                    "domain": domain_name,
                    "description": desc,
                    "source": "synthetic_automated",
                    "ipfs_hash": f"Qm{abs(hash(f'{domain_name}{time.time_ns()}'))}{uuid.uuid4().hex[:16]}",
                }
                await kafka_client.send_event("alerts", alert_item, key=alert_item["alert_id"])
                metrics.events_ingested.labels(domain="alerts", source="synthetic").inc()
            await asyncio.sleep(0.2)

            for _ in range(5):
                hub = random.choice(GLOBAL_HUBS)
                burst_track = {
                    "track_id": str(uuid.uuid4()),
                    "domain": "air",
                    "icao24": f"{random.randint(0, 0xFFFFFF):06x}",
                    "callsign": None,
                    "origin_country": "Unknown",
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "lat": hub[0] + random.uniform(-1, 1),
                    "lon": hub[1] + random.uniform(-1, 1),
                    "baro_altitude_m": random.uniform(5000, 12000),
                    "geo_altitude_m": random.uniform(5000, 12000),
                    "velocity_ms": random.uniform(200, 280),
                    "true_track_deg": random.uniform(0, 360),
                    "vertical_rate_ms": random.uniform(-5, 5),
                    "on_ground": False,
                    "source": "simulated",
                    "classification": "unidentified",
                    "threat_flags": ["squawk_unknown", "no_flight_plan"],
                    "anomaly_flags": [],
                }
                await kafka_client.send_event("air-tracks", burst_track, key=burst_track["icao24"])
                await asyncio.sleep(0.1)

            for _ in range(3):
                burst_vessel = {
                    "mmsi": f"{random.randint(100000000, 999999999)}",
                    "domain": "maritime",
                    "vessel_name": f"MV UNKNOWN-{random.randint(1, 99)}",
                    "vessel_type": "unknown",
                    "flag_state": "XX",
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "lat": random.uniform(-60, 60),
                    "lon": random.uniform(-180, 180),
                    "sog_knots": random.uniform(0, 2),
                    "cog_deg": 0,
                    "heading_deg": 0,
                    "nav_status": "underway",
                    "destination": None,
                    "dark_vessel_suspect": True,
                    "anomaly_flags": ["dark_vessel_suspect", "loitering"],
                    "threat_flags": ["dark_vessel_suspect", "loitering"],
                }
                await kafka_client.send_event("maritime-positions", burst_vessel, key=burst_vessel["mmsi"])
                await asyncio.sleep(0.1)

            burst_rf = {
                "event_id": str(uuid.uuid4()),
                "domain": "rf",
                "timestamp_utc": datetime.utcnow().isoformat(),
                "type": "gps_jamming",
                "anomaly_type": "gps_jamming",
                "freq_mhz": 1575.42,
                "bandwidth_hz": 2000000,
                "signal_strength_dbm": -50,
                "confidence": 0.95,
                "protocol_guess": "unknown",
                "estimated_lat": BASE_LAT,
                "estimated_lon": BASE_LON,
            }
            await kafka_client.send_event("rf-signals", burst_rf, key=f"rf-burst-{time.time_ns()}")
            await asyncio.sleep(0.1)

            burst_cyber = {
                "event_id": str(uuid.uuid4()),
                "domain": "cyber",
                "timestamp_utc": datetime.utcnow().isoformat(),
                "type": "comms_blackout",
                "technique": "comms_blackout",
                "src_ip": f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 255)}",
                "src_port": random.randint(1024, 65535),
                "dst_port": 443,
                "protocol": "TCP",
                "target_sector": "power_grid",
                "severity": "CRITICAL",
                "source_feed": "synthetic",
            }
            await kafka_client.send_event("cyber-events", burst_cyber, key=f"cyber-burst-{time.time_ns()}")

    def _maybe_add_threat_flag(self, track: dict, flags: list):
        for f in flags:
            if random.random() < 0.3:
                track["threat_flags"].append(f)


if __name__ == "__main__":
    gen = SyntheticGenerator()
    asyncio.run(gen.start())
