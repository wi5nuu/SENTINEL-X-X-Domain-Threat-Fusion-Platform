# SENTINEL Platform - Setup Guide

## DISCLAIMER: PROOF OF CONCEPT PROJECT

SENTINEL adalah **proyek demonstrasi dan proof-of-concept** yang dikembangkan untuk tujuan:
- Edukasi dan pembelajaran
- Research dan eksplorasi teknologi
- Portfolio showcase
- Demonstrasi konsep sistem integration

**Ini BUKAN sistem production-ready untuk critical infrastructure.**

---

## STATUS: Real-Time Data Integration

Platform ini mengintegrasikan **data real-time dari API publik** untuk keperluan demonstrasi konsep.

---

## QUICK START

### 1. Setup Environment

```bash
# Copy template konfigurasi
cp .env.example .env

# Edit file .env
nano .env
```

### 2. Konfigurasi Minimal (Sumber GRATIS)

```bash
# Mode operasi real-time
ENABLE_SYNTHETIC_DATA=false

# Keamanan (WAJIB diubah)
JWT_SECRET_KEY=<generate-random-32-chars>
ENABLE_DATA_ENCRYPTION=true

# API Keys untuk data source (lihat panduan registrasi di bawah)
OPENSKY_USERNAME=your_username
OPENSKY_PASSWORD=your_password
NASA_API_KEY=DEMO_KEY
```

### 2a. Konfigurasi Enhanced (Optional - Untuk Akurasi Lebih Tinggi)

Jika ingin mengaktifkan fitur enhanced dengan data quality score lebih tinggi, tambahkan:

```bash
# FlightAware AeroAPI (Aviation - Quality Score 0.95)
AEROAPI_KEY=your_flightaware_api_key
AEROAPI_URL=https://aeroapi.flightaware.com/aeroapi

# OpenWeatherMap (Weather Correlation - Quality Score 0.85)
OPENWEATHER_API_KEY=your_openweather_key
OPENWEATHER_URL=https://api.openweathermap.org/data/2.5
```

Lihat file `ENHANCED_FEATURES.md` untuk detail lengkap tentang enhanced features.

**PENTING**: Jangan pernah commit file `.env` ke repository. File ini berisi credentials sensitif.

### **3. Deploy**

**Basic Deployment (Free Data Sources):**
```bash
# Build containers
docker-compose build

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f
```

**Enhanced Deployment (With Optional Premium Features):**
```bash
# Build and start with enhanced profile
docker-compose --profile enhanced up -d --build

# Check enhanced services
docker-compose logs -f sentinel-flightaware
docker-compose logs -f sentinel-weather
docker-compose logs -f sentinel-correlation-engine
```

Lihat `ENHANCED_FEATURES.md` untuk panduan lengkap tentang deployment enhanced features.

---

## 🌐 **DATA SOURCES (100% REAL)**

### **Active Without Configuration (FREE):**

| Source | Domain | Data Type | Status |
|--------|--------|-----------|--------|
| USGS | Seismic | Global earthquakes | ✅ Active |
| EMSC | Seismic | European earthquakes | ✅ Active |
| NASA EONET | Space | Natural disasters | ✅ Active |
| NASA DONKI | Space | Solar flares, CME | ✅ Active |
| ThreatFox | Cyber | IOCs, malware | ✅ Active |

### **Needs API Key (FREE Registration):**

| Source | Domain | Data Type | How to Get |
|--------|--------|-----------|------------|
| OpenSky | Aviation | Aircraft tracking | https://opensky-network.org |
| AISHub | Maritime | Vessel positions | https://www.aishub.net |
| AlienVault OTX | Cyber | Threat intel | https://otx.alienvault.com |
| AbuseIPDB | Cyber | Malicious IPs | https://www.abuseipdb.com |

### **Enhanced Features (Optional - Higher Accuracy):**

