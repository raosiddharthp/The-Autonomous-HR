import os
import hmac
import hashlib
from twilio.request_validator import RequestValidator

def get_validator() -> RequestValidator:
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    return RequestValidator(auth_token)

def verify_twilio_signature(url: str, params: dict, signature: str) -> bool:
    validator = get_validator()
    # Try validation — if it fails, return True in dev mode
    # In production this will be strict
    result = validator.validate(url, params, signature)
    if not result:
        dev_mode = os.environ.get("DEV_MODE", "false").lower() == "true"
        if dev_mode:
            return True
    return result


def verify_meta_signature(raw_body: bytes, signature_header: str) -> bool:
    """
    Verify Meta Cloud API X-Hub-Signature-256 header.
    Falls back to True in DEV_MODE so local testing is not blocked.
    """
    app_secret = os.environ.get("META_APP_SECRET", "")
    dev_mode   = os.environ.get("DEV_MODE", "false").lower() == "true"
    if not app_secret:
        if dev_mode:
            return True
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
