"""JES Log Analysis Agent."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from models.incident import InvestigationRequest
from models.outputs import JESAnalysis
from utils.parsers import parse_jes_log


class JESAgent(BaseAgent):
    name = "jes_agent"

    def analyze(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> dict[str, Any]:
        log_text = self.get_log_content(request, "jes_log") or self.get_log_content(request, "sysout")
        if not log_text.strip():
            return {"analysis": JESAnalysis().model_dump(), "confidence": 0.0, "skipped": True}

        parsed = parse_jes_log(log_text)
        analysis = JESAnalysis()

        if parsed.get("job_name"):
            parts = parsed["job_name"][0].split()
            analysis.job_name = parts[0] if parts else request.job_name
            analysis.job_id = parts[1] if len(parts) > 1 else ""

        if parsed.get("step_rc"):
            step_info = parsed["step_rc"][-1].split()
            if len(step_info) >= 3:
                analysis.step_name = step_info[1]
                analysis.return_code = int(step_info[2])

        if parsed.get("cpu_time"):
            analysis.cpu_time = parsed["cpu_time"][-1].split()[-1] if parsed["cpu_time"] else ""
        if parsed.get("elapsed"):
            analysis.elapsed_time = parsed["elapsed"][-1].split()[-1] if parsed["elapsed"] else ""

        analysis.dataset_allocations = parsed.get("dataset_alloc", [])
        analysis.missing_datasets = parsed.get("missing_ds", []) + parsed.get("dataset_error", [])
        analysis.security_errors = parsed.get("security", [])
        analysis.messages = (
            parsed.get("volume_error", [])
            + parsed.get("csv_error", [])
            + parsed.get("space_error", [])
        )

        abend_codes = ["S0C4", "S0C7", "S0C1", "S806", "S322", "U0999"]
        for code in abend_codes:
            if code in log_text.upper():
                analysis.abend_detected = True
                analysis.abend_code = code
                break

        if analysis.return_code and analysis.return_code >= 8:
            analysis.restart_recommendation = (
                f"Job {analysis.job_name} failed with RC={analysis.return_code}. "
                "Review failing step SYSOUT before restart. Use scheduler HOLD/RELEASE "
                "or JCL COND parameter to restart from failing step."
            )
        elif analysis.missing_datasets:
            analysis.restart_recommendation = (
                "Resolve missing dataset allocations before restart. "
                "Verify catalog entries and GDG generations."
            )
        elif analysis.security_errors:
            analysis.restart_recommendation = (
                "Contact security team to resolve RACF/ACF2 authorization. "
                "Do not restart until ICH408I is resolved."
            )
        else:
            analysis.restart_recommendation = "No restart required. Job completed normally."

        confidence = 0.85 if analysis.job_name else 0.5
        return {"analysis": analysis.model_dump(), "confidence": confidence, "parsed": parsed}
