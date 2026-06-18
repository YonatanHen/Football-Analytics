---
name: pre-pr-lint
description: Run Ruff lint + format check on the backend before opening a PR. Fix any errors, then open the PR.
---

# Pre-PR Lint Check

Run this skill every time before opening a GitHub PR on this project.

## Steps

### 1. Run Ruff lint

```bash
cd backend
.venv\Scripts\python -m ruff check .
```

If errors are found:
- **Auto-fixable** (`[*]`): run `.venv\Scripts\python -m ruff check --fix .`
- **Manual fixes** (E501 line-too-long, UP045 Optional→X|None, I001 import sort): fix by hand, then re-run check.

### 2. Run Ruff format check

```bash
.venv\Scripts\python -m ruff format --check .
```

If files would be reformatted: run `.venv\Scripts\python -m ruff format .` to apply, then verify with `--check` again.

### 3. Run tests

```bash
.venv\Scripts\python -m pytest tests/ -q
```

All tests must pass before proceeding.

### 4. Commit any fixes

If lint/format fixes were needed, commit them onto the current dev branch before opening the PR:

```
git add backend/
git commit -m "fix: ruff lint/format"
git push origin <branch>
```

### 5. Open the PR

Only after steps 1–4 are all clean:

```bash
gh pr create --base master --head <branch> --title "..." --body "..."
```

## Common fixes

| Error | Fix |
|-------|-----|
| `UP045` `Optional[X]` | Replace with `X \| None`; remove `from typing import Optional` if unused |
| `E501` line too long | Wrap expression across multiple lines |
| `I001` unsorted imports | Sort imports alphabetically within each block |
| `F401` unused import | Remove the import |
| Format mismatch | Run `ruff format .` |
