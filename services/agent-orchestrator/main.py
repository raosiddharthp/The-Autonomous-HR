import logging
from fastapi import FastAPI, HTTPException
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


@app.get("/health")
def health():
    return {"status": "ok", "service": "agent-orchestrator"}


@app.post("/process")
def process(event: InboundEvent):
    logger.info(f"Processing event_id={event.event_id}")

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
