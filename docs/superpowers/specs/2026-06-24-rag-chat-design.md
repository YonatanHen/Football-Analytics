# RAG Chat — Design Spec

- **Date:** 2026-06-24
- **Status:** Approved design, pending implementation plan
- **Branch:** `dev/rag-chat`
- **Author:** Yonatan Hen (with Claude Code)

## 1. Summary

Add a conversational chat feature to the Football-Analytics app. A user asks
natural-language questions about players; the system retrieves the most relevant
player data from MongoDB via vector search and uses Google Gemini to answer.
When the database clearly contains the answer, Gemini answers **from the DB
context only**; when the database does not cover the question, Gemini falls back
to **Google Search grounding** for current/relevant information. The vector
index is rebuilt from the current database state whenever new data is fetched or
refreshed.

## 2. Goals / Non-goals

**Goals**
- Semantic/descriptive questions ("find an undervalued creative winger").
- Single-player explanations ("why is player X flagged as a sleeper?").
- Open, multi-turn conversational follow-ups.
- Answer from the DB when the DB has the answer; only reach the web when it
  doesn't — saving Gemini grounding quota and improving precision.
- Re-vectorize automatically after each data fetch/refresh.

**Non-goals (v1)**
- Primarily analytical/ranking questions ("top 10 by s_final") — those are
  better served by the existing structured endpoints, not vector RAG.
- Server-side chat session storage (multi-turn is stateless in v1).
- Streaming responses.
- Hebrew / multilingual support (English-only embeddings for now).
- A reindex control in the UI (reindexing is automatic + backend-only).
- Sport-5 pricing data and "RAG over everything" — deferred to future phases.

## 3. Stack (decided)

| Layer | Decision |
|---|---|
| Orchestration | FastAPI + LangChain (**retrieval layer only**) |
| LLM | Native `google-genai` unified SDK, model `gemini-3.5-flash`, async (`client.aio.*`), **Grounding with Google Search** used conditionally (see §8) |
| Auth | `GEMINI_API_KEY` env var, resolved automatically by the SDK; loaded via Pydantic Settings from `secrets.env` |
| Resilience | `429` retry+backoff → fallback flash model (`gemini_fallback_model`) → graceful error message |
| Embeddings | **Local** `fastembed` via LangChain `FastEmbedEmbeddings`, model `BAAI/bge-small-en-v1.5` (384-dim, English). Free + unlimited re-indexing, runs in-container on CPU |
| Vector store | MongoDB Atlas Vector Search via `langchain-mongodb` (`MongoDBAtlasVectorSearch`). Requires swapping `mongo:7` → `mongodb/mongodb-atlas-local` |
| Retrieval flow | embed query → `$vectorSearch` top-k **with scores** → confidence gate → DB-only OR web-grounded Gemini call |
| Embedded unit | `build_player_document()` per `(player, season)`, human-readable text |
| Re-vectorization | hook in `fetch_runner` after upsert; backend-only manual endpoint (no UI) |
| Multi-turn | stateless — frontend sends recent `history[]` with each request |
| Frontend | floating circle launcher (top-right) → chat view built with `@chatscope/chat-ui-kit-react`; answer + collapsible sources |

### Why this split

- **Embeddings and generation are decoupled.** The only invariant is that the
  *same* embedding model is used at index time and query time. The LLM is
  irrelevant to the embedding space, so local HuggingFace embeddings + Gemini LLM
  is a valid, deliberate pairing.
- **Local embeddings preserve Gemini free-tier quota.** Re-vectorizing the whole
  DB on every refresh would otherwise burn the strict free-tier RPM budget;
  doing it locally keeps that budget for the chat itself.
- **LangChain is used for retrieval only.** Its Gemini wrapper
  (`langchain-google-genai`) has historically depended on the *legacy*
  `google-generativeai` library, which is explicitly disallowed; all Gemini
  calls therefore go through the native unified `google-genai` SDK. LangChain
  still earns its place in the retrieval layer (vector store + composable
  retrievers) as the corpus grows.

## 4. Architecture

### Data flow — indexing (on data refresh)

```
fetch_runner finishes upsert
  → indexer selects players whose stats changed in this fetch
  → build_player_document(player) → human-readable text per (player, season)
  → fastembed (bge-small-en-v1.5) embeds the text → 384-dim vector
  → upsert into player_embeddings (text + vector + metadata)
```

### Data flow — chat (per question)

