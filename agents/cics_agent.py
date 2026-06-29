"""CICS Error Analysis Agent."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from models.incident import InvestigationRequest
from models.outputs import CICSAnalysis
from utils.parsers import parse_cics_log

CICS_ABEND_KNOWLEDGE: dict[str, dict[str, str]] = {
    "AEI0": {
        "desc": "Transaction abend - program check in application code",
        "recovery": "Review CICS dump. Check program linkage and COMMAREA length.",
    },
    "AEY9": {
        "desc": "Transaction abend - runaway task killed",
        "recovery": "Review transaction timeout settings. Check for infinite loop in program.",
    },
    "APCT": {
        "desc": "Program not found - transaction definition references missing program",
        "recovery": "Verify program is defined in CSD. Check RDO group installation.",
    },
    "AICA": {
        "desc": "Runaway task - exceeded maximum execution time",
        "recovery": "Increase RUNAWAY limit if justified. Optimize program logic.",
    },
    "AKCP": {
        "desc": "Task was purged by operator or system",
        "recovery": "Review purge reason. Check CICS system log for preceding errors.",
    },
}

RESP_KNOWLEDGE: dict[str, str] = {
    "RESP(13)": "NOTFND - Record not found in file",
    "RESP(14)": "DUPKEY - Duplicate key on WRITE",
    "RESP(16)": "INVREQ - Invalid request for file state",
    "RESP(19)": "FILENOTFOUND - File not defined in FCT",
    "RESP(1)": "NORMAL - Successful operation",
}


class CICSAgent(BaseAgent):
    name = "cics_agent"

    def analyze(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> dict[str, Any]:
        log_text = self.get_log_content(request, "cics_log") or self.get_log_content(request, "sysout")
        if not log_text.strip():
            return {"analysis": CICSAnalysis().model_dump(), "confidence": 0.0, "skipped": True}

        parsed = parse_cics_log(log_text)
        analysis = CICSAnalysis()

        analysis.transactions = parsed.get("transaction", [])
        abend_codes = parsed.get("abend", [])
        resp_codes = parsed.get("resp", [])

        for code in abend_codes:
            upper = code.upper()
            analysis.resp_codes.append(upper)
            knowledge = CICS_ABEND_KNOWLEDGE.get(upper, {})
            if knowledge:
                analysis.explanations.append(f"{upper}: {knowledge['desc']}")
                analysis.recovery_steps.append(knowledge["recovery"])
            if upper == "APCT":
                analysis.program_not_found.append(f"Program not found for transaction")

        for resp in resp_codes:
            key = f"RESP({resp})"
            desc = RESP_KNOWLEDGE.get(key, f"RESP code {resp}")
            analysis.explanations.append(desc)
            if resp in ("13", "14", "16", "19"):
                analysis.file_status_errors.append(desc)

        import re

        region = re.compile(r"REGION\s+(\S+).*(?:DOWN|STOPPED|ABEND)", re.IGNORECASE)
        for match in region.finditer(log_text):
            analysis.region_issues.append(match.group(0))

        confidence = 0.85 if abend_codes or resp_codes else 0.45
        return {"analysis": analysis.model_dump(), "confidence": confidence, "parsed": parsed}
