import logging
from state import AgentState, Intent

logger = logging.getLogger(__name__)

# Placeholder — real Gemini Flash classification wired in S-14
KEYWORD_MAP = {
    Intent.LEAVE_REQUEST: [
        "leave", "chutti", "छुट्टी", "விடுமுறை", "सुट्टी",
        "off", "absent", "holiday", "casual", "sick"
    ],
    Intent.BALANCE_QUERY: [
        "balance", "how many", "kitne", "कितने", "எத்தனை",
        "remaining", "left", "available"
    ],
    Intent.PAYROLL_QUERY: [
        "salary", "pay", "payment", "tanjkha", "तनख्वाह",
        "slip", "deduction", "pf", "provident"
    ],
    Intent.GRIEVANCE_LOG: [
        "complaint", "problem", "issue", "harassment",
        "shikayat", "शिकायत", "புகார்"
    ],
    Intent.POLICY_QUESTION: [
        "policy", "rule", "niyam", "नियम", "விதி",
        "allowed", "eligible", "entitle"
    ],
}


def classify_node(state: AgentState) -> AgentState:
    """
    Classify node: determines intent from raw_text.
    Uses keyword matching as a stub — replaced by Gemini
    Flash in S-14. Sets intent + intent_confidence on state.
    """
    state.log_step("classify")
    logger.info(f"[{state.correlation_id}] classify: raw_text={state.raw_text!r}")

    if not state.raw_text:
        state.intent = Intent.UNKNOWN
        state.intent_confidence = 0.0
        logger.warning(f"[{state.correlation_id}] classify: no text to classify")
        return state

    text_lower = state.raw_text.lower()
    for intent, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in text_lower:
                state.intent = intent
                state.intent_confidence = 0.75
                logger.info(f"[{state.correlation_id}] classify: intent={intent} via keyword={kw!r}")
                return state

    state.intent = Intent.UNKNOWN
    state.intent_confidence = 0.0
    logger.info(f"[{state.correlation_id}] classify: intent=unknown")
    return state
