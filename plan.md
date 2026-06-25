# Chat Image/Table Upload — Continuation Plan

Original design rationale lived at `C:\Users\ASUS\.claude\plans\refactored-purring-flame.md` on the previous (Windows) dev machine — **not available in this Linux sandbox**. The architecture summary below is self-contained so this file doesn't depend on that doc anymore.

## Architecture (image/table upload → context → cloud LLM)

1. User uploads an image (jpg/png/webp) or table file (csv/xlsx) via `POST /api/upload`.
2. `extraction/dispatcher.py` classifies the file and routes it:
   - Images → `extraction/vlm_extractor.py`, which sends the image to a **local, GPU-cached vision-language model via Ollama** and gets back a GitHub-flavored Markdown transcription (tables reconstructed, prose preserved, illegible cells marked `[unclear]`).
   - CSV/XLSX → `extraction/table_extractor.py` (pandas), markdown table(s) per sheet.
3. The extracted Markdown is stored on the `Attachment` row (`extracted_text`, `extraction_status`, `extraction_method`).
4. When the user sends a chat message referencing `attachment_ids`, `routers/chat.py` builds the turn history and attaches each successfully-extracted attachment as a `context_block` (`providers/base.py: ChatTurn`).
5. `format_turn_text()` renders `[Attached extract — filename: ...] ... [End of attachment]` blocks ahead of the user's question, and the whole thing is sent to whichever **cloud provider** (Gemini or Anthropic) is selected — the local VLM never talks to the cloud LLM directly, it only produces context that gets relayed.
6. The cloud LLM answers using that context; the response and `provider_used`/`model_id_used` are persisted back to the session.

So: **local cached VLM (vision) → Markdown context → cloud LLM (reasoning/chat)**, two clearly separated stages, swappable independently (extractor model vs. chat provider).

## Status as of 2026-06-25

### Vision model: switched to Qwen3-VL-4B-Instruct
- Now pulled and cached locally via Ollama: `qwen3-vl:4b-instruct` (3.3 GB on disk, ID `ee4b975b58c1`).
- **Tag gotcha worth remembering**: the bare tag `qwen3-vl:4b` on Ollama's registry resolves to the **thinking** variant (manifest `from: qwen3-vl:4b-thinking-bf16`), not Instruct — confirmed by comparing registry manifests for `4b` vs `4b-instruct`. The thinking variant emits reasoning tokens before its answer, which would pollute the extracted Markdown and add latency. Confirmed with the user that `qwen3-vl:4b-instruct` (the real Instruct tag) is what's wanted; that's what's wired in. If anyone is tempted to `ollama pull qwen3-vl:4b` thinking it's the same thing, it isn't.
- Wired into config: `backend/app/config.py` default `ollama_vlm_model`, plus `OLLAMA_VLM_MODEL=qwen3-vl:4b-instruct` in both `.env` and `.env.example` (previously these had drifted to `gemma4:e4b`, a leftover from an earlier experiment — corrected).
- Why 4B over the previously-planned 8.8B (`qwen3-vl:latest`): smaller footprint (3.3 GB vs ~5+ GB), still fits comfortably on the A4000's 15 GB VRAM, and the extraction task (structured table/text transcription) doesn't need the larger model's extra capacity.

### GPU connection: confirmed, extraction verified end-to-end
The RTX A4000 is now attached and Ollama is using it (`ollama ps` → `100% GPU`). This unblocks everything that was previously marked "blocked on GPU connection":
- **Image extraction**: tested with a real table screenshot (`Q3 Regional Sales Report`, 5 rows × 4 cols). Cold call (includes model load): **9.2s**. Warm call: **2.4s**. Both produced an exact Markdown match to the source image, including the bolded table label and the footnote line. No timeout (well under the 120s ceiling in `vlm_extractor.py`).
- **XLSX upload**: tested with a real 2-sheet workbook (`Sales`, `Products`). `extraction_status="success"`, exact markdown match for both sheets, headers and values preserved.
- **Extraction failure path**: stopped Ollama mid-test, re-uploaded the same image, got a clean `extraction_status="failed"` with `"Local extraction model unreachable — is Ollama running?"` — no crash, no stack trace leaked to the client. Restarted Ollama (`systemctl start ollama` — it runs as a systemd service, models live outside the `ubuntu` user's home dir; don't `ollama serve` manually as the `ubuntu` user, that spins up a second instance with an **empty** model store and just adds confusion) and re-confirmed extraction still works.
- **Persistence**: restarted the FastAPI process, `GET /api/sessions/{id}` returned full message history intact across the restart.

