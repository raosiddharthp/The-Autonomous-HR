import uuid
import time
from utils.lang_detect import detect_language

def handle_text(from_number: str, msg_sid: str, body: str) -> dict:
    lang, confidence = detect_language(body)
    return {
        "event_id": str(uuid.uuid4()),
        "schema_version": "1.0",
        "timestamp": int(time.time()),
        "worker_wa_id": from_number,
        "msg_sid": msg_sid,
        "channel": "whatsapp",
        "content_type": "text",
        "text": body,
        "language": lang,
        "lang_confidence": confidence,
        "media_url": None,
        "media_gcs_uri": None,
    }
