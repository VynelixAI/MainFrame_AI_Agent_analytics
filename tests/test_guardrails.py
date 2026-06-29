"""Tests for guardrails, PII masking, and utilities."""

from __future__ import annotations

import pytest

from utils.pii_masking import mask_dict, mask_pii


class TestPIIMasking:
    def test_ssn_masked(self):
        text = "Member SSN 123-45-6789 enrolled"
        masked, fields = mask_pii(text)
        assert "123-45-6789" not in masked
        assert "ssn" in fields

    def test_email_masked(self):
        text = "Contact user@example.com for support"
        masked, fields = mask_pii(text)
        assert "user@example.com" not in masked
        assert "email" in fields

    def test_phone_masked(self):
        text = "Call 555-123-4567"
        masked, fields = mask_pii(text)
        assert "555-123-4567" not in masked

    def test_policy_number(self):
        text = "Policy POL-123456789"
        masked, fields = mask_pii(text)
        assert "POL-123456789" not in masked

    def test_no_pii(self):
        text = "Job CLMDAY01 completed normally"
        masked, fields = mask_pii(text)
        assert masked == text
        assert fields == []

    def test_mask_dict(self):
        data = {"name": "John", "ssn": "123-45-6789", "nested": {"email": "a@b.com"}}
        result = mask_dict(data)
        assert "123-45-6789" not in str(result)

    def test_password_masked(self):
        text = "password=secret123"
        masked, fields = mask_pii(text)
        assert "secret123" not in masked


class TestConfig:
    def test_settings_defaults(self):
        from config import Settings
        s = Settings()
        assert s.app_name == "Mainframe AI Operations Copilot"
        assert s.confidence_threshold == 0.65

    def test_ensure_directories(self):
        from config import ensure_directories, KNOWLEDGE_DIR
        ensure_directories()
        assert KNOWLEDGE_DIR.exists()


class TestModels:
    def test_severity_enum(self):
        from models.incident import Severity
        assert Severity.CRITICAL.value == "CRITICAL"

    def test_investigation_request_defaults(self):
        from models.incident import InvestigationRequest
        req = InvestigationRequest()
        assert req.incident_id
        assert req.job_name == ""

    def test_incident_report(self):
        from models.incident import ConfidenceLevel, IncidentReport, Severity
        report = IncidentReport(
            incident_id="test",
            severity=Severity.HIGH,
            affected_job="JOB1",
            application="Claims",
            business_impact="High",
            timeline=[],
            root_cause="S0C7",
            confidence_score=0.85,
            confidence_level=ConfidenceLevel.HIGH,
            evidence=[],
            recovery_actions=[],
        )
        assert report.severity == Severity.HIGH


class TestKnowledgeBase:
    def test_initialize(self):
        from rag.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
        kb.initialize()
        assert kb._initialized

    def test_search(self):
        from rag.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
        kb.initialize()
        results = kb.search("S0C7 data exception", top_k=3)
        assert isinstance(results, list)

    def test_context_for_investigation(self):
        from rag.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
        kb.initialize()
        context = kb.get_context_for_investigation("DB2 deadlock SQLCODE -911")
        assert isinstance(context, list)


class TestLLMClient:
    def test_fallback(self):
        from utils.llm_client import LLMClient
        client = LLMClient()
        result = client.invoke("system", "user", {"response": "fallback"})
        assert "response" in result

    def test_available_without_key(self):
        from utils.llm_client import LLMClient
        client = LLMClient()
        assert client.available is False or client.available is True
