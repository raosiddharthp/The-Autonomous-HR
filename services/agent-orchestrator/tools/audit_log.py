"""
S-22: Immutable audit log writer.
Appends to Firestore /interactions collection.
Security rules deny update/delete — this is the only write path.
Design doc page-07: written BEFORE any outbound notification.
"""
import os
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from google.cloud import firestore
from state import AgentState, DecisionOutcome

logger    = logging.getLogger(__name__)
PROJECT_ID = os.getenv("GCP_PROJECT", "autonomous-hr-495502")

# Decision path constants — written into every log entry
PATH_AI    = "AI"
PATH_HUMAN = "HUMAN"


def write_audit_log(
    db,
    state:          AgentState,
    decision_path:  str = PATH_AI,
    hitl_resolved_by: Optional[str] = None,
) -> str:
    """
    Append one immutable record to /interactions/{log_id}.

    Fields written (S-22 AC — every field present on every record):
      log_id, timestamp, worker_id, worker_wa_id, correlation_id,
      intent, decision, decision_reasoning, confidence,
      policy_chunk_ids, policy_clause, decision_path,
      agent_version, policy_version, leave_record_id,
      hitl_required, hitl_reason, hitl_resolved_by,
      leave_type, num_days, leave_balance_after

    Raises on write failure — caller must halt before sending notification.
    """
    log_id = str(uuid.uuid4())

    # Extract policy chunk IDs from state.policy_refs
    policy_chunk_ids = [
        ref.chunk_id for ref in (state.policy_refs or [])
    ]

    # Extract slots safely
    leave_type = None
    num_days   = None
    if state.slots:
        leave_type = state.slots.leave_type.value if state.slots.leave_type else None
        num_days   = state.slots.num_days

    record = {
        # Identity
        "log_id":           log_id,
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "worker_id":        state.worker_id,
        "worker_wa_id":     state.worker_wa_id,
        "correlation_id":   state.correlation_id,

        # Decision
        "intent":              state.intent.value if state.intent else "unknown",
        "decision":            state.decision.value if state.decision else "unknown",
        "decision_reasoning":  state.decision_reasoning,
        "confidence":          state.rag_confidence,
        "decision_path":       decision_path,

        # Policy
        "policy_chunk_ids":  policy_chunk_ids,
        "policy_clause":     state.policy_clause,
        "agent_version":     os.getenv("AGENT_VERSION", "dev"),
        "policy_version":    os.getenv("POLICY_VERSION", "unknown"),

        # Leave context
        "leave_type":          leave_type,
        "num_days":            num_days,
        "leave_record_id":     state.leave_record_id,
        "leave_balance_after": state.leave_balance,

        # HITL
        "hitl_required":     state.hitl_required,
        "hitl_reason":       state.hitl_reason,
        "hitl_resolved_by":  hitl_resolved_by,

        # Errors
        "errors": state.errors,
    }

    # Append-only — use set() with the log_id as document ID
    db.collection("interactions").document(log_id).set(record)

    logger.info(
        "write_audit_log OK | emp=%s decision=%s path=%s log_id=%s",
        state.worker_id, record["decision"], decision_path, log_id
    )
    return log_id


def get_audit_log(db, worker_id: str, limit: int = 50) -> list:
    """
    Read audit entries for a worker — ordered by timestamp descending.
    Used for balance history display and CSV export.
    """
    docs = (
        db.collection("interactions")
          .where("worker_id", "==", worker_id)
          .order_by("timestamp", direction=firestore.Query.DESCENDING)
          .limit(limit)
          .stream()
    )
    return [doc.to_dict() for doc in docs]
