"""Base agent class for all specialized agents."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from models.incident import AgentResult, InvestigationRequest
from utils.llm_client import get_llm_client
from utils.logging_config import log_agent_execution, logger
from utils.telemetry import trace_span


class BaseAgent(ABC):
    """Abstract base for mainframe investigation agents."""

    name: str = "base_agent"

    def __init__(self) -> None:
        self.llm = get_llm_client()

    @abstractmethod
    def analyze(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform agent-specific analysis."""

    def run(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> AgentResult:
        start = time.perf_counter()
        try:
            with trace_span(f"agent.{self.name}", {"incident_id": request.incident_id}):
                findings = self.analyze(request, context or {})
            duration_ms = (time.perf_counter() - start) * 1000
            confidence = findings.get("confidence", 0.75)
            result = AgentResult(
                agent_name=self.name,
                success=True,
                confidence=confidence,
                findings=findings,
                duration_ms=duration_ms,
            )
            log_agent_execution(self.name, duration_ms, True)
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception("Agent %s failed: %s", self.name, exc)
            log_agent_execution(self.name, duration_ms, False, error=str(exc))
            return AgentResult(
                agent_name=self.name,
                success=False,
                confidence=0.0,
                errors=[str(exc)],
                duration_ms=duration_ms,
            )

    def get_log_content(self, request: InvestigationRequest, field: str) -> str:
        return getattr(request, field, "") or ""
