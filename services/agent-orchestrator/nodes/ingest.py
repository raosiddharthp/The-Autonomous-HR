import logging
from state import AgentState

logger = logging.getLogger(__name__)


def ingest_node(state: AgentState) -> AgentState:
    """
    Ingest node: normalises the inbound message into a single
    text field the classifier can work with. If the message
    arrived as audio the transcript is already populated by
    the STT service upstream; we just promote it to raw_text.
    """
    state.log_step("ingest")
    logger.info(f"[{state.correlation_id}] ingest: content_type={state.content_type}")

    if state.content_type.startswith("audio") and state.transcript:
        state.raw_text = state.transcript
        logger.info(f"[{state.correlation_id}] ingest: promoted transcript to raw_text")
    elif not state.raw_text:
        state.log_error("ingest: no raw_text and no transcript available")
        logger.warning(f"[{state.correlation_id}] ingest: nothing to process")

    return state
