# UI redesign to match `sketches/`

## Context
The `sketches/` folder has 7 high-fidelity screens: Player details, Player modal, Compare, xGI Outliers, Scatter Plot, Ask AI, and System states. They define a new visual language: a near-black green-tinted theme, an emerald accent, amber/blue/red signal colors, Inter for text, and a monospace font for numbers and labels. The current UI uses gray + indigo, emoji icons, no fonts, and donut charts. It also lacks several elements the sketches show. Goal: rebuild the frontend so it matches the sketches exactly. Add only the backend data these elements need.

Decisions already made by the user:
- **Scope:** full, frontend + backend in one branch.
- **Dependencies:** `@fontsource/inter`, `@fontsource/jetbrains-mono`, `lucide-react`.
- **Chat thumbs up/down:** omit.
- **Avatars:** initials, no photos. Keep the floating chat bubble (restyled).

## Setup
- Branch `dev/ui-redesign` stacked on the current tip. Leave the uncommitted `.gitignore` change for the user.
- Take a DB snapshot first (`db-snapshot` skill).
- Commit this plan as the spec in `docs/superpowers/specs/2026-09-24-ui-redesign-design.md`.

## Part A: backend (TDD, mongomock tests next to the existing ones)
1. **`GET /v1/meta?season=`** in a new `app/api/meta.py`, registered in `main.py`. Returns:
   - `players_total`
   - `last_updated`: the max `updated_at` from `repo.get_fetched()`
   - `seasons`: distinct `player_stats.season`
   - `agent`: `{model, max_tool_calls}` from `config.py`. `model` comes from the resolved provider default in `agent/providers.py`.
   This feeds the header status (`● 2,481 players · updated 22 Jun`), the season dropdown, and the Ask AI header (`gemini-… · 8 tool calls max`).
2. **Confidence:** extract `confidence_tier(apps)` from `ScoringEngine.calculate` (`domain/scoring_engine.py:68-75`) as a pure function. Expose `confidence` on `aggregated_scores` in `PlayerOut`, computed in the API layer from `aggregated_stats`. No DB migration.
3. **Chat trace** in `ChatResponse` (`api/modals/chat_modals.py`):
   - `tool_calls: [{name, rows}]`, built in `ChatAgent.answer` (`agent/agent.py`) from the `AIMessage.tool_calls` and `ToolMessage` of the current turn. Names and row counts only, never arguments or row contents.
   - `uncited: list[str]` from `uncited_numbers()`, used for the specific warning text.
   - This reverses the deliberate "No field can carry a tool trace" comment at `chat_modals.py:11`. The user approved this under "Full scope". Update the comment.
4. **Scatter points** (`api/analysis.py`, `analysis_modals.py`): add `team`, `goals`, `assists`, `xg`, `xa`, `minutes`, `s_final`, `xratio`, `flag`. The frontend does the axis selection, position filter and minutes filter on the client.
5. **Sort by xRatio:** allow `sort_by=xratio` on `GET /v1/players` (maps to `aggregated_scores.sleeper_ratio`). Extend `metric_fields.py` or the repo sort mapping, including the Python-sort path for `stats_view` (`mongo_repository.py:349-367`). Outliers sorts descending for "Due to score" and ascending for "Overperforming".

## Part B: frontend foundation
- **Deps:** `npm i @fontsource/inter @fontsource/jetbrains-mono lucide-react`. Import the fonts in `main.tsx`.
- **`tailwind.config.js` tokens:**
  - `bg`, `surface`, `surface-2`, `border` (dark green-black)
  - `accent` (emerald), `warn` (amber: Due to score), `info` (blue: TOTW, player B wins), `danger` (red)
  - `muted` text
  - `fontFamily.sans=Inter`, `fontFamily.mono=JetBrains Mono`
- **`index.css`:** body background, tabular numbers.
- **New `src/components/ui/`** primitives, reused on every page:
  - `Avatar` (initials)
  - `PosBadge`
  - `SignalBadge`: DUE TO SCORE / OVERPERFORMING / ☆ TOTW ×N
  - `ScoreBar`: value plus thin bar under it
  - `Segmented`: All/Club/National, GK/DF/MF/FW, outlier tabs
  - `Select` and `IconInput`: search / shield / flag icons
  - `FilterChip`: `minutes ≥ 900 ×`
  - `Pagination`: `Showing 1–14 of N`, Prev, `1 / 50`, Next
  - `StatRow`, `StackedBar` + legend (replaces the donut charts)
  - `PageHeader`: title + mono subtitle + right-side meta
  - `DataTable`: sortable header style, row hover, dimmed-while-loading
- **Shell (`App.tsx` → new `components/AppShell.tsx`):**
  - Logo `FOOTBALL ANALYTICS` (second word in accent) and the tab bar with an accent underline.
  - Right side: meta status + season `Select`. On the Ask AI tab it shows the model status + `New chat` instead.
  - A lifted `season` state goes to every API call (`api/*.ts` gain `season`).
  - Navigation helpers instead of a router: `goTo(tab, payload)` for "Compare with…" (preset player A), "Open profile", and "Open in Player details".
