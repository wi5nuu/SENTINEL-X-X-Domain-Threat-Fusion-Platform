# SENTINEL-X — X-Domain Threat Fusion Platform

**SENTINEL-X** adalah platform fusi ancaman multi-domain yang mengintegrasikan 9 domain deteksi (Udara, Maritim, Seismik, RF/SIGINT, dan Siber) dalam satu sistem real-time dengan **AI-powered correlation engine**, **blockchain evidence chain**, dan **automated incident response playbooks**.

Dirancang untuk **Security Operations Center (SOC)**, **infrastructure protection**, dan **situational awareness** — memproses hingga 100.000 event/detik dengan latency <50ms p99.

---

## Fitur Utama: Deteksi & Visualisasi Ancaman

SENTINEL-X dilengkapi dengan mekanisme deteksi otomatis yang memberikan umpan balik visual instan pada dasbor:

- **Deteksi Ancaman Aktif:** Ketika sistem mendeteksi anomali atau ancaman yang terverifikasi, dasbor akan secara otomatis memicu peringatan visual. Tampilan layar akan memberikan indikasi kemerahan disertai dengan *popup* notifikasi yang mendetail untuk menarik perhatian operator segera.
- **Status Normal:** Dalam kondisi tanpa ancaman terdeteksi, antarmuka dasbor akan tetap berada pada tampilan normal (mode standar), memastikan operator tidak terganggu oleh *false alarm* dan dapat fokus pada monitoring rutin.
- **Fusi Multi-Domain:** Menggabungkan data dari domain udara, maritim, siber, seismik, dan RF untuk meminimalkan *false positive* melalui korelasi silang.

---

## Fitur Utama Lainnya

### Multi-Domain Detection
| Domain | Sumber Data | Algoritma Deteksi |
|--------|-------------|-------------------|
| **Udara** | OpenSky Network, ADS-B Exchange, SDR Simulasi | Kalman Filter Fusion, UAV RF Detection, Fréchet Flight Plan Deviation, No-Fly Zone Enforcement, Squawk Monitor |
| **Maritim** | AIS (NMEA), MarineTraffic API | Dark Vessel Detection, Anomalous Behavior Ensemble (speed, course, loitering, draught), Port Arrival Prediction |
| **Seismik** | USGS Earthquake, NOAA SWPC | Magnitude Threshold Alerting, Kp-index Space Weather, Tsunami Hazard Evaluation |
| **RF/SIGINT** | SDR Spectrum Scan, Simulasi GPS | TDOA Geolocation, GPS Jamming/Spoofing Detection, Burst Transmitter Classification |
| **Siber** | ICS Honeypot, OTX, AbuseIPDB | Modbus/DNP3/EtherNet-IP Probe Detection, Threat Intelligence Correlation |

### AI Threat Fusion Engine
- **Multi-modal fusion**: 5 domain-specific encoders (Conv1D + Attention) → Temporal Transformer (4 heads, 4 layers, 256 timesteps)
- **Output heads**: Threat classification (5-level), compound threat type (multi-label), ETA regression, confidence scoring
- **Explainable AI (XAI)**: Attention-based reasoning chain untuk setiap keputusan

### Dark Pattern Correlation
- Graph-based engine (NetworkX) untuk mendeteksi compound threat patterns:
  - **Maritime Deception Stack**: AIS blackout + RF anomaly + unidentified aircraft
  - **Infrastructure Attack Precursor**: GPS jamming + ICS cyber probes + vessel loitering
  - **Pre-Launch Warning**: Multiple unidentified aircraft + abnormal radar + communications blackout

### Blockchain Evidence Chain
- **ThreatLedger.sol**: Smart contract untuk immutable threat event logging dengan hash chaining
- **ResponseLog.sol**: Smart contract untuk operator action audit trail
- **IPFS Evidence Store**: Bundling bukti (sensor data, screenshots, RF captures) dengan IPFS CID

### Automated Response
- **5-level Threat Matrix**: INFORMATIONAL → SUSPICIOUS → ELEVATED → CRITICAL → CATASTROPHIC
- **YAML Playbook Engine**: Automated response phases dengan operator approval gates
- **Multi-Operator Collaboration**: WebSocket-based concurrent incident management, lock system, two-operator confirmation

### Observability
- **Prometheus metrics** per service (ingestion rate, inference latency, consumer lag, error rate)
- **Grafana dashboards** pre-built untuk real-time monitoring
- **OpenTelemetry / Jaeger** untuk distributed tracing
- **Structured JSON logging** semua service

---

## Arsitektur

```
                    ┌──────────────────┐
                    │  React Frontend  │  Port 3000
                    │  (HUD Dashboard) │
                    └────────┬─────────┘
                             │ WebSocket (real-time)
                    ┌────────▼─────────┐
                    │  FastAPI Backend │  Port 8000
                    │  REST + WS       │
                    └────────┬─────────┘
                             │ Kafka Event Stream
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  5 Domains   │   │  AI Fusion   │   │   Response   │
│  Ingestors   │──▶│  Engine      │──▶│  Coordinator │
│  (Air/Mar/   │   │  (PyTorch)   │   │  (Playbook)  │
│   Seis/RF/   │   │              │   │              │
│   Cyber)     │   │              │   │              │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────┐
│  PostgreSQL (TimescaleDB)  │  Redis  │  Elasticsearch│
│  Kafka  │  Ethereum (Hardhat)  │  IPFS              │
└─────────────────────────────────────────────────────┘
```

### Aliran Data Real-Time

```
Sensor/Feed → Ingestor → Kafka Topic → AI Engine → Alert → WebSocket → Dashboard
                   ↓                        ↓
            TimescaleDB              Blockchain + IPFS
```

---

## Memulai

### Prasyarat
- Docker & Docker Compose (untuk production)
- Python 3.12+ (untuk development lokal)
- 8GB+ RAM (16GB direkomendasikan untuk full stack)

### Menjalankan Semua Service

```bash
docker compose up -d
```

### Development Lokal (Tanpa Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Copy konfigurasi
cp .env.example .env

# Jalankan API server
uvicorn src.api.main:app --reload --port 8000
```

---

## API Reference

### REST Endpoints

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `GET` | `/health` | Health check service |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/api/v1/alerts` | List alerts |
| `POST` | `/api/v1/ingest/{domain}` | Manual ingest event |

---

## Konfigurasi

File konfigurasi domain: `config/domains.yaml`

---

## Skenario Deteksi

### Skenario 1: GPS Jamming Detection
1. RF Ingestor mendeteksi noise anomaly di 1575.42 MHz (L1)
2. Alert CRITICAL diterbitkan
3. AI Engine melakukan cross-check dengan vessel tracks di area
4. Jika ada vessel AIS blackout + loitering → Compound Threat ELEVATED

### Skenario 2: Flight Plan Deviation
1. Air Ingestor menerima track dari OpenSky
2. FlightPlanDeviationDetector membandingkan dengan filed flight plan

---

## Testing

```bash
# Semua test
pytest
```

---

## Struktur Proyek

```
sentinel/
├── config/                  # Domain configuration YAML
├── src/                     # Source code
├── tests/                   # Tests
└── ...
```

---

## Lisensi & Penggunaan

SENTINEL-X dirancang untuk tujuan pertahanan infrastruktur kritis dan keamanan nasional yang sah. Pengguna bertanggung jawab penuh atas kepatuhan terhadap hukum dan regulasi yang berlaku di yurisdiksi masing-masing terkait perlindungan data dan keamanan siber.
