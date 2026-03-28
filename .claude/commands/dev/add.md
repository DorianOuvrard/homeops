---
description: ADD Hackathon — Cycle orchestrator. Scope, intent, plan, implement.
---

# ADD — Cycle Orchestrator (Hackathon)

```
$ARGUMENTS
```

---

## 1. Workflow

ADD ships one intention at a time. Each cycle produces working code. No partial cycles.

**Rules:** No commits during the cycle. All agent delegations use `run_in_background: true`. All checkpoints use `AskUserQuestion`. Print a layer summary card + cycle status block after every layer.

### Modes

| Mode | When | Layers |
|------|------|--------|
| **Full** | default | VISION → INTENT → PLAN → IMPLEMENT |
| **Light** | <100 LOC, no new data models, no architectural decisions | VISION → INTENT → IMPLEMENT |

### Checkpoints

**0** — after VISION: scope lock (commitment, exclusions, mode).
**A** — after INTENT: business validation, mode decision.
**B** — after PLAN: architecture approval. *(full only)*

---

## 2. Working unit interfaces

Each unit lives in `.claude/agents/add/{unit}.md`.

### VISION
```
reads:   raw user input
writes:  01-vision.md
post:    scope locked; commitment and exclusions are hard constraints
notes:   no codebase access; 0-1 clarification rounds
```

### INTENT
```
reads:   raw user input, 01-vision.md, CLAUDE.md
writes:  02-brief.md
post:    intention, success criteria, scope, risks, decisions
notes:   iterative (1-2 rounds); explores codebase; scope ≤ 01-vision.md commitment
```

### PLAN *(full only)*
```
reads:   01-vision.md, 02-brief.md, CLAUDE.md
writes:  03-prd.md (decisions, diagram, implementation sequence, file list)
post:    covers costly-to-reverse decisions + diagram
notes:   explores codebase for architecture decisions only
```

### IMPLEMENT
```
reads:   01-vision.md, 02-brief.md, 03-prd.md (if present), CLAUDE.md
writes:  code changes, 05-proof-report.md
post:    feature working end-to-end
notes:   happy path + reasonable edge cases in one pass
```

---

## 3. Orchestration

### Flow

**Full cycle:**

```
VISION → CP-0 → INTENT → CP-A → PLAN → CP-B → IMPLEMENT → done
```

**Light cycle:**

```
VISION → CP-0 → INTENT → CP-A → IMPLEMENT → done
```

### Cycle status block

Print after every layer completes or checkpoint resolves:

```
**Cycle [{slug}] · {Full|Light}**

  VISION       ✅  scope: {focused|broad} · {N} exclusions
  INTENT       ✅  brief: {1-line summary}
  PLAN         🔄  prd: {N} decisions
  IMPLEMENT    ·
```

Markers: `✅` done · `🔄` in progress · `❌` failed · `·` pending.
Omit PLAN row in light cycles.

### Layer summary card

Print **before** the status block after every layer completes. 3-5 bullets from the artifact.

```
**[LAYER] → {artifact filename}**
• {most important point}
• {second point}
• {third point}
```

---

## 4. Setup

**Branch and directory:**
```bash
SLUG="{short-name}"
BRANCH="feat/${SLUG}"
git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"
git push -u origin "$BRANCH"
mkdir -p docs/cycles/${SLUG}
echo "${SLUG}" > docs/cycles/current
```

---

## 5. VISION → Checkpoint 0

Launch `add:vision` with `run_in_background: true` — pass raw input verbatim.

**If question** — relay via `AskUserQuestion`. Resume with answer.

**If finalized** — read `01-vision.md`, print layer summary card, present CP-0:

```
AskUserQuestion:
  header: "Vision — Checkpoint 0"
  question: "Scope locked:"
             [11-star · Scope mode · Commitment · Not building]
  options:
    - label: "Confirmed — proceed"
    - label: "Adjust scope — re-run vision"
```

---

## 6. INTENT → Checkpoint A

Launch `add:intent` with `run_in_background: true`.

Relay questions via `AskUserQuestion`. Expect 1-2 rounds.

When brief finalized: read `02-brief.md`, print layer summary card.

**Mode decision** — propose light if ALL hold: <100 LOC, no new data models, no architectural decisions.

```
AskUserQuestion:
  header: "Intent — Checkpoint A"
  question: "Brief ready:"
             [Intention · Capabilities · Decisions · Risks]
             [Proposed mode: Full / Light]
  options:
    - label: "Full cycle — confirmed"
      description: "Launch PLAN."
    - label: "Light cycle — confirmed"
      description: "Skip PLAN, go to IMPLEMENT."
    - label: "Correct the brief"
      description: "Resume INTENT with corrections."
```

---

## 7. PLAN → Checkpoint B *(full only)*

Launch `add:plan` with `run_in_background: true`.

Relay questions if any (0-1 rounds).

When complete: read `03-prd.md`, print layer summary card, present CP-B:

```
AskUserQuestion:
  header: "Plan — Checkpoint B"
  question: "PRD ready:"
             [Costly-to-reverse decisions · Trade-offs]
  options:
    - label: "Go"
      description: "Proceed to IMPLEMENT."
    - label: "Rework"
      description: "Re-run PLAN with corrections."
    - label: "Skip"
      description: "Established patterns, no risky decisions."
```

---

## 8. IMPLEMENT

Launch `add:implement` with `run_in_background: true`.

Evaluate `05-proof-report.md`:
- **code** level: lint/type clean → required
- **workflow** level: feature works → required

Print layer summary card. If failing, retry once with failure context appended.

---

## 9. Cycle complete

> **Cycle complete.** {One sentence.}
> Deliverable: {how to verify}.
> Cycle docs: `docs/cycles/{slug}/`
> Ready for validation. When satisfied, ask me to ship.

**Do not commit.** Wait for explicit request or `/ship`.
