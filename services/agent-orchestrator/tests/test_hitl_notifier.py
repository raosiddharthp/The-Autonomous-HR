"""
test_hitl_notifier.py
S-24: 8 tests covering hitl_notifier._build_body and send_hitl_alert.
All WhatsApp API calls are mocked — no network, no credentials needed.
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Resolve outbound-sender onto path before importing hitl_notifier
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "../../../services/outbound-sender"),
)

import hitl_notifier
from hitl_notifier import _build_body, _truncate, send_hitl_alert


# ── Fixtures ─────────────────────────────────────────────────────────────────

FULL_BRIEF = {
    "correlation_id": "abcd1234-ef56-7890-abcd-ef1234567890",
    "worker_id": "EMP042",
    "intent": "leave_request",
    "slots": {
        "leave_type": "casual",
        "start_date": "2025-08-01",
        "end_date": "2025-08-03",
        "num_days": 3,
        "reason": "family function",
    },
    "ai_decision": "approve",
    "ai_reasoning": "Employee has sufficient casual leave balance per policy §3.2.",
    "policy_clause": "§3.2: Casual leave up to 3 days approved autonomously.",
    "confidence_score": 0.65,
    "hitl_reason": "Confidence score 0.65 below threshold 0.8",
}

MINIMAL_BRIEF = {
    "correlation_id": "zzzz0000-0000-0000-0000-000000000000",
    "worker_id": "unknown",
    "intent": "unknown",
    "slots": {},
    "ai_decision": "unknown",
    "ai_reasoning": "",
    "policy_clause": "",
    "confidence_score": 0.0,
    "hitl_reason": "",
}


# ── _truncate ─────────────────────────────────────────────────────────────────

def test_truncate_short_string_unchanged():
    assert _truncate("hello", 20) == "hello"

def test_truncate_exact_length_unchanged():
    s = "x" * 20
    assert _truncate(s, 20) == s

def test_truncate_long_string_ends_with_ellipsis():
    result = _truncate("a" * 50, 20)
    assert len(result) == 20
    assert result.endswith("…")


# ── _build_body ───────────────────────────────────────────────────────────────

def test_build_body_contains_all_five_required_fields():
    body = _build_body(FULL_BRIEF)
    assert "EMP042"    in body, "worker id missing"
    assert "APPROVE"   in body, "AI recommendation missing"
    assert "§3.2"      in body, "policy clause missing"
    assert "81%"       in body or "65%" in body, "confidence score missing"
    assert "casual"    in body.lower() or "Leave Request" in body, "request summary missing"

def test_build_body_includes_hitl_reason_when_present():
    body = _build_body(FULL_BRIEF)
    assert "Confidence score" in body or "below threshold" in body or "escalated" in body.lower()

def test_build_body_omits_hitl_reason_line_when_empty():
    body = _build_body(MINIMAL_BRIEF)
    assert "escalated" not in body.lower()

def test_build_body_fits_whatsapp_limit():
    body = _build_body(FULL_BRIEF)
    assert len(body) <= 1024, f"Body too long: {len(body)} chars"


# ── send_hitl_alert ───────────────────────────────────────────────────────────

def test_send_hitl_alert_calls_send_interactive_buttons():
    mock_response = {"messages": [{"id": "wamid.test123"}]}
    with patch("hitl_notifier.send_interactive_buttons", return_value=mock_response) as mock_send:
        result = send_hitl_alert(FULL_BRIEF, "+919876543210")

    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args
    # to= is positional arg 0
    assert call_kwargs[1]["to"] == "+919876543210" or call_kwargs[0][0] == "+919876543210"
    assert result == mock_response

def test_send_hitl_alert_button_ids_within_20_chars():
    captured = {}
    def capture(**kwargs):
        captured.update(kwargs)
        return {"messages": [{"id": "wamid.x"}]}

    with patch("hitl_notifier.send_interactive_buttons", side_effect=capture):
        send_hitl_alert(FULL_BRIEF, "+919876543210")

    for btn in captured.get("buttons", []):
        assert len(btn["id"]) <= 20, f"Button id '{btn['id']}' exceeds 20 chars"
        assert len(btn["title"]) <= 20, f"Button title '{btn['title']}' exceeds 20 chars"
