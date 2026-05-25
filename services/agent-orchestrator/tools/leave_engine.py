from datetime import datetime, timezone
import os
import logging
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../rag-indexer'))
from google.cloud import firestore
from google.api_core.exceptions import Aborted
from state import AgentState, DecisionOutcome, Slots

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT", "autonomous-hr-495502")

LEAVE_TYPE_MAP = {
    "casual": "casual",
    "sick": "sick",
    "earned": "earned",
    "unpaid": "unpaid",
}

POLICY_LIMITS = {
    "casual": 8,
    "sick": 5,
    "earned": 15,
    "unpaid": 30,
}


def get_db():
    return firestore.Client(project=PROJECT_ID)


def lookup_employee(db, worker_wa_id: str) -> dict | None:
    docs = db.collection("employees").where(
        "worker_wa_id", "==", worker_wa_id
    ).limit(1).stream()
    for doc in docs:
        return doc.to_dict()
    return None


def get_leave_balance(db, employee_id: str) -> dict:
    doc = db.collection("leave_balances").document(employee_id).get()
    if doc.exists:
        return doc.to_dict()
    return {"casual": 0, "sick": 0, "earned": 0, "unpaid": 0}


def deduct_leave(db, employee_id: str, leave_type: str, num_days: int) -> dict:
    """
    Atomically deduct num_days from leave_type balance using a Firestore
    transaction. Raises ValueError on insufficient balance. Raises Aborted
    on transaction conflict — caller should retry.
    S-21: Prevents double-deduction on concurrent requests.
    """
    balance_ref = db.collection("leave_balances").document(employee_id)

    @firestore.transactional
    def _txn(transaction, ref):
        snapshot = ref.get(transaction=transaction)
        if not snapshot.exists:
            raise ValueError(f"No leave_balances record for {employee_id}")

        data     = snapshot.to_dict()
        current  = data.get(leave_type, 0)

        if current < num_days:
            raise ValueError(
                f"Insufficient {leave_type} balance: "
                f"requested {num_days}, available {current}"
            )

        new_balance = current - num_days

        history_entry = {
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "leave_type":    leave_type,
            "days_deducted": num_days,
            "balance_after": new_balance,
        }

        transaction.update(ref, {
            leave_type: new_balance,
            "history":  firestore.ArrayUnion([history_entry]),
        })

        return {**data, leave_type: new_balance}

    transaction = db.transaction()
    try:
        updated = _txn(transaction, balance_ref)
        logger.info(
            "deduct_leave OK | emp=%s type=%s days=%d",
            employee_id, leave_type, num_days
        )
        return updated
    except ValueError:
        raise
    except Aborted as e:
        logger.warning("deduct_leave CONFLICT | emp=%s — %s", employee_id, e)
        raise


def run_leave_engine(state: AgentState) -> AgentState:
    """
    Leave approval engine:
    1. Look up employee by WhatsApp ID
    2. Get leave balance
    3. Validate against policy
    4. Return approve / deny / escalate with reasoning
    """
    logger.info(f"[{state.correlation_id}] leave_engine: starting")

    db = get_db()

    # Step 1: lookup employee
    employee = lookup_employee(db, state.worker_wa_id)
    if not employee:
        logger.warning(f"[{state.correlation_id}] leave_engine: employee not found")
        state.decision = DecisionOutcome.ESCALATE
        state.decision_reasoning = "Employee record not found — escalating to HR"
        state.hitl_required = True
        state.hitl_reason = "Employee not found in system"
        return state

    employee_id = employee["employee_id"]
    state.worker_id = employee_id
    logger.info(f"[{state.correlation_id}] leave_engine: found employee={employee_id}")

    # Step 2: get balance
    balance = get_leave_balance(db, employee_id)
    leave_type = (state.slots.leave_type or "casual").value if state.slots.leave_type else "casual"
    num_days = state.slots.num_days or 1
    available = balance.get(leave_type, 0)

    state.leave_balance = {
        "casual": balance.get("casual", 0),
        "sick": balance.get("sick", 0),
        "earned": balance.get("earned", 0),
        "unpaid": balance.get("unpaid", 0),
    }

    logger.info(
        f"[{state.correlation_id}] leave_engine: "
        f"type={leave_type} requested={num_days} available={available}"
    )

    # Step 3: check for zero balance across all types
    total_balance = sum(balance.get(t, 0) for t in ["casual", "sick", "earned"])
    if total_balance == 0:
        state.decision = DecisionOutcome.ESCALATE
        state.decision_reasoning = "Zero leave balance across all types — escalating to MD"
        state.policy_clause = "§4.5: Employee with zero balance triggers HITL escalation to Managing Director"
        return state

    # Step 4: validate and decide
    if available >= num_days:
        state.decision = DecisionOutcome.APPROVE
        state.decision_reasoning = (
            f"Approved {num_days} day(s) of {leave_type} leave. "
            f"Remaining balance after approval: {available - num_days} days."
        )
        state.policy_clause = f"§4.2: {leave_type.capitalize()} leave entitlement: {POLICY_LIMITS.get(leave_type, '?')} days/year"
        # Deduct atomically — transaction-wrapped (S-21)
        try:
            updated_balance = deduct_leave(db, employee_id, leave_type, num_days)
            state.leave_balance[leave_type] = updated_balance.get(leave_type, 0)
            logger.info(
                f"[{state.correlation_id}] leave_engine: APPROVED — "
                f"deducted {num_days} from {leave_type}, "
                f"remaining={state.leave_balance[leave_type]}"
            )
        except Aborted:
            logger.warning(f"[{state.correlation_id}] leave_engine: transaction conflict on deduct")
            state.decision           = DecisionOutcome.ESCALATE
            state.decision_reasoning = "Transaction conflict during balance deduction — escalating for manual review"
            state.hitl_required      = True
            state.hitl_reason        = "Concurrent leave request conflict"
            return state
    else:
        state.decision = DecisionOutcome.DENY
        state.decision_reasoning = (
            f"Insufficient {leave_type} leave balance. "
            f"Requested: {num_days} day(s), Available: {available} day(s)."
        )
        state.policy_clause = f"§4.2: {leave_type.capitalize()} leave entitlement: {POLICY_LIMITS.get(leave_type, '?')} days/year"
        logger.info(f"[{state.correlation_id}] leave_engine: DENIED — insufficient balance")

    return state
