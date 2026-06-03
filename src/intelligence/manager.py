from src.intelligence.base import BaseIntelligenceModule
from typing import Dict

class IntelligenceManager:
    def __init__(self):
        self.modules: Dict[str, BaseIntelligenceModule] = {}

    def register_module(self, module: BaseIntelligenceModule):
        self.modules[module.name] = module

    def get_all_status(self):
        return {name: mod.get_status() for name, mod in self.modules.items()}

intelligence_manager = IntelligenceManager()
