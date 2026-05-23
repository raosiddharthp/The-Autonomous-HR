import os
import json
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.cloud import pubsub_v1

from utils.signature import verify_twilio_signature
from handlers.text_handler import handle_text
from handlers.media_handler import handle_media

logging.basicConfig(level=logging.INFO)
app = FastAPI()

DEMO_LOCKED = os.getenv("DEMO_LOCKED", "false").lower() == "true"
GCP_PROJECT = os.environ["GCP_PROJECT"]
PUBSUB_TOPIC = f"projects/{GCP_PROJECT}/topics/inbound-messages"

publisher = pubsub_v1.PublisherClient()

@app.get("/health")
def health():
    return {"status": "ok", "demo_locked": DEMO_LOCKED}

@app.post("/webhook")
async def webhook(request: Request):
    if DEMO_LOCKED:
        return JSONResponse(status_code=200, content={
            "status": "capacity",
            "message": "Demo is currently at capacity. Please try again later."
        })

    form = await request.form()
    params = dict(form)

    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)

    if not verify_twilio_signature(url, params, signature):
        logging.warning("invalid_twilio_signature")
        return JSONResponse(status_code=403, content={"error": "invalid signature"})

    from_number = params.get("From", "")
    msg_sid     = params.get("MessageSid", "")
    body        = params.get("Body", "")
    num_media   = int(params.get("NumMedia", "0"))

    if num_media > 0:
        media_url  = params.get("MediaUrl0", "")
        media_type = params.get("MediaContentType0", "application/octet-stream")
        event = handle_media(from_number, msg_sid, media_url, media_type)
        logging.info(f"media_received event_id={event['event_id']} type={media_type}")
    else:
        event = handle_text(from_number, msg_sid, body)
        logging.info(f"text_received event_id={event['event_id']} lang={event['language']}")

    publisher.publish(
        PUBSUB_TOPIC,
        json.dumps(event).encode("utf-8"),
        worker_id=from_number,
        content_type=event["content_type"],
    )

    return JSONResponse(status_code=200, content={"status": "ok"})