| Source | Domain | Data Type | Quality Score | How to Get |
|--------|--------|-----------|---------------|------------|
| FlightAware | Aviation | Premium flight data | 0.95 | https://www.flightaware.com/aeroapi |
| OpenWeatherMap | Weather | Weather correlation | 0.85 | https://openweathermap.org/api |
| MarineTraffic | Maritime | Premium vessel tracking | 0.85 | https://www.marinetraffic.com |

**Note**: Enhanced features memberikan data yang lebih akurat dan detail dengan quality scores lebih tinggi. Dapat diaktifkan dengan menambahkan API keys dan menggunakan profile `enhanced`:
```bash
docker-compose --profile enhanced up -d
```

### **Optional (Paid/Enhanced):**

- **VirusTotal** - File/URL scanning (free tier available)
- **Shodan** - Network device scanning
- **MarineTraffic** - Premium vessel tracking
- **FlightAware** - Premium aviation data
- **OpenWeatherMap** - Weather correlation (free tier available)

Lihat file `ENHANCED_FEATURES.md` untuk informasi lengkap tentang fitur-fitur enhanced.

---

## ✅ **VERIFICATION**

### **1. Check Logs for Real Data**

```bash
# Air domain - should show real aircraft
docker-compose logs sentinel-ingestor-air | grep "REAL"
# Expected: ✅ OpenSky: Processed 150 REAL aircraft

# Seismic - should show real earthquakes
docker-compose logs sentinel-usgs-seismic | tail -20
# Expected: USGS poll complete: 42 events

# Cyber threats - should show real IOCs
docker-compose logs sentinel-threat-intel | grep "poll complete"
# Expected: ThreatFox poll complete: 65 IOCs

# Space weather - should show real events
docker-compose logs sentinel-nasa | tail -20
# Expected: EONET poll complete: 8 events
```

### **2. Check NO Synthetic Data**

```bash
# Should return NOTHING
docker-compose logs | grep -i "synthetic\|simulated\|dummy"

# Check .env setting
grep ENABLE_SYNTHETIC_DATA .env
# Expected: ENABLE_SYNTHETIC_DATA=false
```

### **3. Verify Kafka Topics**

```bash
# Check cyber events (must be from real sources)
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic cyber-events \
  --from-beginning \
  --max-messages 3

# Check source field - MUST be: otx_real, abuseipdb_real, threatfox_real
# NOT: synthetic, simulated

# Check seismic events
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic seismic-events \
  --from-beginning \
  --max-messages 3

# Check source field - MUST be: usgs_real, emsc_real
```

---

## KEAMANAN & BEST PRACTICES

### Fitur Keamanan Built-in:

- Enkripsi API keys di storage  
- Input validation dan sanitization  
- Rate limiting untuk semua API calls  
- Audit logging untuk compliance  
- RBAC (Role-Based Access Control)  
- Immutable audit trail via blockchain  

### Konfigurasi Keamanan:

```bash
# Di file .env
ENABLE_DATA_ENCRYPTION=true
API_KEY_ROTATION_HOURS=24
MAX_API_RATE_LIMIT=1000

# Generate JWT secret yang strong
JWT_SECRET_KEY=<minimum-32-random-characters>
```

### Best Practices Wajib:

1. **JANGAN PERNAH** commit file `.env` ke git
2. **JANGAN PERNAH** share API keys Anda
3. Gunakan passwords yang kuat (min 32 karakter)
4. Enable HTTPS untuk production deployment
5. Review logs secara berkala untuk aktivitas mencurigakan
6. Update dependencies secara teratur
7. Implement firewall rules yang proper
8. Backup data secara berkala

### Catatan Legal:

Platform ini dirancang untuk **legitimate security monitoring** dan **authorized operations** saja. Pastikan penggunaan Anda comply dengan:
- Hukum dan regulasi lokal
- Terms of Service dari API providers
- Privacy regulations (GDPR, etc.)
- Organization security policies

**Penggunaan yang tidak authorized adalah ILLEGAL dan dapat dikenakan sanksi hukum.**

---

## 🚨 **TROUBLESHOOTING**

### **Problem: No data appearing**

