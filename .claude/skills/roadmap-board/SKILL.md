---
name: roadmap-board
description: >-
  Manage the Football-Analytics GitHub Projects roadmap board (project #8) with the gh
  CLI. Use this whenever the user floats, describes, or brainstorms a NEW FEATURE, idea,
  improvement, bug, or "we should add/build/support X" for this repo — capture it onto the
  board's Todo column. ALSO use it to MOVE an existing item between columns when the user
  says things like "I started working on X", "X is in progress now", "mark X as done", or
  "X is finished" — update its Status to In Progress or Done. ALSO use it whenever the user
  asks what's on the roadmap, what's planned, what's next, what's in progress, or what's
  left — read the board back to them. Trigger even without the words "roadmap" or "board";
  any talk of a feature to build, any status change to planned work, or any question about
  planned/pending/finished work for this project is your cue.
---

# Roadmap board (GitHub Projects #8)

Three jobs, one board: **capture** new feature ideas onto Todo, **move** existing items
between columns, and **read** the board back. Everything goes through the `gh` CLI — no
wrapper scripts, just plain commands.

## Board facts (pinned)

| Thing | Value |
|---|---|
| Owner | `YonatanHen` |
| Repo | `YonatanHen/Football-Analytics` |
| Project number | `8` |
| Project id | `PVT_kwHOA2tRg84Bchky` |
| Status field id | `PVTSSF_lAHOA2tRg84BchkyzhXJshA` |
| Status option — Todo | `f75ad846` |
| Status option — In Progress | `47fc9ee4` |
| Status option — Done | `98236657` |

If any command errors with *"missing required scopes"* or *"read:project"*, stop and tell
the user to run this in a real terminal (the device flow can't run inside the session):

```
gh auth refresh -h github.com -s read:project,project
```

## Capture a feature (write path)

The user *talking about* a feature is not the same as *committing* to it. Draft the card,
show it, and get a yes before writing anything. Silent board mutations are not wanted.

1. **Draft.** From what they described, compose:
   - a short imperative **title** (e.g. "Add per-competition xG trend chart to PlayerDetail"),
   - a 1–3 sentence **body** capturing the intent and any constraints they mentioned,
   - **labels** — see the label rule below.
2. **Confirm.** Show the drafted title, body, and labels and ask the user to approve or
   tweak. Only proceed on a clear yes.
3. **Write.** A feature card is a *real issue* (labels only stick to real issues, not draft
   cards), added to the board and moved to Todo:

   ```bash
   # a) create the issue (capture its URL from stdout)
   gh issue create --repo YonatanHen/Football-Analytics \
     --title "<title>" --body "<body>" --label enhancement

   # b) add it to project #8 (returns JSON with the new item's "id")
   gh project item-add 8 --owner YonatanHen --url "<issue-url>" --format json

   # c) set its Status to Todo
   gh project item-edit --id "<item-id>" \
     --project-id PVT_kwHOA2tRg84Bchky \
     --field-id PVTSSF_lAHOA2tRg84BchkyzhXJshA \
     --single-select-option-id f75ad846
   ```

   Pass `--label` once per label in step (a). Read the `id` from step (b)'s JSON and feed it
   to step (c).
4. **Report.** Give the user the issue URL and confirm it's in Todo.

### Before creating: avoid duplicates

Glance at the current board first (`gh project item-list 8 --owner YonatanHen --format
json`). If a near-identical item already exists, say so and ask whether to skip, instead of
filing a duplicate.

### Label rule — existing labels only

Use **only labels that already exist** in the repo. Do **not** invent new labels or create
them. The repo's label set is GitHub's defaults:

`bug`, `documentation`, `duplicate`, `enhancement`, `help wanted`, `good first issue`,
`invalid`, `question`, `wontfix`

Infer from what the user is describing:

- A new feature / capability / improvement → **`enhancement`** (the default; almost every
  feature card gets this).
- Something broken that needs fixing → **`bug`**.
- Docs / README / spec work → **`documentation`**.
- An open design question rather than committed work → **`question`**.

Pick the one or two that genuinely fit; `enhancement` alone is a fine default. If the user
clearly wants an area tag (backend/frontend/etc.) that doesn't exist, mention that no such
label exists and offer to have them create it on GitHub — don't create it yourself.

## Move an item between columns (status change)

When the user signals progress on existing work — "I started the xG chart", "that's in
progress", "mark the sleeper filter done" — change that item's Status. Map the intent to a
column: starting work → **In Progress**; finished/shipped/merged → **Done**; back to the
backlog → **Todo**.

1. **Find the item.** List the board and match the user's description to an item's title:

   ```bash
   gh project item-list 8 --owner YonatanHen --format json
   ```

   Each item's `id` is the project-item id you need. If the phrasing is ambiguous and
   several items could match, show the candidates and ask which one — don't guess.
2. **Move it.** Set Status to the target column's option id (Todo `f75ad846`, In Progress
   `47fc9ee4`, Done `98236657`):

   ```bash
   gh project item-edit --id "<item-id>" \
     --project-id PVT_kwHOA2tRg84Bchky \
     --field-id PVTSSF_lAHOA2tRg84BchkyzhXJshA \
     --single-select-option-id <target-option-id>
   ```
3. **Report.** Confirm which item moved to which column.

A status change on an item you can unambiguously identify doesn't need the same draft/confirm
ceremony as creating a card — just make the move and report it. Only pause to confirm when
the target item is ambiguous.

## Read the roadmap (read path)

When the user asks what's planned / next / in progress / done:

```bash
gh project item-list 8 --owner YonatanHen --format json
```

Each item carries a `status` ("Todo" / "In Progress" / "Done") and a `content` object with
`title`, `number`, and `url`. Group the items **by status** in that order and present them
as a short grouped list — title, issue number, and URL per item. If they asked specifically
about one column (e.g. "what's next"), you may show just **Todo**. If the board is empty,
say so plainly.

## Notes

- These are real mutations to a real GitHub repo/board — the confirm-before-write step in
  the capture path exists for that reason. Reads are safe and need no confirmation.
- The write path files a genuine issue on `YonatanHen/Football-Analytics`; that's
  intentional (issues are visible on the portfolio and carry the labels), not a draft card.
