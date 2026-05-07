from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pipeline import (
    colorize_entities,
    detect_phi,
    format_phi_table,
    redact_phi,
    summarize_with_ollama,
    transcribe_audio,
)

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
STATIC_DIR = WEB_DIR / "static"

app = FastAPI(title="PHI-Safe Transcription API")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class LiveGuardRequest(BaseModel):
    text: str
    mode: str = "realtime"


@app.get("/")
def root():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/samples")
def samples():
    return {
        "recommended_audio": "/static/samples/day5_consultation11_combined_loud.mp3",
        "test_tone_audio": "/static/samples/audio_test_tone.wav",
    }


@app.post("/api/live-guard")
def live_guard(payload: LiveGuardRequest):
    mode = payload.mode if payload.mode in {"realtime", "accurate"} else "realtime"
    hits = detect_phi(payload.text or "", mode=mode)
    redacted = redact_phi(payload.text or "", hits)
    return {
        "highlighted": colorize_entities(payload.text or "", hits),
        "redacted": redacted,
        "entities": format_phi_table(hits),
        "count": len(hits),
        "status": f"Live guard ({mode}) detected {len(hits)} PHI entities.",
    }


@app.post("/api/full-pipeline")
async def full_pipeline(
    mode: str = Form("accurate"),
    transcript: str = Form(""),
    summarize: bool = Form(True),
    audio: Optional[UploadFile] = File(None),
):
    mode = mode if mode in {"realtime", "accurate"} else "accurate"
    base_text = (transcript or "").strip()
    status_parts = []

    if audio and audio.filename:
        suffix = Path(audio.filename).suffix or ".wav"
        with NamedTemporaryFile(delete=True, suffix=suffix) as tmp:
            tmp.write(await audio.read())
            tmp.flush()
            base_text = transcribe_audio(tmp.name, mode=mode)
            status_parts.append(f"Transcribed audio in {mode} mode.")

    hits = detect_phi(base_text, mode=mode)
    redacted = redact_phi(base_text, hits)
    soap = summarize_with_ollama(redacted) if summarize else ""

    status_parts.append(f"Detected {len(hits)} PHI entities.")
    if mode == "realtime":
        status_parts.append("Realtime mode favors speed.")
    else:
        status_parts.append("Accurate mode favors recall and precision.")

    return {
        "original": base_text,
        "highlighted": colorize_entities(base_text, hits),
        "redacted": redacted,
        "entities": format_phi_table(hits),
        "soap": soap,
        "status": " ".join(status_parts),
    }
