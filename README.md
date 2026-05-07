# Plaud AI: PHI-Safe Clinical Pipeline Demo

This repository contains a high-end, self-hosted demonstration of **Zero-Latency PII/PHI Redaction** and **Automated SOAP Note Generation** tailored for medical transcripts.

Built to run entirely on-premise, this pipeline ensures that no sensitive Protected Health Information (PHI) ever leaves the local environment. It uses local spaCy/Presidio models for instant masking, and a local, self-hosted Large Language Model (Llama 3.2 via Ollama) to generate clinical summaries from the *safe, redacted* text.

## Features

- **Luxury Dark Mode UI**: A highly polished, presentation-ready web interface with embedded tooltips.
- **Zero-Latency Redaction**: Real-time PHI detection using `Microsoft Presidio` and `spaCy`, providing instant visual feedback as you type without waiting for LLM latency.
- **Self-Hosted AI**: Utilizes `Ollama` running `llama3.2` locally to ensure complete data sovereignty and HIPAA compliance.
- **Idempotent Deployment**: Fully containerized. A single command spins up the backend, frontend, and automatically pulls the required LLM weights.

## Technology Stack

- **Backend**: FastAPI, Uvicorn, Python 3.10
- **NLP & Redaction**: `spacy` (`en_core_web_lg`), `presidio-analyzer`, `presidio-anonymizer`
- **Transcription**: `openai-whisper` (CPU mode optimized for local execution)
- **LLM**: `Ollama`
- **Frontend**: Vanilla HTML/JS, CSS Glassmorphism & Flexbox UI
- **Infrastructure**: Docker, Docker Compose

## Getting Started

### Prerequisites
- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) installed on your machine.

### Deployment (1-Click Run)

The entire application, including the local LLM, is orchestrated via Docker Compose.

1. Clone the repository and navigate into the directory:
   ```bash
   cd plaud_ai
   ```

2. Start the services:
   ```bash
   docker compose up --build
   ```

**What happens next?**
- The `web` service builds the Python environment and starts the FastAPI server.
- The `ollama` service starts the local LLM engine.
- The `ollama-init` service automatically waits for the engine to boot and pulls the `llama3.2` model (this may take a few minutes on the first run depending on your internet connection).

3. Open your browser and navigate to:
   **[http://localhost:8000](http://localhost:8000)**

## Architecture Workflow

1. **Input**: User pastes a transcript or uploads an audio file (processed via Whisper).
2. **Analysis**: The text is streamed to Presidio Analyzer which detects entities (PERSON, DATE, LOCATION, etc.).
3. **Masking**: Presidio Anonymizer replaces identified entities with safe tags (e.g., `<PERSON>`).
4. **Summarization**: The safe, redacted text is sent to the local Ollama container to generate a clinical SOAP note.
5. **Output**: The frontend displays the live highlighted text, the redacted text, the detected entity chips, and the final SOAP note.
