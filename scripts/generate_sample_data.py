#!/usr/bin/env python3
"""Generate realistic enterprise mainframe sample data."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SAMPLE = BASE / "sample_data"
LOGS = BASE / "logs"
KNOWLEDGE = BASE / "knowledge"

JOBS = [
    ("CLMDAY01", "Claims Daily Batch"), ("BILDAY02", "Billing Cycle"),
    ("PAYWEEK1", "Weekly Payments"), ("POLREN01", "Policy Renewal"),
    ("CUSMAST1", "Customer Master"), ("ENRMBR01", "Member Enrollment"),
    ("INVCNT01", "Inventory Count"), ("PRLPAY01", "Payroll Processing"),
    ("FINGL001", "GL Posting"), ("HLTCLM01", "Healthcare Claims"),
    ("CLMADJ01", "Claims Adjudication"), ("BILINV02", "Invoice Generation"),
    ("PAYACH01", "ACH Disbursement"), ("POLUND01", "Policy Underwriting"),
    ("CUSADDR1", "Address Maintenance"), ("ENRELIG1", "Eligibility Check"),
]

ABEND_CODES = ["S0C7", "S0C4", "S0C1", "S806", "S322", "U0999", "U4038", "SOCB", "S013"]
SQLCODES = [-904, -911, -913, -805, -803, -305, -180, -181, -204, -302]
MQ_CODES = ["AMQ9503", "AMQ9208", "AMQ9641", "AMQ9777", "AMQ7469"]
CICS_CODES = ["AEI0", "AEY9", "APCT", "AICA", "AKCP"]


def ts(offset_min: int = 0) -> str:
    t = datetime.now() - timedelta(minutes=offset_min)
    return t.strftime("%y.%j %H:%M:%S")


def gen_jes_log(job: str, abend: str = "", rc: int = 8) -> str:
    jid = f"JOB{random.randint(10000, 99999)}"
    step = random.choice(["STEP010", "STEP020", "STEP030", "STEP040", "STEP050"])
    lines = [
        f"1JOB NAME  LINE 00000000 COMMAND INPUT ===>                                  ",
        f"  ICH408I USER BATCHID  HAS NO ACCESS TO DATASET PROD.CLMS.INPUT(+1)",
        f"  IEF236I ALLOC. FOR {job}     {jid}",
        f"  IEF237I JES2 ALLOCATED TO {job}",
        f"  IEF403I {job}     - STARTED - TIME={ts(30)}",
        f"  IEF285I   DD NAME STEPLIB  DSNAME=PROD.LOADLIB.CLAIMS",
        f"  IEF285I   DD NAME SYSIN    DSNAME=PROD.JCL.CNTL({job})",
        f"  IEF272I {job}     - ELAPSED TIME=00:12:34",
        f"  IEF450I {job}     - CPU TIME=45.23",
    ]
    if abend:
        lines.extend([
            f"  IEC141I  DSN=PROD.BILLING.OUTPUT(+0), UNIT=3390, VOL=SER=PROD01",
            f"  IEA995I  VOLUME PROD01 NOT AVAILABLE ON DEVICE 3390",
            f"  IEF450I {job}     - ABEND CODE={abend}",
            f"  CSV003I  RACF AUTHORIZATION CHECK FAILED FOR DATASET PROD.FINANCE.GL",
        ])
    lines.extend([
        f"  IEF142I {job}     - STEP {step} - COND CODE {rc:04d}",
        f"  IEF404I {job}     - ENDED  - TIME={ts(0)}",
    ])
    return "\n".join(lines)


def gen_abend_log(job: str, code: str) -> str:
    prog = f"PGM{job[:6]}"
    offset = f"{random.randint(0x1000, 0xFFFF):04X}"
    return f"""CEE3202S The thread terminated abnormally with signal SIGSEGV.
CEE3250C The {prog} program was executing at entry point {prog} at offset {offset}.
CEE3250C The program was compiled with ARCH(11).
ABEND CODE: {code}
PROGRAM {prog} AT ENTRY POINT {prog}
OFFSET {offset}
PSA KEY=00000000
JOBNAME={job}
STEPNAME=STEP020
DSN SYSTEM(DSNP)
  PLAN(PLAN{job[:4]}) LIB(PROD.DBRMLIB.DATA)
