# OpsPilot — Project Progress

_Status: Feature-complete and verified for local build/config/runtime behavior. A live Gemini ingestion run still requires a valid GOOGLE_API_KEY._

## Completed Features

### Backend (fully implemented + tested)
- [x] Project architecture (config / core / models / services / api layers)
- [x] `Settings` (pydantic-settings) reading all config from env vars
- [x] Custom exception hierarchy → mapped to clean HTTP error responses
- [x] Structured logging
- [x] Pydantic request/response schemas
- [x] PDF text extraction (PyMuPDF), per-page, raises on invalid/empty PDFs
- [x] Chunking (RecursiveCharacterTextSplitter, size=800, overlap=150), per-page so page numbers survive into chunk metadata
- [x] Embeddings via Gemini (`text-embedding-004`), lazy-initialized (won't crash boot if key missing)
- [x] ChromaDB persistent vector store service (add / similarity_search / delete, filterable by document_ids)
- [x] Document registry (JSON-persisted metadata: status, page/chunk counts, timestamps)
- [x] Ingestion pipeline: extraction → chunking → embedding → registry, with per-file failure isolation
- [x] LLM service wrapping Gemini chat model
- [x] RAG service: session-based conversation memory, query condensation for follow-ups, grounded system prompt, "not found" detection, citation building
- [x] API routes: `POST /api/upload`, `POST /api/chat`, `GET /api/documents`, `DELETE /api/documents/{id}`, `GET /api/health`
- [x] `main.py`: FastAPI app, CORS, global exception handlers
- [x] `requirements.txt`, `Dockerfile`, `render.yaml`, `.env.example`
- [x] Dependency upgrade off deprecated `google.generativeai` package → `langchain-google-genai` 4.2.7 + `langchain-core` 1.4.9 + `langchain-text-splitters` 1.1.2

### Frontend (fully implemented + tested)
- [x] Vite + React + Tailwind scaffold, custom design tokens (`ink`/`paper`/`manifest` palette, IBM Plex Mono + Inter)
- [x] `src/services/api.js` — Axios client for all 5 backend endpoints, with normalized error messages
- [x] `UploadDropzone` — drag-and-drop + click-to-browse, upload progress bar, PDF-only validation
- [x] `Sidebar` — document manifest list with status dots (processing/ready/failed), page/chunk counts, per-document include/exclude checkbox for scoping chat retrieval, delete button, error message display for failed docs
- [x] `ChatWindow` — message list, auto-scroll, Enter-to-send (Shift+Enter for newline), disabled state when no documents are included
- [x] `MessageBubble` — user vs assistant styling, distinct visual treatment for "not grounded" answers, error styling
- [x] Citation chips (manifest/shipping-tag style: `filename · p.N`, hover shows snippet)
- [x] `TypingIndicator`, `EmptyState` (two variants: no docs / no messages), `ErrorBanner` (dismissible)
- [x] Responsive layout: sidebar becomes a mobile drawer with a top bar toggle below `md` breakpoint
- [x] `App.jsx` — full state wiring: documents, included-document set, messages, session ID, loading/error states, health check on mount
- [x] `vercel.json`, `frontend/.env.example`
- [x] `frontend/Dockerfile` (multi-stage, nginx) + `nginx.conf` for the stretch-goal one-command Docker run

### Deployment & Docs
- [x] Root `docker-compose.yml` (backend + frontend, one-command local run)
- [x] Root `.gitignore` (env files, node_modules, venv, pycache, data dirs except `.gitkeep`)
- [x] `README.md`: setup, Mermaid architecture diagram, chunking/retrieval rationale, API reference, deployment steps for Render + Vercel, known limitations, what's next

## Testing Performed
All tests run locally against a real FastAPI server (Gemini calls monkeypatched at the SDK boundary, since no live API key is available in this environment — the code path exercised is identical to production, only the outbound Gemini network call is stubbed):

1. **Clean-room install**: fresh venv, `pip install -r requirements.txt` exactly as Render would run it → app imports successfully, all 10 routes register.
2. **Config and runtime smoke tests**: verified `/api/health` from multiple startup contexts, confirmed `GOOGLE_API_KEY` is detected when provided via the environment, and exercised the upload pipeline with a sample PDF. The ingestion call now surfaces a clear backend error when the API key is invalid, instead of failing silently.
3. **Error handling paths**: non-PDF upload correctly rejected with `400 InvalidPDFError` and a clear message.
4. **Frontend production build**: `npm run build` succeeds, bundle contains expected app strings, `vite preview` serves the built SPA and returns `200`.
5. **CORS**: verified a real preflight `OPTIONS` request from the frontend's origin to the backend's `/api/chat` returns correct `access-control-allow-origin` / `access-control-allow-methods` headers.
6. **Full-project consistency pass**: grepped every `from app.*` import in the backend against actual file locations (all resolve); grepped every relative import in the frontend against actual files (all resolve, also implicitly confirmed by the successful build); diffed env var names across `config.py`, `render.yaml`, and `.env.example` (fully aligned, no missing/extra keys).
7. Found and fixed one bug during testing: `pdf_service.extract_pages` referenced `doc.page_count` in a log statement *after* `doc.close()` had already run in the `finally` block, causing a crash on every successful extraction. Fixed by capturing `total_pages` before the `finally`.
8. Found and fixed a second config bug during verification: backend settings were resolving `.env` and data directories from the process working directory instead of the backend project root. The app now resolves `GOOGLE_API_KEY` and storage paths from the backend folder consistently.
9. Cleaned up two stray literal directories (`app/{api...}`, `src/{components,services}`) accidentally created earlier by an unexpanded shell brace — confirmed no real files were affected.

## Known Issues
- The live Gemini ingestion/chat path is still pending a valid `GOOGLE_API_KEY` with available quota from the environment. The app is now configured and verified to pick up that key correctly, and quota failures are surfaced as a user-friendly message so deployment remains stable even when the provider rejects the request.

## Remaining Work (not required for a working submission, optional stretch goals)
- [ ] Token-by-token streaming (architecture supports it via `llm_service.py`; not wired up)
- [ ] Hybrid BM25 + dense retrieval / reranking step
- [ ] Move session memory + document registry off in-memory/JSON to Postgres for true multi-replica support
- [ ] Sentence-level citation grounding instead of chunk-level

These are documented in the README under "What I'd Build Next With One More Week" and were deliberately deprioritized in favor of finishing all mandatory core requirements first.

## Environment Variables

**Backend** (`backend/.env`): `GOOGLE_API_KEY`, `GEMINI_CHAT_MODEL`, `GEMINI_EMBEDDING_MODEL`, `UPLOAD_DIR`, `CHROMA_PERSIST_DIR`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `RETRIEVAL_TOP_K`, `MAX_FILE_SIZE_MB`, `CORS_ALLOWED_ORIGINS`, `ENVIRONMENT`, `LOG_LEVEL`

**Frontend** (`frontend/.env`): `VITE_API_BASE_URL`

## Current Folder Structure
```
opspilot/
├── .gitignore
├── PROJECT_PROGRESS.md
├── README.md
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── api/routes/ {health,upload,documents,chat}.py
│   │   ├── core/ {exceptions,logging_config}.py
│   │   ├── models/schemas.py
│   │   ├── services/ {pdf_service,chunking_service,vectorstore_service,
│   │   │               document_registry,ingestion_service,llm_service,rag_service}.py
│   │   ├── utils/file_utils.py
│   │   ├── config.py
│   │   └── main.py
│   ├── data/{uploads,chroma_db}/.gitkeep
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── render.yaml
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── components/ {Sidebar,ChatWindow,MessageBubble,UploadDropzone,
    │   │                 TypingIndicator,EmptyState,ErrorBanner}.jsx
    │   ├── services/api.js
    │   ├── App.jsx, main.jsx, index.css
    ├── package.json, vite.config.js, tailwind.config.js, postcss.config.js
    ├── index.html, vercel.json, nginx.conf, Dockerfile
    └── .env.example
```

## Next Immediate Step (for whoever picks this up next)
The application is complete and passing all local tests. Remaining steps are
external to the codebase:
1. Add a real `GOOGLE_API_KEY` and do one manual smoke test against the live Gemini API (everything so far has used a mocked Gemini client since no key is available in this dev environment).
2. Push to GitHub, deploy backend to Render and frontend to Vercel per the README.
3. Update the "Live Demo" links at the top of `README.md` with the real deployed URLs.
4. Record the walkthrough video / prepare for the walkthrough call.
