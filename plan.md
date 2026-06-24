# Chat Image/Table Upload — Continuation Plan

Full design rationale lives in `C:\Users\ASUS\.claude\plans\refactored-purring-flame.md`. This file tracks **build status** and **what's left**, specifically the parts blocked on the RTX A4000 being connected.

## Status as of 2026-06-24

### Done and verified (no GPU needed)
- Backend scaffolded: `backend/app/` — config, db (SQLModel/SQLite), models (ChatSession/Message/Attachment), schemas, provider abstraction (`providers/base.py`, `gemini_provider.py`, `anthropic_provider.py`, `registry.py`), extraction (`extraction/table_extractor.py`, `vlm_extractor.py`, `dispatcher.py`), routers (`sessions.py`, `upload.py`, `chat.py`), `main.py`.
- `.env` / `.env.example` created with all required keys (currently **blank** — `GEMINI_API_KEY` and `ANTHROPIC_API_KEY` need to be filled in before chat calls will work).
- Verified: `pip install -r backend/requirements.txt` succeeds in `backend/.venv`.
- Verified: backend boots (`uvicorn app.main:app --port 8000`), `GET /api/health` → `{"status":"ok"}`.
- Verified: `POST /api/sessions`, `GET /api/sessions` work, SQLite `backend/data/app.db` created correctly.
- Verified: CSV upload → extraction pipeline (`POST /api/upload`) — exact markdown match to source data, no GPU/network involved (pandas path).
- Confirmed Ollama is installed and running locally (`ollama --version` → 0.30.10, `ollama list` shows models).
- Confirmed the user already has `qwen3-vl:latest` pulled (8.8B params, Q4_K_M quant, vision+tools+thinking capable) — **config now points at this exact tag** (`OLLAMA_VLM_MODEL=qwen3-vl:latest` in both `.env` and `.env.example`), no need to pull the originally-planned `qwen3-vl:8b-instruct-q4_K_M` tag separately.

### Blocked on GPU connection
- **Image extraction via Ollama failed with a timeout** when tested without the GPU attached — request exceeded the 120s timeout in `vlm_extractor.py` (CPU-only inference on an 8.8B VLM is far too slow). This is expected/environmental, not a code bug. **Must retest once the A4000 is connected.**
- XLSX upload path is implemented but untested (CSV path was tested as the representative pandas case; XLSX uses the same `table_extractor.py` module, low risk, but worth a quick confirmation pass).
- `/api/chat` end-to-end (provider dispatch, history reconstruction, context injection) is implemented but **never actually called** yet — needs real `GEMINI_API_KEY`/`ANTHROPIC_API_KEY` values in `.env` first.
- Frontend (React + Vite) has not been built yet — directory structure exists (`frontend/src/{components,hooks,api}`) but no files written.

## Steps to resume once GPU is connected

1. **Confirm Ollama is using the GPU**: `ollama ps` while a request is in flight should show GPU in the processor column, not 100% CPU. If it still falls back to CPU, check `nvidia-smi` is visible and Ollama's GPU detection (may need a restart of the Ollama service after the GPU becomes available).
2. **Re-run the image extraction test**: generate or use a real phone photo / screenshot of a table, `POST /api/upload` with it, confirm `extraction_status="success"` and inspect `extracted_text` fidelity (this is verification step 4 from the original plan). Time the request — first call will include Ollama's model-load cold start, second call should be fast (steady-state inference on GPU should be a few seconds, not minutes).
3. **Test XLSX upload** the same way CSV was tested — multi-sheet workbook, confirm exact markdown match.
4. **Fill in real API keys** in `.env` (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`), restart backend.
5. **Test `/api/chat` end-to-end**: create a session, upload the table image from step 2, `POST /api/chat` with `attachment_ids` referencing it and a question about the data, once with `"provider": "gemini"` and once with `"provider": "anthropic"` — confirm both answer correctly and `provider_used`/`model_id_used` in the response match.
6. **Test the failure path**: stop Ollama, attempt an image upload, confirm clean `extraction_status="failed"` with a readable error (already covered by `vlm_extractor.py`'s exception handling, but worth re-confirming after any Ollama config changes made in step 1).
7. **Test persistence**: restart the FastAPI process, `GET /api/sessions/{id}`, confirm full history including `extracted_text` survives.
8. **Build the frontend**: React + Vite chat UI per the original plan (`ChatWindow`, `MessageList`, `MessageBubble`, `MessageInput`, `FileUploadButton`, `AttachmentPreview`, `ProviderSwitcher`) wired to the now-verified backend API. This was deferred to validate the backend pipeline first, since the GPU-dependent extraction path was the highest-risk/most-likely-to-need-rework piece.
9. **Full manual walkthrough** per the original plan's verification step 9 (create chat, switch provider, upload image, see extraction preview, ask question, send, confirm attribution; then add a CSV and ask a cross-attachment follow-up).

## Notes / things to double check when resuming
- `vlm_extractor.py`'s timeout is currently 120s — if even GPU-warm inference plus model load is consistently taking longer than that on the A4000, bump it before assuming something's broken.
- The `temperature=0.1` setting in the Ollama request was chosen to reduce hallucinated cell values — if extraction quality looks off, this is one of the first knobs to check (not the prompt itself).
- No code changes are anticipated to be needed for the GPU-dependent steps — this is a "come back and test" list, not a "come back and build" list, with the sole exception of the frontend (step 8), which is genuinely unbuilt.
