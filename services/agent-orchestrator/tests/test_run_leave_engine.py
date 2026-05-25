"""
S-21 Step 3: run_leave_engine end-to-end integration test.
Covers: approve, deny, escalate (zero balance), employee-not-found.
Runs against Firestore emulator.
Requires:
  FIRESTORE_EMULATOR_HOST=localhost:8080
  GCLOUD_PROJECT=autonomous-hr-495502
"""
import sys, os, uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../rag-indexer"))

from google.cloud import firestore
from state import AgentState, DecisionOutcome, Slots, LeaveType
from leave_engine import run_leave_engine

# ── Fixed test IDs ────────────────────────────────────────────────────────────
WA_ID       = "91900000099"
EMPLOYEE_ID = "EMP-TEST-S21"


def _make_state(leave_type=LeaveType.CASUAL, num_days=1):
    return AgentState(
        correlation_id = str(uuid.uuid4()),
        worker_wa_id   = WA_ID,
        slots          = Slots(leave_type=leave_type, num_days=num_days),
    )


@pytest.fixture()
def db():
    return firestore.Client()


@pytest.fixture(autouse=True)
def cleanup(db):
    yield
    db.collection("employees").document(EMPLOYEE_ID).delete()
    db.collection("leave_balances").document(EMPLOYEE_ID).delete()
    # Clean leave_requests written during tests
    for doc in db.collection("leave_requests") \
                 .where("employee_id", "==", EMPLOYEE_ID).stream():
        doc.reference.delete()


def _seed(db, casual=5, sick=5, earned=10):
    db.collection("employees").document(EMPLOYEE_ID).set({
        "employee_id":  EMPLOYEE_ID,
        "worker_wa_id": WA_ID,
        "name":         "Test Worker S21",
        "dept":         "Assembly",
        "language_pref": "en",
    })
    db.collection("leave_balances").document(EMPLOYEE_ID).set({
        "casual":  casual,
        "sick":    sick,
        "earned":  earned,
        "unpaid":  0,
        "history": [],
    })


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_approve_deducts_balance_and_writes_record(db):
    """Happy path: sufficient balance → APPROVE, balance deducted, record written."""
    _seed(db, casual=5)
    state = _make_state(LeaveType.CASUAL, num_days=2)

    result = run_leave_engine(state)

    assert result.decision == DecisionOutcome.APPROVE, \
        f"Expected APPROVE, got {result.decision}: {result.decision_reasoning}"

    # Balance deducted
    bal = db.collection("leave_balances").document(EMPLOYEE_ID).get().to_dict()
    assert bal["casual"] == 3, f"Expected casual=3, got {bal['casual']}"

    # leave_record_id set on state
    assert result.leave_record_id is not None, "leave_record_id must be set on state"

    # Record committed to Firestore
    doc = db.collection("leave_requests").document(result.leave_record_id).get()
    assert doc.exists, "leave_requests record not found"
    data = doc.to_dict()
    assert data["decision"]   == "approve"
    assert data["leave_type"] == "casual"
    assert data["num_days"]   == 2

    # History appended
    assert len(bal["history"]) == 1
    print(f"\n✅ APPROVE: balance 5→3, record={result.leave_record_id}")


def test_deny_when_insufficient_balance(db):
    """Insufficient balance → DENY, no deduction, no leave record written."""
    _seed(db, casual=1)
    state = _make_state(LeaveType.CASUAL, num_days=3)

    result = run_leave_engine(state)

    assert result.decision == DecisionOutcome.DENY, \
        f"Expected DENY, got {result.decision}"

    # Balance unchanged
    bal = db.collection("leave_balances").document(EMPLOYEE_ID).get().to_dict()
    assert bal["casual"] == 1, f"Balance should be unchanged at 1, got {bal['casual']}"

    # No leave record written
    assert result.leave_record_id is None, \
        "leave_record_id must NOT be set on a DENY"

    print(f"\n✅ DENY: balance unchanged at 1, no record written")


def test_escalate_when_zero_balance(db):
    """Zero balance across all types → ESCALATE to HITL."""
    _seed(db, casual=0, sick=0, earned=0)
    state = _make_state(LeaveType.CASUAL, num_days=1)

    result = run_leave_engine(state)

    assert result.decision == DecisionOutcome.ESCALATE, \
        f"Expected ESCALATE, got {result.decision}"
    assert result.hitl_required is True
    print(f"\n✅ ESCALATE (zero balance): hitl_required=True")


def test_escalate_when_employee_not_found(db):
    """Unknown WhatsApp ID → ESCALATE, hitl_required=True."""
    # Do NOT seed — employee doesn't exist
    state = AgentState(
        correlation_id = str(uuid.uuid4()),
        worker_wa_id   = "00000000000",   # unknown number
        slots          = Slots(leave_type=LeaveType.CASUAL, num_days=1),
    )

    result = run_leave_engine(state)

    assert result.decision == DecisionOutcome.ESCALATE
    assert result.hitl_required is True
    print(f"\n✅ ESCALATE (not found): {result.decision_reasoning}")


def test_approve_updates_state_leave_balance(db):
    """After approve, state.leave_balance reflects post-deduction value."""
    _seed(db, casual=4)
    state = _make_state(LeaveType.CASUAL, num_days=1)

    result = run_leave_engine(state)

    assert result.decision == DecisionOutcome.APPROVE
    assert result.leave_balance["casual"] == 3, \
        f"state.leave_balance should show 3, got {result.leave_balance['casual']}"
    print(f"\n✅ state.leave_balance updated: {result.leave_balance}")
