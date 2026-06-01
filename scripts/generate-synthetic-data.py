#!/usr/bin/env python3
"""
Synthetic Data Generator untuk SENTINEL-X.
Menghasilkan contoh event JSON untuk testing dan demontrasi.

Usage:
    python scripts/generate-synthetic-data.py --count 100 --domain air
    python scripts/generate-synthetic-data.py --count 500 --output ./output/
"""

import argparse
import json
import os
import random
import uuid
from datetime import datetime, timedelta


def random_lat():
    return random.uniform(-90, 90)


def random_lon():
    return random.uniform(-180, 180)


def generate_air_track():
    return {
        "track_id": str(uuid.uuid4()),
        "icao24": f"{random.randint(0, 0xFFFFFF):06x}",
        "callsign": random.choice([f"GIA{random.randint(100,999)}", f"LNI{random.randint(100,999)}", None]),
        "origin_country": random.choice(["Indonesia", "Singapore", "Malaysia", "Australia", "Unknown"]),
        "timestamp_utc": datetime.utcnow().isoformat(),
        "lat": random_lat(),
        "lon": random_lon(),
        "baro_altitude_m": random.uniform(3000, 12000),
        "geo_altitude_m": random.uniform(3000, 12000),
        "velocity_ms": random.uniform(100, 280),
        "true_track_deg": random.uniform(0, 360),
        "vertical_rate_ms": random.uniform(-5, 5),
        "squawk": random.choice(["1200", "1400", "2000", None]),
        "on_ground": False,
        "source": random.choice(["adsb", "mode_s", "simulated"]),
        "classification": "commercial",
        "classification_confidence": random.uniform(0.7, 0.99),
        "sensors_contributing": [],
        "deviation_score": None,
        "threat_flags": [],
    }


def generate_vessel():
    return {
        "mmsi": str(random.randint(100000000, 999999999)),
        "imo": f"IMO{random.randint(9000000, 9999999)}" if random.random() < 0.7 else None,
        "vessel_name": f"MV {random.choice(['MERAPI', 'BROMO', 'RINJANI', 'KRAKATAU', 'SAMUDRA'])}-{random.randint(1,99)}",
        "vessel_type": random.choice(["cargo", "tanker", "passenger", "fishing", "pleasure"]),
        "flag_state": random.choice(["IDN", "SGP", "PAN", "LBR", "MHL"]),
        "timestamp_utc": datetime.utcnow().isoformat(),
        "lat": random.uniform(-10, 10),
        "lon": random.uniform(95, 140),
        "sog_knots": random.uniform(0, 25),
        "cog_deg": random.uniform(0, 360),
        "heading_deg": random.uniform(0, 360),
        "nav_status": random.choice(["underway", "at_anchor", "moored"]),
        "destination": random.choice(["Tanjung Priok", "Singapore", "Surabaya", "Belawan", None]),
        "eta_utc": (datetime.utcnow() + timedelta(hours=random.randint(1, 72))).isoformat() if random.random() < 0.5 else None,
        "draught_m": random.uniform(3, 18),
        "cargo_hazmat_class": random.choice(["1", "2.1", "3", "4.1", None]),
        "ais_class": random.choice(["A", "B"]),
        "last_seen_utc": datetime.utcnow().isoformat(),
        "ais_gap_minutes": round(random.uniform(0, 60), 1),
        "dark_vessel_suspect": random.random() < 0.1,
        "anomaly_flags": [],
    }


def generate_seismic_event():
    return {
        "event_id": f"syn-{uuid.uuid4().hex[:8]}",
        "timestamp_utc": datetime.utcnow().isoformat(),
        "lat": random.uniform(-10, -5),
        "lon": random.uniform(115, 130),
        "depth_km": random.uniform(5, 200),
        "magnitude": round(random.uniform(2.5, 8.5), 1),
        "magnitude_type": "ml",
        "location_description": f"{random.choice(['North', 'South', 'East', 'West'])} of {random.choice(['Jakarta', 'Surabaya', 'Ambon', 'Manado'])}",
        "felt_reports": random.randint(0, 500),
        "tsunami_warning": random.random() < 0.1,
        "source": "usgs",
    }


def generate_rf_anomaly():
    return {
        "event_id": f"rf-{uuid.uuid4().hex[:8]}",
        "timestamp_utc": datetime.utcnow().isoformat(),
        "freq_mhz": random.choice([433, 915, 1575.42, 2400, 5800]),
        "bandwidth_hz": random.uniform(100e3, 20e6),
        "signal_strength_dbm": random.uniform(-90, -20),
        "estimated_lat": random_lat() if random.random() < 0.5 else None,
        "estimated_lon": random_lon() if random.random() < 0.5 else None,
        "confidence": round(random.uniform(0.3, 0.95), 2),
        "anomaly_type": random.choice(["unknown_signal", "gps_jamming", "gps_spoofing", "burst_transmitter"]),
        "protocol_guess": random.choice(["DJI", "Parrot", "FPV", None]),
        "burst_interval_ms": round(random.uniform(1, 50), 1) if random.random() < 0.3 else None,
    }


def generate_cyber_event():
    return {
        "event_id": f"cyber-{uuid.uuid4().hex[:8]}",
        "timestamp_utc": datetime.utcnow().isoformat(),
        "src_ip": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        "src_port": random.randint(1024, 65535),
        "dst_port": random.choice([102, 502, 20000, 44818]),
        "protocol": random.choice(["Modbus TCP", "DNP3", "S7comm", "EtherNet/IP"]),
        "payload_hex": "0300001611be0000000100010061010001000000",
        "technique": random.choice(["Nmap", "Shodan", "Metasploit", None]),
        "target_sector": random.choice(["power_grid", "industrial_control", "maritime", None]),
        "source_feed": "honeypot",
        "severity": random.choice(["INFORMATIONAL", "SUSPICIOUS", "ELEVATED"]),
    }


GENERATORS = {
    "air": generate_air_track,
    "maritime": generate_vessel,
    "seismic": generate_seismic_event,
    "rf": generate_rf_anomaly,
    "cyber": generate_cyber_event,
    "all": lambda: random.choice([
        generate_air_track, generate_vessel, generate_seismic_event,
        generate_rf_anomaly, generate_cyber_event
    ])(),
}


def main():
    parser = argparse.ArgumentParser(description="SENTINEL-X Synthetic Data Generator")
    parser.add_argument("--count", type=int, default=10, help="Number of events to generate")
    parser.add_argument("--domain", choices=list(GENERATORS.keys()), default="all", help="Domain to generate")
    parser.add_argument("--output", type=str, default=None, help="Output directory (default: print to stdout)")
    args = parser.parse_args()

    generator = GENERATORS[args.domain]

    for i in range(args.count):
        event = generator()
        event["sequence"] = i + 1

        if args.output:
            os.makedirs(args.output, exist_ok=True)
            domain = args.domain if args.domain != "all" else event.get("source", event.get("domain", "unknown"))
            fname = f"{domain}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{i:04d}.json"
            with open(os.path.join(args.output, fname), "w") as f:
                json.dump(event, f, indent=2, default=str)
        else:
            print(json.dumps(event, indent=2, default=str))
            print("---")

    print(f"Generated {args.count} events ({args.domain})")


if __name__ == "__main__":
    main()
