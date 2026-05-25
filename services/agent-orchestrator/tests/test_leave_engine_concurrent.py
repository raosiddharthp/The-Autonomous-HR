"""
S-21 AC: Concurrent approve requests — no double deduction.
Runs against Firestore emulator.
Requires:
  FIRESTORE_EMULATOR_HOST=localhost:8080
  GCLOUD_PROJECT=autonomous-hr-495502
"""
import concurrent.futures
import time
import sys, os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../rag-indexer"))

from google.cloud import firestore
from leave_engine import deduct_leave

EMPLOYEE_ID  = "test-concurrent-emp-001"
LEAVE_TYPE   = "casual"
INITIAL_DAYS = 3


@pytest.fixture(autouse=True)
def seed_balance():
    db  = firestore.Client()
    ref = db.collection("leave_balances").document(EMPLOYEE_ID)
    ref.set({
        "casual":  INITIAL_DAYS,
        "sick":    10,
        "earned":  15,
        "unpaid":  0,
        "history": [],
    })
    yield
    ref.delete()


def _attempt_deduct(stagger_ms: int = 0):
    """
    One deduct attempt with optional stagger delay.
    Returns ('ok', remaining), ('insufficient', reason), or ('err', reason).
    """
    if stagger_ms:
        time.sleep(stagger_ms / 1000.0)
    db = firestore.Client()
    try:
        result = deduct_leave(db, EMPLOYEE_ID, LEAVE_TYPE, 1)
        return ("ok", result[LEAVE_TYPE])
    except ValueError as e:
        return ("insufficient", str(e))
    except Exception as e:
        return ("err", str(e))


def test_no_double_deduction_sequential_transactions():
    """
    Core S-21 safety test: stagger 5 requests by 50ms each so the emulator
    can serialise them cleanly. Exactly INITIAL_DAYS must succeed.
    Final balance must be 0, not negative. No double-deduct.
    """
    workers = INITIAL_DAYS + 2      # 5 requests, 3 days available

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        # Stagger each thread by 50ms so transactions don't all contend at t=0
        futures = [
            pool.submit(_attempt_deduct, i * 50)
            for i in range(workers)
        ]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    print("\n--- Concurrent deduct results ---")
    for r in sorted(results):
        print(r)

    ok_count          = sum(1 for r in results if r[0] == "ok")
    insufficient_count = sum(1 for r in results if r[0] == "insufficient")
    err_count         = sum(1 for r in results if r[0] == "err")

    print(f"\nok={ok_count}  insufficient={insufficient_count}  err={err_count}")

    # No errors — every failure must be a clean business rejection
    assert err_count == 0, (
        f"Unexpected errors (not business rejections): "
        f"{[r for r in results if r[0] == 'err']}"
    )

    # Exactly 3 succeed — no more, no less
    assert ok_count == INITIAL_DAYS, (
        f"Expected exactly {INITIAL_DAYS} successful deductions, got {ok_count}.\n"
        f"Possible double-deduct! Full results: {results}"
    )

    # Final balance is exactly 0 — never negative
    db    = firestore.Client()
    final = db.collection("leave_balances").document(EMPLOYEE_ID).get().to_dict()

    assert final[LEAVE_TYPE] == 0, (
        f"Final balance must be 0, got {final[LEAVE_TYPE]} — double-deduct occurred"
    )

    # History entries equal successful deductions — append-only confirmed
    assert len(final["history"]) == INITIAL_DAYS, (
        f"History must have {INITIAL_DAYS} entries, got {len(final['history'])}"
    )

    print(f"✅ Final balance: {final[LEAVE_TYPE]}")
    print(f"✅ History entries: {len(final['history'])}")


def test_balance_never_goes_negative():
    """
    Hammer with 10 rapid requests against a balance of 3.
    Balance must never go below 0 regardless of ordering.
    """
    workers = 10

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_attempt_deduct, i * 20) for i in range(workers)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    db    = firestore.Client()
    final = db.collection("leave_balances").document(EMPLOYEE_ID).get().to_dict()

    print(f"\nFinal balance after 10 rapid requests: {final[LEAVE_TYPE]}")

    assert final[LEAVE_TYPE] >= 0, (
        f"Balance went negative: {final[LEAVE_TYPE]} — transaction guard failed"
    )
    assert final[LEAVE_TYPE] == 0, (
        f"Expected 0 remaining (all 3 days consumed), got {final[LEAVE_TYPE]}"
    )
