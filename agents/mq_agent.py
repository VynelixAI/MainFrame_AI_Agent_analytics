"""MQ Error Analysis Agent."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from models.incident import InvestigationRequest
from models.outputs import MQAnalysis
from utils.parsers import parse_mq_log

MQRC_KNOWLEDGE: dict[str, dict[str, str]] = {
    "AMQ9503": {
        "desc": "Queue full - message put rejected",
        "recovery": "Increase MAXMSGL/MAXDEPTH or drain queue. Check consumer application health.",
    },
    "AMQ9208": {
        "desc": "Channel stopped or in retrying state",
        "recovery": "Check channel status via DISPLAY CHSTATUS. Review network connectivity and SSL config.",
    },
    "AMQ9641": {
        "desc": "Channel connection failure",
        "recovery": "Verify listener is running. Check firewall rules and channel authentication.",
    },
    "AMQ9777": {
        "desc": "Message persistence error",
        "recovery": "Check queue manager log for disk space. Verify log file configuration.",
    },
    "AMQ7469": {
        "desc": "Dead letter queue message threshold exceeded",
        "recovery": "Investigate DLQ messages. Fix underlying processing errors before requeue.",
    },
}


class MQAgent(BaseAgent):
    name = "mq_agent"

    def analyze(self, request: InvestigationRequest, context: dict[str, Any] | None = None) -> dict[str, Any]:
        log_text = self.get_log_content(request, "mq_log") or self.get_log_content(request, "sysout")
        if not log_text.strip():
            return {"analysis": MQAnalysis().model_dump(), "confidence": 0.0, "skipped": True}

        parsed = parse_mq_log(log_text)
        analysis = MQAnalysis()

        analysis.mqrc_codes = parsed.get("mqrc", [])
        analysis.queue_full = parsed.get("queue_full", [])
        analysis.channel_stopped = parsed.get("channel", [])

        import re

        listener = re.compile(r"LISTENER\s+(\S+).*(?:STOPPED|FAILED|NOT\s+STARTED)", re.IGNORECASE)
        for match in listener.finditer(log_text):
            analysis.listener_issues.append(match.group(1))

        dlq = re.compile(r"(?:DLQ|DEAD\s*LETTER).*?(\S+)", re.IGNORECASE)
        for match in dlq.finditer(log_text):
            analysis.dlq_messages.append(match.group(0))

        for code in analysis.mqrc_codes:
            knowledge = MQRC_KNOWLEDGE.get(code.upper(), {})
            if knowledge:
                analysis.explanations.append(f"{code}: {knowledge['desc']}")
                analysis.recovery_steps.append(knowledge["recovery"])

        if analysis.queue_full:
            analysis.recovery_steps.append("Purge or drain full queues before resuming message flow")
        if analysis.channel_stopped:
            analysis.recovery_steps.append("Reset and restart affected channels after root cause fix")

        confidence = 0.85 if analysis.mqrc_codes else 0.45
        return {"analysis": analysis.model_dump(), "confidence": confidence, "parsed": parsed}
