"""Mainframe log parsing utilities."""

from __future__ import annotations

import re
from typing import Any

# JES patterns
JES_PATTERNS = {
    "job_name": re.compile(r"IEF236I\s+ALLOC\. FOR\s+(\S+)\s+(\S+)"),
    "step_rc": re.compile(r"IEF142I\s+(\S+)\s+-\s+STEP\s+(\S+)\s+-\s+COND CODE\s+(\d+)"),
    "job_end": re.compile(r"IEF404I\s+(\S+)\s+-\s+ENDED\s+-\s+TIME=\s*(\S+)"),
    "job_start": re.compile(r"IEF403I\s+(\S+)\s+-\s+STARTED\s+-\s+TIME=\s*(\S+)"),
    "dataset_alloc": re.compile(r"IEF285I\s+(\S+)\s+DD NAME\s+(\S+)\s+DSNAME=(\S+)"),
    "cpu_time": re.compile(r"IEF450I\s+(\S+)\s+-\s+CPU\s+TIME=\s*([\d.]+)"),
    "elapsed": re.compile(r"IEF272I\s+(\S+)\s+-\s+ELAPSED TIME=\s*([\d:]+)"),
    "security": re.compile(r"ICH408I\s+(.+)"),
    "dataset_error": re.compile(r"IEC141I\s+(.+)"),
    "volume_error": re.compile(r"IEA995I\s+(.+)"),
    "csv_error": re.compile(r"CSV003I\s+(.+)"),
    "missing_ds": re.compile(r"IEC130I\s+(.+)"),
    "space_error": re.compile(r"IGD17101I\s+(.+)"),
}

# ABEND patterns
ABEND_PATTERNS = {
    "soc": re.compile(r"(S0C[147]|SOCB|S013|S806|S222|S322)", re.IGNORECASE),
    "user": re.compile(r"(U0999|U4038)", re.IGNORECASE),
    "program": re.compile(r"PROGRAM\s+(\S+)\s+AT\s+ENTRY\s+POINT", re.IGNORECASE),
    "offset": re.compile(r"OFFSET\s+([0-9A-Fa-fXx]+)", re.IGNORECASE),
    "psa": re.compile(r"PSA\s+KEY[=:]?\s*(\S+)", re.IGNORECASE),
    "abend_msg": re.compile(r"CEE\d+I\s+(.+)", re.IGNORECASE),
}

# DB2 patterns
DB2_PATTERNS = {
    "sqlcode": re.compile(r"SQLCODE\s*[=:]?\s*(-?\d+)", re.IGNORECASE),
    "sqlstate": re.compile(r"SQLSTATE\s*[=:]?\s*(\w+)", re.IGNORECASE),
    "deadlock": re.compile(r"DEADLOCK|SQLCODE\s*[=:]?\s*-911", re.IGNORECASE),
    "lock_timeout": re.compile(r"LOCK TIMEOUT|SQLCODE\s*[=:]?\s*-913", re.IGNORECASE),
}

# MQ patterns
MQ_PATTERNS = {
    "mqrc": re.compile(r"AMQ\d{4}[EW]", re.IGNORECASE),
    "queue_full": re.compile(r"QUEUE\s+FULL|AMQ9503", re.IGNORECASE),
    "channel": re.compile(r"CHANNEL\s+STOPPED|AMQ9208", re.IGNORECASE),
}

# CICS patterns
CICS_PATTERNS = {
    "abend": re.compile(r"(AEI0|AEY9|APCT|AICA|AKCP)", re.IGNORECASE),
    "resp": re.compile(r"RESP\s*[=:]?\s*(\w+)", re.IGNORECASE),
    "transaction": re.compile(r"TRANSACTION\s+(\S+)", re.IGNORECASE),
}

# JCL patterns
JCL_PATTERNS = {
    "job": re.compile(r"^//(\S+)\s+JOB\s+", re.MULTILINE | re.IGNORECASE),
    "exec": re.compile(r"^//(\S+)\s+EXEC\s+", re.MULTILINE | re.IGNORECASE),
    "dd": re.compile(r"^//(\S+)\s+DD\s+", re.MULTILINE | re.IGNORECASE),
    "proc": re.compile(r"^//(\S+)\s+PROC\s+", re.MULTILINE | re.IGNORECASE),
    "cond": re.compile(r"COND=\(([^)]+)\)", re.IGNORECASE),
    "disp": re.compile(r"DISP=\(([^)]+)\)", re.IGNORECASE),
    "gdg": re.compile(r"\((\+|-)?\d+\)", re.IGNORECASE),
}

# COBOL patterns
COBOL_PATTERNS = {
    "program_id": re.compile(r"PROGRAM-ID\.\s+(\S+)", re.IGNORECASE),
    "paragraph": re.compile(r"^\s{0,6}(\w[\w-]*)\.\s*$", re.MULTILINE),
    "call": re.compile(r"CALL\s+['\"]?(\S+)['\"]?", re.IGNORECASE),
    "perform": re.compile(r"PERFORM\s+(\S+)", re.IGNORECASE),
    "select": re.compile(r"SELECT\s+(\S+)\s+ASSIGN", re.IGNORECASE),
    "exec_sql": re.compile(r"EXEC\s+SQL", re.IGNORECASE),
    "table": re.compile(r"(?:FROM|INTO|UPDATE|JOIN)\s+(\w+\.\w+|\w+)", re.IGNORECASE),
}

# Scheduler patterns
SCHEDULER_PATTERNS = {
    "ca7": re.compile(r"CA-7|SCHID|SCHTM", re.IGNORECASE),
    "controlm": re.compile(r"CONTROL-M|CTMJOB|ORDER\s+ID", re.IGNORECASE),
    "tws": re.compile(r"TWS|OPC|TRCJOB", re.IGNORECASE),
    "dependency": re.compile(r"DEPENDENCY|PREDECESSOR|SUCCESSOR", re.IGNORECASE),
    "late": re.compile(r"LATE|SLA\s+VIOLATION|BEHIND\s+SCHEDULE", re.IGNORECASE),
}


def extract_all(patterns: dict[str, re.Pattern[str]], text: str) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    for name, pattern in patterns.items():
        matches = pattern.findall(text)
        if matches:
            if isinstance(matches[0], tuple):
                results[name] = [" ".join(m) if isinstance(m, tuple) else str(m) for m in matches]
            else:
                results[name] = [str(m) for m in matches]
    return results


def parse_jes_log(text: str) -> dict[str, Any]:
    return extract_all(JES_PATTERNS, text)


def parse_abend_log(text: str) -> dict[str, Any]:
    return extract_all(ABEND_PATTERNS, text)


def parse_db2_log(text: str) -> dict[str, Any]:
    return extract_all(DB2_PATTERNS, text)


def parse_mq_log(text: str) -> dict[str, Any]:
    return extract_all(MQ_PATTERNS, text)


def parse_cics_log(text: str) -> dict[str, Any]:
    return extract_all(CICS_PATTERNS, text)


def parse_jcl(text: str) -> dict[str, Any]:
    return extract_all(JCL_PATTERNS, text)


def parse_cobol(text: str) -> dict[str, Any]:
    return extract_all(COBOL_PATTERNS, text)


def parse_scheduler_log(text: str) -> dict[str, Any]:
    return extract_all(SCHEDULER_PATTERNS, text)
