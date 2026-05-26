import logging
import json
import os
import requests
from state import AgentState, Intent, Slots, LeaveType

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

SYSTEM_PROMPT = """You are an HR intent classifier for Rathi Textiles, a textile company in Nagpur, India.
Workers communicate in Hindi, English, Marathi, Tamil, Bengali, and Telugu — including code-switched text.

Classify the worker message into exactly one intent:
- leave_request: worker wants to apply for leave
- balance_query: worker wants to know their leave balance
- payroll_query: worker asking about salary, pay slip, deductions
- grievance_log: worker reporting a complaint, harassment, or problem
- policy_question: worker asking about HR rules or policy
- unknown: cannot determine intent

Also extract slots if present:
- leave_type: casual | sick | earned | unpaid | unknown
- start_date: ISO date string YYYY-MM-DD or null
- end_date: ISO date string YYYY-MM-DD or null
- num_days: integer or null
- reason: brief reason string or null

Respond ONLY with valid JSON, no markdown, no explanation:
{
  "intent": "<intent>",
  "confidence": <0.0-1.0>,
  "slots": {
    "leave_type": "<type or null>",
    "start_date": "<date or null>",
    "end_date": "<date or null>",
    "num_days": <int or null>,
    "reason": "<string or null>"
  }
}"""


def _get_api_key() -> str:
    key = GEMINI_API_KEY
    if not key:
        try:
            from google.cloud import secretmanager
            project = os.environ.get("GCLOUD_PROJECT", "autonomous-hr-495502")
            client = secretmanager.SecretManagerServiceClient()
            resource = f"projects/{project}/secrets/gemini-api-key/versions/latest"
            response = client.access_secret_version(name=resource)
            key = response.payload.data.decode("utf-8").strip()
        except Exception as e:
            logger.error(f"classify: failed to get gemini-api-key: {e}")
    return key


def classify_node(state: AgentState) -> AgentState:
    state.log_step("classify")
    logger.info(f"[{state.correlation_id}] classify: text={state.raw_text!r}")

    if not state.raw_text:
        state.intent = Intent.UNKNOWN
        state.intent_confidence = 0.0
        logger.warning(f"[{state.correlation_id}] classify: no text")
        return state

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
            {"role": "model", "parts": [{"text": "Understood. Send me the worker message."}]},
            {"role": "user", "parts": [{"text": state.raw_text}]},
        ]
    }

    try:
        api_key = _get_api_key()
        resp = requests.post(
            ENDPOINT,
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)

        state.intent = Intent(parsed.get("intent", "unknown"))
        state.intent_confidence = float(parsed.get("confidence", 0.0))

        slots_data = parsed.get("slots", {})
        state.slots = Slots(
            leave_type=LeaveType(slots_data["leave_type"]) if slots_data.get("leave_type") and slots_data["leave_type"] not in ("null", None) else None,
            start_date=slots_data.get("start_date"),
            end_date=slots_data.get("end_date"),
            num_days=slots_data.get("num_days"),
            reason=slots_data.get("reason"),
        )

        logger.info(f"[{state.correlation_id}] classify: intent={state.intent} confidence={state.intent_confidence} slots={state.slots}")

    except Exception as e:
        logger.error(f"[{state.correlation_id}] classify: Gemini call failed: {e} — falling back to unknown")
        state.intent = Intent.UNKNOWN
        state.intent_confidence = 0.0
        state.log_error(f"classify fallback: {e}")

    return state
