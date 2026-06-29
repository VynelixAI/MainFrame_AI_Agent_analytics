"""ABEND Analysis Agent."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from models.incident import InvestigationRequest
from models.outputs import AbendAnalysis
from utils.parsers import parse_abend_log

ABEND_KNOWLEDGE: dict[str, dict[str, str]] = {
    "S0C1": {
        "type": "Operation Exception",
        "cause": "Invalid operation code - program attempted to execute data as instructions",
        "impact": "Job/step abends immediately. Batch processing halted for dependent jobs.",
        "recovery": "Review compile options, LINKEDIT output. Check for overlay of code by data. "
        "Verify program was compiled with correct ARCH level.",
        "historical": "Common in programs with incorrect CALL conventions or corrupted load modules.",
    },
    "S0C4": {
        "type": "Protection Exception",
        "cause": "Storage violation - program referenced unavailable or protected storage",
        "impact": "Critical batch failure. May indicate data corruption or program bug.",
        "recovery": "Analyze CEEDUMP/ABENDAID dump. Check working storage lengths, linkage section, "
        "and subscript bounds. Review recent code changes.",
        "historical": "Frequently caused by uninitialized pointers or array bounds violations.",
    },
    "S0C7": {
        "type": "Data Exception",
        "cause": "Invalid decimal data in computational-3 field during arithmetic operation",
        "impact": "Financial/billing batch failure. Data integrity risk for downstream processing.",
        "recovery": "Identify failing data record via OFFSET. Validate input file for non-numeric "
        "characters in packed decimal fields. Reprocess after data correction.",
        "historical": "Common in claims/billing when source system sends corrupted amounts.",
    },
    "S013": {
        "type": "Open Error",
        "cause": "Dataset open failure - DCB mismatch, missing dataset, or authorization",
        "impact": "Step cannot access required files. Dependent steps will not execute.",
        "recovery": "Verify DD statement DCB parameters match dataset attributes. Check DISP and "
        "SPACE parameters. Confirm dataset exists and user has READ access.",
        "historical": "Often seen after catalog recovery or dataset rename operations.",
    },
    "S806": {
        "type": "Module Not Found",
        "cause": "Program module not found in STEPLIB or linklist concatenation",
        "impact": "Program cannot be loaded. Step abends before execution.",
        "recovery": "Verify STEPLIB/JOBLIB DD concatenation. Check program was link-edited and "
        "copied to production load library. Refresh LLA if needed.",
        "historical": "Common after deployment when load module not promoted to all LPARs.",
    },
    "S222": {
        "type": "Job Cancelled",
        "cause": "Job cancelled by operator, scheduler, or JES due to timeout/resource",
        "impact": "Incomplete processing. Restart required from appropriate step.",
        "recovery": "Review JES2 messages for cancel reason. Check JCL TIME parameter. "
        "Coordinate with operations before restart.",
        "historical": "Often triggered by runaway CPU consumption or missed deadline.",
    },
    "S322": {
        "type": "CPU Time Exceeded",
        "cause": "Step exceeded JCL TIME parameter CPU limit",
        "impact": "Step terminated. Partial processing may require rollback.",
        "recovery": "Increase TIME parameter after performance review. Analyze why CPU "
        "consumption increased. Check for infinite loops or missing indexes.",
        "historical": "Seen after DB2 access path changes or data volume increases.",
    },
    "U0999": {
        "type": "User Abend",
        "cause": "Application-defined abend via CALL 'CEE3ABD' or ABEND macro",
        "impact": "Business logic detected unrecoverable error condition.",
        "recovery": "Review application abend handler messages. Check SQLCODE/SQLSTATE in "
        "preceding messages. Consult application team for abend reason code.",
        "historical": "Claims system uses U0999 for validation failures on policy data.",
    },
    "U4038": {
        "type": "Language Environment Abend",
        "cause": "LE runtime detected severe error - often file status or SQL error",
        "impact": "Program terminated by LE. Dump produced for analysis.",
        "recovery": "Analyze CEEDUMP. Check FILE STATUS and SQLCA. Review LE message file.",
        "historical": "Common when DB2 connection lost during batch window.",
    },
    "SOCB": {
        "type": "Operation Exception (SOCB)",
        "cause": "Branch to invalid address or corrupted branch target",
        "impact": "Immediate program termination with potential data inconsistency.",
        "recovery": "Analyze dump at PSW address. Check for storage overlay or corrupted "
        "CALL/RETURN sequence.",
        "historical": "Seen in older COBOL programs with non-standard linkage.",
    },
}


class AbendAgent(BaseAgent):
    name = "abend_agent"

    def analyze(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> dict[str, Any]:
        log_text = (
            self.get_log_content(request, "abend_log")
            or self.get_log_content(request, "sysout")
            or self.get_log_content(request, "jes_log")
        )
        if not log_text.strip():
            return {"analysis": AbendAnalysis().model_dump(), "confidence": 0.0, "skipped": True}

        parsed = parse_abend_log(log_text)
        analysis = AbendAnalysis()

        abend_codes = parsed.get("soc", []) + parsed.get("user", [])
        if abend_codes:
            code = abend_codes[0].upper().replace("SOCB", "SOCB")
            if code.startswith("SOC"):
                code = "S" + code[1:]
            analysis.abend_code = code
            knowledge = ABEND_KNOWLEDGE.get(code, ABEND_KNOWLEDGE.get(code[:4], {}))
            if knowledge:
                analysis.abend_type = knowledge.get("type", "")
                analysis.cause = knowledge.get("cause", "")
                analysis.impact = knowledge.get("impact", "")
                analysis.recovery = knowledge.get("recovery", "")
                analysis.historical_resolution = knowledge.get("historical", "")

        if parsed.get("program"):
            analysis.program = parsed["program"][0]
        if parsed.get("offset"):
            analysis.offset = parsed["offset"][0]
        if parsed.get("psa"):
            analysis.psa = parsed["psa"][0]
        analysis.related_messages = parsed.get("abend_msg", [])

        for iec in ["IEC141I", "IEC130I", "IEA995I", "IGD17101I"]:
            if iec in log_text:
                analysis.related_messages.append(f"{iec} detected in log - dataset/volume issue")

        analysis.examples = [
            f"ABEND {analysis.abend_code} in {analysis.program or 'UNKNOWN'} at offset {analysis.offset or 'N/A'}"
        ]

        confidence = 0.9 if analysis.abend_code else 0.4
        return {"analysis": analysis.model_dump(), "confidence": confidence, "parsed": parsed}
