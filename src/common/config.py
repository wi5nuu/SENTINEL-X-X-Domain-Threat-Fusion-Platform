from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://sentinel:sentinel_pass@postgres:5432/sentinel"
    redis_url: str = "redis://redis:6379/0"
    kafka_bootstrap_servers: str = "kafka:9092"
    elasticsearch_url: str = "http://elasticsearch:9200"
    ethereum_rpc_url: str = "http://hardhat-node:8545"
    ethereum_private_key: Optional[str] = None
    ipfs_rpc_url: str = "http://ipfs:5001"
    jwt_secret_key: str = "change-me-to-a-secure-random-string"
    
    # Security Settings
    enable_synthetic_data: bool = False
    enable_data_encryption: bool = True
    api_key_rotation_hours: int = 24
    max_api_rate_limit: int = 1000
    
    # Aviation Data Sources
    opensky_username: Optional[str] = None
    opensky_password: Optional[str] = None
    opensky_api_url: str = "https://opensky-network.org/api"
    aeroapi_key: Optional[str] = None
    aeroapi_url: str = "https://aeroapi.flightaware.com/aeroapi"
    adsb_exchange_api_key: Optional[str] = None
    adsb_exchange_url: str = "https://adsbexchange-com1.p.rapidapi.com"
    
    # Maritime Data Sources
    marinetraffic_api_key: Optional[str] = None
    marinetraffic_url: str = "https://services.marinetraffic.com/api"
    vesselfinder_api_key: Optional[str] = None
    vesselfinder_url: str = "https://api.vesselfinder.com"
    aishub_username: Optional[str] = None
    aishub_url: str = "http://data.aishub.net"
    
    # Cyber Threat Intelligence
    otx_api_key: Optional[str] = None
    otx_api_url: str = "https://otx.alienvault.com/api/v1"
    abuseipdb_key: Optional[str] = None
    abuseipdb_url: str = "https://api.abuseipdb.com/api/v2"
    shodan_key: Optional[str] = None
    shodan_url: str = "https://api.shodan.io"
    virustotal_api_key: Optional[str] = None
    virustotal_url: str = "https://www.virustotal.com/api/v3"
    threatfox_api_key: Optional[str] = None
    threatfox_url: str = "https://threatfox-api.abuse.ch/api/v1"
    
    # Seismic Data Sources
    usgs_api_url: str = "https://earthquake.usgs.gov/earthquakes/feed/v1.0"
    emsc_api_url: str = "https://www.seismicportal.eu/fdsnws/event/1"
    
    # NASA Space Weather
    nasa_api_key: Optional[str] = None
    nasa_eonet_url: str = "https://eonet.gsfc.nasa.gov/api/v3"
    nasa_donki_url: str = "https://api.nasa.gov/DONKI"
    
    # Weather Data
    openweather_api_key: Optional[str] = None
    openweather_url: str = "https://api.openweathermap.org/data/2.5"
    
    # Notifications
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_number: Optional[str] = None
    sendgrid_api_key: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    
    # System
    database_password: Optional[str] = None
    grafana_password: Optional[str] = None
    model_path: str = "/models/threat_fusion_v1.pt"
    ingestor_type: str = "air"
    
    # Data Retention
    data_retention_days: int = 90
    alert_retention_days: int = 365
    log_retention_days: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
