"""Run one synthetic tool-enabled request and print sanitized provider diagnostics."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents import RunConfig, Runner  # noqa: E402

from agent import build_copilot  # noqa: E402
from database.seed import seed_database  # noqa: E402
from security.auth import demo_actor  # noqa: E402


async def run_one(database: Path) -> None:
    await Runner.run(
        build_copilot(database, demo_actor()),
        [{"role": "user", "content": "Which products are low stock?"}],
        max_turns=2,
        run_config=RunConfig(
            tracing_disabled=True,
            trace_include_sensitive_data=False,
            workflow_name="BizPilot Gemini diagnostic",
        ),
    )


def main() -> int:
    database = ROOT / ".venv" / f"gemini-diagnostic-{uuid4().hex}.sqlite3"
    seed_database(database)
    try:
        asyncio.run(run_one(database))
        print(json.dumps({"ok": True, "stage": "tool_enabled_agent_request"}))
        return 0
    except Exception as exc:  # Provider exception types vary by SDK release.
        key = os.getenv("GEMINI_API_KEY", "")
        message = str(exc)
        if key:
            message = message.replace(key, "[REDACTED]")
        print(
            json.dumps(
                {
                    "ok": False,
                    "stage": "tool_enabled_agent_request",
                    "error_type": type(exc).__name__,
                    "status_code": getattr(exc, "status_code", None),
                    "error_code": getattr(exc, "code", None),
                    "sanitized_message": message[:1500],
                },
                ensure_ascii=False,
            )
        )
        return 1
    finally:
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(f"{database}{suffix}")
            if candidate.exists():
                candidate.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
