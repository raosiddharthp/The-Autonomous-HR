import logging
from state import AgentState, DecisionOutcome
from tools.hitl_packager import package_and_queue

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.8


def confidence_check_node(state: AgentState) -> AgentState:
    """
    Confidence check node: computes overall confidence score,
    sets hitl_required flag, and if HITL is needed packages
    the employer brief into Firestore hitl_queue.
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

    # Package and queue HITL brief if required
    if state.hitl_required:
        try:
            doc_id = package_and_queue(state)
            logger.info(f"[{state.correlation_id}] confidence_check: HITL brief queued as {doc_id}")
        except Exception as e:
            logger.error(f"[{state.correlation_id}] confidence_check: HITL queue failed: {e}")
            state.log_error(f"hitl_queue_failed: {e}")

    return state