SQLCODE=-911 SQLSTATE=40001 REASON=00C90088
IEC130I DDNAME=INPUT01  DSN=PROD.{job[:3]}.INPUT(+1) NOT FOUND
IGD17101I INSUFFICIENT SPACE ON VOLUME PROD01 FOR DATASET PROD.WORK.TEMP
"""


def gen_cobol(name: str, domain: str) -> str:
    return f"""       IDENTIFICATION DIVISION.
       PROGRAM-ID. {name}.
      * {domain} Processing Module
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT INPUT-FILE  ASSIGN TO INFILE
               ORGANIZATION IS SEQUENTIAL.
           SELECT OUTPUT-FILE ASSIGN TO OUTFILE
               ORGANIZATION IS SEQUENTIAL.
       DATA DIVISION.
       FILE SECTION.
       FD  INPUT-FILE.
       01  INPUT-RECORD         PIC X(500).
       FD  OUTPUT-FILE.
       01  OUTPUT-RECORD        PIC X(500).
       WORKING-STORAGE SECTION.
       01  WS-COUNT             PIC 9(9) COMP VALUE ZERO.
       01  WS-SQLCODE           PIC S9(9) COMP.
       01  WS-RETURN-CODE       PIC S9(4) COMP VALUE ZERO.
           EXEC SQL INCLUDE SQLCA END-EXEC.
           EXEC SQL INCLUDE {name[:6]}D END-EXEC.
       PROCEDURE DIVISION.
       0000-MAIN-PROCESS.
           PERFORM 1000-INITIALIZE
           PERFORM 2000-PROCESS-RECORDS UNTIL WS-EOF = 'Y'
           PERFORM 9000-FINALIZE
           GOBACK.
       1000-INITIALIZE.
           OPEN INPUT INPUT-FILE
           OPEN OUTPUT OUTPUT-FILE
           CALL 'SUBVAL01' USING WS-RETURN-CODE.
       2000-PROCESS-RECORDS.
           READ INPUT-FILE AT END MOVE 'Y' TO WS-EOF
           EXEC SQL
               SELECT COUNT(*) INTO :WS-COUNT
               FROM PROD.{domain}_TABLE
               WHERE STATUS = 'A'
           END-EXEC
           PERFORM 2100-VALIDATE-DATA
           PERFORM 2200-WRITE-OUTPUT.
       2100-VALIDATE-DATA.
           IF WS-AMOUNT NOT NUMERIC
               CALL 'CEE3ABD' USING 999
           END-IF.
       2200-WRITE-OUTPUT.
           WRITE OUTPUT-RECORD FROM INPUT-RECORD.
       9000-FINALIZE.
           CLOSE INPUT-FILE OUTPUT-FILE.
"""


def gen_jcl(name: str, util: str) -> str:
    templates = {
        "IDCAMS": f"""//{name}   JOB (ACCT),'IDCAMS REPRO',CLASS=A,MSGCLASS=X,NOTIFY=&SYSUID
//STEP010  EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  REPRO INDATASET(PROD.BACKUP.INPUT) -
        OUTDATASET(PROD.BACKUP.OUTPUT) REPLACE
