# Maint Chat

A chat app for asking questions about uploaded images — photos of documents, tables, diagrams, whiteboards, technical drawings — using a cloud LLM (Gemini or Anthropic) for the actual conversation.

## The pipeline

The core idea: **extraction and reasoning are two separate stages**, run by two different models.

```
                image upload
                      │
                      ▼
      ┌──────────────────────────────┐
      │   Local Qwen3-VL (Ollama)    │
      │      (extraction only)       │
      └───────────────┬──────────────┘
                      │
                      ▼
              Markdown context
          (Extracted Text section +
         Visual Description section)
                      │
                      ▼
      ┌──────────────────────────────┐
      │          Cloud LLM           │
      │     (Gemini / Anthropic)     │
      └───────────────┬──────────────┘
                      │
                      ▼
                   answer
```

1. **Extraction (local, private, no interpretation of the user's question).** When a user uploads an image, the backend immediately sends it to a small vision-language model (Qwen3-VL-4B) running locally via [Ollama](https://ollama.com). This model's only job is to look at the image and produce a structured Markdown description of it — it never sees the user's chat question, and it never talks to the cloud LLM directly.

2. **Reasoning (cloud, no image access).** When the user sends a chat message referencing that upload, the backend pulls the stored Markdown out of the database and hands it to whichever cloud provider is selected (Gemini or Anthropic) as plain text context ahead of the question. The cloud model never sees the raw image — only the local model's Markdown description of it.

This separation means the two models are swappable independently: you could point the extraction stage at a different local VLM, or switch the chat provider mid-conversation, without touching the other side.

### Why extract in two sections instead of one blob of OCR text

The local model is prompted to always produce exactly two Markdown sections per image:

```markdown
## Extracted Text
<verbatim transcription of any visible text, tables reconstructed as GFM pipe tables>

## Visual Description
<description of diagrams, figures, charts, or photos — including how components
 appear to connect or relate to each other>
```

Splitting the prompt into two sections fixes that without giving up the reliable, literal OCR transcription: `Extracted Text` stays exact and quotable (good for tables, forms, signage), while `Visual Description` captures spatial/relational information a pure OCR pass would lose (good for diagrams, charts, photos). Both sections get relayed to the cloud LLM as context, so it can answer questions about either.

An attachment is only marked as failed (`extraction_status="failed"`) if **both** sections come back empty — a diagram with no legible text but a real description of its parts still counts as a successful extraction.

### Why local extraction instead of just sending the image straight to Gemini/Anthropic

- **Cost/latency**: extraction happens once per upload and is reused for every subsequent question in the session, instead of re-sending image bytes to a paid cloud API on every chat turn.
- **Provider independence**: since only the *text description* is what actually gets attached to chat turns, switching cloud providers mid-conversation (or adding a new one later) doesn't require re-processing any previously uploaded images.
- **Swappable extractor**: the local VLM can be upgraded or replaced independently of whichever cloud provider is currently answering questions.

## Request flow

1. `POST /api/upload` — file is saved to disk, classified, and extraction runs **synchronously** (not queued). The response includes the extraction status and text immediately.
2. `POST /api/chat` — takes a message plus a list of already-uploaded `attachment_ids`. Any attachment whose `extraction_status` isn't `"success"` is rejected outright — the cloud LLM never sees a failed or still-pending extraction.
3. On every chat request, the backend reconstructs the **entire session history from the database** (not an in-memory conversation) — pulling each past message's attachments back in as context. This is what makes switching providers mid-session safe: a Gemini-answered turn's image context is still available if you switch to Anthropic for the next question.
4. The assistant's reply, along with which provider/model actually answered, is persisted and returned.

## Running it

### Docker (simplest)

```bash
docker compose up -d --build
```

- Frontend (nginx): `http://localhost:8080`
- Backend (FastAPI): `http://localhost:8000`

The backend container uses `network_mode: host` — this is required so it can reach a locally-running Ollama instance bound to `127.0.0.1:11434` (see [Local model setup](#local-model-setup) below). Don't switch it back to bridge networking without re-solving that reachability problem.

### Manual (backend + frontend separately)

```bash
# Backend
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Configuration

Copy `.env.example` to `.env` at the repo root and fill in what you need:

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` | A provider is only offered to the frontend if its key is set; an unconfigured provider returns a clean `400`, not a crash. |
| `ANTHROPIC_MODEL` / `GEMINI_MODEL` | Which model ID each provider calls. |
| `DEFAULT_PROVIDER` | Provider a new session starts with. |
| `OLLAMA_BASE_URL` | Base URL for Ollama's **native** API (no `/v1` suffix — see below). |
| `OLLAMA_VLM_MODEL` | The local vision model tag. Must be `qwen3-vl:4b-instruct`, not the bare `qwen3-vl:4b` tag — that resolves to a "thinking" variant that leaks reasoning tokens into the extracted Markdown. |
| `OLLAMA_NUM_CTX` | Context window pinned for extraction calls (default `4096`). Without pinning this, Ollama auto-sizes context to whatever VRAM is free — observed ballooning to 262144 tokens (~42GB) on a 48GB GPU for a task that never needs more than a few thousand tokens. |
| `CORS_ORIGINS` | Comma-separated allowed origins — needs both the Vite dev origin and the dockerized nginx origin. |
| `MAX_IMAGE_UPLOAD_MB` | Upload size cap, enforced server-side. |

### Local model setup

The extraction stage needs [Ollama](https://ollama.com) running with the vision model pulled:

```bash
ollama pull qwen3-vl:4b-instruct
```

`vlm_extractor.py` calls Ollama's **native** `/api/chat` endpoint, not the OpenAI-compatibility endpoint (`/v1/chat/completions`) — the compat layer silently drops Ollama-specific fields like `options`, which is how `OLLAMA_NUM_CTX` above actually gets enforced. It also re-encodes every upload to PNG via Pillow before sending it to Ollama regardless of the source format, since the local model's image loader can't decode WebP at all (despite `.webp` being an accepted upload type in the UI).

If you're running the backend on the same machine as Ollama but outside Docker's default bridge network (e.g. Ollama bound to `127.0.0.1` only), use `network_mode: host` as shown in `docker-compose.yml` rather than `host.docker.internal` — the latter resolves to the Docker bridge IP, which a `127.0.0.1`-bound Ollama isn't listening on.

## What's deliberately minimal right now

- **One session per page load.** `GET /api/sessions` exists and returns full history, but there's no UI yet for listing or switching between past sessions.
- **No markdown rendering in the chat UI.** Assistant replies (which are themselves Markdown) currently render as literal text — `**bold**` shows up as asterisks, not bold text.
- **Frontend API base is hardcoded** to `http://localhost:8000/api` in `frontend/src/api/client.js` — not yet build-time configurable, so frontend and backend need to be reachable at that exact address (matters if you're working through remote port-forwarding and only forward one of the two ports).
- **Images only.** CSV/XLSX and PDF upload support existed at one point and were deliberately stripped back down to images-only — the extraction dispatcher (`dispatcher.py`) still looks more general than the single `image` kind it currently routes, which is expected, not leftover cruft.

## Known limitation: dense/small text

A 4B-parameter vision model has a fixed internal budget for how much visual detail it can extract from a single image, regardless of the image's pixel resolution — upscaling a dense image doesn't help and can even blow past the model's context window. Very dense inputs (technical drawings with small multi-column text, tables with many rows) can exceed what the model can reliably resolve in one pass. If extraction comes back empty or clearly incomplete on a dense image, crop it down to the relevant region and upload that instead — the model can accurately transcribe that same content at a smaller, more legible scale.
