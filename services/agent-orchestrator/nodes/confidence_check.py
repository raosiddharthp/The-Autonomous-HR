import logging
from state import AgentState, DecisionOutcome

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.8


def confidence_check_node(state: AgentState) -> AgentState:
    """
    Confidence check node: computes overall confidence score
    and sets hitl_required flag if score is below threshold,
    decision is ESCALATE, or a grievance was logged.
    """
    state.log_step("confidence_check")

    # Compute composite confidence score
    intent_weight = 0.4
    decision_weight = 0.6

    decision_confidence = 1.0 if state.decision in (
        DecisionOutcome.APPROVE, DecisionOutcome.DENY
    ) else 0.5

    state.confidence_score = round(
        (state.intent_confidence * intent_weight) +
        (decision_confidence * decision_weight),
        4
    )

    logger.info(
        f"[{state.correlation_id}] confidence_check: "
        f"score={state.confidence_score} threshold={CONFIDENCE_THRESHOLD}"
    )

    # HITL triggers
    if state.decision == DecisionOutcome.ESCALATE:
        state.hitl_required = True
        state.hitl_reason = "Decision outcome is ESCALATE"

    elif state.confidence_score < CONFIDENCE_THRESHOLD:
        state.hitl_required = True
        state.hitl_reason = (
            f"Confidence score {state.confidence_score} "
            f"below threshold {CONFIDENCE_THRESHOLD}"
        )

    elif state.policy_refs and any(
        "legal" in ref.excerpt.lower() or "terminate" in ref.excerpt.lower()
        for ref in state.policy_refs
    ):
        state.hitl_required = True
        state.hitl_reason = "Legal clause detected in policy references"

    logger.info(
        f"[{state.correlation_id}] confidence_check: "
        f"hitl_required={state.hitl_required} reason={state.hitl_reason!r}"
    )

    return state
