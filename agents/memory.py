"""Investigation memory and persistence layer."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from config import get_settings
from models.incident import InvestigationRequest
from utils.logging_config import logger

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class InvestigationMemory:
    """Multi-tier memory: Redis cache, DuckDB analytics, SQLite metadata."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._redis: Any = None
        self._init_stores()

    def _init_stores(self) -> None:
        Path(self.settings.duckdb_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)

        self._duck = duckdb.connect(self.settings.duckdb_path)
        self._duck.execute("""
            CREATE TABLE IF NOT EXISTS investigations (
                incident_id VARCHAR PRIMARY KEY,
                job_name VARCHAR,
                application VARCHAR,
                severity VARCHAR,
                root_cause VARCHAR,
                confidence_score DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                report_json VARCHAR
            )
        """)

        self._sqlite = sqlite3.connect(self.settings.sqlite_path)
        self._sqlite.execute("""
            CREATE TABLE IF NOT EXISTS investigation_cache (
                incident_id TEXT PRIMARY KEY,
                state_json TEXT,
                updated_at TEXT
            )
        """)
        self._sqlite.commit()

        if self.settings.redis_enabled and REDIS_AVAILABLE:
            try:
                self._redis = redis.from_url(self.settings.redis_url, decode_responses=True)
                self._redis.ping()
            except Exception as exc:
                logger.warning("Redis unavailable: %s", exc)
                self._redis = None

    def cache_state(self, incident_id: str, state: dict[str, Any]) -> None:
        state_json = json.dumps(state, default=str)
        if self._redis:
            self._redis.setex(
                f"investigation:{incident_id}",
                self.settings.cache_ttl_seconds,
                state_json,
            )
        self._sqlite.execute(
            "INSERT OR REPLACE INTO investigation_cache (incident_id, state_json, updated_at) VALUES (?, ?, ?)",
            (incident_id, state_json, datetime.utcnow().isoformat()),
        )
        self._sqlite.commit()

    def get_cached_state(self, incident_id: str) -> dict[str, Any] | None:
        if self._redis:
            cached = self._redis.get(f"investigation:{incident_id}")
            if cached:
                return json.loads(cached)
        row = self._sqlite.execute(
            "SELECT state_json FROM investigation_cache WHERE incident_id = ?",
            (incident_id,),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def store_investigation(self, report: dict[str, Any]) -> None:
        analysis = report.get("analysis", report)
        self._duck.execute(
            """
            INSERT OR REPLACE INTO investigations
            (incident_id, job_name, application, severity, root_cause, confidence_score, report_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                analysis.get("incident_id", ""),
                analysis.get("affected_job", ""),
                analysis.get("application", ""),
                analysis.get("severity", ""),
                analysis.get("root_cause", ""),
                analysis.get("confidence_score", 0.0),
                json.dumps(analysis, default=str),
            ],
        )

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._duck.execute(
            "SELECT * FROM investigations ORDER BY created_at DESC LIMIT ?", [limit]
        ).fetchall()
        columns = ["incident_id", "job_name", "application", "severity", "root_cause", "confidence_score", "created_at", "report_json"]
        return [dict(zip(columns, row)) for row in rows]

    def close(self) -> None:
        self._duck.close()
        self._sqlite.close()


_memory: InvestigationMemory | None = None


def get_memory() -> InvestigationMemory:
    global _memory
    if _memory is None:
        _memory = InvestigationMemory()
    return _memory


def reset_memory() -> None:
    """Reset memory singleton (for tests)."""
    global _memory
    if _memory is not None:
        try:
            _memory.close()
        except Exception:
            pass
    _memory = None
