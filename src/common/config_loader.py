import os
from typing import Any, Dict
import yaml

from src.common.logging import setup_logging

logger = setup_logging("config-loader")


def load_domain_config(path: str = "config/domains.yaml") -> Dict[str, Any]:
    if not os.path.exists(path):
        logger.warning(f"Domain config not found at {path}, using defaults")
        return _default_config()

    with open(path) as f:
        config = yaml.safe_load(f)

    logger.info(f"Domain config loaded from {path}")
    return config


def _default_config() -> Dict[str, Any]:
    return {
        "domains": {
            "air": {"enabled": True, "poll_interval_seconds": 5},
            "maritime": {"enabled": True, "poll_interval_seconds": 10},
            "seismic": {"enabled": True, "usgs_poll_seconds": 60},
            "rf": {"enabled": True, "scan_interval_seconds": 1},
            "cyber": {"enabled": True, "otx_poll_seconds": 300},
        }
    }


domain_config = load_domain_config()
