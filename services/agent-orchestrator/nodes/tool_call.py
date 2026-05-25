import logging
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../rag-indexer'))
from state import AgentState, Intent, DecisionOutcome, PolicyRef
from retriever import retrieve

logger = logging.getLogger(__name__)


def tool_call_node(state: AgentState) -> AgentState:
    """
    Tool call node: dispatches to the appropriate tool based
    on intent. RAG retriever wired for policy/leave intents.
    Leave engine stub — replaced in S-16.
    """
    state.log_step("tool_call")
    logger.info(f"[{state.correlation_id}] tool_call: intent={state.intent}")

    if state.intent == Intent.LEAVE_REQUEST:
        state.leave_balance = {"casual": 8, "sick": 5, "earned": 12}
        # RAG: retrieve policy for this leave type
        query = f"{state.slots.leave_type or 'casual'} leave policy entitlement rules"
        refs = retrieve(query)
        state.policy_refs = [PolicyRef(**r) for r in refs]
        state.decision = DecisionOutcome.PENDING
        state.decision_reasoning = "Leave engine not yet wired — stub response"
        logger.info(f"[{state.correlation_id}] tool_call: leave + {len(refs)} policy refs")

    elif state.intent == Intent.BALANCE_QUERY:
        state.leave_balance = {"casual": 8, "sick": 5, "earned": 12}
        state.decision = DecisionOutcome.PENDING
        logger.info(f"[{state.correlation_id}] tool_call: balance stub invoked")

    elif state.intent == Intent.POLICY_QUESTION:
        query = state.raw_text or "HR policy"
        refs = retrieve(query)
        state.policy_refs = [PolicyRef(**r) for r in refs]
        state.decision = DecisionOutcome.PENDING
        logger.info(f"[{state.correlation_id}] tool_call: policy + {len(refs)} refs")

    elif state.intent == Intent.GRIEVANCE_LOG:
        state.decision = DecisionOutcome.ESCALATE
        state.decision_reasoning = "Grievances always escalate to HR manager"
        logger.info(f"[{state.correlation_id}] tool_call: grievance -> escalate")

    else:
        state.decision = DecisionOutcome.PENDING
        logger.info(f"[{state.correlation_id}] tool_call: no tool for intent={state.intent}")

    return state
