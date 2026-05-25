"""
S-20: Append-only audit log writer.
Writes every agent decision to Firestore `audit_log` collection BEFORE
any outbound notification is sent. Collection is write-once by design —
Firestore security rules deny update/delete on this collection.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from google.cloud import firestore

logger = logging.getLogger(__name__)

PROJECT_ID  = os.getenv("GCP_PROJECT", "autonomous-hr-495502")
COLLECTION  = "audit_log"


def _get_db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def write_audit_entry(
    *,
    employee_id: str,
    intent: str,
    decision: str,                    # "approved" | "denied" | "escalated" | "clarification"
    decision_by: str,                 # "AI" | "HUMAN"
    confidence: float,
    policy_chunk_ids: list[str],
    rag_confidence: float,
    agent_version: str,
    policy_version_id: str,
    raw_message: str       = "",
    leave_type: str        = "",
    leave_dates: list[str] = None,
    hitl_triggered: bool   = False,
    hitl_reason: str       = "",
    extra: dict            = None,
) -> str:
    """
    Append one immutable record to audit_log.
    Returns the log_id of the written document.
    Never raises — logs error and returns empty string on failure
    so the agent flow is never blocked by audit writes.
    """
    log_id = str(uuid.uuid4())
    entry = {
        "log_id":            log_id,
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "employee_id":       employee_id,
        "intent":            intent,
        "decision":          decision,
        "decision_by":       decision_by,
        "confidence":        round(confidence, 4),
        "policy_chunk_ids":  policy_chunk_ids or [],
        "rag_confidence":    round(rag_confidence, 4),
        "agent_version":     agent_version,
        "policy_version_id": policy_version_id,
        "raw_message":       raw_message[:500],   # cap to avoid oversized docs
        "leave_type":        leave_type,
        "leave_dates":       leave_dates or [],
        "hitl_triggered":    hitl_triggered,
        "hitl_reason":       hitl_reason,
        "extra":             extra or {},
    }

    try:
        db = _get_db()
        db.collection(COLLECTION).document(log_id).create(entry)  # .create() fails if doc exists — extra safety
        logger.info(f"audit_log written: {log_id} | {employee_id} | {intent} | {decision}")
    except Exception as e:
        logger.error(f"audit_log WRITE FAILED for {employee_id}: {e}")
        return ""

    return log_id
