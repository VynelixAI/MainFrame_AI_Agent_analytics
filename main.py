"""FastAPI application for Mainframe AI Copilot."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import Response

from config import ensure_directories, get_settings
from graph.workflow import get_investigation_graph
from models.incident import InvestigationRequest
from rag.knowledge_base import get_knowledge_base
from utils.logging_config import logger
from utils.metrics import PrometheusMiddleware, metrics_response, record_investigation
from utils.telemetry import setup_telemetry

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_directories()
    setup_telemetry()
    kb = get_knowledge_base()
    kb.initialize()
    logger.info("%s v%s started", settings.app_name, settings.app_version)
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-Powered Mainframe Operations Copilot for autonomous incident investigation",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PrometheusMiddleware)


class InvestigationResponse(BaseModel):
    incident_id: str
    status: str = "completed"
    incident_report: dict[str, Any] = Field(default_factory=dict)
    runbook: dict[str, Any] = Field(default_factory=dict)
    guardrail: dict[str, Any] = Field(default_factory=dict)
    agent_results: list[dict[str, Any]] = Field(default_factory=list)
    rag_context: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_available: bool


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        llm_available=settings.llm_available,
    )


@app.post(f"{settings.api_prefix}/investigate", response_model=InvestigationResponse, tags=["Investigation"])
async def investigate(request: InvestigationRequest) -> InvestigationResponse:
    start = time.perf_counter()
    try:
        graph = get_investigation_graph()
        result = graph.investigate(request)
        record_investigation(time.perf_counter() - start, success=True)
        return InvestigationResponse(
            incident_id=result.get("incident_id", request.incident_id),
            incident_report=result.get("incident_report", {}),
            runbook=result.get("runbook", {}),
            guardrail=result.get("guardrail_result", {}),
            agent_results=result.get("agent_results", []),
            rag_context=result.get("rag_context", []),
        )
    except Exception as exc:
        record_investigation(time.perf_counter() - start, success=False)
        logger.exception("Investigation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(f"{settings.api_prefix}/investigate/upload", response_model=InvestigationResponse, tags=["Investigation"])
async def investigate_upload(
    job_name: str = "",
    application: str = "",
    description: str = "",
    jes_log: UploadFile | None = File(None),
    sysout: UploadFile | None = File(None),
    abend_log: UploadFile | None = File(None),
    jcl: UploadFile | None = File(None),
    cobol_source: UploadFile | None = File(None),
    db2_log: UploadFile | None = File(None),
    mq_log: UploadFile | None = File(None),
    cics_log: UploadFile | None = File(None),
    scheduler_log: UploadFile | None = File(None),
) -> InvestigationResponse:
    async def read_file(f: UploadFile | None) -> str:
        if f is None:
            return ""
        content = await f.read()
        return content.decode("utf-8", errors="replace")

    request = InvestigationRequest(
        job_name=job_name,
        application=application,
        description=description,
        jes_log=await read_file(jes_log),
        sysout=await read_file(sysout),
        abend_log=await read_file(abend_log),
        jcl=await read_file(jcl),
        cobol_source=await read_file(cobol_source),
        db2_log=await read_file(db2_log),
        mq_log=await read_file(mq_log),
        cics_log=await read_file(cics_log),
        scheduler_log=await read_file(scheduler_log),
    )
    return await investigate(request)


@app.get(f"{settings.api_prefix}/history", tags=["Investigation"])
async def get_history(limit: int = 50) -> list[dict[str, Any]]:
    from agents.memory import get_memory

    return get_memory().get_history(limit)


@app.get(f"{settings.api_prefix}/knowledge/search", tags=["Knowledge"])
async def search_knowledge(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    kb = get_knowledge_base()
    return kb.search(query, top_k)


@app.get("/metrics", tags=["Observability"])
async def metrics() -> Response:
    return metrics_response()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.api_host, port=settings.api_port, reload=settings.debug)
