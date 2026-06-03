> Halo, yang sedang melihat repositori ini. Saya **Wisnu Alfian Nur Ashar** membangun **SENTINEL-X** dengan beberapa alasan:
>
> 1. **Kesadaran akan kerentanan negeri sendiri** — Indonesia adalah negara maritim terbesar dengan ribuan pulau, ribuan penerbangan setiap hari, dan infrastruktur kritis yang tersebar luas. Namun, sistem monitoring ancaman yang terintegrasi masih sangat terbatas.
> 2. **Kemandirian teknologi pertahanan** — Ketergantungan pada platform asing untuk keamanan infrastruktur kritis adalah risiko strategis. Bangsa ini harus punya solusi sendiri.
> 3. **Kesenjangan kemampuan deteksi** — Banyak ancaman bersifat multi-domain (siber + fisik + maritim), tapi belum ada platform open-source yang menyatukan semuanya dalam satu dashboard real-time.
> 4. **Membuktikan bahwa anak bangsa bisa** — Bahwa dengan sumber daya terbatas, kita bisa membangun sistem kelas dunia yang setara dengan platform militer global.
>
> Sehingga dengan itu, saya mencoba membuat solusi ini — sebuah platform fusi ancaman multi-domain yang mengintegrasikan 9 domain deteksi, AI-powered correlation, blockchain evidence chain, dan automated incident response dalam satu sistem real-time. Bukan sekadar project, tapi wujud kontribusi nyata untuk ketahanan nasional.

# SENTINEL-X — X-Domain Threat Fusion Platform

**Platform fusi ancaman multi-domain** yang mengintegrasikan 9 domain deteksi (Udara, Maritim, Seismik, RF/SIGINT, dan Siber) dalam satu sistem real-time dengan **AI-powered correlation engine**, **blockchain evidence chain**, dan **automated incident response playbooks**.

Dirancang untuk **Security Operations Center (SOC)**, **infrastructure protection**, dan **situational awareness** — memproses hingga 100.000 event/detik dengan latency <50ms p99.

---

## Fitur Utama

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

Perintah ini akan menstart 20+ service:
- 5 domain ingestors (berjalan paralel)
- AI threat fusion engine
- REST API + WebSocket server
- React frontend dashboard
- PostgreSQL + TimescaleDB
- Kafka + Zookeeper
- Hardhat Ethereum testnet
- IPFS node
- Prometheus + Grafana
- Jaeger tracing

### Verifikasi

```bash
# Cek status semua service
docker compose ps

# Cek health API
curl http://localhost:8000/health

# Cek WebSocket terhubung
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8000/ws

# Cek metrics Prometheus
curl http://localhost:8000/metrics
```

### Development Lokal (Tanpa Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Copy konfigurasi
cp .env.example .env

# Jalankan satu ingestor
INGESTOR_TYPE=air python -m src.ingestors.runner

# Jalankan API server
uvicorn src.api.main:app --reload --port 8000

# Jalankan AI Engine
python -m src.ai_engine.server

# Jalankan semua test
pytest --cov=tests --cov-report=term-missing
```

---

## API Reference

### REST Endpoints

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `GET` | `/health` | Health check service |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/api/v1/alerts` | List alerts (filter: ?threat_class=&domain=&limit=&offset=) |
| `GET` | `/api/v1/alerts/{id}` | Detail alert |
| `POST` | `/api/v1/alerts/{id}/acknowledge` | Acknowledge alert (body: `{"operator_id": "..."}`) |
| `POST` | `/api/v1/ingest/{domain}` | Manual ingest event ke domain (air/maritime/seismic/rf/cyber) |
| `POST` | `/api/v1/threat/assess` | Assess threat level dari event |

### WebSocket Events

**Server → Client:**
```json
{
  "type": "new_alert",
  "payload": { "alert_id": "...", "threat_class": "CRITICAL", ... },
  "timestamp_utc": "2024-06-01T12:00:00.000000Z",
  "sequence_number": 12345
}
```

