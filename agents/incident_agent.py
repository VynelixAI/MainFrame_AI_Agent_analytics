"""Incident Summary and Report Generation Agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from agents.base_agent import BaseAgent
from config import get_settings
from models.incident import (
    ConfidenceLevel,
    Evidence,
    IncidentReport,
    InvestigationRequest,
    RecoveryAction,
    Severity,
    TimelineEvent,
)
from models.outputs import ServiceNowSummary


class IncidentAgent(BaseAgent):
    name = "incident_agent"

    def analyze(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        settings = get_settings()

        jes = self._get_analysis(context, "jes_analysis")
        abend = self._get_analysis(context, "abend_analysis")
        jcl = self._get_analysis(context, "jcl_analysis")
        db2 = self._get_analysis(context, "db2_analysis")
        mq = self._get_analysis(context, "mq_analysis")
        cics = self._get_analysis(context, "cics_analysis")
        scheduler = self._get_analysis(context, "scheduler_analysis")
        guardrail = self._get_analysis(context, "guardrail_result")

        affected_job = (
            jes.get("job_name")
            or request.job_name
            or jcl.get("job_name")
            or "UNKNOWN"
        )
        application = request.application or self._infer_application(affected_job)
        root_cause = self._determine_root_cause(abend, jes, db2, mq, cics, jcl)
        severity = self._determine_severity(abend, jes, db2)
        business_impact = self._assess_business_impact(severity, application, affected_job)
        timeline = self._build_timeline(jes, abend, scheduler)
        evidence = self._collect_evidence(context)
        recovery_actions = self._build_recovery_actions(abend, jes, db2, mq, scheduler, guardrail)
        commands = self._build_commands(affected_job, abend, db2)
        validation_steps = self._build_validation_steps(affected_job)
        preventive = self._build_preventive_measures(abend, db2, jcl)

        confidences = [
            r.get("confidence", 0.0)
            for r in context.get("agent_results", [])
            if isinstance(r, dict) and r.get("success")
        ]
        confidence_score = sum(confidences) / len(confidences) if confidences else 0.5
        confidence_level = self._confidence_level(confidence_score)

        executive = (
            f"Incident {request.incident_id}: Job {affected_job} ({application}) "
            f"experienced {root_cause[:100]}. Severity: {severity.value}. "
            f"Confidence: {confidence_score:.0%}."
        )

        snow = ServiceNowSummary(
            short_description=f"[{severity.value}] {affected_job} - {abend.get('abend_code', 'Job Failure')}",
            description=(
                f"Job: {affected_job}\nApplication: {application}\n"
                f"Root Cause: {root_cause}\n\nBusiness Impact: {business_impact}"
            ),
            priority=self._snow_priority(severity),
            business_service=application,
            configuration_item=f"z/OS LPAR - {affected_job}",
            work_notes=f"AI Copilot analysis completed. Confidence: {confidence_score:.0%}",
        )

        report = IncidentReport(
            incident_id=request.incident_id,
            severity=severity,
            affected_job=affected_job,
            application=application,
            business_impact=business_impact,
            timeline=timeline,
            root_cause=root_cause,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            evidence=evidence,
            recovery_actions=recovery_actions,
            commands=commands,
            validation_steps=validation_steps,
            preventive_measures=preventive,
            servicenow_summary=snow.model_dump_json(),
            executive_summary=executive,
            requires_human_approval=guardrail.get("requires_human_approval", False),
        )

        return {
            "analysis": report.model_dump(),
            "confidence": confidence_score,
            "servicenow": snow.model_dump(),
        }

    def _get_analysis(self, context: dict[str, Any], key: str) -> dict[str, Any]:
        data = context.get(key, {})
        if isinstance(data, dict) and "analysis" in data:
            return data["analysis"]
        return data if isinstance(data, dict) else {}

    def _infer_application(self, job_name: str) -> str:
        prefixes = {
            "CLM": "Claims Processing",
            "BIL": "Billing",
            "PAY": "Payments",
            "POL": "Policy Administration",
            "CUS": "Customer Management",
            "ENR": "Enrollment",
            "INV": "Inventory",
            "PRL": "Payroll",
            "FIN": "Finance",
            "HLT": "Healthcare",
        }
        return prefixes.get(job_name[:3].upper(), "Enterprise Batch")

    def _determine_root_cause(self, *analyses: dict[str, Any]) -> str:
        abend, jes, db2, mq, cics, jcl = analyses
        if abend.get("abend_code"):
            return f"{abend['abend_code']}: {abend.get('cause', 'Program abend detected')}"
        if db2.get("sqlcodes"):
            return f"DB2 SQLCODE {db2['sqlcodes'][0]}: {db2.get('explanations', ['Database error'])[0]}"
        if mq.get("mqrc_codes"):
            return f"MQ Error {mq['mqrc_codes'][0]}: {mq.get('explanations', ['MQ failure'])[0]}"
        if cics.get("resp_codes"):
            return f"CICS {cics['resp_codes'][0]}: {cics.get('explanations', ['CICS error'])[0]}"
        if jes.get("missing_datasets"):
            return f"Dataset allocation failure: {jes['missing_datasets'][0]}"
        if jcl.get("errors"):
            return f"JCL error: {jcl['errors'][0]}"
        return "Unable to determine definitive root cause - manual investigation required"

    def _determine_severity(self, abend: dict, jes: dict, db2: dict) -> Severity:
        critical_abends = {"S0C4", "S0C7", "U0999", "U4038"}
        if abend.get("abend_code", "").upper() in critical_abends:
            return Severity.CRITICAL
        if db2.get("deadlock_detected") or -904 in db2.get("sqlcodes", []):
            return Severity.HIGH
        rc = jes.get("return_code")
        if rc and rc >= 12:
            return Severity.HIGH
        if rc and rc >= 8:
            return Severity.MEDIUM
        return Severity.LOW

    def _assess_business_impact(self, severity: Severity, app: str, job: str) -> str:
        impacts = {
            Severity.CRITICAL: f"Critical impact to {app}. SLA breach imminent. Downstream {job} dependents blocked.",
            Severity.HIGH: f"Significant impact to {app}. Batch window at risk. Manual intervention required.",
            Severity.MEDIUM: f"Moderate impact to {app}. Job {job} requires restart after correction.",
            Severity.LOW: f"Minor impact to {app}. Monitoring recommended.",
            Severity.INFORMATIONAL: f"No business impact detected for {app}.",
        }
        return impacts.get(severity, impacts[Severity.MEDIUM])

    def _build_timeline(self, jes: dict, abend: dict, scheduler: dict) -> list[TimelineEvent]:
        events: list[TimelineEvent] = []
        if jes.get("job_name"):
            events.append(TimelineEvent(
                timestamp=datetime.utcnow().isoformat(),
                source="JES",
                event="Job Execution",
                details=f"Job {jes['job_name']} RC={jes.get('return_code', 'N/A')}",
            ))
        if abend.get("abend_code"):
            events.append(TimelineEvent(
                timestamp=datetime.utcnow().isoformat(),
                source="ABEND",
                event=f"ABEND {abend['abend_code']}",
                details=f"Program {abend.get('program', 'UNKNOWN')} at offset {abend.get('offset', 'N/A')}",
            ))
        if scheduler.get("failed_jobs"):
            events.append(TimelineEvent(
                timestamp=datetime.utcnow().isoformat(),
                source="Scheduler",
                event="Dependency Failure",
                details=f"Failed jobs: {', '.join(scheduler['failed_jobs'][:3])}",
            ))
        return events

    def _collect_evidence(self, context: dict[str, Any]) -> list[Evidence]:
        evidence: list[Evidence] = []
        for key, artifact_type in [
            ("jes_analysis", "jes_log"),
            ("abend_analysis", "abend_log"),
            ("jcl_analysis", "jcl"),
            ("db2_analysis", "db2_log"),
            ("mq_analysis", "mq_log"),
            ("cics_analysis", "cics_log"),
        ]:
            data = context.get(key, {})
            if data and not data.get("skipped"):
                conf = data.get("confidence", 0.5)
                evidence.append(Evidence(
                    source=key,
                    content=str(data.get("analysis", data))[:500],
                    relevance_score=conf,
                    artifact_type=artifact_type,
                ))
        return evidence

    def _build_recovery_actions(
        self, abend: dict, jes: dict, db2: dict, mq: dict, scheduler: dict, guardrail: dict
    ) -> list[RecoveryAction]:
        actions: list[RecoveryAction] = []
        priority = 1
        requires_approval = guardrail.get("requires_human_approval", True)

        if abend.get("recovery"):
            actions.append(RecoveryAction(
                action=abend["recovery"][:200],
                requires_approval=requires_approval,
                priority=priority,
            ))
            priority += 1

        for step in db2.get("recovery_steps", [])[:3]:
            actions.append(RecoveryAction(action=step, priority=priority))
            priority += 1

        for step in mq.get("recovery_steps", [])[:2]:
            actions.append(RecoveryAction(action=step, priority=priority))
            priority += 1

        if scheduler.get("restart_chain"):
            for step in scheduler["restart_chain"][:3]:
                actions.append(RecoveryAction(
                    action=step,
                    requires_approval=requires_approval,
                    priority=priority,
                ))
                priority += 1

        if jes.get("restart_recommendation") and "No restart" not in jes["restart_recommendation"]:
            actions.append(RecoveryAction(
                action=jes["restart_recommendation"],
                command=f"// RESTART JOB after approval",
                requires_approval=True,
                priority=priority,
            ))

        return actions

    def _build_commands(self, job: str, abend: dict, db2: dict) -> list[str]:
        cmds = [
            f"S JES2,O JOB={job}  /* Display job status */",
            f"//SJOB JOB={job}     /* Display active jobs */",
        ]
        if abend.get("program"):
            cmds.append(f"//SRCH FOR '{abend['program']}' IN LOADLIB")
        if db2.get("sqlcodes"):
            cmds.append("-DIS THREAD(*) DETAIL  /* DB2 thread analysis */")
            cmds.append(f"-DISPLAY DATABASE(*) LIMIT(*)  /* Check DB2 status */")
        return cmds

    def _build_validation_steps(self, job: str) -> list[str]:
        return [
            f"Verify job {job} completed with RC=0",
            "Confirm downstream dependent jobs released by scheduler",
            "Validate output dataset record counts against control totals",
            "Check application team sign-off for financial impacts",
            "Monitor next scheduled run for recurrence",
        ]

    def _build_preventive_measures(self, abend: dict, db2: dict, jcl: dict) -> list[str]:
        measures = [
            "Add proactive monitoring for job RC and elapsed time trends",
            "Review and update operational runbook with this incident",
        ]
        if abend.get("abend_code") == "S0C7":
            measures.append("Implement input file validation before batch processing")
        if db2.get("missing_index"):
            measures.append("Schedule index analysis and RUNSTATS optimization")
        if jcl.get("gdg_issues"):
            measures.append("Add GDG generation verification to pre-job checklist")
        return measures

    def _confidence_level(self, score: float) -> ConfidenceLevel:
        if score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        if score >= 0.75:
            return ConfidenceLevel.HIGH
        if score >= 0.6:
            return ConfidenceLevel.MEDIUM
        if score >= 0.4:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW

    def _snow_priority(self, severity: Severity) -> str:
        return {"CRITICAL": "1", "HIGH": "2", "MEDIUM": "3", "LOW": "4"}.get(severity.value, "3")
