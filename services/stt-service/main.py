import os
import tempfile
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import storage
from faster_whisper import WhisperModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="stt-service", version="1.0.0")

MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "large-v3")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

logger.info(f"Loading Whisper model={MODEL_SIZE} device={DEVICE} compute={COMPUTE_TYPE}")
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
logger.info("Whisper model loaded")

_gcs_client = None

def get_gcs_client():
    global _gcs_client
    if _gcs_client is None:
        _gcs_client = storage.Client()
    return _gcs_client


class TranscribeRequest(BaseModel):
    gcs_uri: str


class TranscribeResponse(BaseModel):
    transcript: str
    language: str
    language_probability: float
    gcs_uri: str


def download_from_gcs(gcs_uri: str) -> str:
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    without_prefix = gcs_uri[len("gs://"):]
    bucket_name, _, blob_name = without_prefix.partition("/")
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    suffix = os.path.splitext(blob_name)[-1] or ".ogg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        blob.download_to_filename(tmp.name)
        return tmp.name


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_SIZE}


@app.post("/transcribe", response_model=TranscribeResponse)
def transcribe(req: TranscribeRequest):
    logger.info(f"Transcribe request: {req.gcs_uri}")
    try:
        local_path = download_from_gcs(req.gcs_uri)
    except Exception as e:
        logger.error(f"GCS download failed: {e}")
        raise HTTPException(status_code=400, detail=f"GCS download failed: {e}")

    try:
        segments, info = model.transcribe(local_path, beam_size=5)
        transcript = " ".join(seg.text.strip() for seg in segments)
        language = info.language
        language_probability = round(info.language_probability, 4)
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    finally:
        try:
            os.unlink(local_path)
        except Exception:
            pass

    logger.info(f"Done: lang={language} prob={language_probability} chars={len(transcript)}")
    return TranscribeResponse(
        transcript=transcript,
        language=language,
        language_probability=language_probability,
        gcs_uri=req.gcs_uri,
    )