```
POST /v1/chat  { message, history[], allow_web? }
  → embed query (same fastembed model)
  → $vectorSearch top-k WITH SCORES from player_embeddings  (LangChain MongoDBAtlasVectorSearch)
  → CONFIDENCE GATE (see §8):
        strong DB match  → Gemini call with DB context only, NO Google Search
        weak/empty match → Gemini call WITH Google Search grounding
  → { answer, sources: { players[], web_citations[] } }
```

## 5. Backend components

Follows the existing layered architecture. RAG orchestration lives in a **new
`services/` package** added **for this feature only** — `modes/` and
`fetch_runner` are left untouched (a repo-wide move into `services/` is an
explicitly separate, future cleanup, not part of this PR).

```
app/
  api/
    chat.py                # POST /v1/chat ; (backend-only) POST /v1/chat/reindex ; GET /v1/chat/index-status
  domain/
    player_document.py     # build_player_document() — pure, unit-testable
  infrastructure/
    gemini_client.py       # shared genai.Client(); async generate (grounded + DB-only) + 429 retry + fallback
    vector_store.py        # MongoDBAtlasVectorSearch setup + scored retrieval; FastEmbedEmbeddings
  services/                # NEW package — RAG orchestration only
    rag_service.py         # retrieve(scored) → confidence gate → assemble prompt → generate → extract sources
    indexer.py             # (re)embed changed players; called by fetch_runner + backend manual endpoint
  config.py                # + gemini_*, embedding_model, vector_dimensions, rag_top_k, rag_grounding_threshold
  dependencies.py          # + get_rag_service(), get_indexer()
```

> Note: there is no separate `embedding_client` module — embeddings come from
> LangChain's `FastEmbedEmbeddings` directly inside `vector_store.py` (no custom
> adapter, since Gemini is not used for embeddings).

## 6. Data model

New collection **`player_embeddings`** — one document per `(player_bio_id, season)`:

```json
{
  "player_bio_id": "<ObjectId ref to player_bios>",
  "season": "2025-2026",
  "sofascore_player_id": "123456",
  "text": "<human-readable player card>",
  "embedding": [/* 384 floats */],
  "metadata": {
    "name": "...", "team": "...", "position": "...",
    "nationality": "...", "sleeper_flag": "...", "low_sample_size": false
  }
}
```

**Atlas vector search index** `vector_index` on `embedding`:
- type: `vectorSearch`, path `embedding`, **384 dimensions**, similarity `cosine`.
- `metadata.*` fields exposed as `filter` fields for future metadata filtering.

## 7. Embedded document design

`build_player_document(player) -> str` is a **pure** function in `domain/`
producing retrieval-friendly natural-language text (not raw numbers), e.g.:

> "Marcus Example is a 24-year-old forward (RW) for Example FC, nationality
> English, in the 2025-2026 season. Over 1,420 minutes across 18 appearances
> (15 starts) he scored 9 goals and 6 assists. Per 90: 0.57 goals, 0.38 assists,
> 0.49 xG, 0.31 xA. Composite fantasy score (s_final): 7.2. Flagged as a
> HIGH_VALUE sleeper (ratio 1.8). Sample size is sufficient."

