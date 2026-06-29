"""Tests for log parsers."""

from __future__ import annotations

import pytest

from utils.parsers import (
    parse_abend_log,
    parse_cics_log,
    parse_cobol,
    parse_db2_log,
    parse_jcl,
    parse_jes_log,
    parse_mq_log,
    parse_scheduler_log,
)


class TestJESParser:
  def test_job_name(self, sample_jes_log):
      result = parse_jes_log(sample_jes_log)
      assert "job_name" in result or "step_rc" in result

  def test_step_rc(self, sample_jes_log):
      result = parse_jes_log(sample_jes_log)
      assert "step_rc" in result

  def test_cpu_time(self, sample_jes_log):
      result = parse_jes_log(sample_jes_log)
      assert "cpu_time" in result

  def test_elapsed(self, sample_jes_log):
      result = parse_jes_log(sample_jes_log)
      assert "elapsed" in result

  def test_empty_log(self):
      assert parse_jes_log("") == {}

  def test_security_error(self):
      log = "ICH408I USER BATCHID HAS NO ACCESS TO DATASET"
      result = parse_jes_log(log)
      assert "security" in result

  def test_dataset_error(self):
      log = "IEC141I DSN=PROD.DATA NOT FOUND"
      result = parse_jes_log(log)
      assert "dataset_error" in result

  def test_volume_error(self):
      log = "IEA995I VOLUME PROD01 NOT AVAILABLE"
      result = parse_jes_log(log)
      assert "volume_error" in result

  def test_csv_error(self):
      log = "CSV003I RACF AUTHORIZATION CHECK FAILED"
      result = parse_jes_log(log)
      assert "csv_error" in result

  def test_missing_ds(self):
      log = "IEC130I DDNAME=INPUT DSN NOT FOUND"
      result = parse_jes_log(log)
      assert "missing_ds" in result

  def test_space_error(self):
      log = "IGD17101I INSUFFICIENT SPACE ON VOLUME"
      result = parse_jes_log(log)
      assert "space_error" in result

  def test_job_start(self):
      log = "IEF403I CLMDAY01 - STARTED - TIME=24.180 02:00:00"
      result = parse_jes_log(log)
      assert "job_start" in result

  def test_job_end(self):
      log = "IEF404I CLMDAY01 - ENDED - TIME=24.180 02:15:00"
      result = parse_jes_log(log)
      assert "job_end" in result


class TestAbendParser:
  @pytest.mark.parametrize("code", ["S0C7", "S0C4", "S0C1", "S806", "S322", "U0999", "U4038", "SOCB", "S013"])
  def test_abend_codes(self, code):
      result = parse_abend_log(f"ABEND CODE: {code}")
      assert "soc" in result or "user" in result

  def test_program(self, sample_abend_log):
      result = parse_abend_log(sample_abend_log)
      assert "program" in result

  def test_offset(self, sample_abend_log):
      result = parse_abend_log(sample_abend_log)
      assert "offset" in result

  def test_psa(self, sample_abend_log):
      result = parse_abend_log(sample_abend_log)
      assert "psa" in result

  def test_empty(self):
      assert parse_abend_log("") == {}


class TestDB2Parser:
  @pytest.mark.parametrize("code", [-904, -911, -913, -805, -803, -305, -180, -181, -204, -302])
  def test_sqlcodes(self, code):
      result = parse_db2_log(f"SQLCODE={code}")
      assert "sqlcode" in result

  def test_deadlock(self):
      result = parse_db2_log("DEADLOCK DETECTED SQLCODE=-911")
      assert "deadlock" in result

  def test_lock_timeout(self):
      result = parse_db2_log("LOCK TIMEOUT SQLCODE=-913")
      assert "lock_timeout" in result

  def test_sqlstate(self):
      result = parse_db2_log("SQLSTATE=40001")
      assert "sqlstate" in result


class TestMQParser:
  @pytest.mark.parametrize("code", ["AMQ9503", "AMQ9208", "AMQ9641", "AMQ9777", "AMQ7469"])
  def test_mqrc(self, code):
      result = parse_mq_log(f"{code}E Queue error")
      assert "mqrc" in result

  def test_queue_full(self, sample_mq_log):
      result = parse_mq_log(sample_mq_log)
      assert "queue_full" in result or "mqrc" in result


class TestCICSParser:
  @pytest.mark.parametrize("code", ["AEI0", "AEY9", "APCT", "AICA", "AKCP"])
  def test_abend_codes(self, code):
      result = parse_cics_log(f"ABEND {code}")
      assert "abend" in result

  def test_resp(self):
      result = parse_cics_log("RESP=13 NOTFND")
      assert "resp" in result


class TestJCLParser:
  def test_job(self, sample_jcl):
      result = parse_jcl(sample_jcl)
      assert "job" in result

  def test_exec(self, sample_jcl):
      result = parse_jcl(sample_jcl)
      assert "exec" in result

  def test_dd(self, sample_jcl):
      result = parse_jcl(sample_jcl)
      assert "dd" in result


class TestCOBOLParser:
  def test_program_id(self, sample_cobol):
      result = parse_cobol(sample_cobol)
      assert "program_id" in result

  def test_call(self, sample_cobol):
      result = parse_cobol(sample_cobol)
      assert "call" in result

  def test_perform(self, sample_cobol):
      result = parse_cobol(sample_cobol)
      assert "perform" in result

  def test_exec_sql(self, sample_cobol):
      result = parse_cobol(sample_cobol)
      assert "exec_sql" in result


class TestSchedulerParser:
  def test_ca7(self, sample_scheduler_log):
      result = parse_scheduler_log(sample_scheduler_log)
      assert "ca7" in result

  def test_controlm(self):
      result = parse_scheduler_log("CONTROL-M ORDER ID 00A1B")
      assert "controlm" in result

  def test_tws(self):
      result = parse_scheduler_log("TWS TRCJOB CLMDAY01")
      assert "tws" in result

  def test_dependency(self, sample_scheduler_log):
      result = parse_scheduler_log(sample_scheduler_log)
      assert "dependency" in result
