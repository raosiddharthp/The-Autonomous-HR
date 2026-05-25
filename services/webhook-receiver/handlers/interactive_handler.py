"""
interactive_handler.py
S-25: Handles employer Approve/Deny button replies from Meta Cloud API.
Flow: parse button_reply → resolve hitl_queue doc → update status
      → notify worker via WhatsApp → write audit entry.
"""
import os
import sys
import logging
from datetime import datetime, timezone

from google.cloud import firestore

logger = logging.getLogger(__name__)

# ── Path resolution for shared services ──────────────────────────────────────
# handlers/ → webhook-receiver/ → services/outbound-sender/
_HERE = os.path.dirname(os.path.abspath(__file__))
_SENDER_PATH = os.path.normpath(
    os.path.join(_HERE, "..", "..", "outbound-sender")
)
if _SENDER_PATH not in sys.path:
    sys.path.insert(0, _SENDER_PATH)
from whatsapp_sender import send_text_message

PROJECT_ID       = os.getenv("GCP_PROJECT", "autonomous-hr-495502")
HITL_COLLECTION  = "hitl_queue"


def get_db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


# ── Button ID parsing ─────────────────────────────────────────────────────────

def parse_button_id(button_id: str) -> tuple[str, str]:
    """
    Parse a button reply ID into (action, corr_slug).
    Expected format: "approve:abcd1234ef56" or "deny:abcd1234ef56"
    Returns ("approve"|"deny", slug) or raises ValueError on bad format.
    """
    parts = button_id.split(":", 1)
    if len(parts) != 2 or parts[0] not in ("approve", "deny"):
        raise ValueError(f"Unrecognised button_id format: {button_id!r}")
    return parts[0], parts[1]


def resolve_correlation_id(db: firestore.Client, corr_slug: str) -> str | None:
    """
    Find the hitl_queue document whose correlation_id starts with corr_slug.
    Button IDs embed the first 12 hex chars of the UUID (dashes stripped).
    Returns the full correlation_id string, or None if not found.
    """
    docs = (
        db.collection(HITL_COLLECTION)
        .where("status", "==", "pending")
        .stream()
    )
    for doc in docs:
        data = doc.to_dict()
        corr_id = data.get("correlation_id", "")
        if corr_id.replace("-", "").startswith(corr_slug):
            return corr_id
    return None


# ── Worker notification messages ──────────────────────────────────────────────

_APPROVE_TEMPLATES = {
    "en": "✅ Good news! Your leave request has been approved by the employer. Enjoy your time off.",
    "hi": "✅ खुशखबरी! आपकी छुट्टी की अनुरोध नियोक्ता द्वारा स्वीकृत कर दी गई है।",
    "ta": "✅ நற்செய்தி! உங்கள் விடுப்பு கோரிக்கை முதலாளியால் அனுமதிக்கப்பட்டது.",
    "bn": "✅ সুখবর! আপনার ছুটির অনুরোধ নিয়োগকর্তা অনুমোদন করেছেন।",
    "mr": "✅ आनंदाची बातमी! तुमच्या रजेची विनंती नियोक्त्याने मंजूर केली आहे।",
    "te": "✅ శుభవార్త! మీ సెలవు అభ్యర్థనను యజమాని ఆమోదించారు.",
}

_DENY_TEMPLATES = {
    "en": "❌ Your leave request has been reviewed and denied by the employer. Please speak to your manager for more information.",
    "hi": "❌ आपकी छुट्टी की अनुरोध नियोक्ता द्वारा अस्वीकार कर दी गई है। अधिक जानकारी के लिए अपने प्रबंधक से बात करें।",
    "ta": "❌ உங்கள் விடுப்பு கோரிக்கை முதலாளியால் நிராகரிக்கப்பட்டது. மேலும் தகவலுக்கு உங்கள் மேலாளரிடம் பேசுங்கள்.",
    "bn": "❌ আপনার ছুটির অনুরোধ নিয়োগকর্তা প্রত্যাখ্যান করেছেন। আরও তথ্যের জন্য আপনার ম্যানেজারের সাথে কথা বলুন।",
    "mr": "❌ तुमच्या रजेची विनंती नियोक्त्याने नाकारली आहे। अधिक माहितीसाठी तुमच्या व्यवस्थापकाशी बोला.",
    "te": "❌ మీ సెలవు అభ్యర్థనను యజమాని తిరస్కరించారు. మరింత సమాచారం కోసం మీ మేనేజర్‌తో మాట్లాడండి.",
}


