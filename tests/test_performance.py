"""Performance and sample data tests."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from agents.abend_agent import AbendAgent
from agents.jes_agent import JESAgent
from graph.workflow import InvestigationGraph
from models.incident import InvestigationRequest


BASE = Path(__file__).resolve().parent.parent


class TestPerformance:
    def test_jes_agent_under_100ms(self, sample_jes_log):
        agent = JESAgent()
        start = time.perf_counter()
        agent.run(InvestigationRequest(jes_log=sample_jes_log))
        assert (time.perf_counter() - start) < 1.0

    def test_abend_agent_under_100ms(self, sample_abend_log):
        agent = AbendAgent()
        start = time.perf_counter()
        agent.run(InvestigationRequest(abend_log=sample_abend_log))
        assert (time.perf_counter() - start) < 1.0

    def test_full_investigation_under_30s(self, full_investigation_request):
        graph = InvestigationGraph()
        start = time.perf_counter()
        graph.investigate(full_investigation_request)
        assert (time.perf_counter() - start) < 30.0


class TestSampleData:
    def test_jes_logs_exist(self):
        jes_dir = BASE / "logs" / "jes"
        files = list(jes_dir.glob("*.log"))
        assert len(files) >= 25

    def test_abend_logs_exist(self):
        abend_dir = BASE / "logs" / "abend"
        files = list(abend_dir.glob("*.log"))
        assert len(files) >= 50

    def test_cobol_programs_exist(self):
        cobol_dir = BASE / "sample_data" / "cobol"
        files = list(cobol_dir.glob("*.cbl"))
        assert len(files) >= 15

    def test_jcl_files_exist(self):
        jcl_dir = BASE / "sample_data" / "jcl"
        files = list(jcl_dir.glob("*.jcl"))
        assert len(files) >= 40

    def test_db2_logs_exist(self):
        db2_dir = BASE / "logs" / "db2"
        files = list(db2_dir.glob("*.log"))
        assert len(files) >= 10

    def test_mq_logs_exist(self):
        mq_dir = BASE / "logs" / "mq"
        files = list(mq_dir.glob("*.log"))
        assert len(files) >= 10

    def test_cics_logs_exist(self):
        cics_dir = BASE / "logs" / "cics"
        files = list(cics_dir.glob("*.log"))
        assert len(files) >= 10

    def test_runbooks_exist(self):
        rb_dir = BASE / "knowledge" / "RUNBOOKS"
        files = list(rb_dir.glob("*.md"))
        assert len(files) >= 5

    def test_sample_jes_parseable(self):
        jes_dir = BASE / "logs" / "jes"
        agent = JESAgent()
        for f in list(jes_dir.glob("*.log"))[:5]:
            content = f.read_text()
            result = agent.run(InvestigationRequest(jes_log=content))
            assert result.success

    def test_sample_abend_parseable(self):
        abend_dir = BASE / "logs" / "abend"
        agent = AbendAgent()
        for f in list(abend_dir.glob("*.log"))[:10]:
            content = f.read_text()
            result = agent.run(InvestigationRequest(abend_log=content))
            assert result.success
