"""Scheduler Log Analysis Agent (CA-7, Control-M, TWS)."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from models.incident import InvestigationRequest
from models.outputs import SchedulerAnalysis
from utils.parsers import parse_scheduler_log


class SchedulerAgent(BaseAgent):
    name = "scheduler_agent"

    def analyze(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> dict[str, Any]:
        log_text = self.get_log_content(request, "scheduler_log") or self.get_log_content(request, "jes_log")
        if not log_text.strip():
            return {"analysis": SchedulerAnalysis().model_dump(), "confidence": 0.0, "skipped": True}

        parsed = parse_scheduler_log(log_text)
        analysis = SchedulerAnalysis()

        if parsed.get("ca7"):
            analysis.scheduler_type = "CA-7"
        elif parsed.get("controlm"):
            analysis.scheduler_type = "Control-M"
        elif parsed.get("tws"):
            analysis.scheduler_type = "TWS/OPC"
        else:
            analysis.scheduler_type = "Unknown"

        import re

        job_fail = re.compile(
            r"(?:JOB|JNAME)[=\s]+(\S+).*(?:FAILED|ABEND|RC\s*[>=]\s*8|STATUS=FAILED)",
            re.IGNORECASE,
        )
        for match in job_fail.finditer(log_text):
            analysis.failed_jobs.append(match.group(1))

        late = re.compile(r"(?:LATE|SLA)\s+.*?(?:JOB|JNAME)\s+(\S+)", re.IGNORECASE)
        for match in late.finditer(log_text):
            analysis.late_jobs.append(match.group(1))

        dep_fail = re.compile(
            r"(?:DEPENDENCY|PREDECESSOR)\s+(\S+).*(?:NOT\s+MET|FAILED|INCOMPLETE)",
            re.IGNORECASE,
        )
        for match in dep_fail.finditer(log_text):
            analysis.dependency_failures.append(match.group(1))

        if "CIRCULAR" in log_text.upper():
            analysis.circular_dependencies.append("Circular dependency detected in job network")

        if analysis.failed_jobs:
            analysis.restart_chain = [
                f"1. Resolve root cause for {analysis.failed_jobs[0]}",
                f"2. Force-complete or bypass dependent jobs if approved",
                f"3. Restart {analysis.failed_jobs[0]} from failing step",
                "4. Monitor downstream dependency chain",
            ]
            analysis.recommendations.append(
                f"Restart job {analysis.failed_jobs[0]} after root cause resolution"
            )

        if analysis.late_jobs:
            analysis.recommendations.append(
                f"SLA at risk for {', '.join(analysis.late_jobs[:3])}. Consider parallel processing."
            )

        confidence = 0.8 if analysis.scheduler_type != "Unknown" else 0.5
        return {"analysis": analysis.model_dump(), "confidence": confidence, "parsed": parsed}