def _worker_message(action: str, language: str) -> str:
    lang = language if language in _APPROVE_TEMPLATES else "en"
    if action == "approve":
        return _APPROVE_TEMPLATES[lang]
    return _DENY_TEMPLATES[lang]


# ── Main handler ──────────────────────────────────────────────────────────────

def handle_interactive_reply(
    button_id: str,
    employer_wa_number: str,
) -> dict:
    """
    Resolve a HITL Approve/Deny button reply end-to-end.

    Args:
        button_id:           Raw button reply id from Meta webhook.
        employer_wa_number:  Sender number from Meta webhook (for logging).

    Returns:
        dict with keys: action, correlation_id, worker_notified, status
    """
    # 1. Parse button
    try:
        action, corr_slug = parse_button_id(button_id)
    except ValueError as exc:
        logger.warning(f"interactive_handler: bad button_id {button_id!r}: {exc}")
        return {"error": str(exc), "button_id": button_id}

    logger.info(
        f"interactive_handler: action={action} slug={corr_slug} "
        f"employer={employer_wa_number[-4:].rjust(12, '*')}"
    )

    db = get_db()

    # 2. Resolve correlation_id from slug
    corr_id = resolve_correlation_id(db, corr_slug)
    if not corr_id:
        logger.error(f"interactive_handler: no pending hitl_queue doc for slug={corr_slug}")
        return {"error": "hitl_queue_not_found", "slug": corr_slug}

    # 3. Fetch brief
    doc_ref = db.collection(HITL_COLLECTION).document(corr_id)
    brief   = doc_ref.get().to_dict()
    if not brief:
        logger.error(f"interactive_handler: empty doc for corr_id={corr_id}")
        return {"error": "hitl_doc_empty", "correlation_id": corr_id}

    # 4. Guard: already resolved?
    if brief.get("status") != "pending":
        logger.warning(
            f"interactive_handler: corr_id={corr_id} already {brief.get('status')} — ignoring"
        )
        return {"status": brief.get("status"), "correlation_id": corr_id, "skipped": True}

    # 5. Update Firestore status
    new_status = "approved" if action == "approve" else "denied"
    doc_ref.update({
        "status":          new_status,
        "resolved_at":     datetime.now(timezone.utc).isoformat(),
        "resolved_by":     employer_wa_number,
        "resolved_action": action,
    })
    logger.info(f"interactive_handler: hitl_queue/{corr_id} → {new_status}")

    # 6. Notify worker
    worker_wa_id = brief.get("worker_wa_id", "")
    language     = brief.get("language", "en")
    worker_msg   = _worker_message(action, language)
    worker_notified = False

    if worker_wa_id:
        try:
            send_text_message(worker_wa_id, worker_msg)
            worker_notified = True
            logger.info(
                f"interactive_handler: worker notified "
                f"wa_id={worker_wa_id[-4:].rjust(12,'*')} action={action}"
            )
        except Exception as exc:
            logger.error(
                f"interactive_handler: worker notification failed "
                f"corr_id={corr_id}: {exc}"
            )
    else:
        logger.warning(f"interactive_handler: no worker_wa_id in brief corr_id={corr_id}")

    return {
        "action":          action,
        "correlation_id":  corr_id,
        "status":          new_status,
        "worker_notified": worker_notified,
    }