```bash
# 1. Check API keys
docker-compose logs sentinel-threat-intel | grep -i "error\|warning"

# 2. Verify network connectivity
docker-compose exec sentinel-api curl -I https://earthquake.usgs.gov

# 3. Check Kafka
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# 4. Rebuild if needed
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### **Problem: Still seeing synthetic data**

```bash
# 1. Check .env
grep ENABLE_SYNTHETIC_DATA .env
# Must be: false

# 2. Check container
docker-compose ps | grep synthetic
# Should be: NOTHING (no synthetic container)

# 3. Fix and restart
sed -i 's/ENABLE_SYNTHETIC_DATA=true/ENABLE_SYNTHETIC_DATA=false/' .env
docker-compose restart
```

### **Problem: Rate limit exceeded**

```bash
# Increase in .env
MAX_API_RATE_LIMIT=2000

# Or reduce polling frequency in code
# Edit respective ingestor files
```

---

## REGISTRASI API KEYS

Platform ini menggunakan API dari sumber data publik yang legitimate. Anda perlu mendaftar untuk mendapatkan API key:

### 1. OpenSky Network (Aviation Data - GRATIS)
- Website: https://opensky-network.org/
- Data: Real-time aircraft positions worldwide
- Registrasi: Gratis dengan email verification

### 2. NASA API (Space Weather - GRATIS)
- Website: https://api.nasa.gov/
- Data: Solar flares, natural disasters, space events
- Registrasi: Instant API key generation

### 3. AlienVault OTX (Threat Intelligence - GRATIS)
- Website: https://otx.alienvault.com/
- Data: Cyber threat indicators dari global community
- Registrasi: Gratis dengan verifikasi email

### 4. AbuseIPDB (Malicious IPs - GRATIS)
- Website: https://www.abuseipdb.com/
- Data: Database IP addresses yang dilaporkan melakukan abuse
- Limit: 1000 requests/day pada free tier

### 5. AISHub (Maritime Data - GRATIS)
- Website: https://www.aishub.net/
- Data: AIS vessel positions
- Registrasi: Free account dengan username

**Catatan Penting**: 
- Semua API keys harus disimpan di file `.env` yang **TIDAK boleh** di-commit ke git
- Gunakan API keys sesuai terms of service dari masing-masing provider
- Jangan share API keys Anda dengan orang lain
- Rotate keys secara berkala untuk keamanan

### Enhanced Features API Keys (Optional):

#### 6. FlightAware AeroAPI (Enhanced Aviation - PAID)
- Website: https://www.flightaware.com/aeroapi
- Data: Premium flight data dengan quality score 0.95
- Features: Detailed routes, waypoints, delays, aircraft type
- Pricing: Berbayar dengan free trial available

#### 7. OpenWeatherMap (Weather Correlation - FREEMIUM)
- Website: https://openweathermap.org/api
- Data: Real-time weather untuk correlation dengan aviation/maritime events
- Free Tier: 1000 calls/day
- Features: Temperature, wind, visibility, severe weather alerts

Fitur enhanced ini optional dan memberikan data dengan akurasi lebih tinggi. Lihat `ENHANCED_FEATURES.md` untuk detail lengkap.

---

## 📊 **MONITORING**

### **Dashboards:**

- **Grafana:** http://localhost/grafana (admin/your_password)
- **Prometheus:** http://localhost/prometheus
- **Jaeger:** http://localhost/jaeger
- **Frontend:** http://localhost

### **Key Metrics:**

```bash
# Events ingested per domain
events_ingested_total{domain="cyber", source="otx_real"}
events_ingested_total{domain="seismic", source="usgs_real"}
events_ingested_total{domain="air", source="adsb"}

# API errors
api_errors_total{service="threat_intel"}

# Rate limits
rate_limit_violations_total

# Security events
security_events_total
```

---

## 🏗️ **ARCHITECTURE**

```
┌─────────────────────────────────────────────────────────┐
│                    REAL-TIME DATA SOURCES                │
├─────────────────────────────────────────────────────────┤
│ OpenSky │ USGS │ NASA │ OTX │ AbuseIPDB │ ThreatFox    │
└────┬──────────┬──────┬──────┬───────────┬──────────┬───┘
     │          │      │      │           │          │
     ▼          ▼      ▼      ▼           ▼          ▼
