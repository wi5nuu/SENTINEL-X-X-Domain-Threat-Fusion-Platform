import abc
from datetime import datetime
from typing import Dict, Any

class BaseIntelligenceModule(abc.ABC):
    def __init__(self, name: str):
        self.name = name
        self.last_update = datetime.utcnow()
        self.status = "NOMINAL"

    @abc.abstractmethod
    def ingest_data(self, data: Dict[str, Any]):
        pass

    @abc.abstractmethod
    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "last_update": self.last_update.isoformat()
        }
