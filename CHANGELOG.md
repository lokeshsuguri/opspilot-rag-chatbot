# CHANGELOG — Upload/Chat Incident Fix

## Root cause

`vectorstore_service._get_embeddings()` loaded the sentence-transformer
embedding model synchronously, on the request thread, on every cold start,
with no persisted cache — directly inside the async `/api/upload` handler
with no thread offload. On a fresh deploy this either blocked the single
event loop long enough to trip the platform's proxy timeout (502) or failed
outright if the model download stalled, and it froze `/api/health` and every
other concurrent request for the same duration.

## Fixes applied

1. **`backend/requirements.txt`** — removed a duplicate, conflicting
   `sentence-transformers` version pin (`5.6.0` and `3.3.1` were both
   present). This made a clean `pip install -r requirements.txt` fail
   outright with `ResolutionImpossible` on any fresh build (verified).

2. **`backend/app/services/vectorstore_service.py`**
   - Embedding model now caches to a directory on the app's persisted disk
     (`hf_cache_dir`) instead of the default `~/.cache/huggingface`, so it
     survives container restarts/redeploys instead of re-downloading every
     time.
   - Added `warm_up()` to force-load the embedding model and Chroma client
     once, eagerly, instead of lazily on a user's first request.
   - Disabled Chroma's telemetry (`anonymized_telemetry=False`) — it was
     throwing an internally-caught `TypeError` on every startup
     (`capture() takes 1 positional argument but 3 were given`), which was
     pure log noise but made real errors harder to spot.

3. **`backend/app/main.py`** — added a FastAPI startup hook that calls
   `vectorstore_service.warm_up()` via `asyncio.to_thread` at boot. A failed
   warm-up (e.g. no network) now logs a full traceback at startup and the
   app still boots so `/api/health` can report it, instead of failing
   silently mid-request.

4. **`backend/app/api/routes/upload.py`** — the blocking, CPU-bound
   ingestion call (PDF parse + chunk + embed) is now run via
   `asyncio.to_thread(...)` instead of being awaited directly on the event
   loop. Uploads (and slow/cold ones especially) can no longer freeze
   `/api/health` or other concurrent requests.

5. **`backend/app/api/routes/health.py`** — removed leftover debug `print()`
   statements.

6. **`backend/app/config.py`** — added `hf_cache_dir` setting (defaults to
   `data/hf_cache`, alongside the existing Chroma/upload dirs).

7. **`backend/.env.example`** — replaced stale Gemini variables
   (`GOOGLE_API_KEY`, `GEMINI_CHAT_MODEL`, `GEMINI_EMBEDDING_MODEL`, none of
   which the app reads) with the ones actually used (`GROQ_API_KEY`,
   `CHAT_MODEL`, `EMBEDDING_MODEL`, `HF_CACHE_DIR`).

8. **`backend/render.yaml`** — same fix: replaced stale Gemini env vars with
   `GROQ_API_KEY`/`CHAT_MODEL`/`EMBEDDING_MODEL`, and added `HF_CACHE_DIR`
   pointed at the mounted persistent disk so the embedding model cache
   survives Render redeploys.

9. **`docker-compose.yml`** — same fix: backend service was only passing
   Gemini env vars, so `GROQ_API_KEY` never reached the container and chat
   would fail immediately with a missing-API-key error. Also moved
   `VITE_API_BASE_URL` from the frontend service's runtime `environment:`
   (a no-op — Vite bakes this in at build time for a static nginx image) to
   a build `arg:`, matching how the frontend Dockerfile already consumes it.

10. **`backend/Dockerfile`** — image now also creates `data/hf_cache` at
    build time, matching the other persisted data directories.

11. Removed stray, non-portable artifacts that had been committed into the
    project: a Windows-built `.venv/`, a `backend/venv/` (Windows-built,
    14MB+), a stray top-level `data/` directory, and `.vs/` (Visual Studio
    IDE cache). `frontend/node_modules/` was removed for the same reason —
    it contained a platform-specific `rollup` binary that made `npm run
    build` fail with `Cannot find module @rollup/rollup-linux-x64-gnu` on
    Linux/Render; run `npm install` fresh instead of relying on a committed
    `node_modules/`.

## What was verified directly (not assumed)

- `pip install -r backend/requirements.txt` succeeds in a clean virtualenv
  (previously failed with `ResolutionImpossible`).
- `npm install && npm run build` succeeds in the frontend from a clean
  state (previously failed with a missing native `rollup` binary from the
  committed `node_modules/`).
- Backend boots, `/api/health` returns `200`, `/api/documents` returns
  `200`, and `/api/upload` returns a clean, structured `200` response
  (with a per-file `status`/`error_message`, never a hang or a 500/502)
  end-to-end against the real code.
- All backend `.py` files pass `py_compile`; `render.yaml` and
  `docker-compose.yml` parse as valid YAML.

## What could not be exercised end-to-end in this environment

The sandbox this fix was built and tested in blocks outbound network access
to `huggingface.co` and `api.groq.com` (confirmed: both return `403` at the
network layer here). That means the actual embedding download and the
actual Groq chat completion could not be executed live in this environment.
Every other part of the pipeline — PDF parsing, chunking, Chroma writes,
the async/threading behavior, startup warm-up, error handling, and the
full request/response contract — was exercised against the real code and
confirmed working. With normal internet access (your machine, Render, etc.)
the embedding download and Groq call will run through the same,
now-non-blocking code path.
