import uuid
import time
import os
import httpx

GCS_BUCKET = os.environ.get("MEDIA_BUCKET", "autonomous-hr-media-staging")

def _get_gcs_client():
    from google.cloud import storage
    return storage.Client()

def _download_and_stage(media_url: str, msg_sid: str, wa_id: str, ext: str) -> str:
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token  = os.environ["TWILIO_AUTH_TOKEN"]

    with httpx.Client() as client:
        resp = client.get(media_url, auth=(account_sid, auth_token), timeout=30)
        resp.raise_for_status()
        data = resp.content

    blob_name = f"{wa_id}/{msg_sid}.{ext}"
    bucket = _get_gcs_client().bucket(GCS_BUCKET)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data, content_type=resp.headers.get("content-type", "application/octet-stream"))

    return f"gs://{GCS_BUCKET}/{blob_name}"

def handle_media(from_number: str, msg_sid: str, media_url: str, media_type: str) -> dict:
    ext_map = {
        "audio/ogg":  "ogg",
        "audio/mpeg": "mp3",
        "image/jpeg": "jpg",
        "image/png":  "png",
        "application/pdf": "pdf",
    }
    ext = ext_map.get(media_type, "bin")
    wa_id = from_number.replace("whatsapp:+", "").replace("+", "")

    dev_mode = os.environ.get("DEV_MODE", "false").lower() == "true"

    if dev_mode:
        gcs_uri = f"gs://{GCS_BUCKET}/{wa_id}/{msg_sid}.{ext}"
    else:
        gcs_uri = _download_and_stage(media_url, msg_sid, wa_id, ext)

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
        "media_gcs_uri": gcs_uri,
    }
