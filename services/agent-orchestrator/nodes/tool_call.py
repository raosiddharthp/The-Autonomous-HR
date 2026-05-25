import logging
from state import AgentState, Intent, DecisionOutcome

logger = logging.getLogger(__name__)


def tool_call_node(state: AgentState) -> AgentState:
    """
    Tool call node: dispatches to the appropriate tool based
    on intent. Real tools wired in S-15 (RAG) and S-16
    (leave engine). Stubs return safe defaults for now.
    """
    state.log_step("tool_call")
    logger.info(f"[{state.correlation_id}] tool_call: intent={state.intent}")

    if state.intent == Intent.LEAVE_REQUEST:
        # Stub — real leave engine in S-16
        state.leave_balance = {"casual": 8, "sick": 5, "earned": 12}
        state.decision = DecisionOutcome.PENDING
        state.decision_reasoning = "Leave engine not yet wired — stub response"
        logger.info(f"[{state.correlation_id}] tool_call: leave stub invoked")

    elif state.intent == Intent.BALANCE_QUERY:
        # Stub — real Firestore lookup in S-16
        state.leave_balance = {"casual": 8, "sick": 5, "earned": 12}
        state.decision = DecisionOutcome.PENDING
        logger.info(f"[{state.correlation_id}] tool_call: balance stub invoked")

    elif state.intent == Intent.POLICY_QUESTION:
        # Stub — real RAG retriever in S-15
        state.policy_refs = []
        state.decision = DecisionOutcome.PENDING
        logger.info(f"[{state.correlation_id}] tool_call: policy stub invoked")

    elif state.intent == Intent.GRIEVANCE_LOG:
        state.decision = DecisionOutcome.ESCALATE
        state.decision_reasoning = "Grievances always escalate to HR manager"
        logger.info(f"[{state.correlation_id}] tool_call: grievance -> escalate")

    else:
        state.decision = DecisionOutcome.PENDING
        logger.info(f"[{state.correlation_id}] tool_call: no tool for intent={state.intent}")

    return state