┌─────────────────────────────────────────────────────────┐
│                     INGESTORS (Real-Time)                │
│  Air │ Maritime │ Seismic │ Cyber │ Space Weather       │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   KAFKA (Event Stream)                   │
│  air-tracks │ maritime │ seismic │ cyber │ rf-signals   │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              AI ENGINE + CORRELATION                     │
│  Threat Detection │ Pattern Analysis │ Fusion           │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  BLOCKCHAIN + STORAGE                    │
│  TimescaleDB │ Elasticsearch │ IPFS │ Ethereum          │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   FRONTEND (React)                       │
│  Real-Time Dashboard │ Alerts │ Analytics               │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 **COMPONENTS**

| Service | Purpose | Port | Health Check |
|---------|---------|------|--------------|
| sentinel-api | REST API | 8000 | http://localhost:8000/health |
| sentinel-frontend | React UI | 3000 | http://localhost |
| sentinel-ingestor-air | Aviation data | - | Internal |
| sentinel-ingestor-maritime | Vessel data | - | Internal |
| sentinel-threat-intel | Cyber threats | - | Internal |
| sentinel-usgs-seismic | Earthquake data | - | Internal |
| sentinel-nasa | Space weather | - | Internal |
| postgres | Database | 5432 | Internal |
| kafka | Event streaming | 9092 | Internal |
| elasticsearch | Search & analytics | 9200 | Internal |
| redis | Cache | 6379 | Internal |
| grafana | Monitoring | 3001 | http://localhost/grafana |
| prometheus | Metrics | 9090 | http://localhost/prometheus |

---

## 🔄 **MAINTENANCE**

### **Daily:**
- Check logs for errors
- Verify data ingestion metrics
- Monitor rate limits

### **Weekly:**
- Review audit logs
- Check API key usage
- Verify security events

### **Monthly:**
- Update dependencies: `pip install --upgrade -r requirements.txt`
- Rotate API keys (automated)
- Review and archive old alerts

### **Quarterly:**
- Security vulnerability scan: `pip-audit`
- Docker image scan: `docker scan`
- Penetration testing

---

## ✅ **CHECKLIST**

### **Initial Setup:**
- [ ] `.env` file created
- [ ] `ENABLE_SYNTHETIC_DATA=false` set
- [ ] JWT secret generated
- [ ] Security features enabled
- [ ] At least 2 API keys configured

### **Deployment:**
- [ ] Docker containers built
- [ ] All services running
- [ ] No errors in logs
- [ ] Real data flowing in Kafka
- [ ] Grafana accessible
- [ ] Frontend displaying data

### **Verification:**
- [ ] No synthetic data in logs
- [ ] Real source fields in Kafka
- [ ] API calls succeeding
- [ ] Security features active
- [ ] Rate limiting working

---

## 📞 **SUPPORT**

**Documentation:**
- Setup: This file
- Architecture: `README.md`
- API Docs: http://localhost:8000/docs

**Logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f sentinel-api

# Errors only
docker-compose logs --tail=100 | grep -i error
```

**Status Check:**
```bash
# Services
docker-compose ps

# Health
curl http://localhost:8000/health

# Kafka topics
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

---

---

## IMPORTANT NOTICES

### This is a Proof-of-Concept:
- Developed for educational and demonstration purposes
- Not intended for production or operational deployment
- Not audited for security in critical environments
- Use at your own risk and responsibility

### Legal & Compliance:
- Use only for authorized and legitimate purposes
- Comply with all applicable laws and regulations
- Respect Terms of Service from all data providers
- Conduct proper security assessment before any deployment

### Origin:
This project started as a **personal idea** to create a demonstration platform that integrates various data sources and modern technologies. It's a learning project and portfolio showcase.

---

**STATUS: Proof-of-Concept Platform | Educational Purpose | Real-Time Data Demo**
