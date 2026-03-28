---
description: Ship the current branch — commit, PR, merge, clean up.
---

# Ship — Hackathon Shipping Workflow

```
$ARGUMENTS
```

You handle the full shipping workflow for the current branch. If `$ARGUMENTS` contains `--dry-run`, preview each phase without executing destructive actions.

---

## Phase 0 — Safety checks

1. **Branch guard**: `git branch --show-current`. If `main` or `master`, STOP: "Refusing to ship from main."
2. **Sensitive file check**: `git status`. Warn if `.env*`, `*.pem`, `*.key`, `credentials*`, `*.secret`, `*token*` are staged/untracked. Never stage these.
3. **Existing PR check**: `gh pr view HEAD --json number,state 2>/dev/null`. If open PR exists, skip Phase 1, reuse its number.

---

## Phase 1 — Commit

1. Run `git status` and `git diff`.
2. Scan diff for leaked secrets. Warn if found.
3. Stage files by explicit name. Never `git add -A` or `git add .`.
4. Commit with atomic, conventional commits. Match style from `git log --oneline -10`.
5. If pre-commit hooks fail, fix and create a NEW commit (never amend).

---

## Phase 2 — Rebase + Create PR

1. **Rebase**: `git fetch origin main`. If `git log HEAD..origin/main --oneline` is non-empty, `git rebase origin/main`. Resolve conflicts.
2. **Push**: `git push -u origin HEAD`.
3. **Detect issue**: parse branch name (e.g., `feat/028-my-feature` → #28). Override with `$ARGUMENTS` if present.
4. **Create PR**: `gh pr create` with short conventional title, summary bullets, `Closes #<issue>` if applicable. Target: `main`.
5. Report PR number and URL.

---

## Phase 3 — Merge (requires confirmation)

**STOP and ask user for confirmation.** Present:
- PR URL, one-line summary, commit count.

After explicit approval:
1. `gh pr merge <pr-number> --merge --delete-branch`.
2. `git checkout main && git pull origin main`.
3. Clean up cycle tracking: `rm docs/cycles/current 2>/dev/null`.
4. Confirm success.

---

## Behavior notes

- Be concise. Only report meaningful progress.
- If `$ARGUMENTS` is empty, infer everything from branch and git state.
- If re-run on a branch with an existing PR, resume from the appropriate phase.
