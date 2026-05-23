import os
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
