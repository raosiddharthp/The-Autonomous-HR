import logging
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../rag-indexer'))
from state import AgentState, Intent, DecisionOutcome, PolicyRef
from retriever import retrieve
from tools.leave_engine import run_leave_engine

logger = logging.getLogger(__name__)


def tool_call_node(state: AgentState) -> AgentState:
    state.log_step("tool_call")
    logger.info(f"[{state.correlation_id}] tool_call: intent={state.intent}")

    if state.intent == Intent.LEAVE_REQUEST:
        # RAG: retrieve relevant policy chunks
        query = f"{state.slots.leave_type or 'casual'} leave policy entitlement rules"
        refs = retrieve(query)
        state.policy_refs = [PolicyRef(**r) for r in refs]
        # Real leave engine
        state = run_leave_engine(state)
        logger.info(f"[{state.correlation_id}] tool_call: leave decision={state.decision}")

    elif state.intent == Intent.BALANCE_QUERY:
        from tools.leave_engine import lookup_employee, get_leave_balance, get_db
        db = get_db()
        employee = lookup_employee(db, state.worker_wa_id)
        if employee:
            balance = get_leave_balance(db, employee["employee_id"])
            state.leave_balance = {
                "casual": balance.get("casual", 0),
                "sick": balance.get("sick", 0),
                "earned": balance.get("earned", 0),
                "unpaid": balance.get("unpaid", 0),
            }
            state.worker_id = employee["employee_id"]
        state.decision = DecisionOutcome.PENDING
        logger.info(f"[{state.correlation_id}] tool_call: balance={state.leave_balance}")

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
