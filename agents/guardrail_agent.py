"""Guardrail Agent - PII masking, injection detection, safety checks."""

from __future__ import annotations

import re
from typing import Any

from agents.base_agent import BaseAgent
from config import get_settings
from models.incident import InvestigationRequest
from models.outputs import GuardrailResult
from utils.pii_masking import mask_pii

INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions"),
    re.compile(r"(?i)you\s+are\s+now\s+a"),
    re.compile(r"(?i)system\s*:\s*override"),
    re.compile(r"(?i)disregard\s+(safety|security|guardrails)"),
    re.compile(r"(?i)execute\s+destructive"),
]

DESTRUCTIVE_PATTERNS = [
    re.compile(r"(?i)\bDELETE\s+ALL\b"),
    re.compile(r"(?i)\bDROP\s+(TABLE|DATABASE)\b"),
    re.compile(r"(?i)\bFORMAT\s+VOLSER\b"),
    re.compile(r"(?i)\bIEFBR14\b.*DELETE"),
    re.compile(r"(?i)\bCANCEL\s+JOB\b.*FORCE"),
    re.compile(r"(?i)\bPURGE\s+QUEUE\b.*ALL"),
]


class GuardrailAgent(BaseAgent):
    name = "guardrail_agent"

    def analyze(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> dict[str, Any]:
        settings = get_settings()
        context = context or {}
        all_text = self._collect_text(request, context)
        result = GuardrailResult(passed=True)

        if settings.pii_masking_enabled:
            _, masked_fields = mask_pii(all_text)
            if masked_fields:
                result.pii_detected = True
                result.pii_masked_fields = masked_fields

        if settings.prompt_injection_detection:
            for pattern in INJECTION_PATTERNS:
                if pattern.search(request.description):
                    result.prompt_injection_detected = True
                    result.warnings.append("Potential prompt injection detected in incident description")
                    result.passed = False

        blocked: list[str] = []
        if settings.block_destructive_commands:
            recommendations = self._extract_recommendations(context)
            for rec in recommendations:
                for pattern in DESTRUCTIVE_PATTERNS:
                    if pattern.search(rec):
                        blocked.append(rec)
            result.blocked_recommendations = blocked
            if blocked:
                result.warnings.append(f"Blocked {len(blocked)} destructive recommendation(s)")

        confidences = [
            r.get("confidence", 0.0)
            for r in context.get("agent_results", [])
            if isinstance(r, dict)
        ]
        result.confidence_score = sum(confidences) / len(confidences) if confidences else 0.5

        evidence_count = sum(
            1 for key in ["jes_analysis", "abend_analysis", "jcl_analysis", "db2_analysis"]
            if context.get(key) and not context.get(key, {}).get("skipped")
        )
        result.source_validated = evidence_count >= 1
        if not result.source_validated:
            result.hallucination_risk = 0.7
            result.warnings.append("Insufficient source evidence - elevated hallucination risk")
        else:
            result.hallucination_risk = max(0.0, 1.0 - result.confidence_score)

        restart_needed = any(
            "restart" in str(v).lower()
            for v in self._extract_recommendations(context)
        )
        if restart_needed and settings.require_human_approval_for_restart:
            result.requires_human_approval = True
            result.warnings.append("Human approval required before job restart")

        if result.confidence_score < settings.confidence_threshold:
            result.warnings.append(
                f"Confidence {result.confidence_score:.2f} below threshold {settings.confidence_threshold}"
            )

        result.passed = (
            result.passed
            and not result.prompt_injection_detected
            and result.hallucination_risk < 0.8
            and len(blocked) == 0
        )

        return {
            "analysis": result.model_dump(),
            "confidence": result.confidence_score,
            "passed": result.passed,
        }

    def _collect_text(self, request: InvestigationRequest, context: dict[str, Any]) -> str:
        parts = [
            request.description,
            request.jes_log,
            request.sysout,
            request.abend_log,
            request.jcl,
            request.cobol_source,
            request.db2_log,
            request.mq_log,
            request.cics_log,
            request.scheduler_log,
        ]
        return "\n".join(p for p in parts if p)

    def _extract_recommendations(self, context: dict[str, Any]) -> list[str]:
        recs: list[str] = []
        for key in ["jes_analysis", "abend_analysis", "db2_analysis", "mq_analysis", "scheduler_analysis"]:
            analysis = context.get(key, {})
            if isinstance(analysis, dict):
                inner = analysis.get("analysis", analysis)
                for field in ["restart_recommendation", "recovery", "recovery_steps", "recommendations"]:
                    val = inner.get(field, "")
                    if isinstance(val, list):
                        recs.extend(val)
                    elif val:
                        recs.append(str(val))
        return recs
