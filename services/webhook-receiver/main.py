import os
import json
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.cloud import pubsub_v1

from utils.signature import verify_twilio_signature, verify_meta_signature
from handlers.text_handler import handle_text
from handlers.media_handler import handle_media
from handlers.interactive_handler import handle_interactive_reply

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


# ── Meta Cloud API webhook (S-25) ────────────────────────────────────────

@app.get("/webhook/meta")
async def meta_verify(request: Request):
    """Meta hub verification challenge — required to register the webhook URL."""
    params     = dict(request.query_params)
    mode       = params.get("hub.mode", "")
    token      = params.get("hub.verify_token", "")
    challenge  = params.get("hub.challenge", "")
    expected   = os.environ.get("META_VERIFY_TOKEN", "")
    if mode == "subscribe" and token == expected:
        logging.info("meta_webhook_verified")
        return JSONResponse(status_code=200, content=int(challenge))
    logging.warning(f"meta_verify_failed mode={mode} token={token!r}")
    return JSONResponse(status_code=403, content={"error": "forbidden"})


@app.post("/webhook/meta")
async def meta_webhook(request: Request):
    """Receives all Meta Cloud API events: worker messages + employer button replies."""
    if DEMO_LOCKED:
        return JSONResponse(status_code=200, content={"status": "capacity"})

    raw_body = await request.body()
    sig      = request.headers.get("X-Hub-Signature-256", "")
    if not verify_meta_signature(raw_body, sig):
        logging.warning("invalid_meta_signature")
        return JSONResponse(status_code=403, content={"error": "invalid signature"})

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "bad json"})

    # Walk the Meta event envelope
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value    = change.get("value", {})
            messages = value.get("messages", [])
            for msg in messages:
                sender     = msg.get("from", "")
                msg_type   = msg.get("type", "")

                if msg_type == "interactive":
                    interactive = msg.get("interactive", {})
                    if interactive.get("type") == "button_reply":
                        button_id = interactive["button_reply"]["id"]
                        logging.info(f"meta_interactive button_id={button_id} from={sender[-4:].rjust(12,'*')}")
                        result = handle_interactive_reply(button_id, sender)
                        logging.info(f"hitl_resolved result={result}")

                elif msg_type in ("text", "audio"):
                    # Worker messages via Meta — route same as Twilio path
                    text_body = msg.get("text", {}).get("body", "")
                    msg_id    = msg.get("id", "")
                    event     = handle_text(sender, msg_id, text_body)
                    publisher.publish(
                        PUBSUB_TOPIC,
                        json.dumps(event).encode("utf-8"),
                        worker_id=sender,
                        content_type=event["content_type"],
                    )
                    logging.info(f"meta_text_routed event_id={event['event_id']}")

    return JSONResponse(status_code=200, content={"status": "ok"})
