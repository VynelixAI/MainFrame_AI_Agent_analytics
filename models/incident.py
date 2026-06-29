"""Core incident and investigation models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class ConfidenceLevel(str, Enum):
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"


class TimelineEvent(BaseModel):
    timestamp: str
    source: str
    event: str
    details: str = ""


class Evidence(BaseModel):
    source: str
    content: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    artifact_type: str = "log"


class RecoveryAction(BaseModel):
    action: str
    command: str = ""
    requires_approval: bool = False
    priority: int = 1
    validation_step: str = ""


class AgentResult(BaseModel):
    agent_name: str
    success: bool
    confidence: float = Field(ge=0.0, le=1.0)
    findings: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0


class InvestigationRequest(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid4()))
    jes_log: str = ""
    sysout: str = ""
    abend_log: str = ""
    jcl: str = ""
    cobol_source: str = ""
    db2_log: str = ""
    mq_log: str = ""
    cics_log: str = ""
    scheduler_log: str = ""
    description: str = ""
    application: str = ""
    job_name: str = ""


class InvestigationState(BaseModel):
    """LangGraph state for multi-agent investigation."""

    request: InvestigationRequest
    incident_id: str = ""
    planner_output: dict[str, Any] = Field(default_factory=dict)
    jes_analysis: dict[str, Any] = Field(default_factory=dict)
    abend_analysis: dict[str, Any] = Field(default_factory=dict)
    jcl_analysis: dict[str, Any] = Field(default_factory=dict)
    cobol_analysis: dict[str, Any] = Field(default_factory=dict)
    db2_analysis: dict[str, Any] = Field(default_factory=dict)
    mq_analysis: dict[str, Any] = Field(default_factory=dict)
    scheduler_analysis: dict[str, Any] = Field(default_factory=dict)
    cics_analysis: dict[str, Any] = Field(default_factory=dict)
    guardrail_result: dict[str, Any] = Field(default_factory=dict)
    incident_report: dict[str, Any] = Field(default_factory=dict)
    runbook: dict[str, Any] = Field(default_factory=dict)
    agent_results: list[dict[str, Any]] = Field(default_factory=list)
    rag_context: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    current_step: str = "planner"
    completed_steps: list[str] = Field(default_factory=list)


class IncidentReport(BaseModel):
    incident_id: str
    severity: Severity
    affected_job: str
    application: str
    business_impact: str
    timeline: list[TimelineEvent]
    root_cause: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    evidence: list[Evidence]
    recovery_actions: list[RecoveryAction]
    runbook_id: str = ""
    commands: list[str] = Field(default_factory=list)
    validation_steps: list[str] = Field(default_factory=list)
    preventive_measures: list[str] = Field(default_factory=list)
    servicenow_summary: str = ""
    executive_summary: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    requires_human_approval: bool = False
