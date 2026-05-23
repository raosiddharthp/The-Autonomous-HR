import uuid
import time

def handle_media(from_number: str, msg_sid: str, media_url: str, media_type: str) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "schema_version": "1.0",
        "timestamp": int(time.time()),
        "worker_wa_id": from_number,
        "msg_sid": msg_sid,
        "channel": "whatsapp",
        "content_type": media_type,
        "text": None,
        "language": None,
        "lang_confidence": None,
        "media_url": media_url,
        "media_gcs_uri": None,
    }
