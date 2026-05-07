# Plaud AI: PHI-Safe Pipeline

A proof-of-concept that shows how a PHI-safe clinical pipeline could be built on top of Plaud recordings.

The core idea: medical consultation audio contains sensitive patient data. Before any AI model touches the transcript, all Protected Health Information must be detected and removed on-device.

## What This Does

1. Transcribes audio using OpenAI Whisper running locally
2. Detects PHI entities (names, dates, phone numbers, SSNs, medical IDs, locations) using Microsoft Presidio
3. Redacts PHI inline, word-for-word, preserving the full transcript structure
4. Generates a clinical SOAP note from the redacted transcript using a local LLM (Llama 3.2 via Ollama)

No patient data ever leaves the local network.

## Stack

| Layer | Technology |
|---|---|
| Transcription | OpenAI Whisper (CPU, local) |
| PHI Detection | Microsoft Presidio + spaCy en_core_web_lg |
| Redaction | Presidio Anonymizer |
| SOAP Generation | Llama 3.2 via Ollama (self-hosted) |
| Backend | FastAPI + Uvicorn |
| Frontend | Vanilla HTML / CSS / JS |
| Infrastructure | Docker + Docker Compose |

## Live Demo

Static demo (pre-computed sample): https://pavan-249.github.io/plaud-ai-demo/

Note: the static demo shows pre-computed Whisper output for the bundled sample audio. Real-time transcription from arbitrary audio requires the local backend.

## Run Locally

Requires Docker and Docker Compose.

```bash
git clone https://github.com/Pavan-249/plaud-ai-demo.git
cd plaud-ai-demo
docker compose up --build
```

Then open http://localhost:8000.

On first run, the `ollama-init` container automatically pulls the `llama3.2` model. This takes a few minutes depending on your connection. Subsequent runs are instant.

## What Happens in the Pipeline

1. User uploads audio or pastes a transcript
2. Whisper transcribes the audio to text (runs locally)
3. Presidio scans the transcript and flags PHI entities
4. Each flagged entity is replaced inline with a tag like `<PERSON>` or `<DATE_TIME>`
5. The redacted transcript is passed to Ollama for SOAP note generation
6. The full transcript, redacted version, detected entities, and SOAP note are displayed

## Limitations

- Whisper transcription is CPU-only in this setup. A 4-minute audio clip takes roughly 60 to 90 seconds.
- SOAP note generation requires Ollama to be running. Without it, the redaction output still works correctly.
- The GitHub Pages static demo cannot transcribe arbitrary uploaded audio files. Use the Docker setup for full functionality.

## Demo Notes

The bundled sample audio is from the PriMock57 dataset, a publicly available collection of simulated clinical consultations.
