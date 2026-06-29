"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import ensure_directories, get_settings
from models.incident import InvestigationRequest

_TEST_DATA_DIR = tempfile.mkdtemp(prefix="copilot_test_")


@pytest.fixture(scope="session", autouse=True)
def setup_dirs():
    os.environ["DUCKDB_PATH"] = str(Path(_TEST_DATA_DIR) / "test.duckdb")
    os.environ["SQLITE_PATH"] = str(Path(_TEST_DATA_DIR) / "test.sqlite")
    os.environ["REDIS_ENABLED"] = "false"
    get_settings.cache_clear()
    ensure_directories()
    from scripts.generate_sample_data import main as gen_data
    gen_data()
    yield
    from agents.memory import reset_memory
    from graph.workflow import reset_investigation_graph
    reset_memory()
    reset_investigation_graph()


@pytest.fixture(autouse=True)
def reset_singletons():
    from agents.memory import reset_memory
    from graph.workflow import reset_investigation_graph
    yield
    reset_memory()
    reset_investigation_graph()
    get_settings.cache_clear()


@pytest.fixture
def sample_jes_log() -> str:
    return """IEF403I CLMDAY01     - STARTED - TIME=24.180 02:00:00
IEF285I   DD NAME STEPLIB  DSNAME=PROD.LOADLIB.CLAIMS
IEF272I CLMDAY01     - ELAPSED TIME=00:12:34
IEF450I CLMDAY01     - CPU TIME=45.23
IEF142I CLMDAY01     - STEP STEP020 - COND CODE 0012
IEF450I CLMDAY01     - ABEND CODE=S0C7
IEF404I CLMDAY01     - ENDED  - TIME=24.180 02:15:00"""


@pytest.fixture
def sample_abend_log() -> str:
    return """CEE3202S The thread terminated abnormally.
ABEND CODE: S0C7
PROGRAM PGMCLMDA AT ENTRY POINT PGMCLMDA
OFFSET 2A4F
PSA KEY=00000000"""


@pytest.fixture
def sample_jcl() -> str:
    return """//CLMDAY01 JOB (ACCT),'CLAIMS BATCH',CLASS=A
//STEP010  EXEC PGM=IKJEFT01
//STEPLIB  DD DSN=PROD.DBRMLIB.LOAD,DISP=SHR
//SYSTSIN  DD *
  DSN SYSTEM(DSNP)
  RUN PROGRAM(PGMCLM) PLAN(PLANCLM)
/*
"""


@pytest.fixture
def sample_cobol() -> str:
    return """       IDENTIFICATION DIVISION.
       PROGRAM-ID. PGMCLM01.
       PROCEDURE DIVISION.
       0000-MAIN.
           PERFORM 1000-INIT
           CALL 'SUBVAL01'
           GOBACK.
       1000-INIT.
           EXEC SQL SELECT COUNT(*) FROM PROD.CLAIMS_TABLE END-EXEC.
"""


@pytest.fixture
def sample_db2_log() -> str:
    return "SQLCODE=-911 SQLSTATE=40001 DEADLOCK DETECTED ON TABLE PROD.CLAIMS.MASTER"


@pytest.fixture
def sample_mq_log() -> str:
    return "AMQ9503E Queue 'PAYMENT.REQUEST' is full.\nAMQ9208E Channel stopped."


@pytest.fixture
def sample_cics_log() -> str:
    return "DFHAP0001 Transaction CLM1 ABEND AEI0\nRESP=13 NOTFND"


@pytest.fixture
def sample_scheduler_log() -> str:
    return "CA-7 SCHID=001 JOB=CLMDAY01 STATUS=FAILED\nDEPENDENCY PREDECESSOR CLMPRE01 NOT MET FAILED"


@pytest.fixture
def full_investigation_request(
    sample_jes_log, sample_abend_log, sample_jcl, sample_cobol,
    sample_db2_log, sample_mq_log, sample_cics_log, sample_scheduler_log,
) -> InvestigationRequest:
    return InvestigationRequest(
        job_name="CLMDAY01",
        application="Claims Processing",
        description="Claims daily batch failed with S0C7",
        jes_log=sample_jes_log,
        abend_log=sample_abend_log,
        jcl=sample_jcl,
        cobol_source=sample_cobol,
        db2_log=sample_db2_log,
        mq_log=sample_mq_log,
        cics_log=sample_cics_log,
        scheduler_log=sample_scheduler_log,
    )
