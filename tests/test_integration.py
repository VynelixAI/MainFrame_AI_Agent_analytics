"""Integration and workflow tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from graph.workflow import InvestigationGraph, get_investigation_graph
from models.incident import InvestigationRequest, InvestigationState


class TestInvestigationGraph:
    def test_full_investigation(self, full_investigation_request):
        graph = InvestigationGraph()
        result = graph.investigate(full_investigation_request)
        assert result["incident_id"]
        assert result["incident_report"]
        assert result["runbook"]
        assert len(result["agent_results"]) >= 10

    def test_minimal_investigation(self):
        graph = InvestigationGraph()
        req = InvestigationRequest(job_name="TESTJOB", jes_log="IEF403I TESTJOB - STARTED")
        result = graph.investigate(req)
        assert result["incident_id"]

    def test_state_progression(self, full_investigation_request):
        graph = InvestigationGraph()
        result = graph.investigate(full_investigation_request)
        assert "planner" in result["completed_steps"]
        assert "runbook_agent" in result["completed_steps"]


class TestInvestigationState:
    def test_create_state(self, full_investigation_request):
        state = InvestigationState(request=full_investigation_request)
        assert state.request.job_name == "CLMDAY01"

    def test_default_values(self):
        state = InvestigationState(request=InvestigationRequest())
        assert state.current_step == "planner"
        assert state.errors == []


class TestAPI:
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_investigate(self, client, full_investigation_request):
        response = client.post(
            "/api/v1/investigate",
            json=full_investigation_request.model_dump(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["incident_id"]
        assert data["status"] == "completed"

    def test_history(self, client, full_investigation_request):
        client.post("/api/v1/investigate", json=full_investigation_request.model_dump())
        response = client.get("/api/v1/history")
        assert response.status_code == 200

    def test_knowledge_search(self, client):
        response = client.get("/api/v1/knowledge/search", params={"query": "S0C7 abend"})
        assert response.status_code == 200


class TestMemory:
    def test_cache_and_retrieve(self, full_investigation_request):
        from agents.memory import get_memory
        memory = get_memory()
        state = {"incident_id": "test-123", "status": "completed"}
        memory.cache_state("test-123", state)
        cached = memory.get_cached_state("test-123")
        assert cached is not None
        assert cached["incident_id"] == "test-123"

    def test_store_investigation(self, full_investigation_request):
        from agents.memory import get_memory
        memory = get_memory()
        report = {
            "analysis": {
                "incident_id": "store-test",
                "affected_job": "CLMDAY01",
                "application": "Claims",
                "severity": "HIGH",
                "root_cause": "S0C7",
                "confidence_score": 0.85,
            }
        }
        memory.store_investigation(report)
        history = memory.get_history(limit=5)
        assert any(h.get("incident_id") == "store-test" for h in history)
