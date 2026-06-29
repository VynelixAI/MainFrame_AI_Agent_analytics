"""Application configuration with environment-based settings."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
LOGS_DIR = BASE_DIR / "logs"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
VECTOR_STORE_DIR = BASE_DIR / "data" / "vector_store"
INCIDENT_DB_PATH = BASE_DIR / "data" / "incidents.duckdb"
SQLITE_PATH = BASE_DIR / "data" / "copilot.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Mainframe AI Operations Copilot"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1"
    openai_temperature: float = 0.1
    openai_max_tokens: int = 4096
    llm_fallback_enabled: bool = True

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Vector stores
    vector_store_backend: Literal["faiss", "chroma"] = "faiss"
    chroma_persist_dir: str = str(VECTOR_STORE_DIR / "chroma")
    faiss_index_path: str = str(VECTOR_STORE_DIR / "faiss.index")

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = True
    cache_ttl_seconds: int = 3600

    # Database
    duckdb_path: str = str(INCIDENT_DB_PATH)
    sqlite_path: str = str(SQLITE_PATH)

    # Guardrails
    confidence_threshold: float = 0.65
    require_human_approval_for_restart: bool = True
    pii_masking_enabled: bool = True
    prompt_injection_detection: bool = True
    block_destructive_commands: bool = True

    # Observability
    otel_enabled: bool = True
    otel_service_name: str = "mainframe-ai-copilot"
    otel_exporter_endpoint: str = "http://localhost:4317"
    prometheus_port: int = 9090
    log_level: str = "INFO"

    # Investigation
    max_agent_retries: int = 2
    investigation_timeout_seconds: int = 300

    @property
    def llm_available(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_directories() -> None:
    """Create required runtime directories."""
    for path in [
        KNOWLEDGE_DIR,
        LOGS_DIR,
        SAMPLE_DATA_DIR,
        VECTOR_STORE_DIR,
        BASE_DIR / "data",
        BASE_DIR / "reports",
    ]:
        path.mkdir(parents=True, exist_ok=True)
    for sub in ["jes", "sysout", "abend", "scheduler", "mq", "cics", "db2"]:
        (LOGS_DIR / sub).mkdir(parents=True, exist_ok=True)
    for sub in ["JCL", "COBOL", "ABEND", "RUNBOOKS", "DB2", "MQ", "CICS"]:
        (KNOWLEDGE_DIR / sub).mkdir(parents=True, exist_ok=True)
