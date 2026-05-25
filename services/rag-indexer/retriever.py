import os
import logging
import requests
import google.auth
import google.auth.transport.requests
from google.cloud import firestore
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT", "autonomous-hr-495502")
LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_ENDPOINT = (
    f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}"
    f"/locations/{LOCATION}/publishers/google/models/{EMBEDDING_MODEL}:predict"
)
COLLECTION = "policy_chunks"
TOP_K = 3


def get_token() -> str:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def embed_query(text: str) -> list[float]:
    token = get_token()
    resp = requests.post(
        EMBEDDING_ENDPOINT,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"instances": [{"content": text}]},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["predictions"][0]["embeddings"]["values"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Retrieve top_k most relevant policy chunks for a query.
    Returns list of dicts with chunk_id, page_number, excerpt, relevance_score.
    """
    logger.info(f"Retrieving top-{top_k} chunks for query: {query!r}")

    query_embedding = embed_query(query)

    db = firestore.Client(project=PROJECT_ID)
    docs = db.collection(COLLECTION).stream()

    scored = []
    for doc in docs:
        data = doc.to_dict()
        chunk_embedding = data.get("embedding", [])
        if not chunk_embedding:
            continue
        score = cosine_similarity(query_embedding, chunk_embedding)
        scored.append({
            "chunk_id": data["chunk_id"],
            "page_number": data["page_number"],
            "excerpt": data["text"][:300],
            "relevance_score": round(score, 4),
        })

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    top = scored[:top_k]

    logger.info(f"Retrieved {len(top)} chunks, top score={top[0]['relevance_score'] if top else 0}")
    return top


if __name__ == "__main__":
    results = retrieve("how many casual leaves am I entitled to?")
    for r in results:
        print(f"Page {r['page_number']} | score={r['relevance_score']}")
        print(r['excerpt'])
        print("---")
