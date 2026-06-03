# SENTINEL-X — X-Domain Threat Fusion Platform

**SENTINEL-X** adalah platform fusi ancaman multi-domain yang mengintegrasikan berbagai domain deteksi ancaman ke dalam satu sistem real-time dengan **AI-powered correlation engine**, **blockchain evidence chain**, dan **automated incident response playbooks**.

Dirancang untuk **Security Operations Center (SOC)**, **infrastructure protection**, dan **situational awareness** — memproses hingga 100.000 event/detik dengan latency <50ms p99.

---

## Fitur Utama: Deteksi & Visualisasi Ancaman

SENTINEL-X dilengkapi dengan mekanisme deteksi otomatis yang memberikan umpan balik visual instan pada dasbor:

- **Deteksi Ancaman Aktif:** Ketika sistem mendeteksi anomali atau ancaman yang terverifikasi, dasbor akan secara otomatis memicu peringatan visual. Tampilan layar akan memberikan indikasi kemerahan disertai dengan *popup* notifikasi yang mendetail untuk menarik perhatian operator segera.
- **Status Normal:** Dalam kondisi tanpa ancaman terdeteksi, antarmuka dasbor akan tetap berada pada tampilan normal (mode standar), memastikan operator tidak terganggu oleh *false alarm* dan dapat fokus pada monitoring rutin.
- **Fusi Multi-Domain:** Menggabungkan data dari berbagai domain untuk meminimalkan *false positive* melalui korelasi silang.

### Visualisasi Deteksi
| Status Normal | Deteksi Ancaman |
| :---: | :---: |
| ![Status Normal](public/sentinelpagenondetect.webp) | ![Deteksi Ancaman](public/sentinelpagedetected.webp) |

---

## Fitur Utama Lainnya

### Domain Deteksi & Ingestor
Sistem mengintegrasikan data dari 6 domain utama:
- **Udara**: OpenSky Network, ADS-B Exchange
- **Maritim**: AIS parser (NMEA)
- **Seismik**: USGS earthquake monitoring
- **RF/SIGINT**: SDR signal analysis
- **Siber**: ICS honeypot, threat feeds
- **NASA**: Data relevan dari dataset NASA

### Intelijen Lanjutan
- **CBRN-Watch**: Modul pemantauan tingkat radiasi dan ancaman CBRN.
- **Dark-Fleet-Tracker**: Modul khusus untuk melacak aktivitas kapal yang mencurigakan (*dark vessels*).

### AI Threat Fusion Engine
- **Multi-modal fusion**: 5 domain-specific encoders (Conv1D + Attention) → Temporal Transformer (4 heads, 4 layers, 256 timesteps)
- **Output heads**: Threat classification (5-level), compound threat type (multi-label), ETA regression, confidence scoring
- **Explainable AI (XAI)**: Attention-based reasoning chain untuk setiap keputusan

### Blockchain Evidence Chain
- **ThreatLedger.sol**: Smart contract untuk immutable threat event logging dengan hash chaining.
- **ResponseLog.sol**: Smart contract untuk operator action audit trail.
- **IPFS Evidence Store**: Bundling bukti sensor dengan IPFS CID.

### Automated Response
- **5-level Threat Matrix**: INFORMATIONAL → SUSPICIOUS → ELEVATED → CRITICAL → CATASTROPHIC
- **YAML Playbook Engine**: Automated response phases dengan operator approval gates

---

## Arsitektur Detail

```
                    ┌────────────────────────────┐
                    │       React Frontend       │ (Port 3000)
                    │   (Tactical Dashboard)     │
                    └─────────────┬──────────────┘
                                  │ WebSocket
                    ┌─────────────▼──────────────┐
                    │      FastAPI Backend       │ (Port 8000)
                    │ (REST API + WS Broadcast)  │
                    └─────────────┬──────────────┘
                                  │ Kafka
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│  Ingestors   │          │  AI Fusion   │          │   Response   │
│ (Air/Mar/RF/ │          │    Engine    │          │  Coordinator │
│ Seis/Cyber)  │          │ (PyTorch)    │          │  (Playbook)  │
└──────┬───────┘          └──────┬───────┘          └──────┬───────┘
       │                         │                         │
       └─────────────────────────┼─────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────┐
│                      Persistence & Shared                │
├──────────────────────────┬──────────────┬────────────────┤
│ PostgreSQL (TimescaleDB) │    Redis     │ Elasticsearch  │
├──────────────────────────┼──────────────┴────────────────┤
│          Kafka           │      Ethereum (Hardhat)       │
├──────────────────────────┴───────────────────────────────┤
│                          IPFS                            │
└──────────────────────────────────────────────────────────┘
```

---

## Struktur Proyek

Proyek ini memiliki beberapa modul yang terbagi ke dalam berbagai direktori untuk memudahkan pengembangan dan pemisahan *concerns*:

- **`src/`** — *Source code* utama dari keseluruhan sistem SENTINEL-X:
  - **`api/`**: Backend API berbasis FastAPI.
  - **`frontend/`**: Antarmuka pengguna *Tactical Dashboard* menggunakan React.
  - **`ai_engine/`**: Model *machine learning* dan pipeline PyTorch untuk *Threat Fusion*.
  - **`ingestors/`**: Modul integrasi yang menarik data dari berbagai domain (Udara, Laut, RF, Siber, dll).
  - **`blockchain/`**: *Smart contracts* Ethereum dan integrasi IPFS untuk *immutable logging*.
  - **`intelligence/`**: Modul intelijen lanjutan (seperti *CBRN-Watch*, *Dark-Fleet-Tracker*).
  - **`response/`**: Sistem pengelola otomatisasi *response playbook*.
  - **`synthetic_generator/`**: Modul pembuat data sintetis untuk keperluan pengujian.
  - **`common/`**: *Library* dan kode utilitas umum.
- **`config/`** — Direktori sentral untuk manajemen konfigurasi environment.
- **`docker/`** — Kumpulan *Dockerfiles*, skrip *entrypoint*, dan konfigurasi layanan (Nginx, Prometheus, dll).
- **`deploy/`** — *Script* untuk otomatisasi *deployment* infrastruktur menggunakan Ansible dan Terraform.
- **`models/`** — Definisi *schema* dan struktur data (Pydantic, SQLAlchemy).
- **`migrations/`** — Skrip migrasi *database* otomatis dengan Alembic.
- **`playbooks/`** — Kumpulan YAML Playbook untuk menangani respons insiden.
- **`public/`** — Aset publik statis dan referensi visual (seperti gambar dokumentasi).
- **`scripts/`** — Skrip utilitas pengembangan, instalasi, dan pemeliharaan.
- **`tests/`** — Kumpulan *unit test* dan *integration test* menggunakan Pytest.
- **`examples/`** — Contoh kode dan penggunaan integrasi data untuk referensi.

---

## Memulai

### Menjalankan dengan Docker
```bash
docker compose up -d
```

### Pengembangan Lokal
```bash
# Install dependencies
pip install -r requirements.txt

# Jalankan API server
uvicorn src.api.main:app --reload --port 8000
```

---

## Lisensi & Penggunaan

SENTINEL-X dirancang untuk tujuan pertahanan infrastruktur kritis dan keamanan nasional yang sah. Pengguna bertanggung jawab penuh atas kepatuhan terhadap hukum dan regulasi yang berlaku di yurisdiksi masing-masing.
