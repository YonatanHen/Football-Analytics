# Seed UI Design — 2026-05-27

## Overview

When the database is empty, replace the entire app content area with a guided empty state that lets the user load the 2025/26 season data with a single button click. Once data is loaded, transition automatically to the Rankings tab.

---

## Placement

**Global content-area takeover.** When the app detects no players exist in the DB, all tab content is replaced by the seed UI — regardless of which tab the user is on. The nav bar remains visible. This ensures the user cannot miss the empty state and understands the whole app is waiting for data, not just one page.

---

## Detection

On app mount (`App.tsx`), call `GET /v1/players/?page_size=1` (existing endpoint). If `total === 0`, render the seed UI instead of the tab content. Once seeding completes, re-run the check and restore normal tab rendering.

---

## States

### 1. Idle (empty DB detected)

- Icon: ⚽
- Heading: **No player data loaded**
- Body: "Load the 2025/26 season to get started. You'll get 2,800+ players across the top 5 European leagues — ranked, scored, and ready to explore."
- Sub-text: "This takes about 10–30 seconds and only needs to be done once."
- Button: **Load 2025/26 Season** (indigo, primary CTA)
- No mention of scraping, Kaggle, FBref, or any technical process.

### 2. Loading (button clicked, waiting for API)

- Icon: ⏳
- Heading: **Loading season data…**
- Body: "Fetching and processing player stats. This usually takes 10–30 seconds."
- Sub-text: "Please don't close this tab."
- Button disabled / hidden.

### 3. Done (API returned success)

- Icon: ✅
- Heading: **Ready!**
- Body: "2,839 players loaded. Taking you to Rankings…"
- Auto-transitions to Rankings tab after 1.5 s.

### 4. Error (API returned failure)

- Icon: ⚠️
- Heading: **Something went wrong**
- Body: "Couldn't load player data. Please try again."
- Button re-enabled: **Try Again**

---

## API Call

Button triggers `POST /v1/fetch/` with body `{ "mode": "fantasy" }` — the existing `triggerFetch` helper in `frontend/src/api/fetch.ts`.

---

## Component Structure

- **`App.tsx`** — owns `isEmpty: boolean` state and the check-on-mount logic. Passes `onSeeded` callback down.
- **`components/SeedPrompt.tsx`** — new component; renders all 4 states based on props (`status: 'idle' | 'loading' | 'done' | 'error'`). Stateless — App drives it.

---

## Styling

Matches existing dark theme (`bg-gray-950`, `text-gray-100`, indigo accent). Centered vertically in the content area. No new CSS dependencies.

---

## Out of Scope

- Progress steps / step-by-step loading log (keep loading state simple)
- Per-page empty states (handled by global takeover)
- Manual season selection (always loads 2025/26)
