import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

DEMO_LOCKED = os.getenv("DEMO_LOCKED", "false").lower() == "true"

@app.get("/health")
def health():
    return {"status": "ok", "demo_locked": DEMO_LOCKED}

@app.post("/webhook")
async def webhook(request: Request):
    if DEMO_LOCKED:
        return JSONResponse(
            status_code=200,
            content={"status": "capacity", "message": "Demo is currently at capacity. Please try again later."}
        )

    body = await request.json()

    # Log structured event for monitoring
    print({
        "severity": "INFO",
        "event": "new_conversation",
        "message": "Inbound webhook received",
        "body": body
    })

    return {"status": "received"}