**Client → Server:**
```json
{ "type": "ping" }
```

**Server → Client Response:**
```json
{ "type": "pong", "timestamp_utc": "...", "connections": 5 }
```

### Contoh Alert dengan XAI Reasoning

```json
{
  "threat_id": "TH-2024-001",
  "threat_class": "CRITICAL",
  "confidence": 0.89,
  "compound_pattern": "Maritime Deception Stack",
  "reasoning_chain": [
    {
      "step": 1,
      "domain": "maritime",
      "observation": "Vessel AIS blackout 47 menit",
      "contribution": 0.35
    },
    {
      "step": 2,
      "domain": "rf_sigint",
      "observation": "RF anomaly 156.8 MHz burst transmission",
      "contribution": 0.28
    },
    {
      "step": 3,
      "domain": "cyber",
      "observation": "Port Authority spear phishing 6 jam lalu",
      "contribution": 0.26
    }
  ],
  "recommended_actions": [
    "Task ISR assets to area",
    "Coordinate with regional authorities",
    "Notify port authority"
  ]
}
```

---

## Konfigurasi

### Environment Variables

| Variable | Default | Deskripsi |
|----------|---------|-----------|
| `DATABASE_URL` | `postgresql://sentinel:...@postgres:5432/sentinel` | Koneksi TimescaleDB |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka broker |
| `ETHEREUM_RPC_URL` | `http://hardhat-node:8545` | RPC Ethereum |
| `IPFS_RPC_URL` | `http://ipfs:5001` | RPC IPFS |
| `OPENSKY_USERNAME` | - | Username OpenSky Network |
| `OTX_API_KEY` | - | API Key AlienVault OTX |
| `SHODAN_KEY` | - | API Key Shodan |

File konfigurasi domain: `config/domains.yaml`

### Playbook Response

Playbook YAML di `playbooks/` mendefinisikan automated response:
- **maritime_dark_vessel_critical.yaml**: Response untuk Maritime Deception Stack
- **cyber_physical_attack_precursor.yaml**: Response untuk Infrastructure Attack Precursor

Struktur playbook:
```yaml
name: "Nama Playbook"
trigger:
  threat_class: CRITICAL
  compound_pattern: "Pattern Name"
phases:
  - name: "Phase Name"
    automated_steps:
      - action: action_name
        params: {key: value}
    operator_actions_required:
      - "Action required from operator"
```

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
3. Fréchet distance > threshold → deviation_score dihitung
4. Jika squawk 7700 + deviation → CATASTROPHIC

### Skenario 3: ICS/SCADA Probe
1. Cyber Ingestor (honeypot) menerima koneksi ke port 502 (Modbus)
2. Payload fingerprinting: Nmap/Shodan/Metasploit
3. Jika source IP dari negara tidak lazim → SUSPICIOUS
4. Compound dengan seismic activity di area → Infrastructure Attack Precursor

---

## Monitoring

### Grafana Dashboard
Akses di `http://localhost/grafana/` (login: `admin` / `sentinel_admin`)

Dashboard pre-built mencakup:
- Events ingested rate per domain
- Alerts by severity (pie chart)
- Ingestion latency (p50/p95/p99)
- Kafka consumer lag
- Error rate per service
- AI inference latency

### Prometheus Metrics
Akses di `http://localhost/prometheus/`

Key metrics:
```
sentinel_events_ingested_total{domain="air"}
sentinel_alerts_generated_total{severity="CRITICAL"}
sentinel_ai_inference_latency_seconds
sentinel_kafka_consumer_lag{topic="air-tracks"}
```

### Distributed Tracing (Jaeger)
Akses di `http://localhost/jaeger/`

---

## Testing

```bash
# Semua test
pytest

# Dengan coverage
pytest --cov=tests --cov-report=term-missing --cov-report=html

# Test spesifik domain
pytest tests/unit/test_air_ingestor.py -v
pytest tests/unit/test_maritime_ingestor.py -v

# Integration tests
pytest tests/integration/ -v
```