/*
""",
        "SORT": f"""//{name}   JOB (ACCT),'SORT JOB',CLASS=A,MSGCLASS=X
//STEP010  EXEC PGM=SORT
//SORTIN   DD DSN=PROD.{name[:3]}.INPUT,DISP=SHR
//SORTOUT  DD DSN=PROD.{name[:3]}.SORTED(+1),DISP=(NEW,CATLG,DELETE),
//            SPACE=(CYL,(100,50),RLSE),UNIT=3390
//SYSIN    DD *
  SORT FIELDS=(1,10,CH,A)
/*
""",
        "IKJEFT01": f"""//{name}   JOB (ACCT),'DB2 BATCH',CLASS=A,MSGCLASS=X
//STEP010  EXEC PGM=IKJEFT01,DYNAMNBR=20
//STEPLIB  DD DSN=PROD.DBRMLIB.LOAD,DISP=SHR
//SYSTSPRT DD SYSOUT=*
//SYSTSIN  DD *
  DSN SYSTEM(DSNP)
  RUN PROGRAM(PGM{name[:4]}) PLAN(PLAN{name[:4]})
/*
""",
        "DSNUTILB": f"""//{name}   JOB (ACCT),'DB2 REORG',CLASS=A,MSGCLASS=X
//STEP010  EXEC PGM=DSNUTILB,REGION=0M
//STEPLIB  DD DSN=SYS1.SDSNLOAD,DISP=SHR
//SYSUT1   DD UNIT=3390,SPACE=(CYL,(500,100))
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  REORG TABLESPACE PROD.{name[:3]}.TS001
  SHRLEVEL CHANGE
/*
""",
    }
    return templates.get(util, templates["IKJEFT01"])


def gen_db2_log(job: str, sqlcode: int) -> str:
    return f"""DSN SYSTEM(DSNP)
DSN COMMAND DISPLAY THREAD(*) DETAIL
JOBNAME={job} AUTHID=BATCHID PLAN=PLAN{job[:4]}
SQLCODE={sqlcode} SQLSTATE=40001 REASON=00C90088
DSNR040I NOT FOUND PLAN PLAN{job[:4]} IN COLLECTION PROD
DEADLOCK DETECTED ON TABLE PROD.CLAIMS.MASTER
LOCK TIMEOUT EXPIRED WAITING FOR RESOURCE
"""


def gen_mq_log(code: str) -> str:
    return f"""{code}E Channel 'TO.PAYMENTS' is stopped.
AMQ9208E Channel 'FROM.CLAIMS' is in RETRYING state.
AMQ9503E Queue 'PAYMENT.REQUEST' is full. MaxMsgLen=4194304 MaxDepth=500000
AMQ9641E Channel connection failed for channel 'BANK.ACH.OUT'.
AMQ9777E Message persistence error on queue manager QM1.
AMQ7469W Dead letter queue DLQ.PAYMENTS has exceeded threshold.
LISTENER TCP.LISTENER01 STOPPED - NOT STARTED
"""


def gen_cics_log(code: str) -> str:
    trans = random.choice(["CLM1", "BIL2", "PAY3", "POL4"])
    return f"""DFHAP0001 CICS Region CICSPROD - Transaction {trans} ABEND {code}
DFHAC2236 Transaction {trans} program PGM{trans} not found in CSD
RESP=13 NOTFND - Record not found in file CLMMAST
RESP=14 DUPKEY - Duplicate key on WRITE to BILFILE
REGION CICSPROD DOWN - STOPPED BY OPERATOR
TRANSACTION {trans} PURGED BY SYSTEM
"""


def gen_scheduler_log(job: str, sched: str) -> str:
  templates = {
      "CA7": f"CA-7 SCHID=001 JOB={job} STATUS=FAILED RC=0012\nDEPENDENCY PREDECESSOR CLMPRE01 NOT MET FAILED",
      "ControlM": f"CONTROL-M ORDER ID 00A1B JOBNAME {job} STATUS ENDED NOT OK\nLATE SLA VIOLATION JOB {job} BEHIND SCHEDULE",
      "TWS": f"TWS TRCJOB {job} STATUS ABEND\nPREDECESSOR JOB CLMDEP01 INCOMPLETE",
  }
  return templates.get(sched, templates["CA7"])


def gen_runbook(rb_id: str, title: str) -> str:
    return f"""# {title}

## Steps
- Acknowledge incident and notify application team
- Collect JES log, SYSOUT, and dump datasets
- Analyze ABEND code and offset in program
- Verify dataset allocations and GDG generations
- Apply corrective action per recovery procedure
- Obtain manager approval for job restart
- Restart job from failing step
- Validate output and release dependent jobs

## Commands
- S JES2,O JOB=<JOBNAME>
- //DISPLAY JOB=<JOBNAME>
- -DIS THREAD(*) DETAIL

## Validation
- Confirm job completed RC=0000
- Verify output record counts
- Check downstream scheduler dependencies

## Preventive
- Update monitoring thresholds
- Review and update operational runbook
- Schedule code review for affected module
"""


def gen_knowledge_docs() -> None:
    docs = {
        "ABEND/S0C7-manual.md": "S0C7 Data Exception: Invalid packed decimal data during arithmetic. Common in billing batch.",
        "ABEND/S0C4-manual.md": "S0C4 Protection Exception: Storage violation. Analyze CEEDUMP for failing address.",
        "JCL/JCL-Reference.md": "JCL DD DISP parameters: SHR, OLD, NEW, MOD, CATLG, DELETE, KEEP, PASS.",
        "COBOL/COBOL-Best-Practices.md": "COBOL best practices: Initialize working storage, validate numeric fields, use EXEC SQL WHENEVER.",
        "DB2/DB2-Error-Manual.md": "SQLCODE -911 deadlock, -913 lock timeout, -805 package not found.",
        "MQ/MQ-Error-Manual.md": "AMQ9503 queue full, AMQ9208 channel stopped.",
        "CICS/CICS-Error-Manual.md": "CICS AEI0 program check, APCT program not found.",
    }
    for path, content in docs.items():
        p = KNOWLEDGE / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {path}\n\n{content}\n")


def main() -> None:
    random.seed(42)
    for d in [SAMPLE, LOGS / "jes", LOGS / "abend", LOGS / "db2", LOGS / "mq",
              LOGS / "cics", LOGS / "scheduler", SAMPLE / "cobol", SAMPLE / "jcl",
              KNOWLEDGE / "COBOL", KNOWLEDGE / "JCL", KNOWLEDGE / "RUNBOOKS",
              KNOWLEDGE / "ABEND", KNOWLEDGE / "DB2", KNOWLEDGE / "MQ", KNOWLEDGE / "CICS"]:
        d.mkdir(parents=True, exist_ok=True)

    # 25 JES logs
    for i in range(25):
        job, _ = random.choice(JOBS)
        abend = random.choice(ABEND_CODES) if i % 3 == 0 else ""
        rc = random.choice([0, 4, 8, 12]) if not abend else 12
        (LOGS / "jes" / f"jes_{job}_{i:03d}.log").write_text(gen_jes_log(job, abend, rc))

    # 50 ABEND logs
    for i in range(50):
        job, _ = random.choice(JOBS)
        code = ABEND_CODES[i % len(ABEND_CODES)]
        (LOGS / "abend" / f"abend_{code}_{i:03d}.log").write_text(gen_abend_log(job, code))

    # 15 COBOL programs
    domains = ["Claims", "Billing", "Payments", "Policy", "Customer", "Enrollment",
               "Inventory", "Payroll", "Finance", "Healthcare", "Claims", "Billing",
               "Payments", "Policy", "Customer"]
    for i, domain in enumerate(domains):
        name = f"PGM{domain[:3].upper()}{i:02d}"
        (SAMPLE / "cobol" / f"{name}.cbl").write_text(gen_cobol(name, domain.upper()))
        (KNOWLEDGE / "COBOL" / f"{name}.cbl").write_text(gen_cobol(name, domain.upper()))

    # 40 JCLs
    utils = ["IDCAMS", "SORT", "IKJEFT01", "DSNUTILB"] * 10
    for i in range(40):
        job, _ = JOBS[i % len(JOBS)]
        (SAMPLE / "jcl" / f"{job}_{utils[i]}_{i:03d}.jcl").write_text(gen_jcl(job, utils[i]))
        (KNOWLEDGE / "JCL" / f"{job}_{utils[i]}_{i:03d}.jcl").write_text(gen_jcl(job, utils[i]))

    # DB2 errors
    for i, sqlcode in enumerate(SQLCODES * 3):
        job, _ = random.choice(JOBS)
        (LOGS / "db2" / f"db2_{sqlcode}_{i:03d}.log").write_text(gen_db2_log(job, sqlcode))

    # MQ logs
    for i, code in enumerate(MQ_CODES * 4):
        (LOGS / "mq" / f"mq_{code}_{i:03d}.log").write_text(gen_mq_log(code))

    # CICS logs
    for i, code in enumerate(CICS_CODES * 4):
        (LOGS / "cics" / f"cics_{code}_{i:03d}.log").write_text(gen_cics_log(code))

    # Scheduler logs
    for i in range(20):
        job, _ = random.choice(JOBS)
        sched = ["CA7", "ControlM", "TWS"][i % 3]
        (LOGS / "scheduler" / f"sched_{sched}_{i:03d}.log").write_text(gen_scheduler_log(job, sched))

    # Runbooks
    runbooks = [
        ("RB-ABEND-S0C4", "S0C4 Protection Exception Recovery"),
        ("RB-ABEND-S0C7", "S0C7 Data Exception Recovery"),
        ("RB-ABEND-S0C1", "S0C1 Operation Exception Recovery"),
        ("RB-ABEND-S806", "S806 Module Not Found Recovery"),
        ("RB-DB2-DEADLOCK", "DB2 Deadlock Recovery"),
        ("RB-DB2-LOCKTIMEOUT", "DB2 Lock Timeout Recovery"),
        ("RB-MQ-QUEUE-FULL", "MQ Queue Full Recovery"),
        ("RB-MQ-CHANNEL", "MQ Channel Recovery"),
        ("RB-CICS-ABEND", "CICS Transaction Abend Recovery"),
        ("RB-GENERAL-ABEND", "General ABEND Recovery"),
        ("RB-GENERAL-INCIDENT", "General Incident Response"),
    ]
    for rb_id, title in runbooks:
        (KNOWLEDGE / "RUNBOOKS" / f"{rb_id}.md").write_text(gen_runbook(rb_id, title))

    gen_knowledge_docs()
    print(f"Generated sample data in {SAMPLE} and {LOGS}")


if __name__ == "__main__":
    main()
