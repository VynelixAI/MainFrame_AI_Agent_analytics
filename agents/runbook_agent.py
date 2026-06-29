"""Runbook Recommendation Agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from config import KNOWLEDGE_DIR
from models.incident import InvestigationRequest
from models.outputs import RunbookRecommendation


class RunbookAgent(BaseAgent):
    name = "runbook_agent"

    RUNBOOK_MAP: dict[str, str] = {
        "S0C4": "RB-ABEND-S0C4",
        "S0C7": "RB-ABEND-S0C7",
        "S0C1": "RB-ABEND-S0C1",
        "S806": "RB-ABEND-S806",
        "S322": "RB-JCL-TIMEOUT",
        "U0999": "RB-APP-USER-ABEND",
        "-911": "RB-DB2-DEADLOCK",
        "-913": "RB-DB2-LOCKTIMEOUT",
        "-805": "RB-DB2-BIND",
        "AMQ9503": "RB-MQ-QUEUE-FULL",
        "AMQ9208": "RB-MQ-CHANNEL",
        "AEI0": "RB-CICS-ABEND",
        "APCT": "RB-CICS-PROG-NOT-FOUND",
    }

    def analyze(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        abend = self._get_inner(context, "abend_analysis")
        db2 = self._get_inner(context, "db2_analysis")
        mq = self._get_inner(context, "mq_analysis")
        cics = self._get_inner(context, "cics_analysis")

        runbook_id = self._select_runbook(abend, db2, mq, cics)
        runbook_content = self._load_runbook(runbook_id)
        incident = self._get_inner(context, "incident_report")

        recommendation = RunbookRecommendation(
            runbook_id=runbook_id,
            title=runbook_content.get("title", f"Runbook {runbook_id}"),
            steps=runbook_content.get("steps", self._default_steps(abend)),
            commands=runbook_content.get("commands", incident.get("commands", [])),
            validation_steps=runbook_content.get("validation", incident.get("validation_steps", [])),
            preventive_measures=runbook_content.get("preventive", incident.get("preventive_measures", [])),
            source="knowledge_base" if runbook_content else "generated",
        )

        return {"analysis": recommendation.model_dump(), "confidence": 0.8, "runbook_id": runbook_id}

    def _get_inner(self, context: dict[str, Any], key: str) -> dict[str, Any]:
        data = context.get(key, {})
        if isinstance(data, dict) and "analysis" in data:
            return data["analysis"]
        return data if isinstance(data, dict) else {}

    def _select_runbook(self, abend: dict, db2: dict, mq: dict, cics: dict) -> str:
        if abend.get("abend_code"):
            return self.RUNBOOK_MAP.get(abend["abend_code"].upper(), "RB-GENERAL-ABEND")
        for code in db2.get("sqlcodes", []):
            key = str(code)
            if key in self.RUNBOOK_MAP:
                return self.RUNBOOK_MAP[key]
        for code in mq.get("mqrc_codes", []):
            if code.upper() in self.RUNBOOK_MAP:
                return self.RUNBOOK_MAP[code.upper()]
        for code in cics.get("resp_codes", []):
            if code.upper() in self.RUNBOOK_MAP:
                return self.RUNBOOK_MAP[code.upper()]
        return "RB-GENERAL-INCIDENT"

    def _load_runbook(self, runbook_id: str) -> dict[str, Any]:
        runbook_dir = KNOWLEDGE_DIR / "RUNBOOKS"
        for ext in [".md", ".txt"]:
            path = runbook_dir / f"{runbook_id}{ext}"
            if path.exists():
                return self._parse_runbook(path.read_text())
        return {}

    def _parse_runbook(self, content: str) -> dict[str, Any]:
        lines = content.strip().splitlines()
        result: dict[str, Any] = {"title": "", "steps": [], "commands": [], "validation": [], "preventive": []}
        section = "steps"
        for line in lines:
            if line.startswith("# "):
                result["title"] = line[2:].strip()
            elif line.startswith("## Steps"):
                section = "steps"
            elif line.startswith("## Commands"):
                section = "commands"
            elif line.startswith("## Validation"):
                section = "validation"
            elif line.startswith("## Preventive"):
                section = "preventive"
            elif line.strip().startswith(("-", "1.", "2.", "3.", "4.", "5.")):
                result[section].append(line.strip().lstrip("- ").lstrip("0123456789. "))
        return result

    def _default_steps(self, abend: dict) -> list[str]:
        code = abend.get("abend_code", "UNKNOWN")
        return [
            f"1. Acknowledge incident for ABEND {code}",
            "2. Collect SYSOUT, JES log, and dump datasets",
            "3. Analyze root cause using AI copilot findings",
            "4. Apply corrective action per recovery recommendations",
            "5. Obtain approval for job restart",
            "6. Restart job and validate completion",
            "7. Update incident ticket and runbook",
        ]