### Cloud API keys: filled in, chat verified end-to-end with both providers
- `GEMINI_API_KEY` and `ANTHROPIC_API_KEY` are now set in `.env`. Backend restarted to pick them up.
- Before keys were added, confirmed the failure mode was clean: `POST /api/chat` returned `400 {"detail":"Provider '<x>' is not configured (missing API key) or is not a known provider."}` for both providers — no crash.
- With real keys: uploaded the test table image, asked "Which region had the highest revenue, and what was its growth percent?" with `"provider":"gemini"` → correct answer (West, +15.2%) using the extracted Markdown as context, `model_id_used="gemini-3.5-flash"`. Same session, no new attachment, asked a follow-up with `"provider":"anthropic"` → correct answer (South, -3.1%), `model_id_used="claude-sonnet-4-6"` — confirms history reconstruction correctly carries prior-turn attachment context across a provider switch, not just within one provider.
- The full pipeline (local VLM extraction → Markdown context → cloud LLM) is now verified end-to-end, not just per-stage.

### Frontend: built — minimal React + Vite chat UI
- Node.js wasn't installed in this sandbox (only ancient Node 12 via apt) — installed Node 20 LTS via NodeSource.
- Scaffolded with `npm create vite@latest frontend -- --template react` (plain JS, not TS — kept minimal).
- Components (`frontend/src/components/`): `ChatWindow` (session bootstrap + message state), `MessageList`, `MessageBubble` (renders attachments + provider/model attribution), `MessageInput` (textarea + send, Enter-to-send), `FileUploadButton` (hidden file input, accepts jpg/png/webp/csv/xlsx), `AttachmentPreview` (extraction status: pending/success/failed, collapsible extracted-text preview, remove button), `ProviderSwitcher` (gemini/anthropic select).
- `frontend/src/api/client.js`: thin fetch wrapper for the four endpoints (`createSession`, `getSession`, `uploadAttachment`, `sendChatMessage`). Base URL hardcoded to `http://localhost:8000/api` — no `.env`-driven API base yet, fine for local dev, would need to be configurable before any real deployment.
- Scope deliberately cut to "minimal": one session auto-created per page load, no session list/switcher UI, no markdown rendering in message bubbles (plain text/`white-space: pre-wrap`). These are the obvious next additions if the UI needs to grow beyond a single-session demo.
- **Verified in an actual browser**, not just typechecked: installed Playwright + Chromium (no `chromium-cli` available in this sandbox), drove the running Vite dev server (`localhost:5173`) against the running backend (`localhost:8000`) — loaded the app, uploaded the test table image, confirmed the extraction preview rendered with `attachment-success`, asked a question on Gemini, switched to Anthropic mid-session and asked a second question, confirmed both responses rendered with correct attribution, zero browser console errors. Screenshot matched expected layout. Playwright was removed from `package.json` again afterward since it was only needed for this one verification pass, not an ongoing dependency.

