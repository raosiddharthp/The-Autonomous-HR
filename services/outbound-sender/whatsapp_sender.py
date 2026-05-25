"""
whatsapp_sender.py
Low-level Meta WhatsApp Cloud API client.
Owns: credential fetch, HTTP POST to /messages, retry on 429/5xx.
Never called directly by orchestrator — go through hitl_notifier.py.
"""
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

# ── Credential resolution ─────────────────────────────────────────────────────
# Prefer Secret Manager in prod; fall back to env vars for local/emulator runs.

def _get_secret(name: str) -> str:
    """Pull a secret from GCP Secret Manager, or fall back to os.environ."""
    try:
        from google.cloud import secretmanager
        project = os.environ.get("GCLOUD_PROJECT", "autonomous-hr-495502")
        client  = secretmanager.SecretManagerServiceClient()
        resource = f"projects/{project}/secrets/{name}/versions/latest"
        response = client.access_secret_version(name=resource)
        return response.payload.data.decode("utf-8").strip()
    except Exception as exc:
        logger.warning(f"SecretManager unavailable ({exc}), falling back to env var {name}")
        val = os.environ.get(name, "")
        if not val:
            raise EnvironmentError(f"Required credential '{name}' not found in SecretManager or env") from exc
        return val


def _get_wa_credentials() -> tuple[str, str]:
    """Returns (phone_number_id, bearer_token)."""
    phone_number_id = _get_secret("WHATSAPP_PHONE_NUMBER_ID")
    token           = _get_secret("WHATSAPP_TOKEN")
    return phone_number_id, token


# ── Core sender ───────────────────────────────────────────────────────────────

WA_API_VERSION = "v19.0"
MAX_RETRIES    = 3
RETRY_DELAYS   = [1, 2, 4]   # seconds — exponential backoff


def post_message(payload: dict) -> dict:
    """
    POST payload to Meta Cloud API /messages endpoint.
    Retries on 429 (rate-limit) and 5xx (server errors).
    Returns the parsed JSON response on success.
    Raises RuntimeError on final failure.
    """
    phone_number_id, token = _get_wa_credentials()
    url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }

    last_exc: Exception | None = None
    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                logger.info(f"whatsapp_sender: POST ok attempt={attempt} status=200")
                return resp.json()
            if resp.status_code == 429 or resp.status_code >= 500:
                logger.warning(
                    f"whatsapp_sender: retriable error attempt={attempt} "
                    f"status={resp.status_code} body={resp.text[:200]}"
                )
                time.sleep(delay)
                continue
            # 4xx that is not 429 — do not retry
            raise RuntimeError(
                f"whatsapp_sender: non-retriable error "
                f"status={resp.status_code} body={resp.text[:400]}"
            )
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(f"whatsapp_sender: network error attempt={attempt}: {exc}")
            time.sleep(delay)

    raise RuntimeError(
        f"whatsapp_sender: all {MAX_RETRIES} attempts failed. last_exc={last_exc}"
    )


def send_text_message(to: str, body: str) -> dict:
    """Send a plain text message to a WhatsApp number."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    return post_message(payload)


def send_interactive_buttons(
    to: str,
    header_text: str,
    body_text: str,
    footer_text: str,
    buttons: list[dict],
) -> dict:
    """
    Send a WhatsApp interactive message with up to 3 reply buttons.
    buttons format: [{"id": "approve:abc123", "title": "✅ Approve"}, ...]
    Button id max 20 chars. Title max 20 chars.
    """
    if len(buttons) > 3:
        raise ValueError("WhatsApp interactive buttons: max 3 buttons allowed")
    for btn in buttons:
        if len(btn["id"]) > 20:
            raise ValueError(f"Button id '{btn['id']}' exceeds 20-char limit")
        if len(btn["title"]) > 20:
            raise ValueError(f"Button title '{btn['title']}' exceeds 20-char limit")

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {"type": "text", "text": header_text},
            "body":   {"text": body_text},
            "footer": {"text": footer_text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": btn["id"], "title": btn["title"]}}
                    for btn in buttons
                ]
            },
        },
    }
    return post_message(payload)
