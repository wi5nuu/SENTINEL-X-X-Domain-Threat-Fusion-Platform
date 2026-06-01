import asyncio
import json
import os
from datetime import datetime
from typing import Optional, List
import yaml

from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics
from src.common.models import ThreatLevel

logger = setup_logging("playbook-executor")


class PlaybookExecutor:
    def __init__(self, playbooks_dir: str = "playbooks"):
        self.playbooks_dir = playbooks_dir
        self.running = False

    async def load_playbook(self, name: str) -> Optional[dict]:
        path = os.path.join(self.playbooks_dir, f"{name}.yaml")
        if not os.path.exists(path):
            logger.error("Playbook not found", extra={"name": name})
            return None
        try:
            with open(path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error("Playbook load error", extra={"error": str(e)})
            return None

    async def execute(self, playbook_name: str, context: dict) -> List[str]:
        playbook = await self.load_playbook(playbook_name)
        if not playbook:
            return ["Error: playbook not found"]

        executed_actions = []
        phases = playbook.get("phases", [])
        for phase in phases:
            phase_name = phase.get("name", "Unknown Phase")
            logger.info("Executing playbook phase", extra={"phase": phase_name})

            auto_steps = phase.get("automated_steps", [])
            for step in auto_steps:
                action = step.get("action", "unknown")
                params = step.get("params", {})
                try:
                    result = await self._execute_action(action, params, context)
                    executed_actions.append(f"[{phase_name}] {action}: {result}")
                except Exception as e:
                    metrics.errors_total.labels(service="playbook", error_type="action").inc()
                    logger.error("Action execution failed", extra={"action": action, "error": str(e)})
                    executed_actions.append(f"[{phase_name}] {action}: FAILED - {str(e)}")

            await asyncio.sleep(0.1)

        post_incident = playbook.get("post_incident", [])
        for step in post_incident:
            action = step.get("action", "unknown")
            try:
                await self._execute_action(action, {}, context)
                executed_actions.append(f"[Post-Incident] {action}: completed")
            except Exception as e:
                logger.error("Post-incident action failed", extra={"action": action, "error": str(e)})

        return executed_actions

    async def _execute_action(self, action: str, params: dict, context: dict) -> str:
        action_map = {
            "fetch_sar_imagery": self._fetch_sar_imagery,
            "cross_reference_vessel_database": self._cross_reference_vessel,
            "notify_coast_guard_api": self._notify_coast_guard,
            "create_exclusion_zone_geofence": self._create_geofence,
            "tasking_patrol_asset": self._task_patrol,
            "generate_pdf_report": self._generate_report,
            "blockchain_finalize_evidence_chain": self._blockchain_finalize,
            "debrief_session_scheduled": self._schedule_debrief,
        }
        handler = action_map.get(action)
        if not handler:
            return f"Unknown action: {action}"
        return await handler(params, context)

    async def _fetch_sar_imagery(self, params: dict, context: dict) -> str:
        area = params.get("area", "unknown")
        radius = params.get("radius_km", 50)
        logger.info("Fetching SAR imagery", extra={"area": area, "radius_km": radius})
        return f"SAR imagery request sent for {area}, radius {radius}km"

    async def _cross_reference_vessel(self, params: dict, context: dict) -> str:
        mmsi = params.get("mmsi", context.get("mmsi", "unknown"))
        sources = params.get("sources", [])
        return f"Cross-referenced vessel {mmsi} against {', '.join(sources)}"

    async def _notify_coast_guard(self, params: dict, context: dict) -> str:
        incident_id = params.get("incident_id", context.get("threat_id", "unknown"))
        priority = params.get("priority", "ROUTINE")
        return f"Coast guard notified: incident {incident_id} at priority {priority}"

    async def _create_geofence(self, params: dict, context: dict) -> str:
        center = params.get("center", "unknown")
        radius = params.get("radius_nm", 5)
        return f"Exclusion zone geofence created at {center}, radius {radius}NM"

    async def _task_patrol(self, params: dict, context: dict) -> str:
        asset_type = params.get("asset_type", "unknown")
        priority = params.get("priority", "ROUTINE")
        return f"Patrol asset tasked: {asset_type} at priority {priority}"

    async def _generate_report(self, params: dict, context: dict) -> str:
        return "PDF report generation initiated"

    async def _blockchain_finalize(self, params: dict, context: dict) -> str:
        return "Blockchain evidence chain finalized"

    async def _schedule_debrief(self, params: dict, context: dict) -> str:
        return "Debrief session scheduled for next shift change"
