import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

try:
    import whisper
except ImportError:
    whisper = None


ENTITY_LABELS: Dict[str, str] = {
    "PERSON": "[PATIENT_NAME]",
    "DATE_TIME": "[DATE]",
    "PHONE_NUMBER": "[PHONE]",
    "EMAIL_ADDRESS": "[EMAIL]",
    "LOCATION": "[LOCATION]",
    "MEDICAL_LICENSE": "[MEDICAL_LICENSE]",
    "US_DRIVER_LICENSE": "[US_DRIVER_LICENSE]",
    "US_SSN": "[SSN]",
    "AGE": "[AGE]",
}

ENTITY_COLORS: Dict[str, str] = {
    "PERSON": "#3F1D24", # Deep burgundy
    "DATE_TIME": "#1E293B", # Deep slate
    "LOCATION": "#362F1C", # Dark gold
    "PHONE_NUMBER": "#172554", # Deep blue
    "EMAIL_ADDRESS": "#064E3B", # Deep emerald
    "MEDICAL_LICENSE": "#451A03", # Deep amber
    "US_DRIVER_LICENSE": "#312E81", # Deep indigo
    "US_SSN": "#4C1D95", # Deep violet
    "AGE": "#1F2937", # Gray 800
}

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
_ANALYZER: Optional[AnalyzerEngine] = None
_WHISPER_MODELS: Dict[str, object] = {}


@dataclass
class PhiHit:
    entity_type: str
    text: str
    start: int
    end: int
    score: float


def _score_threshold(mode: str) -> float:
    return 0.60 if mode == "realtime" else 0.35


def get_analyzer() -> AnalyzerEngine:
    global _ANALYZER
    if _ANALYZER is None:
        _ANALYZER = AnalyzerEngine()
    return _ANALYZER


def load_whisper_model(mode: str):
    if whisper is None:
        raise RuntimeError("Whisper is not installed.")
    model_name = "base" if mode == "realtime" else "small"
    if model_name not in _WHISPER_MODELS:
        _WHISPER_MODELS[model_name] = whisper.load_model(model_name)
    return _WHISPER_MODELS[model_name]


def transcribe_audio(audio_path: str, mode: str) -> str:
    try:
        model = load_whisper_model(mode)
        result = model.transcribe(audio_path)
        return result.get("text", "").strip()
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required for audio transcription.") from exc


def detect_phi(text: str, mode: str) -> List[PhiHit]:
    if not text.strip():
        return []
    analyzer = get_analyzer()
    results = analyzer.analyze(text=text, entities=list(ENTITY_LABELS.keys()), language="en")
    threshold = _score_threshold(mode)
    hits = [
        PhiHit(r.entity_type, text[r.start : r.end], r.start, r.end, r.score)
        for r in results
        if r.score >= threshold
    ]
    hits.sort(key=lambda h: (h.start, -(h.end - h.start), -h.score))
    deduped: List[PhiHit] = []
    cursor_end = -1
    for h in hits:
        if h.start < cursor_end:
            continue
        deduped.append(h)
        cursor_end = h.end
    return deduped


def redact_phi(text: str, hits: List[PhiHit]) -> str:
    if not text.strip():
        return ""
    operators = {
        entity: OperatorConfig("replace", {"new_value": label})
        for entity, label in ENTITY_LABELS.items()
    }
    anonymizer = AnonymizerEngine()
    analyzer_results = [
        RecognizerResult(entity_type=h.entity_type, start=h.start, end=h.end, score=h.score)
        for h in hits
    ]
    return anonymizer.anonymize(text=text, analyzer_results=analyzer_results, operators=operators).text


def colorize_entities(text: str, hits: List[PhiHit]) -> str:
    if not text:
        return ""
    out: List[str] = []
    cursor = 0
    for h in hits:
        if h.start < cursor:
            continue
        out.append(_escape_html(text[cursor : h.start]))
        color = ENTITY_COLORS.get(h.entity_type, "#1E293B")
        chunk = _escape_html(text[h.start : h.end])
        out.append(
            f"<mark style='background:{color};border:1px solid rgba(255,255,255,0.15);"
            "padding:2px 4px;border-radius:4px;'>"
            f"{chunk} <b>{h.entity_type}</b></mark>"
        )
        cursor = h.end
    out.append(_escape_html(text[cursor:]))
    return "".join(out).replace("\n", "<br>")


def format_phi_table(hits: List[PhiHit]) -> List[Dict[str, str]]:
    return [
        {
            "entity": h.entity_type,
            "value": re.sub(r"\s+", " ", h.text.strip()),
            "confidence": f"{h.score:.2f}",
        }
        for h in hits
    ]


def summarize_with_ollama(redacted_text: str) -> str:
    if not redacted_text.strip():
        return ""
    prompt = (
        "You are a clinical documentation assistant.\n"
        "Create a concise SOAP note from this redacted transcript.\n"
        "Use neutral clinical language.\n\n"
        f"Transcript:\n{redacted_text}"
    )
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=90)
        response.raise_for_status()
        return response.json().get("response", "").strip() or "No summary generated."
    except requests.exceptions.ConnectionError:
        return (
            "⚠️ Ollama is unreachable.\n"
            "If you are running locally, please start Ollama (`ollama serve`).\n"
            "If using Docker, ensure the `ollama` container is running."
        )
    except Exception as exc:
        return f"Ollama summary failed: {exc}"


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