### Dockerized: backend + frontend, both verified end-to-end
- `backend/Dockerfile`: `python:3.11-slim`, installs `requirements.txt`, copies `app/`, runs `uvicorn app.main:app` on 8000.
- `frontend/Dockerfile`: multi-stage — `node:20-alpine` builds the Vite app (`npm ci && npm run build`), then `nginx:alpine` serves the static `dist/` output (`frontend/nginx.conf` has SPA fallback: `try_files $uri $uri/ /index.html`). Exposes port 80.
- `docker-compose.yml` (repo root) wires them: backend on host port 8000, frontend nginx on host port 8080.
- **Key gotcha**: Ollama's systemd service on this host binds only to `127.0.0.1:11434`, not `0.0.0.0`. The obvious Docker move — bridge network + `host.docker.internal` via `extra_hosts: host-gateway` — resolves the hostname fine but still gets `Connection refused`, because `host.docker.internal` maps to the docker0 bridge IP (`172.17.0.1`), which Ollama isn't listening on. Reconfiguring Ollama to bind `0.0.0.0` would fix it but widens what can reach it (and it's a shared system service, not really this project's to reconfigure casually). Fix used instead: `network_mode: host` on the **backend** container only — it shares the host's network namespace directly, so `OLLAMA_BASE_URL=http://localhost:11434/v1` (already in `.env`, unchanged) just works. The frontend container stays on the default bridge network (it never needs to reach Ollama or the backend container directly — the browser calls `localhost:8000` itself, same as in dev).
- `backend/app/config.py` gained `cors_origins` (comma-separated, default `http://localhost:5173,http://localhost:8080`) and a `cors_origins_list` property; `main.py`'s CORS middleware now reads from it instead of a single hardcoded Vite-dev origin. Needed because the dockerized frontend serves from a different origin (`:8080`) than Vite dev (`:5173`), and the browser's CORS check is origin-exact.
- `./backend/data` is volume-mounted into the backend container so the SQLite DB and uploaded files persist across container restarts and are shared with the non-Docker dev backend if you switch between the two.
- **Verified for real, not just "docker build succeeded"**: `docker compose up -d`, then through the running containers — `GET /api/health` (200), image upload → GPU extraction succeeded (9.1s, same as non-Docker path, confirming `network_mode: host` actually reaches the A4000-backed Ollama), `/api/chat` with `provider=gemini` answered correctly, and a full browser pass (Playwright again, removed afterward) against `localhost:8080` — upload, extraction preview, question, correct attributed answer, zero console errors.
- Stopped the manually-run dev `uvicorn` process on port 8000 before bringing the compose stack up (`network_mode: host` means the backend container binds 8000 directly, same as any other process — only one can hold the port at a time). The Vite dev server on `:5173` was left running independently; it doesn't conflict with the Docker stack on `:8000`/`:8080`.

### Environment note: shared host, port collisions
This sandbox shares its Docker daemon with an unrelated pre-existing project ("doc-standards") whose backend container also happens to listen on **port 8000** (and frontend on 3000) — coincidence of both projects using the same conventional ports. When testing, the backend for *this* project was run manually:
```
cd backend && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
If port 8000 is ever occupied by `doc-standards-backend-1` again, either ask before stopping that container (it's not part of this project) or run this backend on a different port (8001 worked fine in testing) and update `CORS`/frontend config accordingly.

## Steps to resume

Core pipeline (extraction → context → cloud LLM → minimal UI) is fully built and verified end-to-end as of this status update. What's left is polish/scope, not unblocking:

1. **Session management UI**: currently one session is auto-created per page load with no way to list, rename, or switch back to a previous session (`GET /api/sessions` is implemented backend-side but unused by the frontend). Add a session sidebar if multi-session use is actually needed.
2. **Markdown rendering in chat bubbles**: assistant responses (and extracted-text previews) are plain text right now; the cloud LLMs return Markdown (bold, etc. — visible as literal `**West**` in the UI). Add a markdown renderer (e.g. `react-markdown`) if formatted output matters.
3. **Configurable API base URL**: `frontend/src/api/client.js` hardcodes `http://localhost:8000/api`. Still fine right now because both the Vite dev server and the dockerized nginx happen to run on the same machine as the backend, so `localhost:8000` resolves correctly from the browser either way — but this breaks the moment frontend and backend run on different hosts (e.g. real deployment, or even just accessing the dockerized frontend from another machine on the LAN). Needs a build-time-injected base URL (Vite's `import.meta.env.VITE_API_BASE_URL`, set via `docker-compose.yml` build args) before that point.
4. ~~CSV/XLSX cross-attachment walkthrough~~ — done: attached the table image and a CSV (warehouse stock) to the same message in the browser, asked "which region is high revenue but low stock?" — Gemini correctly joined both extracted datasets and answered "West" with a comparison table. Both pending attachments rendered correctly with independent remove buttons before send.

## Notes / things to double check when resuming
- `vlm_extractor.py`'s timeout is 120s — warm-state inference on the A4000 with `qwen3-vl:4b-instruct` is ~2.4s, cold (model load) ~9.2s, so there's a lot of headroom; no need to touch this.
- `temperature=0.1` in the Ollama request reduces hallucinated cell values — first knob to check if extraction quality looks off, not the prompt.
- Ollama model `OLLAMA_KEEP_ALIVE` default is 5 minutes — if the extractor is idle longer than that between requests, expect the next call to pay the ~9s cold-load cost again (this is normal, not a bug).
