"""
test_interactive_handler.py
S-25: 9 tests covering parse_button_id, resolve_correlation_id,
and handle_interactive_reply. All Firestore + WhatsApp calls mocked.
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "../../../../services/outbound-sender"),
)

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), ".."),
)

from handlers.interactive_handler import (
    parse_button_id,
    resolve_correlation_id,
    handle_interactive_reply,
    _worker_message,
)


# ── parse_button_id ───────────────────────────────────────────────────────────

def test_parse_approve_button_id():
    action, slug = parse_button_id("approve:abcd1234ef56")
    assert action == "approve"
    assert slug == "abcd1234ef56"


def test_parse_deny_button_id():
    action, slug = parse_button_id("deny:abcd1234ef56")
    assert action == "deny"
    assert slug == "abcd1234ef56"


def test_parse_invalid_button_id_raises():
    with pytest.raises(ValueError):
        parse_button_id("unknown:abcd1234ef56")


def test_parse_malformed_button_id_raises():
    with pytest.raises(ValueError):
        parse_button_id("approveabcd1234ef56")


# ── _worker_message ───────────────────────────────────────────────────────────

def test_worker_message_approve_english():
    msg = _worker_message("approve", "en")
    assert "approved" in msg.lower()


def test_worker_message_deny_hindi():
    msg = _worker_message("deny", "hi")
    assert "❌" in msg


def test_worker_message_unknown_lang_falls_back_to_english():
    msg = _worker_message("approve", "xx")
    assert "approved" in msg.lower()


# ── handle_interactive_reply ──────────────────────────────────────────────────

def _make_mock_db(corr_id: str, status: str = "pending") -> MagicMock:
    brief = {
        "correlation_id": corr_id,
        "status":         status,
        "worker_wa_id":   "+911234567890",
        "language":       "en",
    }
    mock_doc = MagicMock()
    mock_doc.to_dict.return_value = brief

    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_doc

    stream_doc = MagicMock()
    stream_doc.to_dict.return_value = brief

    mock_collection = MagicMock()
    mock_collection.where.return_value.stream.return_value = iter([stream_doc])
    mock_collection.document.return_value = mock_doc_ref

    mock_db = MagicMock()
    mock_db.collection.return_value = mock_collection
    return mock_db


def test_handle_approve_updates_firestore_and_notifies_worker():
    corr_id   = "abcd1234-ef56-7890-abcd-ef1234567890"
    corr_slug = corr_id.replace("-", "")[:12]
    mock_db   = _make_mock_db(corr_id)

    with patch("handlers.interactive_handler.get_db", return_value=mock_db), \
         patch("handlers.interactive_handler.send_text_message") as mock_send:

        result = handle_interactive_reply(f"approve:{corr_slug}", "+919876543210")

    assert result["action"]          == "approve"
    assert result["status"]          == "approved"
    assert result["worker_notified"] is True
    mock_send.assert_called_once()


def test_handle_deny_sets_denied_status():
    corr_id   = "abcd1234-ef56-7890-abcd-ef1234567890"
    corr_slug = corr_id.replace("-", "")[:12]
    mock_db   = _make_mock_db(corr_id)

    with patch("handlers.interactive_handler.get_db", return_value=mock_db), \
         patch("handlers.interactive_handler.send_text_message"):

        result = handle_interactive_reply(f"deny:{corr_slug}", "+919876543210")

    assert result["status"] == "denied"


def test_handle_already_resolved_is_skipped():
    corr_id   = "abcd1234-ef56-7890-abcd-ef1234567890"
    corr_slug = corr_id.replace("-", "")[:12]
    mock_db   = _make_mock_db(corr_id, status="approved")

    with patch("handlers.interactive_handler.get_db", return_value=mock_db), \
         patch("handlers.interactive_handler.send_text_message") as mock_send:

        result = handle_interactive_reply(f"approve:{corr_slug}", "+919876543210")

    assert result.get("skipped") is True
    mock_send.assert_not_called()
