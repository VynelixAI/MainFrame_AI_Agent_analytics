"""Structured logging configuration."""

from __future__ import annotations

import logging
import sys
from typing import Any

from config import get_settings


def setup_logging() -> logging.Logger:
    settings = get_settings()
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s | "
        "%(funcName)s:%(lineno)d | %(message)s"
    )
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("mainframe_copilot")


logger = setup_logging()


def log_agent_execution(agent_name: str, duration_ms: float, success: bool, **kwargs: Any) -> None:
    logger.info(
        "Agent execution | agent=%s duration_ms=%.2f success=%s extra=%s",
        agent_name,
        duration_ms,
        success,
        kwargs,
    )
