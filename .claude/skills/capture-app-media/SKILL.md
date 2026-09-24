---
name: capture-app-media
description: Record the README demo GIFs of the app with a fixed set of Claude-in-Chrome tool calls. Trigger when the user asks to capture, refresh or record app GIFs, screenshots or demo media for the README, or after a UI change when the README media is outdated.
---

# Capture App Media

Records the README GIFs into `screenshots/` with Claude-in-Chrome tools only. No script, no Playwright, no new dependencies.

## Steps

### 1. Preflight

```bash
docker compose ps --format "{{.Service}} {{.State}}"
```

- The app must answer at http://localhost:5173. If the stack is down, tell the user to run `docker compose up -d`. Do not start it without asking.
- Work on a `dev/*` branch. Never on `master`.

### 2. Load the tools in ONE ToolSearch call

```
select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__find,mcp__claude-in-chrome__resize_window,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__gif_creator,mcp__claude-in-chrome__browser_batch
```

### 3. Set up the browser

1. `tabs_context_mcp {createIfEmpty: true}`
2. `tabs_create_mcp` and keep its `tabId`
3. `resize_window {width: 1440, height: 900}`
4. `navigate {url: "http://localhost:5173"}`
5. `javascript_tool` → `window.innerWidth`. `resize_window` may report success but not change it (seen: 1920). Continue at that size; step 8 crops the frames.

### 4. Gotchas

- Screenshot coordinates do not match click coordinates. Prefer `find` refs. If `find` misses an element (it missed table headers), read its `getBoundingClientRect()` center with `javascript_tool` and divide by the scale factor. Measure the factor once with a test click; it was 1.36.
- Scatter points: use `javascript_tool` to dispatch a click on the `<circle>` next to a labelled SVG `<text>`.
- Never use `computer` `zoom` while recording: the zoomed crop becomes a small frame on a white canvas.
- Setup steps outside a recording (switching tabs, closing a modal) can be plain JS clicks.
- A frame is captured only on an action or a screenshot. Take a screenshot after each step. Identical frames in a row are dropped, so a pause needs a visible change.

### 5. Recording pattern (per GIF)

```
gif_creator    {action: "start_recording", tabId}
computer       {action: "screenshot", tabId}   # x2
...steps: find -> computer {action: "left_click", ref} -> computer {action: "screenshot"}
computer       {action: "screenshot", tabId}   # x2
gif_creator    {action: "stop_recording", tabId}
gif_creator    {action: "export", tabId, download: true, filename: "<name>.gif",
                options: {showClickIndicators: false, showActionLabels: false,
                          showProgressBar: false, showWatermark: false,
                          showDragPaths: false, quality: 10}}
gif_creator    {action: "clear", tabId}
```

Then move the file (check for a ` (1)` suffix if an older copy exists):

```bash
mv "$USERPROFILE/Downloads/<name>.gif" screenshots/<name>.gif
```

### 6. Shot list

You may record only a subset, for example only the pages that changed.

| File | Steps |
|------|-------|
| `01-player-details.gif` | Ranked table; type "Liverpool" in Team; click the "G" header to sort; clear Team |
| `02-player-modal.gif` | Open the top player's modal; "Show all 35 metrics"; close |
| `03-compare.gif` | Modal → "Compare with..." → pick player B via search → show the table |
| `04-xgi-outliers.gif` | "Due to score" table, then switch to "Overperforming" |
| `05-scatter-plot.gif` | Select a labelled point; position filter FW; toggle "Highlight outliers" off, then on |
| `06-ask-ai.gif` | "New chat", then the chip "Top 5 scorers this season"; wait for the answer with the "RAN …" trace |

`06-ask-ai.gif` uses one free-tier Gemini request. Ask the user before recording it.

### 7. Permissions

Exporting a GIF is a browser download. The user's request to capture media is the approval for these files only.

### 8. Finish

1. `tabs_close_mcp {tabId}`
2. Crop the empty right strip (scrollbar) and bottom band. Sample pixels first to find the content box; it was `(0, 0, 1399, 667)` for 1568x743 frames. Pillow is already in the backend venv:
   ```bash
   backend/.venv/Scripts/python - <<'PY'
   import os
   from PIL import Image, ImageSequence
   BOX = (0, 0, 1399, 667)
   for f in sorted(os.listdir("screenshots")):
       im = Image.open(f"screenshots/{f}")
       fr = [x.convert("RGB").crop(BOX).quantize(256) for x in ImageSequence.Iterator(im)]
       d = [x.info.get("duration", 100) for x in ImageSequence.Iterator(im)]
       fr[0].save(f"screenshots/{f}", save_all=True, append_images=fr[1:], duration=d, loop=0, optimize=True)
   PY
   ```
3. `ls -la screenshots/`
4. Warn if any GIF is larger than 8 MB. Suggest fewer frames or `quality: 15-20`, not new tools.
5. If a filename is new, add it to the README "Screenshots" grid (an HTML table with `screenshots/<name>.gif`).
6. Commit on the dev branch. Follow the `pre-pr-lint` skill before opening a PR.
