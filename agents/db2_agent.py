"""DB2 Error Analysis Agent."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from models.incident import InvestigationRequest
from models.outputs import DB2Analysis
from utils.parsers import parse_db2_log

SQLCODE_KNOWLEDGE: dict[int, dict[str, str]] = {
    -904: {
        "desc": "Resource unavailable - DB2 subsystem or connection limit reached",
        "recovery": "Check DB2 subsystem status. Verify thread limits. Contact DBA for -904 analysis.",
    },
    -911: {
        "desc": "Deadlock or timeout - rollback due to deadlock",
        "recovery": "Retry transaction. Review lock contention. Analyze deadlock graph via DB2 utilities.",
    },
    -913: {
        "desc": "Lock timeout - resource held by another transaction",
        "recovery": "Increase LOCKTIMEOUT if appropriate. Review long-running transactions. Check for lock escalation.",
    },
    -805: {
        "desc": "Package/plan not found in plan table",
        "recovery": "Verify BIND was executed. Check PKLIST in JCL. Rebind package if needed.",
    },
    -803: {
        "desc": "Duplicate key on INSERT - unique constraint violation",
        "recovery": "Review input data for duplicates. Check if restart is reprocessing records.",
    },
    -305: {
        "desc": "NULL value in NOT NULL column",
        "recovery": "Validate input data. Check host variable initialization in COBOL program.",
    },
    -180: {
        "desc": "Bad DATE, TIME, or TIMESTAMP value",
        "recovery": "Validate date formats in input. Check PIC clause alignment with DB2 column type.",
    },
    -181: {
        "desc": "Bad mixed DATE, TIME, or TIMESTAMP value",
        "recovery": "Review SQL WHERE clause date comparisons. Ensure consistent format.",
    },
    -204: {
        "desc": "Object name undefined - table/view does not exist",
        "recovery": "Verify table name and schema qualifier. Check BIND authorization.",
    },
    -302: {
        "desc": "Input value too large for host variable",
        "recovery": "Review PIC clause sizes vs column definitions. Check for data truncation.",
    },
}


class DB2Agent(BaseAgent):
    name = "db2_agent"

    def analyze(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> dict[str, Any]:
        log_text = self.get_log_content(request, "db2_log") or self.get_log_content(request, "sysout")
        if not log_text.strip():
            return {"analysis": DB2Analysis().model_dump(), "confidence": 0.0, "skipped": True}

        parsed = parse_db2_log(log_text)
        analysis = DB2Analysis()

        sqlcodes_raw = parsed.get("sqlcode", [])
        analysis.sqlcodes = list({int(c) for c in sqlcodes_raw})
        analysis.sqlstates = parsed.get("sqlstate", [])
        analysis.deadlock_detected = bool(parsed.get("deadlock")) or -911 in analysis.sqlcodes
        analysis.lock_timeout = bool(parsed.get("lock_timeout")) or -913 in analysis.sqlcodes

        for code in analysis.sqlcodes:
            knowledge = SQLCODE_KNOWLEDGE.get(code, {})
            if knowledge:
                analysis.explanations.append(f"SQLCODE {code}: {knowledge['desc']}")
                analysis.recovery_steps.append(knowledge["recovery"])

        if "BIND" in log_text.upper() and "ERROR" in log_text.upper():
            analysis.package_issues.append("BIND error detected - verify package consistency")
        if "ACCESS PATH" in log_text.upper() or "TABLESPACE SCAN" in log_text.upper():
            analysis.missing_index = True
            analysis.explanations.append("Potential missing index - tablespace scan detected")
            analysis.recovery_steps.append("Run RUNSTATS and REVIEW access path via EXPLAIN")

        confidence = 0.9 if analysis.sqlcodes else 0.45
        return {"analysis": analysis.model_dump(), "confidence": confidence, "parsed": parsed}
