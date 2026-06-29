"""JCL Parsing and Analysis Agent."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from models.incident import InvestigationRequest
from models.outputs import JCLAnalysis
from utils.parsers import parse_jcl

UTILITY_PROGRAMS = {
    "IDCAMS", "SORT", "IKJEFT01", "DSNUTILB", "IEBGENER", "IEBCOPY",
    "FTP", "DYNAMNBR", "IKJEFT1B", "DSN1COPY", "DSN1PRNT",
}


class JCLAgent(BaseAgent):
    name = "jcl_agent"

    def analyze(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> dict[str, Any]:
        jcl_text = self.get_log_content(request, "jcl")
        if not jcl_text.strip():
            return {"analysis": JCLAnalysis().model_dump(), "confidence": 0.0, "skipped": True}

        parsed = parse_jcl(jcl_text)
        analysis = JCLAnalysis()

        if parsed.get("job"):
            analysis.job_name = parsed["job"][0]
        if parsed.get("proc"):
            analysis.procs = parsed["proc"]

        exec_steps = parsed.get("exec", [])
        dd_statements = parsed.get("dd", [])
        for step_name in exec_steps:
            analysis.steps.append({"step_name": step_name, "type": "EXEC"})

        for dd in dd_statements:
            if dd not in [s.get("step_name") for s in analysis.steps]:
                analysis.steps.append({"step_name": dd, "type": "DD"})

        for util in UTILITY_PROGRAMS:
            if util in jcl_text.upper():
                analysis.utilities.append(util)

        disp_issues = parsed.get("disp", [])
        for disp in disp_issues:
            if "MOD" in disp.upper() and "OLD" not in disp.upper():
                analysis.disp_issues.append(f"Review DISP=({disp}) - potential sharing conflict")

        gdg_refs = parsed.get("gdg", [])
        for gdg in gdg_refs:
            if gdg in ("(+0)", "(+1)"):
                analysis.gdg_issues.append(f"GDG reference {gdg} - verify generation exists")

        if "SPACE" in jcl_text.upper() and ("CYL" in jcl_text.upper() or "TRK" in jcl_text.upper()):
            if "SECONDARY" not in jcl_text.upper():
                analysis.space_errors.append("Primary space only - no SECONDARY allocation defined")

        lines = jcl_text.splitlines()
        dd_names = {d.upper() for d in dd_statements}
        for line in lines:
            upper = line.upper()
            if "DSN=" in upper and "NOT FOUND" in upper:
                analysis.dataset_issues.append(line.strip())
            if "MISSING" in upper and "DD" in upper:
                analysis.missing_dd.append(line.strip())

        standard_dds = {"SYSOUT", "SYSPRINT", "SYSUDUMP", "SYSTSIN", "SYSIN"}
        for step in exec_steps:
            step_dds = [d for d in dd_statements if step.upper() in jcl_text.upper()]
            if not step_dds and step.upper() not in standard_dds:
                pass  # PROC may define DDs

        if analysis.missing_dd:
            analysis.errors.append("Missing DD statements detected")
        if analysis.disp_issues:
            analysis.errors.append("DISP parameter issues found")
        if analysis.gdg_issues:
            analysis.errors.append("GDG generation issues detected")
        if analysis.space_errors:
            analysis.errors.append("Space allocation concerns identified")

        confidence = 0.85 if analysis.job_name else 0.55
        return {"analysis": analysis.model_dump(), "confidence": confidence, "parsed": parsed}
