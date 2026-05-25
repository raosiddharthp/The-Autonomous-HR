"""
S-23: Policy version control tests.
AC: Version ID present in every interaction record
    · Previous version retrievable
    · Latest-version flag works after re-upload
Runs against Firestore emulator.
"""
import sys, os, uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from google.cloud import firestore
from retriever import get_latest_version_id, retrieve

META_COLLECTION  = "policy_versions"
CHUNK_COLLECTION = "policy_chunks"

VERSION_A = "aaaa1111deadbeef"
VERSION_B = "bbbb2222cafebabe"


def _seed_version(db, version_id: str, is_latest: bool, chunk_count: int = 2):
    db.collection(META_COLLECTION).document(version_id).set({
        "version_id":  version_id,
        "pdf_path":    "hr-policy-rathi-textiles.pdf",
        "chunk_count": chunk_count,
        "indexed_at":  "2026-01-01T00:00:00+00:00",
        "status":      "complete",
        "is_latest":   is_latest,
    })
    for i in range(chunk_count):
        chunk_id = f"{version_id}-chunk-{i}"
        db.collection(CHUNK_COLLECTION).document(chunk_id).set({
            "chunk_id":    chunk_id,
            "version_id":  version_id,
            "page_number": i + 1,
            "text":        f"Sample policy text chunk {i} for version {version_id}. "
                           f"Casual leave entitlement is 8 days per year.",
            "embedding":   [0.1 * (i + 1)] * 768,
            "indexed_at":  "2026-01-01T00:00:00+00:00",
        })


@pytest.fixture(autouse=True)
def cleanup():
    """
    Before each test: demote any real is_latest version so our seeds win.
    After each test: remove all test seeds.
    """
    db = firestore.Client()

    # Save real latest so we can restore it after
    real_latest_docs = list(
        db.collection(META_COLLECTION).where("is_latest", "==", True).stream()
    )
    real_latest_ids = [d.id for d in real_latest_docs]

    # Demote all real latest versions for test isolation
    for d in real_latest_docs:
        d.reference.update({"is_latest": False})

    yield

    # Tear down test seeds
    for vid in [VERSION_A, VERSION_B]:
        db.collection(META_COLLECTION).document(vid).delete()
        for i in range(3):
            db.collection(CHUNK_COLLECTION).document(f"{vid}-chunk-{i}").delete()

    # Restore real latest versions
    for rid in real_latest_ids:
        ref = db.collection(META_COLLECTION).document(rid)
        if ref.get().exists:
            ref.update({"is_latest": True})


def test_get_latest_version_id_returns_latest():
    db = firestore.Client()
    _seed_version(db, VERSION_A, is_latest=False)
    _seed_version(db, VERSION_B, is_latest=True)

    latest = get_latest_version_id(db)
    assert latest == VERSION_B, f"Expected {VERSION_B}, got {latest}"
    print(f"\n✅ Latest version: {latest}")


def test_retrieve_filters_to_latest_version_only():
    db = firestore.Client()
    _seed_version(db, VERSION_A, is_latest=False, chunk_count=2)
    _seed_version(db, VERSION_B, is_latest=True,  chunk_count=2)

    results = retrieve("casual leave entitlement", top_k=10)

    version_ids_returned = {r["version_id"] for r in results}
    print(f"\nVersions in results: {version_ids_returned}")

    assert VERSION_A not in version_ids_returned, \
        f"Stale version {VERSION_A} chunks must not be returned"
    assert VERSION_B in version_ids_returned, \
        f"Latest version {VERSION_B} chunks must be returned"
    print(f"✅ Only latest version {VERSION_B} returned")


def test_previous_version_retrievable_by_explicit_id():
    db = firestore.Client()
    _seed_version(db, VERSION_A, is_latest=False, chunk_count=2)
    _seed_version(db, VERSION_B, is_latest=True,  chunk_count=2)

    old_results = retrieve("casual leave", top_k=10, version_id=VERSION_A)

    version_ids = {r["version_id"] for r in old_results}
    assert VERSION_A in version_ids, \
        f"Previous version {VERSION_A} must be retrievable by explicit version_id"
    assert VERSION_B not in version_ids, \
        f"Latest version must not appear when querying old version"
    print(f"✅ Previous version {VERSION_A} retrievable explicitly")


def test_latest_flag_switches_after_reupload():
    db = firestore.Client()

    _seed_version(db, VERSION_A, is_latest=True)
    assert get_latest_version_id(db) == VERSION_A

    _seed_version(db, VERSION_B, is_latest=True)
    db.collection(META_COLLECTION).document(VERSION_A).update({"is_latest": False})

    latest = get_latest_version_id(db)
    assert latest == VERSION_B, \
        f"After re-upload, latest must be {VERSION_B}, got {latest}"

    old_doc = db.collection(META_COLLECTION).document(VERSION_A).get()
    assert old_doc.exists
    assert old_doc.to_dict()["is_latest"] == False
    print(f"✅ Latest flipped to {VERSION_B}, {VERSION_A} retained with is_latest=False")


def test_version_id_present_in_retrieved_chunks():
    db = firestore.Client()
    _seed_version(db, VERSION_B, is_latest=True, chunk_count=2)

    results = retrieve("casual leave", top_k=5)

    for r in results:
        assert "version_id" in r, f"version_id missing from chunk: {r}"
        assert r["version_id"] == VERSION_B
    print(f"✅ version_id={VERSION_B} present in all {len(results)} results")
