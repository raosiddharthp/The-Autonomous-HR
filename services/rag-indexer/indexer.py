import os
import hashlib
import logging
import requests
import google.auth
import google.auth.transport.requests
from datetime import datetime, timezone
from pypdf import PdfReader
from google.cloud import firestore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID   = os.getenv("GCP_PROJECT", "autonomous-hr-495502")
LOCATION     = os.getenv("VERTEX_LOCATION", "us-central1")
EMBEDDING_MODEL   = "text-embedding-004"
EMBEDDING_ENDPOINT = (
    f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}"
    f"/locations/{LOCATION}/publishers/google/models/{EMBEDDING_MODEL}:predict"
)
CHUNK_SIZE    = 400
CHUNK_OVERLAP = 80
COLLECTION    = "policy_chunks"
META_COLLECTION = "policy_versions"


def get_token() -> str:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def embed(texts: list[str]) -> list[list[float]]:
    token = get_token()
    instances = [{"content": t} for t in texts]
    resp = requests.post(
        EMBEDDING_ENDPOINT,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"instances": instances},
        timeout=30,
    )
    resp.raise_for_status()
    return [p["embeddings"]["values"] for p in resp.json()["predictions"]]


def file_sha256(pdf_path: str) -> str:
    """Stable content hash — same file = same version_id, no re-index needed."""
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()[:16]


def extract_chunks(pdf_path: str, version_id: str) -> list[dict]:
    reader = PdfReader(pdf_path)
    chunks = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        words = text.split()
        start = 0
        while start < len(words):
            end = start + CHUNK_SIZE
            chunk_text = " ".join(words[start:end])
            # chunk_id is deterministic for this version
            chunk_id = hashlib.md5(
                f"{version_id}:{page_num}:{start}:{chunk_text[:50]}".encode()
            ).hexdigest()
            chunks.append({
                "chunk_id":    chunk_id,
                "version_id":  version_id,
                "page_number": page_num,
                "text":        chunk_text,
            })
            start += CHUNK_SIZE - CHUNK_OVERLAP
    logger.info(f"Extracted {len(chunks)} chunks from {len(reader.pages)} pages (version={version_id})")
    return chunks


def delete_stale_chunks(db: firestore.Client, current_version_id: str):
    """Delete all chunks that don't belong to the current version."""
    stale = db.collection(COLLECTION)\
               .where("version_id", "!=", current_version_id)\
               .stream()
    batch = db.batch()
    count = 0
    for doc in stale:
        batch.delete(doc.reference)
        count += 1
        if count % 500 == 0:          # Firestore batch limit is 500
            batch.commit()
            batch = db.batch()
    if count % 500 != 0:
        batch.commit()
    logger.info(f"Deleted {count} stale chunks from previous versions")


def index_pdf(pdf_path: str):
    db = firestore.Client(project=PROJECT_ID)

    # ── 1. Compute version ID from file content ──────────────────────────────
    version_id = file_sha256(pdf_path)
    logger.info(f"PDF version_id: {version_id}")

    # ── 2. Check if this version is already indexed (idempotent) ────────────
    version_ref = db.collection(META_COLLECTION).document(version_id)
    version_doc = version_ref.get()
    if version_doc.exists and version_doc.to_dict().get("status") == "complete":
        logger.info(f"Version {version_id} already indexed — skipping. Use --force to re-index.")
        return version_id

    # ── 3. Extract + embed chunks ────────────────────────────────────────────
    chunks = extract_chunks(pdf_path, version_id)

    BATCH_SIZE = 5
    total = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch_chunks = chunks[i:i + BATCH_SIZE]
        texts = [c["text"] for c in batch_chunks]
        logger.info(f"Embedding batch {i//BATCH_SIZE + 1} ({len(texts)} chunks)...")
        embeddings = embed(texts)

        fs_batch = db.batch()
        for chunk, embedding in zip(batch_chunks, embeddings):
            doc_ref = db.collection(COLLECTION).document(chunk["chunk_id"])
            fs_batch.set(doc_ref, {
                "chunk_id":    chunk["chunk_id"],
                "version_id":  chunk["version_id"],
                "page_number": chunk["page_number"],
                "text":        chunk["text"],
                "embedding":   embedding,
                "indexed_at":  datetime.now(timezone.utc).isoformat(),
            })
        fs_batch.commit()
        total += len(batch_chunks)
        logger.info(f"Indexed {total}/{len(chunks)} chunks")

    # ── 4. Delete stale chunks from old versions ─────────────────────────────
    delete_stale_chunks(db, version_id)

    # ── 5. Write version metadata record ────────────────────────────────────
    version_ref.set({
        "version_id":   version_id,
        "pdf_path":     os.path.basename(pdf_path),
        "chunk_count":  total,
        "indexed_at":   datetime.now(timezone.utc).isoformat(),
        "status":       "complete",
        "is_latest":    True,
    })

    # Mark all other versions as not-latest
    old_versions = db.collection(META_COLLECTION)\
                     .where("version_id", "!=", version_id)\
                     .stream()
    for v in old_versions:
        v.reference.update({"is_latest": False})

    logger.info(f"Indexing complete. {total} chunks, version={version_id}")
    return version_id


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    args  = [a for a in sys.argv[1:] if not a.startswith("--")]
    pdf_path = args[0] if args else "hr-policy-rathi-textiles.pdf"

    if force:
        # Wipe version record so idempotency check is bypassed
        db_temp = firestore.Client(project=PROJECT_ID)
        vid = file_sha256(pdf_path)
        db_temp.collection(META_COLLECTION).document(vid).delete()
        logger.info("--force: version record deleted, re-indexing...")

    index_pdf(pdf_path)
