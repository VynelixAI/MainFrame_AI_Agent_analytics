"""COBOL Source Analysis Agent."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from models.incident import InvestigationRequest
from models.outputs import COBOLAnalysis
from utils.parsers import parse_cobol

DOMAIN_PURPOSES: dict[str, str] = {
    "CLM": "Claims processing and adjudication",
    "BIL": "Billing and invoicing operations",
    "PAY": "Payment processing and disbursement",
    "POL": "Policy administration and maintenance",
    "CUS": "Customer master data management",
    "ENR": "Member enrollment and eligibility",
    "INV": "Inventory management and tracking",
    "PRL": "Payroll calculation and reporting",
    "FIN": "Financial reporting and GL posting",
    "HLT": "Healthcare claims and benefits administration",
}


class COBOLAgent(BaseAgent):
    name = "cobol_agent"

    def analyze(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> dict[str, Any]:
        source = self.get_log_content(request, "cobol_source")
        if not source.strip():
            return {"analysis": COBOLAnalysis().model_dump(), "confidence": 0.0, "skipped": True}

        parsed = parse_cobol(source)
        analysis = COBOLAnalysis()

        if parsed.get("program_id"):
            analysis.program_name = parsed["program_id"][0].rstrip(".")
        else:
            analysis.program_name = request.job_name or "UNKNOWN"

        prefix = analysis.program_name[:3].upper()
        analysis.business_purpose = DOMAIN_PURPOSES.get(
            prefix, f"Enterprise batch application module {analysis.program_name}"
        )

        analysis.input_files = [f"SELECT {s}" for s in parsed.get("select", []) if "OUT" not in s.upper()]
        analysis.output_files = parsed.get("select", [])
        analysis.call_hierarchy = parsed.get("call", [])
        analysis.perform_hierarchy = list(dict.fromkeys(parsed.get("perform", [])))
        analysis.paragraphs = parsed.get("paragraph", [])[:50]

        if parsed.get("exec_sql") or "EXEC SQL" in source.upper():
            tables = parsed.get("table", [])
            analysis.db2_tables = list(dict.fromkeys(tables))[:20]

        analysis.key_variables = self._extract_variables(source)
        analysis.impacted_modules = analysis.call_hierarchy + [
            p for p in analysis.paragraphs if "ERROR" in p.upper() or "ABEND" in p.upper()
        ]

        analysis.explanation = (
            f"Program {analysis.program_name} is a {analysis.business_purpose.lower()} module. "
            f"It contains {len(analysis.paragraphs)} paragraphs, "
            f"{len(analysis.call_hierarchy)} external calls, and "
            f"{'DB2 SQL access' if analysis.db2_tables else 'no DB2 dependencies'}."
        )

        confidence = 0.8 if analysis.program_name != "UNKNOWN" else 0.5
        return {"analysis": analysis.model_dump(), "confidence": confidence, "parsed": parsed}

    def _extract_variables(self, source: str) -> list[str]:
        import re

        pattern = re.compile(r"\b([A-Z][A-Z0-9-]{2,30})\s+PIC\b", re.IGNORECASE)
        return list(dict.fromkeys(m.group(1) for m in pattern.finditer(source)))[:15]
