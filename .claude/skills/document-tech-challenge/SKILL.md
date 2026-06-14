---
name: document-tech-challenge
description: Capture a tech challenge or investigation from the current conversation into a dated markdown file in the project root, structured so the user can revisit it later. Trigger this whenever the user says things like "document this challenge", "save this for later", "this would make a good post", "write this up", "log this", or asks to remember a debugging session, performance investigation, architectural decision, or a non-obvious tradeoff. Also offer this proactively when a substantive investigation just concluded — the user may not think to ask. Output is one .md per challenge in the project root.
---

# Documenting tech challenges

Capture a tech challenge worked through in the current conversation as a standalone markdown file. The artifact serves two audiences: future-you (revisiting the issue) and a potential LinkedIn audience (sharing the lesson). The structure below works for both because the things that make a writeup useful months later — the wrong turns, the concrete numbers, the actual root cause — are the same things that make it interesting to other engineers.

## When this triggers

Explicit cues: "document this challenge", "save this for later", "write this up", "log this for me", "let's remember this one".

Implicit cues — offer to use this skill if the user hasn't asked:
- A substantive investigation or debugging session just concluded
- The user surfaced a non-obvious tradeoff or design decision
- A counterintuitive result came up worth remembering (e.g. "I assumed X, turned out Y")

Don't trigger for trivial fixes (a typo, a one-line config change, a dependency bump). Those aren't post-worthy and clutter the directory.

## File location and naming

- Directory: project root (`C:\Users\yonat\projects\Football-Analytics\`)
- Filename: `challenge-YYYY-MM-DD-kebab-case-slug.md`
- Use today's date from context, not a guess
- Slug should be 3-6 words describing the challenge (e.g. `fetch-bottleneck-investigation`, `mongo-vs-scraping-perf`)

## Template

Always use this structure. Section order matters — it mirrors how a reader (or LinkedIn audience) actually consumes the story: symptom first, then journey, then payoff.

```markdown
# {Title — concise, describes the challenge}

**Date:** YYYY-MM-DD
**Tags:** {2-5 short tags, e.g. performance, scraping, mongodb}

## The symptom
{What the user observed. One short paragraph. Concrete: what was slow, what failed, what felt off. Numbers if available.}

## Investigation
{What was looked at and in what order. Include wrong turns and initial hypotheses that didn't hold up — those are often the most interesting bits for a post. Reference the code with file:line pointers.}

## Root cause
{The actual underlying reason. Sharp and specific. If multiple factors contributed, list them in order of impact.}

## Resolution
{What was done, or what was decided. If left unresolved, say so explicitly and capture the next-step options that were on the table — that's still useful context for future-you.}

## What makes this worth sharing
{2-4 bullets: the non-obvious insight, the lesson, the misconception that got corrected. This is the LinkedIn angle — write it like you're explaining to a peer engineer why this was interesting, not like marketing copy.}

## References
{File paths with line numbers, function names, links to docs or tickets, related commits. Keep this concrete so future-you can jump back into the code without rummaging.}
```

## How to write the content

- **Draw from the conversation, not your imagination.** Pull concrete numbers, file paths, function names, and quotes from what was actually discussed in this session. If a detail wasn't established, leave it out — invented specifics are worse than missing ones.
- **Show the wrong turns.** A writeup that says "I assumed it was X, turned out to be Y because Z" is more useful and more interesting than a sanitized root-cause statement. Honesty about the investigation path is most of the value.
- **Keep it skimmable.** Each section: 1-3 short paragraphs or a tight bullet list. The whole document should fit on one screen for a fast reread later.
- **Don't editorialize in the body.** The "What makes this worth sharing" section is the only place for framing the lesson. Lead even that section with the technical insight, not with hooks like "Here's what I learned…".
- **Reference the code, don't quote it.** Pointers like `backend/app/modes/fantasy.py:68` are more useful than pasted snippets, which go stale the moment the code changes.

## After saving

Tell the user the absolute path of the file you wrote so they can open it. If the project root already contains a `CHALLENGES.md` index, add a one-line entry to it (`- [Title](challenge-YYYY-MM-DD-slug.md) — one-line hook`). Don't create the index proactively — only maintain it if the user has already started one.

Don't read the file back to the user or summarize what you wrote — they can open it themselves, and the value is in the file existing for later, not in re-narrating it now.
