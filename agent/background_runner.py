"""Background polling worker for automated briefings and publishing schedules."""

import json
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from agent.config import settings
from agent.logging_config import logger
from agent.permissions import PermissionContext, PermissionScope
from agent.tool_executor import executor as default_executor
from agent.orchestrator import orchestrator
from database.models import (
    get_latest_daily_briefing,
    set_system_setting,
    get_system_setting,
)


class BackgroundRunner:
    """Continuous background worker managing scheduled intelligence sweeps and publication queues."""

    def __init__(
        self,
        poll_interval_seconds: int = 60,
        briefing_hour_utc: int = 8,
        health_file_path: Optional[Path] = None,
    ):
        self.poll_interval = poll_interval_seconds
        self.briefing_hour_utc = briefing_hour_utc
        self.health_file_path = health_file_path or (settings.base_dir / "data" / "health.json")
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._ensure_health_dir()

    def _ensure_health_dir(self) -> None:
        if not self.health_file_path.parent.exists():
            try:
                self.health_file_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.warning(f"Failed to create health directory: {e}")

    def update_heartbeat(self, status: str = "HEALTHY", error_msg: Optional[str] = None) -> None:
        """Write liveness heartbeat to database and health.json for Docker healthchecks."""
        now_iso = datetime.now(timezone.utc).isoformat()
        heartbeat_payload = {
            "status": status,
            "timestamp": now_iso,
            "error": error_msg,
            "pid": threading.get_native_id() if hasattr(threading, "get_native_id") else None,
        }

        # 1. Update database system_settings
        try:
            set_system_setting(
                "health_heartbeat",
                json.dumps(heartbeat_payload),
                description="Background worker liveness heartbeat",
            )
        except Exception as dbe:
            logger.warning(f"Database heartbeat update warning: {dbe}")

        # 2. Write quick health file
        try:
            self._ensure_health_dir()
            with open(self.health_file_path, "w", encoding="utf-8") as f:
                json.dump(heartbeat_payload, f, indent=2)
        except Exception as fe:
            logger.warning(f"Health file update warning: {fe}")

    def check_and_execute_schedules(self, context: Optional[PermissionContext] = None) -> Dict[str, Any]:
        """Check active publishing schedule and execute queued releases."""
        perm_ctx = context or PermissionContext(
            user_id="system_background_worker",
            active_skill="content_publishing",
        )
        perm_ctx.add_scope(PermissionScope.CONTENT_PUBLISH)
        perm_ctx.add_scope(PermissionScope.KNOWLEDGE_READ)

        res = default_executor.execute("execute_schedule", {}, context=perm_ctx)
        if res.success and res.data.get("published_count", 0) > 0:
            logger.info(f"Background worker published {res.data['published_count']} queued posts.")
        return res.data if res.success else {"published_count": 0, "error": res.error.message if res.error else "Failed"}

    def check_and_generate_daily_briefing(self, context: Optional[PermissionContext] = None) -> Optional[Dict[str, Any]]:
        """Trigger daily AI intelligence briefing if due for today."""
        now_utc = datetime.now(timezone.utc)
        today_str = now_utc.strftime("%Y-%m-%d")

        # Check hour
        if now_utc.hour < self.briefing_hour_utc:
            return None

        # Check if already generated today
        latest = get_latest_daily_briefing()
        if latest and latest.get("briefing_date") == today_str:
            return None

        logger.info(f"Scheduled briefing trigger: generating daily AI intelligence for {today_str}...")
        perm_ctx = context or PermissionContext(
            user_id="system_background_worker",
            active_skill="daily_briefing",
        )
        perm_ctx.add_scope(PermissionScope.EXTERNAL_READ)
        perm_ctx.add_scope(PermissionScope.KNOWLEDGE_READ)
        perm_ctx.add_scope(PermissionScope.KNOWLEDGE_WRITE)

        briefing_res = orchestrator.execute_daily_briefing_workflow(perm_ctx)
        logger.info(f"Daily briefing for {today_str} successfully completed.")
        return briefing_res

    def run_once(self) -> Dict[str, Any]:
        """Execute a single evaluation pass across all background tasks."""
        results = {
            "schedule": None,
            "briefing": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            results["schedule"] = self.check_and_execute_schedules()
            results["briefing"] = self.check_and_generate_daily_briefing()
            self.update_heartbeat(status="HEALTHY")
        except Exception as e:
            logger.error(f"Error during background pass: {e}")
            self.update_heartbeat(status="DEGRADED", error_msg=str(e))
            results["error"] = str(e)

        return results

    def _loop(self) -> None:
        """Continuous polling execution loop."""
        logger.info(f"Background runner thread started. Polling every {self.poll_interval}s.")
        while self._running:
            self.run_once()
            # Sleep with short intervals to allow responsive shutdown
            for _ in range(self.poll_interval):
                if not self._running:
                    break
                time.sleep(1)
        logger.info("Background runner thread stopped cleanly.")

    def start(self) -> None:
        """Start background runner in a daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="CaspianBackgroundRunner")
        self._thread.start()

    def stop(self) -> None:
        """Stop background runner."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._thread = None


# Global background runner singleton
background_runner = BackgroundRunner()
