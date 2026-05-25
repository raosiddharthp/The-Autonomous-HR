import logging
from state import AgentState, Intent, DecisionOutcome

logger = logging.getLogger(__name__)

RESPONSES = {
    Intent.LEAVE_REQUEST: {
        DecisionOutcome.APPROVE: "Your leave request has been approved. ✅",
        DecisionOutcome.DENY: "Your leave request has been denied. Please contact HR for details.",
        DecisionOutcome.ESCALATE: "Your leave request has been sent to your HR manager for review.",
        DecisionOutcome.PENDING: "Your leave request is being processed. You will hear back shortly.",
    },
    Intent.BALANCE_QUERY: {
        DecisionOutcome.PENDING: (
            "Your current leave balance:\n"
            "• Casual: {casual} days\n"
            "• Sick: {sick} days\n"
            "• Earned: {earned} days"
        ),
    },
    Intent.PAYROLL_QUERY: {
        DecisionOutcome.PENDING: "Your payroll query has been logged. HR will respond within 24 hours.",
    },
    Intent.GRIEVANCE_LOG: {
        DecisionOutcome.ESCALATE: (
            "Your grievance has been logged and escalated to HR. "
            "Reference ID: {correlation_id}. "
            "You will be contacted within 48 hours."
        ),
    },
    Intent.POLICY_QUESTION: {
        DecisionOutcome.PENDING: "Here is what the policy says: {policy_summary}",
    },
    Intent.UNKNOWN: {
        DecisionOutcome.PENDING: (
            "I didn't quite understand that. You can ask me about:\n"
            "• Leave requests\n"
            "• Leave balance\n"
            "• Salary queries\n"
            "• HR policy questions"
        ),
    },
}


def respond_node(state: AgentState) -> AgentState:
    """
    Respond node: builds the final response_text from state.
    If HITL is required, builds the employer brief instead
    and sets response_text to an acknowledgement for the worker.
    """
    state.log_step("respond")
    logger.info(
        f"[{state.correlation_id}] respond: "
        f"intent={state.intent} decision={state.decision} hitl={state.hitl_required}"
    )

    if state.hitl_required:
        state.response_text = (
            "Your request requires review by your HR manager. "
            f"Reference: {state.correlation_id}. "
            "You will receive a response within 24 hours."
        )
        logger.info(f"[{state.correlation_id}] respond: HITL acknowledgement sent")
        return state

    intent = state.intent or Intent.UNKNOWN
    decision = state.decision or DecisionOutcome.PENDING

    template_map = RESPONSES.get(intent, RESPONSES[Intent.UNKNOWN])
    template = template_map.get(decision, RESPONSES[Intent.UNKNOWN][DecisionOutcome.PENDING])

    balance = state.leave_balance or {}
    policy_summary = (
        state.policy_refs[0].excerpt if state.policy_refs else "No policy found."
    )

    state.response_text = template.format(
        casual=balance.get("casual", "?"),
        sick=balance.get("sick", "?"),
        earned=balance.get("earned", "?"),
        correlation_id=state.correlation_id,
        policy_summary=policy_summary,
    )

    logger.info(f"[{state.correlation_id}] respond: response built")
    return state
