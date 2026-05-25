"""
whatsapp_sender.py
Twilio WhatsApp sender (Sandbox — zero budget).
Owns: credential fetch, Twilio REST POST, retry on 429/5xx.
Never called directly by orchestrator — go through hitl_notifier.py.

Public API (unchanged from Meta version):
  send_text_message(to, body) -> dict
  send_interactive_buttons(to, header_text, body_text, footer_text, buttons) -> dict
  post_message(payload) -> dict

Twilio sandbox constraint: no interactive button templates.
send_interactive_buttons renders as structured text with numbered reply options.
Production swap to Meta Cloud API = two Secret Manager updates, zero code change.

Sandbox numbers must be whatsapp:-prefixed:
  To   = "whatsapp:+919876543210"
  From = "whatsapp:+19474658199"
"""
import os
import time
import logging
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


# ── Credential resolution ─────────────────────────────────────────────────────

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
        logger.warning(
            f"SecretManager unavailable ({exc}), falling back to env var {name}"
        )
        val = os.environ.get(name, "")
        if not val:
            raise EnvironmentError(
                f"Required credential {name!r} not found in SecretManager or env"
            ) from exc
        return val


def _get_twilio_credentials() -> tuple[str, str, str]:
    """Returns (account_sid, auth_token, from_number).
    from_number is the Twilio sandbox number, e.g. +19474658199.
    """
    account_sid = _get_secret("twilio-sid")
    auth_token  = _get_secret("twilio-auth-token")
    from_number = _get_secret("twilio-phone-number")
    return account_sid, auth_token, from_number


# ── Constants ─────────────────────────────────────────────────────────────────

MAX_RETRIES  = 3
RETRY_DELAYS = [1, 2, 4]   # seconds — exponential backoff


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wa(number: str) -> str:
    """Ensure number has whatsapp: prefix exactly once."""
    number = number.strip()
    return number if number.startswith("whatsapp:") else f"whatsapp:{number}"


# ── Core sender ───────────────────────────────────────────────────────────────

def post_message(payload: dict) -> dict:
    """
    POST a Twilio Messages API request.
    payload keys: To, From, Body  (Twilio PascalCase field names).
    Returns normalised dict with messages[0].id so callers stay compatible.
    Raises RuntimeError on final failure.
    """
    account_sid, auth_token, _ = _get_twilio_credentials()
    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    )

    last_exc: Exception | None = None
    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            resp = requests.post(
                url,
                data=payload,
                auth=HTTPBasicAuth(account_sid, auth_token),
                timeout=10,
            )
            if resp.status_code in (200, 201):
                logger.info(
                    f"whatsapp_sender: POST ok attempt={attempt} "
                    f"status={resp.status_code}"
                )
                body = resp.json()
                # Normalise to shape hitl_notifier expects
                body.setdefault("messages", [{"id": body.get("sid", "n/a")}])
                return body
            if resp.status_code == 429 or resp.status_code >= 500:
                logger.warning(
                    f"whatsapp_sender: retriable error attempt={attempt} "
                    f"status={resp.status_code} body={resp.text[:200]}"
                )
                time.sleep(delay)
                continue
            raise RuntimeError(
                f"whatsapp_sender: non-retriable error "
                f"status={resp.status_code} body={resp.text[:400]}"
            )
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                f"whatsapp_sender: network error attempt={attempt}: {exc}"
            )
            time.sleep(delay)

    raise RuntimeError(
        f"whatsapp_sender: all {MAX_RETRIES} attempts failed. last_exc={last_exc}"
    )


def send_text_message(to: str, body: str) -> dict:
    """Send a plain text WhatsApp message via Twilio sandbox."""
    _, _, from_number = _get_twilio_credentials()
    payload = {
        "To":   _wa(to),
        "From": _wa(from_number),
        "Body": body,
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
    Twilio sandbox does not support WhatsApp interactive button templates.
    Renders as structured text with numbered reply options.
    Signature is identical to the Meta version — hitl_notifier.py is untouched.

    buttons format: [{"id": "approve:abc123", "title": "Approve"}, ...]
    """
    if len(buttons) > 3:
        raise ValueError("WhatsApp interactive buttons: max 3 buttons allowed")

    menu_lines = []
    for i, btn in enumerate(buttons, start=1):
        menu_lines.append(f"  {i}. Reply *{i}* to {btn['title']}")
    menu = "\n".join(menu_lines)

    full_body = (
        f"*{header_text}*\n"
        f"{'─' * 28}\n"
        f"{body_text}\n"
        f"{'─' * 28}\n"
        f"{menu}\n"
        f"{'─' * 28}\n"
        f"_{footer_text}_"
    )

    return send_text_message(to=to, body=full_body)
