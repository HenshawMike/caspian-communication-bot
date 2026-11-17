#!/usr/bin/env python3
"""Container healthcheck script for Docker and cloud monitoring."""

import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import database.connection


def check_health(manager=None) -> int:
    """Evaluate database connectivity and background runner liveness."""
    try:
        mgr = manager or database.connection.db_manager
        # 1. Database responsiveness check
        with mgr.connection() as conn:
            cur = conn.execute("SELECT 1;")
            val = cur.fetchone()[0]
            if val != 1:
                print("HEALTHCHECK FAILED: Database ping returned unexpected value.", file=sys.stderr)
                return 1

            # 2. Check heartbeat record if exists
            cur = conn.execute("SELECT value FROM system_settings WHERE key = 'health_heartbeat' LIMIT 1;")
            row = cur.fetchone()
            if row:
                try:
                    payload = json.loads(row[0])
                    hb_time = datetime.fromisoformat(payload.get("timestamp"))
                    now = datetime.now(timezone.utc)
                    # Heartbeat must be within 10 minutes
                    if now - hb_time > timedelta(minutes=10):
                        print(f"HEALTHCHECK WARNING: Heartbeat stale ({hb_time}).", file=sys.stderr)
                        return 1
                except Exception as pe:
                    print(f"HEALTHCHECK WARNING: Heartbeat parsing error: {pe}", file=sys.stderr)

        print("HEALTHCHECK OK: Database and system responsive.")
        return 0

    except Exception as e:
        print(f"HEALTHCHECK FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(check_health())
