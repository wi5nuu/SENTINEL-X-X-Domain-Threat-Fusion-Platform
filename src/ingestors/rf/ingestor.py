import asyncio
import random
import time
from datetime import datetime
from typing import Optional, List, Tuple
import numpy as np

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics, track_latency
from src.common.kafka import kafka_client
from src.common.models import RFAnomaly

logger = setup_logging("rf-ingestor")


class SimulatedRFEnvironment:
    def __init__(self):
        self.background_noise = -120
        self.active_jammers = {}
        self.active_spoofers = {}

    def generate_gps_jamming_scenario(self, center_lat: float = 40.7128, center_lon: float = -74.0060):
        jammer_id = f"jammer-{time.time_ns()}"
        self.active_jammers[jammer_id] = {
            "lat": center_lat + random.uniform(-0.5, 0.5),
            "lon": center_lon + random.uniform(-0.5, 0.5),
            "freqs_mhz": [1575.42, 1227.60],
            "power_dbm": random.uniform(-30, -10),
            "radius_km": random.uniform(20, 50),
            "started_at": datetime.utcnow(),
        }
        logger.info("GPS jamming scenario active", extra={"jammer_id": jammer_id})

    def generate_gps_spoofing_scenario(self, target_lat: float = 40.7580, target_lon: float = -73.9855):
        spoofer_id = f"spoofer-{time.time_ns()}"
        self.active_spoofers[spoofer_id] = {
            "lat": target_lat,
            "lon": target_lon,
            "spoofed_lat": target_lat + 0.05,
            "spoofed_lon": target_lon - 0.05,
            "freq_mhz": 1575.42,
            "power_dbm": random.uniform(-50, -30),
            "started_at": datetime.utcnow(),
        }
        logger.info("GPS spoofing scenario active", extra={"spoofer_id": spoofer_id})


class TDOAGeolocationEngine:
    def __init__(self):
        self.sensors = [
            {"id": "S1", "lat": 40.7128, "lon": -74.0060},
            {"id": "S2", "lat": 40.7580, "lon": -73.9855},
            {"id": "S3", "lat": 40.6892, "lon": -74.0445},
            {"id": "S4", "lat": 40.7484, "lon": -73.9857},
        ]

    def locate(self, tdoa_measurements: List[Tuple[str, str, float]]) -> Optional[dict]:
        if len(tdoa_measurements) < 3:
            return None
        try:
            A = []
            b = []
            ref_sensor_id = tdoa_measurements[0][0]
            ref = next(s for s in self.sensors if s["id"] == ref_sensor_id)
            for s1_id, s2_id, tdoa in tdoa_measurements:
                s1 = next(s for s in self.sensors if s["id"] == s1_id)
                s2 = next(s for s in self.sensors if s["id"] == s2_id)
                x1, y1 = s1["lon"], s1["lat"]
                x2, y2 = s2["lon"], s2["lat"]
                xr, yr = ref["lon"], ref["lat"]
                c = 299792458  # speed of light
                d = tdoa * c / 1000  # convert to meters
                A.append([2*(x1-xr), 2*(y1-yr)])
                b.append([d**2 - (x1**2 - xr**2) - (y1**2 - yr**2)])
            A = np.array(A)
            b = np.array(b)
            try:
                x, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)
                est_lon, est_lat = float(x[0][0]), float(x[1][0])
                uncertainty = float(np.std(residuals)) if len(residuals) > 0 else 100
                return {
                    "estimated_lat": est_lat,
                    "estimated_lon": est_lon,
                    "uncertainty_ellipse_axes_m": [uncertainty, uncertainty],
                    "confidence": max(0.3, min(0.95, 1.0 - uncertainty / 1000)),
                }
            except np.linalg.LinAlgError:
                return None
        except Exception as e:
            logger.error("TDOA localization error", extra={"error": str(e)})
            return None


class RFIngestor:
    def __init__(self):
        self.rf_env = SimulatedRFEnvironment()
        self.tdoa = TDOAGeolocationEngine()
        self.running = False

    async def start(self):
        self.running = True
        await kafka_client.start()
        logger.info("RF Domain Ingestor started")
        tasks = [
            self.scan_spectrum(),
            self.simulate_anomalies(),
        ]
        await asyncio.gather(*tasks)

    async def stop(self):
        self.running = False
        await kafka_client.stop()

    @track_latency("rf")
    async def scan_spectrum(self):
        bands = [433, 915, 2400, 5800, 1090]
        while self.running:
            await asyncio.sleep(1)
            for band_mhz in bands:
                noise = random.uniform(-120, -90)
                signal = random.uniform(-80, -30) if random.random() < 0.05 else 0
                power_dbm = max(noise, signal)
                if power_dbm > -50:
                    anomaly = RFAnomaly(
                        freq_mhz=band_mhz,
                        bandwidth_hz=random.uniform(100e3, 20e6),
                        signal_strength_dbm=power_dbm,
                        anomaly_type="unknown_signal",
                        confidence=min(0.9, max(0.3, (power_dbm + 50) / 50)),
                    )
                    metrics.events_ingested.labels(domain="rf", source="scanner").inc()
                    await kafka_client.send_event("rf-signals", anomaly.model_dump(), key=f"rf-{time.time_ns()}")

    async def simulate_anomalies(self):
        while self.running:
            await asyncio.sleep(30)
            if random.random() < 0.3:
                self.rf_env.generate_gps_jamming_scenario()
                jammer_event = {
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "type": "gps_jamming",
                    "severity": "CRITICAL",
                    "description": "GPS jamming detected on L1/L2 frequencies",
                    "freqs_mhz": [1575.42, 1227.60],
                    "estimated_radius_km": 50,
                }
                await kafka_client.send_event("alerts", jammer_event, key=f"jam-{time.time_ns()}")

            if random.random() < 0.2:
                self.rf_env.generate_gps_spoofing_scenario()
                spoofer_event = {
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "type": "gps_spoofing",
                    "severity": "CRITICAL",
                    "description": "GPS spoofing detected - position discrepancy",
                    "freq_mhz": 1575.42,
                }
                await kafka_client.send_event("alerts", spoofer_event, key=f"spoof-{time.time_ns()}")
