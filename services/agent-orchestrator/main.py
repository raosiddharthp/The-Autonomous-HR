import logging
import base64
import json
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from state import AgentState
from graph import agent_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="agent-orchestrator", version="1.0.0")


class InboundEvent(BaseModel):
    event_id: str
    worker_wa_id: str
    text: Optional[str] = None
    transcript: Optional[str] = None
    language: str = "en"
    content_type: str = "text"


def run_agent(event: InboundEvent) -> dict:
    state = AgentState(
        correlation_id=event.event_id,
        worker_wa_id=event.worker_wa_id,
        raw_text=event.text,
        transcript=event.transcript,
        language=event.language,
        content_type=event.content_type,
    )
    try:
        raw = agent_graph.invoke(state)
        result = AgentState(**raw)
    except Exception as e:
        logger.error(f"Graph execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "correlation_id": result.correlation_id,
        "intent": result.intent,
        "decision": result.decision,
        "confidence_score": result.confidence_score,
        "hitl_required": result.hitl_required,
        "hitl_reason": result.hitl_reason,
        "response_text": result.response_text,
        "processing_steps": result.processing_steps,
        "errors": result.errors,
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "agent-orchestrator"}


@app.post("/process")
def process(event: InboundEvent):
    """Direct JSON endpoint — for testing."""
    logger.info(f"Processing event_id={event.event_id}")
    return run_agent(event)


@app.post("/pubsub")
async def pubsub_push(request: Request):
    """
    Pub/Sub push endpoint.
    Unwraps the Pub/Sub envelope, decodes base64 data, calls the agent.
    Always returns 200 to ack the message (even on agent error).
    """
    try:
        body = await request.json()
        message = body.get("message", {})
        data_b64 = message.get("data", "")
        data_str = base64.b64decode(data_b64).decode("utf-8")
        event_dict = json.loads(data_str)
        logger.info(f"pubsub_push: received event_id={event_dict.get('event_id')}")
        event = InboundEvent(**event_dict)
        result = run_agent(event)
        logger.info(f"pubsub_push: agent completed decision={result.get('decision')}")
        return {"status": "ok", "decision": result.get("decision")}
    except Exception as e:
        logger.error(f"pubsub_push: failed to process message: {e}")
        # Return 200 to ack and avoid infinite retry loop
        return {"status": "error", "detail": str(e)}
