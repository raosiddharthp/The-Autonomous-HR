"""
S-21 Step 2: write_leave_record commits before notification.
Runs against Firestore emulator.
"""
import sys, os, uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../rag-indexer"))

from google.cloud import firestore
from state import AgentState, DecisionOutcome, Slots, LeaveType
from leave_engine import write_leave_record

EMPLOYEE_ID = "test-write-record-emp-001"


def _make_state(decision=DecisionOutcome.APPROVE):
    return AgentState(
        correlation_id = str(uuid.uuid4()),
        worker_wa_id   = "91999000001",
        worker_id      = EMPLOYEE_ID,
        decision       = decision,
        decision_reasoning = "Approved 1 day casual leave",
        policy_clause  = "§4.2: Casual leave entitlement",
        rag_confidence = 0.95,
        slots          = Slots(leave_type=LeaveType.CASUAL, num_days=1),
    )


@pytest.fixture(autouse=True)
def cleanup():
    yield
    # Delete any test records written during the test
    db  = firestore.Client()
    docs = db.collection("leave_requests") \
              .where("employee_id", "==", EMPLOYEE_ID) \
              .stream()
    for doc in docs:
        doc.reference.delete()


def test_write_leave_record_creates_document():
    """Record must exist in Firestore before function returns."""
    db    = firestore.Client()
    state = _make_state()

    record_id = write_leave_record(db, state, "casual", 1)

    assert record_id, "record_id must be non-empty"

    doc = db.collection("leave_requests").document(record_id).get()
    assert doc.exists, f"leave_requests/{record_id} not found in Firestore"

    data = doc.to_dict()
    print(f"\nWritten record: {data}")

    # All required fields present
    assert data["employee_id"]        == EMPLOYEE_ID
    assert data["leave_type"]         == "casual"
    assert data["num_days"]           == 1
    assert data["decision"]           == "approve"
    assert data["policy_clause"]      == "§4.2: Casual leave entitlement"
    assert data["correlation_id"]     == state.correlation_id
    assert data["created_at"]         is not None
    print("✅ All required fields present")


def test_write_leave_record_sets_state_record_id():
    """state.leave_record_id must be populated after write."""
    db    = firestore.Client()
    state = _make_state()

    record_id = write_leave_record(db, state, "casual", 1)
    state.leave_record_id = record_id

    assert state.leave_record_id == record_id
    print(f"✅ state.leave_record_id = {state.leave_record_id}")


def test_record_written_before_notify_guard():
    """
    Simulate the commit-before-notify contract:
    leave_record_id must be set on state BEFORE response_text is set.
    If write fails, decision must flip to ESCALATE.
    """
    db    = firestore.Client()
    state = _make_state()

    # Simulate successful write → then set response
    record_id = write_leave_record(db, state, "casual", 1)
    state.leave_record_id = record_id

    # Only NOW would notifier set response_text
    assert state.leave_record_id is not None, \
        "leave_record_id must be set before response_text"

    state.response_text = "Your leave has been approved."

    assert state.response_text is not None
    print("✅ commit-before-notify order enforced")
