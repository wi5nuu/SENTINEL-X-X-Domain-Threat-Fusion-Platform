from src.intelligence.base import BaseIntelligenceModule
from typing import Dict, Any

class CBRNWatch(BaseIntelligenceModule):
    def __init__(self):
        super().__init__("CBRN-Watch")
        self.radiation_level = 0.0

    def ingest_data(self, data: Dict[str, Any]):
        self.radiation_level = data.get("rad_level", 0.0)
        if self.radiation_level > 50.0:
            self.status = "CRITICAL"
        else:
            self.status = "NOMINAL"

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status.update({"radiation_level": self.radiation_level})
        return status

class DarkFleetTracker(BaseIntelligenceModule):
    def __init__(self):
        super().__init__("Dark-Fleet-Tracker")
        self.ships_detected = 0

    def ingest_data(self, data: Dict[str, Any]):
        self.ships_detected = data.get("ships_detected", 0)
        self.status = "ACTIVE"

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status.update({"ships_detected": self.ships_detected})
        return status
