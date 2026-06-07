<div align="center">
  <img src="public/sentinelpagenondetect.webp" alt="Sentinel-X Logo" width="900">
  
  # SENTINEL-X
  **Platform Inteligensi Ancaman & Fusion Multi-Domain Perusahaan**

  [![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
  [![React](https://img.shields.io/badge/Frontend-React%20%7C%20Deck.GL-61DAFB?logo=react&logoColor=black)](https://reactjs.org/)
  [![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![PyTorch](https://img.shields.io/badge/AI_Engine-PyTorch-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
  [![Blockchain](https://img.shields.io/badge/Blockchain-Ethereum%20%7C%20IPFS-3C3C3D?logo=ethereum&logoColor=white)](https://ethereum.org/)
  [![Docker](https://img.shields.io/badge/Deployment-Docker%20Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

  *Kesadaran Situasional Tingkat Lanjut, Korelasi Berbasis AI, dan Respons Insiden Otomatis untuk Pusat Operasi Keamanan (SOC), Komando Militer, dan Perlindungan Infrastruktur Kritis.*
</div>

---

## Ringkasan Eksekutif

**SENTINEL-X** adalah platform fusi ancaman mission-critical dengan latensi ultra-rendah yang dirancang untuk memberikan gambaran operasional yang terpadu dan real-time. Dengan mengintegrasikan inteligensi mentah secara mulus dari domain udara, maritim, siber, ruang angkasa, seismik, dan RF, platform ini mengeliminasi masalah "swivel-chair" yang dihadapi oleh operator SOC modern.

Didukung oleh **AI Correlation Engine berbasis PyTorch**, SENTINEL-X tidak hanya menampilkan data—tetapi juga mengontekstualisasikannya. Platform ini menggunakan **Explainable AI (XAI)** untuk menentukan peringkat ancaman, menghitung regresi ETA, dan memicu playbook respons otomatis. Untuk memastikan integritas data mutlak dan jejak audit zero-trust, semua peristiwa kritis dan tindakan operator di-hash secara kriptografis dan dicatat langsung ke **Blockchain** berbasis Ethereum dan disimpan secara aman melalui **IPFS**.

Mampu memproses hingga **100.000 peristiwa/detik** dengan **latensi p99 <50ms**, SENTINEL-X mewakili generasi berikutnya dari infrastruktur pertahanan otomatis.

---

## Tur Visual Platform

SENTINEL-X menyediakan serangkaian antarmuka taktis yang disesuaikan untuk berbagai persyaratan operasional. Di bawah ini adalah tampilan mendetail dari tampilan inti platform:

### 1. Dashboard Taktis (Kondisi Normal)
Antarmuka operasional utama dalam kondisi standarnya. Ketika tidak ada ancaman aktif yang terdeteksi, UI tetap tenang, menggunakan estetika siber berwarna biru sejuk. Ini menampilkan telemetri langsung, status sensor aktif, dan log pelacakan normal tanpa membebani operator.
<div align="center">
  <img src="public/sentinelpagenondetect.webp" alt="Dashboard Taktis Kondisi Normal" width="800">
</div>

### 2. Deteksi Ancaman Aktif & Peringatan
Ketika AI Fusion Engine mengonfirmasi ancaman kritis, dashboard secara dinamis mengubah tata letak dan skema warnanya. Antarmuka secara agresif menyoroti anomali (berubah menjadi merah/amber), memicu peringatan modal prioritas tinggi dan memfokuskan perhatian operator sepenuhnya pada insiden aktif dan playbook yang direkomendasikan.
<div align="center">
  <img src="public/sentinelpagedetected.webp" alt="Ancaman Aktif Terdeteksi" width="800">
</div>

### 3. Kesadaran Situasional Global 3D Imersif
Didukung oleh `deck.gl`, tampilan ini memberikan representasi 3D globe yang sepenuhnya interaktif. Operator dapat memantau jejak langsung (termasuk lintasan ICBM simulasi dan armada angkatan laut) yang dipetakan terhadap lebih dari 60 instalasi militer dunia nyata. Fitur ini menyertakan latar belakang kanvas ruang angkasa WebGL kustom lengkap dengan aurora, nebula, dan pencahayaan dinamis.
<div align="center">
  <img src="public/sentinel3d.webp" alt="Kesadaran Situasional Global 3D" width="800">
</div>

### 4. Status Inteligensi Global
Dashboard tingkat makro yang didedikasikan untuk umpan inteligensi global. Ini mengagregasi tingkat ancaman siber di seluruh dunia, indikator risiko geopolitik, anomali seismik, dan kesehatan jaringan sensor global ke dalam satu ringkasan terpadu.
<div align="center">
  <img src="public/senstinelpageglobal.webp" alt="Status Inteligensi Global" width="800">
</div>

### 5. Analitik & Statistik Tingkat Lanjut
Tampilan analitis mendalam yang menyediakan korelasi data historis, metrik kinerja AI, grafik distribusi ancaman, dan telemetri sistem. Dirancang dengan UI glassmorphic yang bersih, ini menghilangkan elemen yang tidak perlu (seperti emoji) untuk memberikan wawasan yang murni profesional dan padat data.
<div align="center">
  <img src="public/sentinelstatistik.webp" alt="Analitik dan Statistik Tingkat Lanjut" width="800">
</div>

---

## Kemampuan Inti

### Ingesti Data Multi-Domain
Mengagregasi dan menormalisasi inteligensi mentah dari 6 domain utama secara mulus melalui antrean pesan Kafka yang sangat dioptimalkan:
- **Pertahanan Udara (ADS-B):** Integrasi OpenSky Network, ADS-B Exchange.
- **Keamanan Maritim (AIS):** Parser NMEA untuk pelacakan kapal gelap (dark vessel).
- **Aktivitas Seismik:** Pemantauan gempa bumi dan bawah tanah USGS.
- **RF/SIGINT:** Analisis sinyal Software-Defined Radio (SDR).
- **Perang Siber:** Honeypot ICS dan umpan ancaman global.
- **Ruang Angkasa & Satelit:** Dataset NASA dan pemantauan orbital.

### AI Threat Fusion Engine
- **Arsitektur Multi-Modal:** Menggunakan 5 encoder khusus domain (Conv1D + Attention) yang masuk ke Temporal Transformer (4 head, 4 layer, 256 timestep).
- **Analitik Prediktif:** Menghasilkan klasifikasi ancaman 5 tingkat, tipe ancaman gabungan multi-label, regresi ETA, dan skor kepercayaan.
- **Explainable AI (XAI):** Menyediakan rantai penalaran berbasis atensi untuk transparansi penuh dalam pengambilan keputusan, memastikan operator mengetahui *mengapa* AI menandai ancaman tersebut.

### Rantai Bukti Blockchain (Audit Zero-Trust)
- **ThreatLedger.sol:** Smart contract yang memastikan pencatatan peristiwa ancaman yang tidak dapat diubah melalui perantaian hash kriptografis.
- **ResponseLog.sol:** Smart contract yang menyediakan jejak audit tahan rusak untuk tindakan operator.
- **Integrasi IPFS:** Penyimpanan terdesentralisasi untuk membundel bukti sensor mentah (file PCAP, sapuan radar) dengan CID IPFS yang aman, memastikan bukti tidak dapat dirusak oleh pihak jahat.

### Respons Insiden Otomatis
- **Matriks Ancaman 5 Tingkat:** Secara otomatis berskala dari *INFORMATIONAL* > *SUSPICIOUS* > *ELEVATED* > *CRITICAL* > *CATASTROPHIC*.
- **YAML Playbook Engine:** Mengeksekusi fase respons otomatis sambil mendukung gerbang persetujuan operator manual untuk tindakan kritis (misalnya, isolasi firewall, otorisasi respons kinetik).

---

## Sumber Data & Simulasi

SENTINEL-X beroperasi dengan pendekatan hibrida (hybrid), menggabungkan simulasi taktis tingkat tinggi dengan integrasi data dunia nyata:

### 1. Data Simulasi & Sintetis (Dummy)
Proyek ini memiliki modul khusus bernama **SyntheticGenerator** (di `src/synthetic_generator/generator.py`). Modul ini berfungsi untuk membuat data buatan yang realistis untuk tujuan demo, pengujian, dan pelatihan model AI tanpa harus bergantung pada koneksi internet atau API berbayar.
- **Target Strategis**: Data simulasi ini menggunakan koordinat nyata dari pangkalan militer dunia, kota-kota besar (termasuk Jakarta, Manila, dll), dan jalur maritim internasional.
- **Skenario**: Modul ini mensimulasikan pergerakan pesawat (air tracks), posisi kapal (maritime positions), serangan cyber, anomali sinyal RF, hingga jalur peluncuran rudal (missile tracks) yang dihitung secara matematis berdasarkan kecepatan Mach dan lintasan Great Circle.

### 2. Data Real-World (Integrasi API Nyata)
Selain data simulasi, Sentinel dirancang untuk terhubung ke sumber data dunia nyata melalui modul-modul Ingestor:
- **Air Domain**: Terintegrasi dengan **OpenSky Network API** (di `src/ingestors/air/ingestor.py`) untuk mengambil data penerbangan asli di seluruh dunia secara real-time.
- **Space & Natural Events**: Terintegrasi dengan **NASA API** (di `src/ingestors/nasa/ingestor.py`) untuk mengambil data asli mengenai:
  - **EONET**: Kejadian alam nyata (kebakaran hutan, badai, gunung meletus).
  - **DONKI**: Data cuaca luar angkasa nyata (Solar Flares/Badai Matahari, Geomagnetic Storms) yang berdampak pada sinyal GPS dan RF di bumi.
- **Cyber Domain**: Siap terhubung ke *threat intelligence feeds* seperti **OTX (AlienVault)**, **Shodan**, dan **AbuseIPDB** untuk mendeteksi IP berbahaya yang benar-benar ada di internet.

---

## Arsitektur Sistem

SENTINEL-X bergantung pada arsitektur microservices berbasis peristiwa yang sangat skalabel:

```text
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
│               Persistensi & Berbagi Data                 │
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

- **`src/`** — Kode sumber inti
  - **`api/`**: Server backend FastAPI (WebSocket, REST endpoint).
  - **`frontend/`**: UI berbasis React (Vite, TypeScript, Deck.gl, Leaflet).
  - **`ai_engine/`**: Model ML PyTorch dan pipeline inferensi.
  - **`ingestors/`**: Modul ingesti data untuk polling API eksternal dan parsing socket.
  - **`blockchain/`**: Smart contract Ethereum (`.sol`) dan skrip integrasi Web3/IPFS.
  - **`response/`**: Skrip otomatisasi playbook.
- **`config/`** — Konfigurasi `.env` dan YAML terpusat.
- **`docker/`** — Dockerfile dan konfigurasi entrypoint.
- **`deploy/`** — Infrastructure as Code (Ansible/Terraform).
- **`tests/`** — Suite Pytest untuk pipeline CI/CD.
- **`public/`** — Aset statis dan dokumentasi gambar.

---

## Memulai

### Prasyarat
- **Docker & Docker Compose** (Minimal v2.0+)
- **Node.js** (v18+ untuk pengembangan frontend lokal)
- **Python** (3.10+ untuk pengembangan backend lokal)
- RAM Sistem Minimal: 16GB (karena model AI dan Elasticsearch)

### Deployment melalui Docker (Direkomendasikan)
Luncurkan seluruh tumpukan microservices (Frontend, API, Kafka, Zookeeper, Postgres, Redis, IPFS, Hardhat) dengan satu perintah:

```bash
# Klon repositori
git clone https://github.com/yourusername/sentinel-x.git
cd sentinel-x

# Bangun dan deploy semua kontainer dalam mode detached
docker compose up -d --build
```

**Titik Akses:**
- **Dashboard Taktis:** [http://localhost:3000](http://localhost:3000)
- **Dokumentasi Swagger FastAPI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Prometheus/Grafana (jika diaktifkan):** [http://localhost:3001](http://localhost:3001)

---

## Keamanan & Kontribusi

- **Audit Keamanan:** Harap laporkan kerentanan potensial ke email keamanan yang tercantum di `SECURITY.md`. Jangan membuka issue publik untuk zero-day.
- **Kontribusi:** Kami menyambut PR untuk domain Ingestor baru atau konfigurasi Playbook. Harap tinjau `CONTRIBUTING.md` sebelum mengirimkan.

---

## Diagram Arsitektur

### Diagram Urutan (Sequence Diagram)

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Sensors
    participant MilitaryIntel
    participant Satellite
    participant OSINT
    participant Ingestors
    participant Kafka
    participant AIEngine
    participant ResponseEngine
    participant Blockchain
    participant IPFS
    participant Monitoring
    participant Database

    User->>Frontend: Buka dashboard dan autentikasi
    Frontend->>Backend: GET /dashboard, berlangganan WebSocket
    Backend->>Database: Muat konfigurasi pengguna, status sesi, ambang batas
    Backend->>Monitoring: Laporkan latensi permintaan dan kesehatan
    Backend->>Frontend: Kembalikan payload awal dashboard
    Sensors->>Ingestors: Kirim radar, ADS-B, SIGINT dan telemetri sensor
    MilitaryIntel->>Ingestors: Kirim umpan ancaman terklasifikasi
    Satellite->>Ingestors: Kirim data ruang angkasa, orbital, dan citra
    OSINT->>Ingestors: Kirim umpan siber open-source dan geopolitik
    Ingestors->>Kafka: Publikasikan peristiwa domain yang dinormalisasi
    Kafka->>Backend: Kirim aliran peristiwa untuk ingesti
    Backend->>AIEngine: Teruskan batch peristiwa untuk penilaian fusi
    AIEngine->>Backend: Kembalikan klasifikasi ancaman + kepercayaan
    Backend->>ResponseEngine: Korelasikan peringatan dan rekomendasikan playbook
    ResponseEngine->>Blockchain: Simpan hash bukti audit
    ResponseEngine->>IPFS: Simpan bundel bukti mentah
    ResponseEngine->>Backend: Kembalikan proposal tindakan otomatis
    Backend->>Kafka: Publikasikan peristiwa pemberitahuan peringatan
    Backend->>Frontend: Siarkan pembaruan ancaman langsung
    Frontend->>User: Render peta ancaman, detail insiden, status respons
```

Aliran mendetail tentang bagaimana interaksi pengguna, ingesti peristiwa, fusi ancaman, dan otomatisasi respons bergerak melalui platform.

### Diagram Kelas (Class Diagram)

```mermaid
classDiagram
    class Frontend {
        +Dashboard
        +ThreatMap
        +WebSocketClient
        +PlaybookPanel
        +NotificationFeed
    }
    class Backend {
        +REST API
        +WebSocket Server
        +Event Router
        +Auth & Session
        +Config Loader
    }
    class Ingestors {
        +AirIngestor
        +MaritimeIngestor
        +CyberIngestor
        +RFIngestor
        +SeismicIngestor
        +MilitaryIntelIngestor
        +SatelliteIngestor
        +OSINTIngestor
    }
    class AIEngine {
        +FeatureEncoder
        +TemporalTransformer
        +ThreatClassifier
        +XAI Explainer
    }
    class ResponseEngine {
        +PlaybookExecutor
        +AlertCorrelation
        +IncidentManager
        +Notification Dispatcher
    }
    class Persistence {
        +PostgreSQL
        +Redis
        +Elasticsearch
        +TimescaleDB
        +Kafka
    }
    class Blockchain {
        +Ethereum Hardhat
        +SmartContracts
        +EvidenceLedger
    }
    class IPFS {
        +EvidenceStorage
        +CID Registry
    }
    class Monitoring {
        +Prometheus
        +Grafana
        +HealthChecks
        +MetricsExporter
    }

    Frontend --> Backend: REST / WebSocket
    Backend --> Persistence: simpan + cache + cari
    Backend --> Kafka: publikasi/langganan
    Backend --> Ingestors: kontrol / konfigurasi
    Backend --> AIEngine: permintaan inferensi
    Backend --> ResponseEngine: tindakan insiden
    ResponseEngine --> Blockchain: pencatatan audit
    ResponseEngine --> IPFS: penyimpanan bukti
    Backend --> Monitoring: metrik dan kesehatan
    Ingestors --> Kafka: aliran peristiwa
    Kafka --> Backend: konsumsi peristiwa
```

Tinjauan arsitektur profesional yang memetakan modul inti, dependensi runtime, dan aliran data di seluruh platform Sentinel-X.

### Diagram Deployment

```mermaid
flowchart LR
    subgraph UI
        Frontend["Frontend\nReact + Vite"]
    end

    subgraph API
        Backend["Backend\nFastAPI + WebSocket"]
        Kafka["Kafka\nTopic Bus"]
    end

    subgraph DataStore
        Postgres["PostgreSQL\nTimescaleDB"]
        Redis["Redis\nCache & Sesi"]
        Elastic["Elasticsearch\nCari & Analitik"]
    end

    subgraph Infra
        Blockchain["Ethereum Hardhat\nBuku Besar Audit"]
        IPFS["IPFS\nPenyimpanan Bukti"]
        Monitoring["Prometheus / Grafana\nMetrik + Dashboard"]
    end

    subgraph Ingestion
        Ingestors["Ingestors\nUdara/Maritim/Siber/RF/Seismik\nIntel Militer / Satelit / OSINT"]
    end

    Frontend -->|HTTP / WS| Backend
    Backend -->|Publikasi peristiwa| Kafka
    Ingestors -->|Hasilkan peristiwa| Kafka
    Backend -->|Kueri / simpan| Postgres
    Backend -->|Cache / sesi| Redis
    Backend -->|Indeks / cari| Elastic
    Backend -->|Keluarkan metrik| Monitoring
    Backend -->|Panggil respons| Blockchain
    Backend -->|Simpan bukti| IPFS
    Kafka -->|Konsumsi aliran| Backend
    Frontend -->|Pantau UI| Monitoring
```

Tinjauan deployment yang menunjukkan bagaimana kontainer layanan dan komponen infrastruktur berinteraksi dalam tumpukan Sentinel-X.

---

## Lisensi & Hukum

**SENTINEL-X** dirancang untuk pertahanan infrastruktur kritis yang sah dan penelitian keamanan nasional. Pengguna bertanggung jawab penuh atas kepatuhan terhadap semua hukum lokal, nasional, dan internasional yang berlaku mengenai SIGINT, pemantauan siber, dan privasi data.

Dirilis di bawah **Lisensi MIT**. Lihat `LICENSE` untuk detailnya.

<div align="center">
  <br>
  <i>Dikembangkan dengan presisi dan mempertimbangkan keamanan.</i>
</div>