- **States (sketch 07):**
  - `EmptyDatabase` replaces `SeedPrompt`: DB icon, the fetch_cli code block with Copy, `Open API docs ↗` (`${API}/docs`), and `Check again`. The header shows amber `0 players · database empty`.
  - `BackendUnreachable`: only the content region, auto-retry every 10 s + manual retry.
  - `NoResults`: lists the active filters, with `clear all filters` / `remove last clause`.
  - Loading: skeleton on first load, then dimmed rows (keep the existing `requestId` stale-drop logic).

## Part C: pages (one commit each)
- **Player details** (`pages/PlayerDetails.tsx`, `FilterBar.tsx`, `PlayerTable.tsx`):
  - Header: formula subtitle and `N results`.
  - Filter row: name / position / team / nationality / flags, and `+ Add metric filter` (it adds a popover row; applied clauses render as removable `FilterChip`s).
  - Second row: `STATS VIEW` segmented, competition select, chips, `sorted by …` label.
  - Columns: #, Player (avatar + name + nationality), Pos, Team, Fantasy Score (ScoreBar), Apps, G, A, xG, xA, Min, Rating, Signal (flag + TOTW badges).
- **Player modal** (`PlayerModal.tsx`, `PlayerCard.tsx`):
  - Header with TOTW + xRatio chips.
  - Score panel: Fantasy Score, Offensive, Defensive, Tactical, Confidence bar.
  - Aggregate stats list (left). Per-competition rows with CLUB/NT tags (right).
  - Goal types and shot outcome as `StackedBar`s. Blocked shots = total − on − off, as today.
  - `Show all 35 metrics` expander, `Compare with…` (→ Compare with A preset), and `last updated`.
  - Keep the refresh-bio behaviour.
- **Compare** (`pages/Compare.tsx`):
  - Two player cards (A / VS / B) with Fantasy Score and a swap/change button that opens the existing debounced search.
  - Mirrored bar table: A value + bar | metric | bar + B value | Δ. The winner's bar is accent for A and info-blue for B; the loser's bar is muted. Δ is colored by "higher is better", and the cards are inverted.
  - Rows as in sketch 03.
- **xGI Outliers** (`pages/Sleepers.tsx`):
  - Two rule cards (amber and green left border, formula + text), the segmented tab, `N players flagged · sorted by xRatio`.
  - Columns: …, xRatio (amber ScoreBar), Apps, G, A, xG, xA (accent), Min, Score, Signal + `+7.7 xGI` delta.
  - The rule text uses the thresholds from `sleeper_detector.py`. The sketch's `1.25×` matches the code: a ratio below 0.8 means G+A > 1.25 × (xG+xA).
- **Scatter** (`ScatterPage.tsx`, `ScatterPlot.tsx`):
  - Controls: X/Y metric selects (xG+xA, xG, xA / G+A, Goals, Assists), position segmented, `minutes ≥` input, `Highlight outliers` toggle.
  - Recharts: the diagonal labelled `xGI = GI`, dots colored by flag (gray when in line or when highlighting is off), labels for the selected point and the most extreme outliers.
  - Keep zoom and pan.
  - Right column: Legend card, `SELECTED POINT` card (xG+xA, G+A, xRatio, Minutes, Fantasy Score, badge, `Open profile ↗` → modal), and the hint `Click any point to inspect the player`.
- **Ask AI** (`ChatPanel.tsx`, `ChatFullScreen.tsx`, `ChatWidget.tsx`):
  - Accent user bubble on the right. The assistant message has a sparkle icon, a `RAN tool() tool() → N rows` chip row, markdown with a styled GFM table (xRatio column in amber), and an amber warning box built from `uncited`.
  - Actions: `Copy`, `Open in Player details`.
  - Static suggestion chips above the input. The input shows a `0 / 2000` counter and a `Send ↑` button, with the footer `Session history is kept for 7 days…`.
  - The widget reuses the same restyled panel.

## Docs
Invoke the `technical-writer` agent: CLAUDE.md (frontend pages, `/v1/meta`, chat trace fields), README, and the API docs.

## Verification
- `backend/.venv\Scripts\python -m pytest` must be green, with new tests for meta, confidence tier, chat trace (fake model with tool calls), scatter fields and xratio sort.
- `npm run build` + `npm run lint` in `frontend/` (tsc + eslint).
- `docker compose build backend` and recreate the frontend (new node deps, anonymous volume).
- Use the `run` skill / Chrome: open each tab at 1440 px wide, screenshot it, and compare it side by side with the matching `sketches/0X-*.png`. Check the modal, the Compare flow from "Compare with…", scatter point selection, a live chat answer (trace + warning), empty-DB state (load an empty DB or point at an empty season), and backend-down state (stop the backend container).
- Run the `pre-pr-lint` skill before the PR. Open a PR to master, and merge only after the user approves with CI green.
