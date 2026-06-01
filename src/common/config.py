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
    opensky_username: Optional[str] = None
    opensky_password: Optional[str] = None
    otx_api_key: Optional[str] = None
    abuseipdb_key: Optional[str] = None
    shodan_key: Optional[str] = None
    aeroapi_key: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_number: Optional[str] = None
    sendgrid_api_key: Optional[str] = None
    model_path: str = "/models/threat_fusion_v1.pt"
    ingestor_type: str = "air"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
