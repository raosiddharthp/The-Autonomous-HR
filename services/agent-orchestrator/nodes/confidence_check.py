import logging
from state import AgentState, DecisionOutcome
from tools.hitl_packager import package_and_queue
from tools.audit_logger import write_audit_entry

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.8
AGENT_VERSION        = "ep3-v1"


def confidence_check_node(state: AgentState) -> AgentState:
    """
    Confidence check node: computes overall confidence score,
    sets hitl_required flag, packages HITL brief if needed,
    then writes an immutable audit log entry before returning.
    Audit log is written here — BEFORE respond node sends anything out.
    """
    state.log_step("confidence_check")

    # ── Composite confidence score ───────────────────────────────────────────
    decision_confidence = 1.0 if state.decision in (
        DecisionOutcome.APPROVE, DecisionOutcome.DENY
    ) else 0.5

    state.confidence_score = round(
        (state.intent_confidence * 0.4) +
        (decision_confidence * 0.6),
        4
    )

    logger.info(
        f"[{state.correlation_id}] confidence_check: "
        f"score={state.confidence_score} threshold={CONFIDENCE_THRESHOLD}"
    )

    # ── HITL triggers ────────────────────────────────────────────────────────
    if state.decision == DecisionOutcome.ESCALATE:
        state.hitl_required = True
        state.hitl_reason   = "Decision outcome is ESCALATE"

    elif state.confidence_score < CONFIDENCE_THRESHOLD:
        state.hitl_required = True
        state.hitl_reason   = (
            f"Confidence score {state.confidence_score} "
            f"below threshold {CONFIDENCE_THRESHOLD}"
        )

    elif state.policy_refs and any(
        "legal" in ref.excerpt.lower() or "terminate" in ref.excerpt.lower()
        for ref in state.policy_refs
    ):
        state.hitl_required = True
        state.hitl_reason   = "Legal clause detected in policy references"

    logger.info(
        f"[{state.correlation_id}] confidence_check: "
        f"hitl_required={state.hitl_required} reason={state.hitl_reason!r}"
    )

    # ── Queue HITL brief if required ─────────────────────────────────────────
    if state.hitl_required:
        try:
            doc_id = package_and_queue(state)
            logger.info(f"[{state.correlation_id}] HITL brief queued as {doc_id}")
        except Exception as e:
            logger.error(f"[{state.correlation_id}] HITL queue failed: {e}")
            state.log_error(f"hitl_queue_failed: {e}")

    # ── Audit log — written BEFORE respond node fires ────────────────────────
    policy_chunk_ids = [ref.chunk_id        for ref in state.policy_refs] if state.policy_refs else []
    rag_confidence   = min([ref.relevance_score for ref in state.policy_refs], default=0.0) if state.policy_refs else 0.0
    policy_version   = state.policy_refs[0].version_id if state.policy_refs else "unknown"

    log_id = write_audit_entry(
        employee_id       = state.worker_id or "unknown",
        intent            = state.intent.value if state.intent else "unknown",
        decision          = state.decision.value if state.decision else "unknown",
        decision_by       = "HUMAN" if state.hitl_required else "AI",
        confidence        = state.confidence_score,
        policy_chunk_ids  = policy_chunk_ids,
        rag_confidence    = rag_confidence,
        agent_version     = AGENT_VERSION,
        policy_version_id = policy_version,
        raw_message       = state.raw_text or "",
        leave_type        = state.slots.leave_type.value if state.slots.leave_type else "",
        leave_dates       = [d for d in [state.slots.start_date, state.slots.end_date] if d],
        hitl_triggered    = state.hitl_required,
        hitl_reason       = state.hitl_reason or "",
    )

    if log_id:
        logger.info(f"[{state.correlation_id}] audit_log written: {log_id}")
    else:
        logger.warning(f"[{state.correlation_id}] audit_log write failed — continuing")

    return state
