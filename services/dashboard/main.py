"""
dashboard/main.py
S-26: HITL queue dashboard — password-protected, reads Firestore directly.
Endpoints:
  GET  /              → HTML dashboard (Basic Auth)
  GET  /api/queue     → JSON list of pending + recent items (Basic Auth)
  POST /api/resolve/{corr_id} → mark item resolved (Basic Auth)
"""
import os
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from google.cloud import firestore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app       = FastAPI(docs_url=None, redoc_url=None)
security  = HTTPBasic()
templates = Jinja2Templates(directory="templates")

PROJECT_ID      = os.getenv("GCP_PROJECT", "autonomous-hr-495502")
HITL_COLLECTION = "hitl_queue"


# ── Auth ──────────────────────────────────────────────────────────────────────

def _get_password() -> str:
    """Pull DASHBOARD_PASSWORD from env (Secret Manager injects it at runtime)."""
    pw = os.environ.get("DASHBOARD_PASSWORD", "")
    if not pw:
        raise RuntimeError("DASHBOARD_PASSWORD env var not set")
    return pw


def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    expected_pw = _get_password()
    pw_ok = secrets.compare_digest(
        credentials.password.encode(), expected_pw.encode()
    )
    user_ok = secrets.compare_digest(
        credentials.username.encode(), b"employer"
    )
    if not (pw_ok and user_ok):
        raise HTTPException(
            status_code=401,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ── Firestore helpers ─────────────────────────────────────────────────────────

def get_db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def _age_minutes(created_at_iso: str) -> int:
    try:
        created = datetime.fromisoformat(created_at_iso)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - created
        return max(0, int(delta.total_seconds() / 60))
    except Exception:
        return -1


def fetch_queue(status_filter: Optional[str] = None) -> list[dict]:
    db   = get_db()
    col  = db.collection(HITL_COLLECTION)
    docs = col.order_by("created_at", direction=firestore.Query.DESCENDING).limit(50).stream()

    items = []
    for doc in docs:
        d = doc.to_dict()
        if status_filter and d.get("status") != status_filter:
            continue
        slots = d.get("slots", {})
        items.append({
            "corr_id":        d.get("correlation_id", doc.id),
            "worker_id":      d.get("worker_id", "unknown"),
            "intent":         d.get("intent", "unknown").replace("_", " ").title(),
            "leave_type":     (slots.get("leave_type") or "—").title(),
            "start_date":     slots.get("start_date") or "—",
            "end_date":       slots.get("end_date") or "—",
            "ai_decision":    d.get("ai_decision", "unknown").upper(),
            "confidence_pct": f"{round(d.get('confidence_score', 0) * 100)}%",
            "hitl_reason":    d.get("hitl_reason", ""),
            "policy_clause":  d.get("policy_clause", "")[:60],
            "status":         d.get("status", "pending"),
            "age_minutes":    _age_minutes(d.get("created_at", "")),
            "created_at":     d.get("created_at", "")[:19].replace("T", " "),
        })
    return items


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, _: str = Depends(require_auth)):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/queue")
def api_queue(
    status: Optional[str] = None,
    _: str = Depends(require_auth),
):
    items = fetch_queue(status_filter=status)
    pending = [i for i in items if i["status"] == "pending"]
    resolved = [i for i in items if i["status"] != "pending"]
    return JSONResponse(content={
        "pending":  pending,
        "resolved": resolved,
        "total":    len(items),
    })


@app.post("/api/resolve/{corr_id}")
def api_resolve(corr_id: str, _: str = Depends(require_auth)):
    db      = get_db()
    doc_ref = db.collection(HITL_COLLECTION).document(corr_id)
    doc     = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Item not found")
    data = doc.to_dict()
    if data.get("status") != "pending":
        return JSONResponse(content={"status": data.get("status"), "skipped": True})
    doc_ref.update({
        "status":      "resolved",
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "resolved_by": "dashboard",
    })
    logger.info(f"dashboard: manually resolved corr_id={corr_id}")
    return JSONResponse(content={"status": "resolved", "corr_id": corr_id})
