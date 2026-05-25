"""
hitl_notifier.py
Builds and sends the employer WhatsApp interactive HITL alert.
Consumes a HITL brief dict (same shape as hitl_queue Firestore doc).
Single public function: send_hitl_alert(brief, employer_wa_number)
"""
import logging
from whatsapp_sender import send_interactive_buttons

logger = logging.getLogger(__name__)

# Button ID prefix length: "approve:" = 8 chars, leaving 12 for corr_id slice
_CORR_SLICE = 12


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _build_body(brief: dict) -> str:
    """
    Assembles the message body from the HITL brief.
    All 5 required fields per design doc (page-07 S-24):
      worker name, request summary, AI recommendation,
      policy reference, confidence score.
    Fits within WhatsApp interactive body limit (1024 chars).
    """
    worker_id   = brief.get("worker_id", "Unknown")
    intent      = brief.get("intent", "unknown").replace("_", " ").title()
    slots       = brief.get("slots", {})
    leave_type  = (slots.get("leave_type") or "unspecified").title()
    start_date  = slots.get("start_date") or "?"
    end_date    = slots.get("end_date") or "?"
    num_days    = slots.get("num_days")
    days_str    = f"{num_days}d" if num_days else "?"

    ai_decision = brief.get("ai_decision", "unknown").upper()
    reasoning   = _truncate(brief.get("ai_reasoning", "No reasoning provided."), 120)
    policy      = _truncate(brief.get("policy_clause", "See attached policy."), 80)
    confidence  = brief.get("confidence_score", 0.0)
    conf_pct    = f"{round(confidence * 100)}%"
    hitl_reason = _truncate(brief.get("hitl_reason", ""), 80)

    lines = [
        f"👤 *Worker:* {worker_id}",
        f"📋 *Request:* {intent} — {leave_type} {start_date}→{end_date} ({days_str})",
        f"🤖 *AI Rec:* {ai_decision}",
        f"📄 *Policy:* {policy}",
        f"📊 *Confidence:* {conf_pct}",
    ]
    if hitl_reason:
        lines.append(f"⚠️  *Reason escalated:* {hitl_reason}")

    return "\n".join(lines)


def send_hitl_alert(brief: dict, employer_wa_number: str) -> dict:
    """
    Send the employer a WhatsApp interactive message for HITL review.

    Args:
        brief:               Dict matching hitl_queue Firestore schema.
        employer_wa_number:  E.164 format, e.g. "+919876543210"

    Returns:
        Meta API response dict with message id on success.

    Raises:
        RuntimeError if WhatsApp delivery fails after all retries.
    """
    corr_id = brief.get("correlation_id", "unknown")
    # Button IDs: "approve:xxxxxxxxxxxx" / "deny:xxxxxxxxxxxx" — max 20 chars each
    corr_slug = corr_id.replace("-", "")[:_CORR_SLICE]
    approve_id = f"approve:{corr_slug}"   # 8 + 12 = 20 chars exactly
    deny_id    = f"deny:{corr_slug}"      # 5 + 12 = 17 chars

    header  = "⚡ Action Required"
    body    = _build_body(brief)
    footer  = f"Ref: {corr_id[:8]}…  ·  AutoHR"

    buttons = [
        {"id": approve_id, "title": "✅ Approve"},
        {"id": deny_id,    "title": "❌ Deny"},
    ]

    logger.info(
        f"[{corr_id}] hitl_notifier: sending alert to employer "
        f"number={employer_wa_number[-4:].rjust(12,'*')}"
    )

    response = send_interactive_buttons(
        to          = employer_wa_number,
        header_text = header,
        body_text   = body,
        footer_text = footer,
        buttons     = buttons,
    )

    logger.info(f"[{corr_id}] hitl_notifier: alert delivered wa_msg_id={response.get('messages', [{}])[0].get('id', 'n/a')}")
    return response