Keeping it human-readable (per the project's RAG note) materially improves
retrieval over embedding opaque numeric blobs.

## 8. Conditional grounding (web only when needed)

Core principle: **if the database can answer, do not call the web.** Web
grounding is reserved for questions the DB does not cover.

**Confidence gate** — decided before the Gemini call, from retrieval results:
1. Vector-search the DB and return top-k **with similarity scores**
   (`similarity_search_with_score`).
2. **Measuring confidence:** Atlas returns a per-result `score`; for cosine it is
   normalized to `(1 + cosθ)/2 ∈ [0,1]` (1 = identical). The v1 signal is the
   **top-1 score** (optionally also requiring ≥1 doc above threshold). A future
   refinement can add a score-gap signal (top-1 minus the rest) to detect a clear
   standout. *(Exact normalization is a build-time verify item.)*
3. Branch:
   - **Strong DB match** (top-1 ≥ `rag_grounding_threshold`): build the prompt
     from retrieved player docs and call Gemini **without** the Google Search
     tool. Answer synthesized purely from DB context. **Zero web-search quota.**
   - **Weak / empty match** (top-1 < threshold): call Gemini **with** Google
     Search grounding enabled, as the fallback for uncovered or time-sensitive
     questions.

Either branch is a single Gemini call.

**Choosing the threshold (empirical — cannot be picked a priori):**
- Assemble a small labeled eval set: questions the DB *can* answer vs. questions
  that *need* the web.
- Run them through retrieval, record top-1 scores, and pick the cutoff that best
  separates the two score distributions (the valley between them).
- This is the `data-analyst` agent's job. Ship a placeholder default
  (~`0.72` normalized cosine) and tune from the eval.
- **Trade-off the threshold controls:** too low → DB-answerable questions still
  hit the web (wastes quota); too high → questions the DB can't fully answer get
  answered DB-only (hurts accuracy). Bias toward web-fallback if accuracy matters
  more, toward DB-only if quota is tight.

**Backstops & controls:**
- **Model discretion:** even on the web branch, Gemini only issues a search query
  when it judges the context insufficient — enabling grounding ≠ always
  searching. The confidence gate is the explicit control; model restraint is a
  secondary saver.
- **Per-request override:** `allow_web: bool` on `POST /v1/chat` (default `true`).
  When `false`, the web branch is never taken regardless of confidence — a
  "search my data only" mode.

## 9. LLM, grounding & resilience

- One shared `genai.Client()` created once in `infrastructure/gemini_client.py`
  (resolves `GEMINI_API_KEY` from env).
- DB-only generation: `await client.aio.models.generate_content(model=settings.gemini_model, contents=prompt)` (no tools).
- Web-grounded generation: same call with `config=GenerateContentConfig(tools=[Tool(google_search=GoogleSearch())])`.
- Async throughout so the FastAPI event loop is never blocked. PyMongo is sync,
  so the retriever call runs via `run_in_threadpool`.
- **Resilience policy** (wraps the native calls; LangChain never sees a Gemini
  error):
  1. Retry with exponential backoff on `429` (e.g. `tenacity`).
  2. On persistent failure / model unavailability, fall back to
     `settings.gemini_fallback_model` (a free-tier flash model).
  3. If all attempts fail, return a graceful "couldn't reach the model right now"
     answer rather than a 500. App stability prioritized over completeness.

## 10. API endpoints

| Method | Path | Surfaced in UI? | Purpose |
|---|---|---|---|
| `POST` | `/v1/chat` | Yes | Body `{ message, history[], allow_web? }` → `{ answer, sources }`. `history` is client-held; `allow_web` defaults `true`. |
| `POST` | `/v1/chat/reindex` | **No (backend-only)** | Manual embedding rebuild. Also callable from a `scripts/` utility. |
| `GET`  | `/v1/chat/index-status` | **No (backend-only)** | Embedding coverage / last reindex time. |

## 11. Re-vectorization trigger

- **Automatic:** `fetch_runner` calls `indexer.reindex(changed_player_ids)` after
  its upsert step, embedding only players whose stats changed in that fetch.
- **Manual (backend-only):** `POST /v1/chat/reindex` / a `scripts/` utility — **no
  UI control.**
- Consistent with the "no auto-fetch; all data loads are explicit user actions"
  rule — embedding happens only as a consequence of a user-triggered fetch or an
  explicit backend reindex.

## 12. Multi-turn (stateless)

The frontend holds the conversation and sends recent `history[]` with each
request; the backend is stateless. No new sessions collection in v1. Server-side
session storage can be added later without changing the retrieval/generation
core.

## 13. Frontend

- **Floating launcher:** a small custom Tailwind component — a circular button
  fixed to the **top-right** (`fixed top-4 right-4 rounded-full`). Clicking it
  toggles the chat view open/closed.
- **Chat view:** built with **`@chatscope/chat-ui-kit-react`**
  (`MainContainer` / `ChatContainer` / `MessageList` / `Message` / `MessageInput`
  / `TypingIndicator`). State: a `messages` array; on send → `POST /v1/chat` with
  the recent `history[]`; show `TypingIndicator` while awaiting; append the
  answer.
- **Sources:** collapsible section under an answer — DB player sources link/open
  the existing `PlayerDetail` modal; web citations (only when the web-grounded
  branch ran) come from Gemini grounding metadata.
- **Styling caveat:** `@chatscope/chat-ui-kit-styles` ships its own CSS; some
  overrides are needed to match the app's Tailwind look. Acceptable, planned.
- **No reindex / index-status controls anywhere in the UI.**

## 14. Config / `.env`

Add to `config.py` Settings (read from `secrets.env`):

| Setting | Default |
|---|---|
| `gemini_api_key` | (from env `GEMINI_API_KEY`) |
| `gemini_model` | `gemini-3.5-flash` |
| `gemini_fallback_model` | a free-tier flash model (confirmed at build) |
| `embedding_model` | `BAAI/bge-small-en-v1.5` |
| `vector_dimensions` | `384` |
| `rag_top_k` | e.g. `8` |
| `rag_grounding_threshold` | tuned with data-analyst (placeholder ~`0.72`) |

## 15. Dependencies

**Backend:** `google-genai` (unified SDK), `langchain`, `langchain-mongodb`,
`fastembed` (+ the LangChain fastembed embeddings integration), `tenacity`.
(No `langchain-google-genai` — avoids the legacy SDK.)

**Frontend:** `@chatscope/chat-ui-kit-react`, `@chatscope/chat-ui-kit-styles`.

## 16. Infrastructure changes

- `docker-compose.yml`: replace the `mongo:7` service with
  `mongodb/mongodb-atlas-local` so `$vectorSearch` is available locally. Keep the
  same `MONGO_URI` shape; create the `vector_index` on startup (init step or
  app-lifespan check).
- Backend image gains the `fastembed` model weights (small; baked or downloaded
  on first run).

## 17. Testing strategy

- **Pure units** (`pytest`): `build_player_document()`, prompt assembly, the
  confidence gate (strong vs weak → correct branch + `allow_web=false` override),
  source extraction, resilience/fallback logic (mock the Gemini client).
- **Vector layer**: `$vectorSearch` is **not** supported by `mongomock`, so the
  vector-store layer is mocked in unit tests.
- **Optional integration test** against `mongodb-atlas-local` to exercise real
  `$vectorSearch` (skipped when the container isn't available).
- No frontend tests (consistent with the current project).
- All backend modules run via `.venv\Scripts\python` per project convention.

## 18. Build-time verifications

1. Confirm `gemini-3.5-flash` is a current model ID **and** available on the free
   AI Studio tier (`client.models.list()`); pick `gemini_fallback_model` from the
   free flash models actually offered.
2. Confirm the chosen model supports **Google Search grounding**.
3. Confirm the exact `$vectorSearch` score normalization for cosine (sets the
   `rag_grounding_threshold` scale) and whether a grounded request that performs
   no search still counts against grounding quota.
4. Confirm `mongodb/mongodb-atlas-local` runs locally and the vector index can be
   created.

All model strings are config-driven, so these are low-risk swaps if a check fails.

## 19. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Free-tier RPM / grounding quota exhaustion | Confidence gate avoids web search for DB-answerable questions; local embeddings keep bulk work off the quota; `429` retry + fallback model; graceful error |
| Confidence threshold mis-tuned (wrong branch) | Default + `data-analyst` calibration against real queries; `allow_web` override; threshold is config-driven |
| `gemini-3.5-flash` not on free tier | Config-driven model string; verified at build; fallback model |
| Atlas-local adds infra weight / setup friction | Single container swap; documented; only `$vectorSearch` depends on it |
| Embedded text quality drives retrieval quality | `data-analyst` reviews `build_player_document()` output against real data |
| chatscope CSS clashes with Tailwind | Scoped style overrides; chat view is self-contained |
| `mongomock` can't test vector search | Mock the vector layer; optional atlas-local integration test |

## 20. Out of scope / future

- Server-side multi-turn sessions; streaming responses.
- Hebrew/multilingual embeddings (`bge-m3` / multilingual-e5 swap).
- Chunked retrieval over match reports / news articles; re-ranking; NL→metadata
  self-query (LangChain retrieval composition — the reason LangChain is retained).
- Repo-wide move of existing orchestration into `services/`.
- Sport-5 pricing integration; broader "RAG over everything".

## 21. Implementation outline (high level)

Detailed steps will come from the implementation-plan phase. Broad order:

1. DB snapshot (project rule: snapshot before implementing).
2. Infra: docker-compose → atlas-local; create `vector_index`.
3. Config + dependencies.
4. `domain/player_document.py` + tests; `data-analyst` review of output.
5. `infrastructure/vector_store.py` (FastEmbedEmbeddings + MongoDBAtlasVectorSearch, scored retrieval).
6. `infrastructure/gemini_client.py` (native async generate, DB-only + grounded, resilience).
7. `services/rag_service.py` (retrieve(scored) → confidence gate → ground/DB-only → answer → sources).
8. `services/indexer.py` + `fetch_runner` hook + backend reindex/index-status endpoints.
9. `api/chat.py` + DI wiring.
10. Frontend: floating launcher + chatscope chat view + sources rendering.
11. Tests green; build-time verifications; pre-PR lint; PR to master.

## 22. Process notes

- New feature branch `dev/rag-chat` (created).
- DB snapshot before implementation.
- `data-analyst` agent to sanity-check embedded document content and calibrate
  `rag_grounding_threshold` (read-only on the DB).
- Real `GEMINI_API_KEY` required to exercise the live path.
- PR to `master` only after CI passes; delete branch after merge.
