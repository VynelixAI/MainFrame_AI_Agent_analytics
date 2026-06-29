# S0C7 Data Exception Recovery

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
