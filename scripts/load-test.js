import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const errorRate = new Rate("errors");
const ingestLatency = new Trend("ingest_latency");

export const options = {
  stages: [
    { duration: "30s", target: 1000 },
    { duration: "1m", target: 5000 },
    { duration: "30s", target: 10000 },
    { duration: "2m", target: 10000 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    errors: ["rate<0.01"],
    http_req_duration: ["p(95)<200", "p(99)<500"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const DOMAINS = ["air", "maritime", "seismic", "rf", "cyber"];

function randomEvent(domain) {
  const base = { timestamp_utc: new Date().toISOString() };
  switch (domain) {
    case "air":
      return {
        ...base,
        icao24: Math.random().toString(16).slice(2, 8),
        callsign: `TEST${Math.floor(Math.random() * 900) + 100}`,
        lat: (Math.random() - 0.5) * 180,
        lon: (Math.random() - 0.5) * 360,
        geo_altitude_m: Math.random() * 12000,
        velocity_ms: Math.random() * 280,
      };
    case "maritime":
      return {
        ...base,
        mmsi: String(Math.floor(Math.random() * 900000000) + 100000000),
        lat: (Math.random() - 0.5) * 120,
        lon: (Math.random() - 0.5) * 360,
        sog_knots: Math.random() * 25,
      };
    case "seismic":
      return {
        ...base,
        lat: (Math.random() - 0.5) * 180,
        lon: (Math.random() - 0.5) * 360,
        depth_km: Math.random() * 100,
        magnitude: Math.random() * 9,
      };
    case "rf":
      return {
        ...base,
        freq_mhz: [433, 915, 2400, 5800, 1575][Math.floor(Math.random() * 5)],
        signal_strength_dbm: -120 + Math.random() * 90,
        anomaly_type: Math.random() > 0.8 ? "gps_jamming" : "unknown_signal",
      };
    case "cyber":
      return {
        ...base,
        src_ip: `${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}`,
        dst_port: [102, 502, 20000, 44818][Math.floor(Math.random() * 4)],
        payload_hex: "0300001611be0000000100010061010001000000",
        severity: ["INFORMATIONAL", "SUSPICIOUS"][Math.floor(Math.random() * 2)],
      };
  }
}

export default function () {
  const domain = DOMAINS[Math.floor(Math.random() * DOMAINS.length)];
  const event = randomEvent(domain);

  const res = http.post(
    `${BASE_URL}/api/v1/ingest/${domain}`,
    JSON.stringify(event),
    { headers: { "Content-Type": "application/json" } }
  );

  const ok = check(res, { "status is 200": (r) => r.status === 200 });
  errorRate.add(!ok);
  ingestLatency.add(res.timings.duration);
  sleep(0.1);
}
