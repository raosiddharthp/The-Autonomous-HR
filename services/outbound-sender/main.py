import os
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from twilio.rest import Client

logging.basicConfig(level=logging.INFO)
app = FastAPI()

def get_twilio_client() -> Client:
    return Client(
        os.environ["TWILIO_ACCOUNT_SID"],
        os.environ["TWILIO_AUTH_TOKEN"]
    )

SANDBOX_NUMBER = os.environ.get("TWILIO_SANDBOX_NUMBER", "+14155238886")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/send/text")
async def send_text(payload: dict):
    to      = payload["to"]
    message = payload["message"]
    client  = get_twilio_client()
    msg = client.messages.create(
        from_=f"whatsapp:{SANDBOX_NUMBER}",
        to=f"whatsapp:{to}",
        body=message
    )
    logging.info(f"sent_text to={to} sid={msg.sid}")
    return JSONResponse(status_code=200, content={"sid": msg.sid})

@app.post("/send/buttons")
async def send_buttons(payload: dict):
    to      = payload["to"]
    message = payload["message"]
    ref_id  = payload.get("ref_id", "")
    client  = get_twilio_client()
    body = f"{message}\n\nReply *APPROVE_{ref_id}* to approve or *DENY_{ref_id}* to deny."
    msg = client.messages.create(
        from_=f"whatsapp:{SANDBOX_NUMBER}",
        to=f"whatsapp:{to}",
        body=body
    )
    logging.info(f"sent_buttons to={to} sid={msg.sid} ref_id={ref_id}")
    return JSONResponse(status_code=200, content={"sid": msg.sid})