---

## Struktur Proyek

```
sentinel/
├── config/                  # Domain configuration YAML
├── docker/                  # Dockerfiles, Grafana, Prometheus configs
├── migrations/              # Alembic database migrations
├── models/                  # Trained AI model weights
├── playbooks/               # YAML incident response playbooks
├── src/
│   ├── api/                 # FastAPI REST + WebSocket server
│   ├── ai_engine/           # PyTorch multi-modal fusion model
│   │   ├── model.py         # ThreatFusionModel architecture
│   │   ├── train.py         # Training pipeline (500K synthetic samples)
│   │   └── server.py        # Inference server
│   ├── blockchain/          # Smart contracts + blockchain service
│   │   ├── contracts/       # ThreatLedger.sol, ResponseLog.sol
│   │   └── service.py       # Web3 + IPFS integration
│   ├── common/              # Shared modules
│   │   ├── config.py        # Pydantic settings
│   │   ├── database.py      # SQLAlchemy + TimescaleDB models
│   │   ├── kafka.py         # Async Kafka producer/consumer
│   │   ├── models.py        # Pydantic data models
│   │   ├── metrics.py       # Prometheus metrics
│   │   └── websocket_broadcast.py
│   ├── ingestors/           # Domain-specific data ingestors
│   │   ├── air/             # OpenSky, ADS-B, SDR simulator
│   │   ├── maritime/        # AIS parser, vessel tracking
│   │   ├── seismic/         # USGS, NOAA space weather
│   │   ├── rf/              # RF spectrum, GPS jammer/spoofer
│   │   ├── cyber/           # ICS honeypot, threat feeds
│   │   └── runner.py        # Ingestor entry point
│   └── response/            # Threat response system
│       ├── threat_classifier.py
│       ├── correlation.py   # Dark pattern graph engine
│       └── playbook.py      # YAML playbook executor
└── tests/
    ├── unit/                # Unit tests (32+ tests)
    └── integration/         # Integration tests (8+ tests)
```

---

## Kebutuhan Sistem

| Komponen | Minimum | Direkomendasikan |
|----------|---------|------------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Disk | 20 GB | 100 GB SSD |
| GPU | - | NVIDIA CUDA (untuk AI inference) |
| Docker | 24+ | 24+ |
| Python | 3.12 | 3.12 |

---

---

## Kebutuhan Sistem

| Komponen | Minimum | Direkomendasikan |
|----------|---------|------------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Disk | 20 GB | 100 GB SSD |
| GPU | - | NVIDIA CUDA (untuk AI inference) |
| Docker | 24+ | 24+ |
| Python | 3.12 | 3.12 |

---

## Author

**Wisnu Alfian Nur Ashar**

> *"Dibangun untuk menjaga dan membantu negeri ini. Jika tidak dihargai, saya akan terus membantu dari belakang dengan selalu mengasah skill — karena bangsa ini membutuhkan lebih banyak orang yang bisa, bukan hanya yang bicara."*

Platform ini adalah wujud kontribusi nyata di bidang keamanan siber dan pertahanan infrastruktur kritis. Didedikasikan untuk ketahanan nasional Indonesia.

---

## Lisensi

SENTINEL-X adalah platform keamanan siber yang dirancang untuk **pertahanan infrastruktur kritis dan keamanan nasional yang sah**. Penggunaan untuk pelanggaran privasi, pengawasan ilegal, atau pelanggaran hukum lainnya tidak diizinkan. Pengguna bertanggung jawab penuh atas kepatuhan terhadap hukum dan regulasi yang berlaku di yurisdiksi masing-masing, termasuk Undang-Undang Dasar Negara Republik Indonesia Tahun 1945 dan peraturan perundang-undangan terkait perlindungan data dan keamanan siber.