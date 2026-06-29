"""LangGraph multi-agent investigation workflow."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, StateGraph

from agents.abend_agent import AbendAgent
from agents.cics_agent import CICSAgent
from agents.cobol_agent import COBOLAgent
from agents.db2_agent import DB2Agent
from agents.guardrail_agent import GuardrailAgent
from agents.incident_agent import IncidentAgent
from agents.jcl_agent import JCLAgent
from agents.jes_agent import JESAgent
from agents.memory import get_memory
from agents.mq_agent import MQAgent
from agents.planner import PlannerAgent
from agents.runbook_agent import RunbookAgent
from agents.scheduler_agent import SchedulerAgent
from models.incident import InvestigationRequest, InvestigationState
from rag.knowledge_base import get_knowledge_base
from utils.logging_config import logger
from utils.telemetry import trace_span


class InvestigationGraph:
    """LangGraph orchestration for mainframe incident investigation."""

    def __init__(self) -> None:
        self.planner = PlannerAgent()
        self.jes_agent = JESAgent()
        self.abend_agent = AbendAgent()
        self.jcl_agent = JCLAgent()
        self.cobol_agent = COBOLAgent()
        self.db2_agent = DB2Agent()
        self.mq_agent = MQAgent()
        self.scheduler_agent = SchedulerAgent()
        self.cics_agent = CICSAgent()
        self.guardrail_agent = GuardrailAgent()
        self.incident_agent = IncidentAgent()
        self.runbook_agent = RunbookAgent()
        self.memory = get_memory()
        self.kb = get_knowledge_base()
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        graph = StateGraph(dict)

        graph.add_node("planner", self._node_planner)
        graph.add_node("jes_agent", self._node_jes)
        graph.add_node("abend_agent", self._node_abend)
        graph.add_node("jcl_agent", self._node_jcl)
        graph.add_node("cobol_agent", self._node_cobol)
        graph.add_node("db2_agent", self._node_db2)
        graph.add_node("mq_agent", self._node_mq)
        graph.add_node("scheduler_agent", self._node_scheduler)
        graph.add_node("cics_agent", self._node_cics)
        graph.add_node("guardrail_agent", self._node_guardrail)
        graph.add_node("incident_agent", self._node_incident)
        graph.add_node("runbook_agent", self._node_runbook)

        graph.set_entry_point("planner")
        graph.add_edge("planner", "jes_agent")
        graph.add_edge("jes_agent", "abend_agent")
        graph.add_edge("abend_agent", "jcl_agent")
        graph.add_edge("jcl_agent", "cobol_agent")
        graph.add_edge("cobol_agent", "db2_agent")
        graph.add_edge("db2_agent", "mq_agent")
        graph.add_edge("mq_agent", "scheduler_agent")
        graph.add_edge("scheduler_agent", "cics_agent")
        graph.add_edge("cics_agent", "guardrail_agent")
        graph.add_edge("guardrail_agent", "incident_agent")
        graph.add_edge("incident_agent", "runbook_agent")
        graph.add_edge("runbook_agent", END)

        return graph.compile()

    def _run_agent(self, agent: Any, state: dict[str, Any], result_key: str) -> dict[str, Any]:
        request = InvestigationRequest(**state["request"])
        result = agent.run(request, state)
        state[result_key] = result.findings
        state["agent_results"] = state.get("agent_results", []) + [result.model_dump()]
        state["completed_steps"] = state.get("completed_steps", []) + [agent.name]
        state["current_step"] = agent.name
        return state

    def _node_planner(self, state: dict[str, Any]) -> dict[str, Any]:
        with trace_span("graph.planner"):
            request = InvestigationRequest(**state["request"])
            query = f"{request.job_name} {request.description} {request.abend_log[:200]}"
            state["rag_context"] = self.kb.get_context_for_investigation(query)
            result = self.planner.run(request, state)
            state["planner_output"] = result.findings
            state["incident_id"] = request.incident_id
            state["agent_results"] = [result.model_dump()]
            state["completed_steps"] = ["planner"]
            return state

    def _node_jes(self, state: dict[str, Any]) -> dict[str, Any]:
        return self._run_agent(self.jes_agent, state, "jes_analysis")

    def _node_abend(self, state: dict[str, Any]) -> dict[str, Any]:
        return self._run_agent(self.abend_agent, state, "abend_analysis")

    def _node_jcl(self, state: dict[str, Any]) -> dict[str, Any]:
        return self._run_agent(self.jcl_agent, state, "jcl_analysis")

    def _node_cobol(self, state: dict[str, Any]) -> dict[str, Any]:
        return self._run_agent(self.cobol_agent, state, "cobol_analysis")

    def _node_db2(self, state: dict[str, Any]) -> dict[str, Any]:
        return self._run_agent(self.db2_agent, state, "db2_analysis")

    def _node_mq(self, state: dict[str, Any]) -> dict[str, Any]:
        return self._run_agent(self.mq_agent, state, "mq_analysis")

    def _node_scheduler(self, state: dict[str, Any]) -> dict[str, Any]:
        return self._run_agent(self.scheduler_agent, state, "scheduler_analysis")

    def _node_cics(self, state: dict[str, Any]) -> dict[str, Any]:
        return self._run_agent(self.cics_agent, state, "cics_analysis")

    def _node_guardrail(self, state: dict[str, Any]) -> dict[str, Any]:
        return self._run_agent(self.guardrail_agent, state, "guardrail_result")

    def _node_incident(self, state: dict[str, Any]) -> dict[str, Any]:
        return self._run_agent(self.incident_agent, state, "incident_report")

    def _node_runbook(self, state: dict[str, Any]) -> dict[str, Any]:
        state = self._run_agent(self.runbook_agent, state, "runbook")
        self.memory.cache_state(state["incident_id"], state)
        incident = state.get("incident_report", {})
        if incident:
            self.memory.store_investigation(incident)
        logger.info("Investigation %s completed", state["incident_id"])
        return state

    def investigate(self, request: InvestigationRequest) -> dict[str, Any]:
        with trace_span("investigation", {"incident_id": request.incident_id}):
            initial_state: dict[str, Any] = InvestigationState(request=request).model_dump()
            result = self._graph.invoke(initial_state)
            return result


_graph: InvestigationGraph | None = None


def get_investigation_graph() -> InvestigationGraph:
    global _graph
    if _graph is None:
        _graph = InvestigationGraph()
    return _graph


def reset_investigation_graph() -> None:
    """Reset graph singleton (for tests)."""
    global _graph
    _graph = None
