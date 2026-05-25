import os
import json
import hashlib
import logging
import requests
import google.auth
import google.auth.transport.requests
from pypdf import PdfReader
from google.cloud import firestore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT", "autonomous-hr-495502")
LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_ENDPOINT = (
    f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}"
    f"/locations/{LOCATION}/publishers/google/models/{EMBEDDING_MODEL}:predict"
)
CHUNK_SIZE = 400
CHUNK_OVERLAP = 80
COLLECTION = "policy_chunks"


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


def extract_chunks(pdf_path: str) -> list[dict]:
    reader = PdfReader(pdf_path)
    chunks = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if not text:
            continue
        # Sliding window chunking
        words = text.split()
        start = 0
        while start < len(words):
            end = start + CHUNK_SIZE
            chunk_text = " ".join(words[start:end])
            chunk_id = hashlib.md5(f"{page_num}:{start}:{chunk_text[:50]}".encode()).hexdigest()
            chunks.append({
                "chunk_id": chunk_id,
                "page_number": page_num,
                "text": chunk_text,
            })
            start += CHUNK_SIZE - CHUNK_OVERLAP
    logger.info(f"Extracted {len(chunks)} chunks from {len(reader.pages)} pages")
    return chunks


def index_pdf(pdf_path: str):
    db = firestore.Client(project=PROJECT_ID)
    chunks = extract_chunks(pdf_path)

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
                "chunk_id": chunk["chunk_id"],
                "page_number": chunk["page_number"],
                "text": chunk["text"],
                "embedding": embedding,
            })
        fs_batch.commit()
        total += len(batch_chunks)
        logger.info(f"Indexed {total}/{len(chunks)} chunks")

    logger.info(f"Indexing complete. {total} chunks in Firestore collection '{COLLECTION}'")


if __name__ == "__main__":
    import sys
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "hr-policy-rathi-textiles.pdf"
    index_pdf(pdf_path)
