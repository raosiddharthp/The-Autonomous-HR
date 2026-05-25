import os
import logging
from datetime import datetime, timezone
from google.cloud import firestore
from state import AgentState

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT", "autonomous-hr-495502")
HITL_COLLECTION = "hitl_queue"


def get_db():
    return firestore.Client(project=PROJECT_ID)


def package_and_queue(state: AgentState) -> str:
    """
    Builds employer brief and writes to Firestore hitl_queue.
    Returns the hitl_queue document ID.
    """
    logger.info(f"[{state.correlation_id}] hitl_packager: building brief")

    policy_summary = []
    for ref in state.policy_refs:
        policy_summary.append({
            "page": ref.page_number,
            "excerpt": ref.excerpt[:200],
            "relevance": ref.relevance_score,
        })

    brief = {
        "correlation_id": state.correlation_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",

        # Worker info
        "worker_wa_id": state.worker_wa_id,
        "worker_id": state.worker_id or "unknown",
        "language": state.language,

        # Request summary
        "intent": state.intent.value if state.intent else "unknown",
        "raw_text": state.raw_text or "",
        "slots": {
            "leave_type": state.slots.leave_type.value if state.slots.leave_type else None,
            "start_date": state.slots.start_date,
            "end_date": state.slots.end_date,
            "num_days": state.slots.num_days,
            "reason": state.slots.reason,
        },

        # AI recommendation
        "ai_decision": state.decision.value if state.decision else "unknown",
        "ai_reasoning": state.decision_reasoning or "",
        "confidence_score": state.confidence_score,
        "hitl_reason": state.hitl_reason or "",

        # Policy references
        "policy_clause": state.policy_clause or "",
        "policy_refs": policy_summary,

        # Leave balance at time of request
        "leave_balance": state.leave_balance or {},

        # Errors if any
        "errors": state.errors,
    }

    db = get_db()
    doc_ref = db.collection(HITL_COLLECTION).document(state.correlation_id)
    doc_ref.set(brief)

    logger.info(
        f"[{state.correlation_id}] hitl_packager: brief queued "
        f"in {HITL_COLLECTION}/{state.correlation_id}"
    )
    return state.correlation_id
