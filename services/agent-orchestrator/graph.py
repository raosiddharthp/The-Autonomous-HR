import logging
from langgraph.graph import StateGraph, END
from state import AgentState, Intent, DecisionOutcome
from nodes.ingest import ingest_node
from nodes.classify import classify_node
from nodes.tool_call import tool_call_node
from nodes.confidence_check import confidence_check_node
from nodes.respond import respond_node

logger = logging.getLogger(__name__)


def route_after_classify(state: AgentState) -> str:
    """Route to tool_call for actionable intents, straight to respond for unknown."""
    if state.intent == Intent.UNKNOWN:
        return "respond"
    return "tool_call"


def route_after_confidence(state: AgentState) -> str:
    """Always go to respond — confidence_check sets hitl_required flag."""
    return "respond"


def build_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("ingest", ingest_node)
    workflow.add_node("classify", classify_node)
    workflow.add_node("tool_call", tool_call_node)
    workflow.add_node("confidence_check", confidence_check_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("ingest")

    workflow.add_edge("ingest", "classify")

    workflow.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "tool_call": "tool_call",
            "respond": "respond",
        }
    )

    workflow.add_edge("tool_call", "confidence_check")

    workflow.add_conditional_edges(
        "confidence_check",
        route_after_confidence,
        {
            "respond": "respond",
        }
    )

    workflow.add_edge("respond", END)

    return workflow.compile()


# Compile once at module load — reused across requests
agent_graph = build_graph()
