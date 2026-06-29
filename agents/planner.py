"""Investigation Planner Agent."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from models.incident import InvestigationRequest
from models.outputs import PlannerOutput


class PlannerAgent(BaseAgent):
    name = "planner"

    AGENT_SEQUENCE = [
        "jes_agent",
        "abend_agent",
        "jcl_agent",
        "cobol_agent",
        "db2_agent",
        "mq_agent",
        "scheduler_agent",
        "cics_agent",
        "guardrail_agent",
        "incident_agent",
        "runbook_agent",
    ]

    def analyze(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> dict[str, Any]:
        available_inputs = self._detect_inputs(request)
        priority_agents = self._prioritize_agents(available_inputs)
        severity = self._estimate_severity(available_inputs, request)
        focus_areas = self._identify_focus_areas(available_inputs)

        plan = PlannerOutput(
            investigation_plan=self.AGENT_SEQUENCE,
            priority_agents=priority_agents,
            estimated_severity=severity,
            focus_areas=focus_areas,
            rationale=(
                f"Investigation planned based on {len(available_inputs)} input artifacts. "
                f"Priority agents: {', '.join(priority_agents[:4])}. "
                f"Estimated severity: {severity}."
            ),
        )

        return {
            "analysis": plan.model_dump(),
            "confidence": 0.9,
            "available_inputs": available_inputs,
            "agent_sequence": self.AGENT_SEQUENCE,
        }

    def _detect_inputs(self, request: InvestigationRequest) -> dict[str, bool]:
        return {
            "jes_log": bool(request.jes_log.strip()),
            "sysout": bool(request.sysout.strip()),
            "abend_log": bool(request.abend_log.strip()),
            "jcl": bool(request.jcl.strip()),
            "cobol_source": bool(request.cobol_source.strip()),
            "db2_log": bool(request.db2_log.strip()),
            "mq_log": bool(request.mq_log.strip()),
            "cics_log": bool(request.cics_log.strip()),
            "scheduler_log": bool(request.scheduler_log.strip()),
        }

    def _prioritize_agents(self, inputs: dict[str, bool]) -> list[str]:
        priority: list[str] = ["jes_agent"]
        if inputs.get("abend_log") or inputs.get("sysout"):
            priority.append("abend_agent")
        if inputs.get("jcl"):
            priority.append("jcl_agent")
        if inputs.get("cobol_source"):
            priority.append("cobol_agent")
        if inputs.get("db2_log"):
            priority.append("db2_agent")
        if inputs.get("mq_log"):
            priority.append("mq_agent")
        if inputs.get("scheduler_log"):
            priority.append("scheduler_agent")
        if inputs.get("cics_log"):
            priority.append("cics_agent")
        priority.extend(["guardrail_agent", "incident_agent", "runbook_agent"])
        return priority

    def _estimate_severity(self, inputs: dict[str, bool], request: InvestigationRequest) -> str:
        combined = (
            request.jes_log + request.abend_log + request.sysout + request.db2_log
        ).upper()
        if any(code in combined for code in ["S0C4", "S0C7", "U0999", "-904", "-911"]):
            return "CRITICAL"
        if any(code in combined for code in ["S806", "S322", "-913", "AMQ9503"]):
            return "HIGH"
        if any(code in combined for code in ["S013", "-805", "AMQ9208"]):
            return "MEDIUM"
        return "LOW"

    def _identify_focus_areas(self, inputs: dict[str, bool]) -> list[str]:
        areas: list[str] = []
        mapping = {
            "jes_log": "JES job execution analysis",
            "abend_log": "ABEND root cause analysis",
            "jcl": "JCL validation and error detection",
            "cobol_source": "COBOL program impact analysis",
            "db2_log": "DB2 SQL error analysis",
            "mq_log": "MQ messaging failure analysis",
            "cics_log": "CICS transaction error analysis",
            "scheduler_log": "Scheduler dependency analysis",
        }
        for key, area in mapping.items():
            if inputs.get(key):
                areas.append(area)
        if not areas:
            areas.append("General incident triage")
        return areas
