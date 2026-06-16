# Design: `ci-engineer` agent + first CI pipeline

**Date:** 2026-06-16
**Status:** Approved (brainstorm), pending implementation plan
**Branch:** `dev/ci-pipeline`

## Goal

Add CI to this monorepo (FastAPI backend + React/Vite frontend), and do it by first
building a **reusable, CI-only subagent** (`ci-engineer`) that then executes the first CI
pass. The agent persists for all future CI work; a separate **DevOps-engineer agent**
(future, out of scope here) will own infrastructure, deployment, registries, and k8s.

**Scope boundary:** CI only — lint, type-check, test, app-build verification. **No** Docker
**no** CD (no registry push, no deploy).

## Why this shape

- Portfolio monorepo on GitHub → GitHub Actions is the natural platform.
- Keeping CI and CD strictly separate, and structuring jobs to be *additive per path/service*,
  means a future microservices split or k8s/CD move is "add an entry / add a new agent," not a
  rewrite.

## Agent-authoring principle (applies to Deliverable 1)

The agent definition must be **generic and timeless** — it describes the agent's
responsibilities, boundaries, and conventions, never a snapshot of the current repo
(no "there is no CI yet" / "no lint config exists" framing). Transient context belongs only in
one-off task prompts, not in the reusable agent file.

## Deliverable 1 — the `ci-engineer` agent

File: `.claude/agents/ci-engineer.md`, following existing agent conventions
(`data-analyst.md`, `technical-writer.md`): YAML frontmatter + tight identity + explicit
**boundaries** + project knowledge + output format.

| Field | Value |
|---|---|
| `name` | `ci-engineer` |
| `model` | `sonnet` (CI config is precise/deterministic, not research-heavy; cheap for frequent "fix the red build" calls) |
| `color` | `yellow` (blue/green already used) |
| `description` | Trigger-focused: invoke for CI workflow authoring/maintenance, adding/fixing checks, wiring a new path/service into CI, and lint/test/type-check tooling config; keeping CI green. |

**Owns:** `.github/workflows/` (CI workflows only) and the tool configs those workflows run —
ruff config, ESLint config, `pytest.ini`.

**Explicitly does NOT own** (defers to the future devops-engineer agent, says so and stops):
Dockerfiles, `docker-compose.yml`, deployment, GHCR/registries, k8s, secrets, hosting.

**Embedded discipline** (from `CLAUDE.md` + user rules):
- Never works on `master`; opens `dev/<feature>`.
- Never edits application logic to force a test green — surfaces the failure instead.
- Validates locally before claiming green (evidence before assertions).
- Consults the user before adding heavy or opinionated tooling.
- One branch = one feature.

**Forward-compat knowledge it carries:**
- CI ends at "checks pass" — it never deploys.
- Jobs are path-filtered and list/matrix-driven so adding a future service is additive.

**Project-level memory** (per CLAUDE.md "Build all agent with project level memory"):
- The agent is aware of the project memory dir and its conventions.
- A memory entry is recorded documenting the `ci-engineer` agent's existence, remit, and the
  CI-vs-DevOps split, indexed in `MEMORY.md`.

## Deliverable 2 — first CI pass (executed by the agent)

### Backend (`backend/`)
- Add **ruff** config (`backend/ruff.toml`) and a pinned `backend/requirements-dev.txt`
  (ruff; pytest/pytest-asyncio already in `requirements.txt`).
- Reach a green baseline: `ruff check --fix` + `ruff format` for safe auto-fixes, then fix or
  explicitly ignore the remainder.

### Frontend (`frontend/`)
- Add **ESLint** flat config (`eslint.config.js`) with `typescript-eslint`,
  `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`; add the matching devDependencies
  and a `"lint": "eslint ."` script to `package.json`.
- Reach a green baseline (fix or explicitly ignore existing violations).

### Workflow `.github/workflows/ci.yml`
- Triggers: `pull_request` and `push` to `master`.
- `concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }`.
- `permissions: { contents: read }` (least privilege).
- **`changes` job:** `dorny/paths-filter` → outputs `backend`, `frontend` booleans.
- **`backend` job** (if `backend` changed): Python 3.12, pip cache → install
  `requirements.txt` + `requirements-dev.txt` → `ruff check` → `ruff format --check` →
  `pytest`. **No MongoDB service** — tests use `mongomock`.
- **`frontend` job** (if `frontend` changed): Node 20, npm cache → `npm ci` → `npm run lint` →
  `tsc --noEmit` → `npm run build` (app build = build verification; not a Docker build).
- **`ci-success` job:** depends on `backend` + `frontend`; passes only if neither failed
  (treats skipped as ok). This is the single stable **required status check** for branch
  protection, so monorepo path-skips don't block merges.

### Notes / caveats
- `ScraperFC` is a `git+https` dependency → backend install clones it in CI (slower first run;
  pip cache mitigates). Tests do not launch Chrome, so no browser is needed on the runner.
- Bringing existing ruff/ESLint violations to green is part of the task.
- Branch protection (requiring `ci-success`) is a GitHub repo setting, not a file — documented
  as a recommended manual step, not applied by this work.
- Pin third-party actions to a version (e.g. `dorny/paths-filter@v3`); use official
  `actions/setup-python`, `actions/setup-node`, `actions/checkout`.

## Out of scope (explicit)
- Docker image build in CI; any CD (registry push, deploy).
- k8s manifests, hosting, live demo.
- The DevOps-engineer agent (separate future effort).
- Frontend unit tests (type-check + lint + build is the frontend gate).

## Acceptance
- `ci-engineer` agent file exists, matches project agent conventions, and is written
  generically (no transient repo-state framing).
- A project-memory entry for the agent exists and is indexed in `MEMORY.md`.
- ruff + ESLint configured; `ruff check`, `ruff format --check`, `pytest`, `npm run lint`,
  `tsc --noEmit`, `npm run build` all pass locally.
- `.github/workflows/ci.yml` present, path-filtered, with a `ci-success` gate; green on a test
  PR.