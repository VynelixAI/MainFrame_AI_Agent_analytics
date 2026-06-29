"""Agent-specific output models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlannerOutput(BaseModel):
    investigation_plan: list[str]
    priority_agents: list[str]
    estimated_severity: str
    focus_areas: list[str]
    rationale: str


class JESAnalysis(BaseModel):
    job_name: str = ""
    job_id: str = ""
    step_name: str = ""
    return_code: int | None = None
    elapsed_time: str = ""
    cpu_time: str = ""
    dataset_allocations: list[str] = Field(default_factory=list)
    missing_datasets: list[str] = Field(default_factory=list)
    security_errors: list[str] = Field(default_factory=list)
    restart_recommendation: str = ""
    messages: list[str] = Field(default_factory=list)
    abend_detected: bool = False
    abend_code: str = ""


class AbendAnalysis(BaseModel):
    abend_code: str = ""
    abend_type: str = ""
    program: str = ""
    offset: str = ""
    psa: str = ""
    cause: str = ""
    impact: str = ""
    recovery: str = ""
    examples: list[str] = Field(default_factory=list)
    historical_resolution: str = ""
    related_messages: list[str] = Field(default_factory=list)


class COBOLAnalysis(BaseModel):
    program_name: str = ""
    business_purpose: str = ""
    input_files: list[str] = Field(default_factory=list)
    output_files: list[str] = Field(default_factory=list)
    db2_tables: list[str] = Field(default_factory=list)
    call_hierarchy: list[str] = Field(default_factory=list)
    perform_hierarchy: list[str] = Field(default_factory=list)
    key_variables: list[str] = Field(default_factory=list)
    paragraphs: list[str] = Field(default_factory=list)
    impacted_modules: list[str] = Field(default_factory=list)
    explanation: str = ""


class JCLAnalysis(BaseModel):
    job_name: str = ""
    steps: list[dict[str, Any]] = Field(default_factory=list)
    procs: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    missing_dd: list[str] = Field(default_factory=list)
    disp_issues: list[str] = Field(default_factory=list)
    dataset_issues: list[str] = Field(default_factory=list)
    gdg_issues: list[str] = Field(default_factory=list)
    space_errors: list[str] = Field(default_factory=list)
    utilities: list[str] = Field(default_factory=list)


class DB2Analysis(BaseModel):
    sqlcodes: list[int] = Field(default_factory=list)
    sqlstates: list[str] = Field(default_factory=list)
    deadlock_detected: bool = False
    lock_timeout: bool = False
    missing_index: bool = False
    package_issues: list[str] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    recovery_steps: list[str] = Field(default_factory=list)


class SchedulerAnalysis(BaseModel):
    scheduler_type: str = ""
    failed_jobs: list[str] = Field(default_factory=list)
    late_jobs: list[str] = Field(default_factory=list)
    dependency_failures: list[str] = Field(default_factory=list)
    circular_dependencies: list[str] = Field(default_factory=list)
    restart_chain: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class MQAnalysis(BaseModel):
    mqrc_codes: list[str] = Field(default_factory=list)
    queue_full: list[str] = Field(default_factory=list)
    channel_stopped: list[str] = Field(default_factory=list)
    listener_issues: list[str] = Field(default_factory=list)
    dlq_messages: list[str] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    recovery_steps: list[str] = Field(default_factory=list)


class CICSAnalysis(BaseModel):
    transactions: list[str] = Field(default_factory=list)
    resp_codes: list[str] = Field(default_factory=list)
    file_status_errors: list[str] = Field(default_factory=list)
    region_issues: list[str] = Field(default_factory=list)
    program_not_found: list[str] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    recovery_steps: list[str] = Field(default_factory=list)


class GuardrailResult(BaseModel):
    passed: bool
    pii_detected: bool = False
    pii_masked_fields: list[str] = Field(default_factory=list)
    prompt_injection_detected: bool = False
    hallucination_risk: float = 0.0
    confidence_score: float = 0.0
    source_validated: bool = True
    blocked_recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requires_human_approval: bool = False


class RunbookRecommendation(BaseModel):
    runbook_id: str
    title: str
    steps: list[str]
    commands: list[str]
    validation_steps: list[str]
    preventive_measures: list[str]
    source: str = "knowledge_base"


class ServiceNowSummary(BaseModel):
    short_description: str
    description: str
    category: str = "Mainframe Operations"
    subcategory: str = "Batch Processing"
    priority: str = "3"
    assignment_group: str = "Mainframe Operations"
    business_service: str = ""
    configuration_item: str = ""
    work_notes: str = ""
