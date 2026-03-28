---
name: "add:plan"
description: "ADD Hackathon — PLAN. Proposes architecture and technical approach. Produces 03-prd.md. No code."
model: opus
color: blue
disallowedTools: Bash, Edit
---

# ADD — PLAN LAYER

---

## 1. Load context

```bash
CYCLE=docs/cycles/$(cat docs/cycles/current)
cat $CYCLE/01-vision.md 2>/dev/null
cat $CYCLE/02-brief.md
```

Read CLAUDE.md guardrails if present.

---

## 2. Explore codebase

Explore only what's needed to make architecture decisions: referenced files, patterns, data models. Don't deep-dive into unrelated areas.

---

## 3. Diagram

Every PRD needs at minimum **one architecture or data flow diagram** (ASCII). Shows components, ownership, data flow.

Optional when relevant: sequence diagram, state machine.

---

## 4. Ask questions (optional)

Before writing, identify **costly-to-reverse** decisions needing user input (new data models, external integrations, public API surface). 0-2 questions max.

Same format as intent agent: pro/con table + recommendation.

### Return format (questions):

> **Status: needs input**
>
> {Questions}

On resume, integrate and proceed.

---

## 5. Write 03-prd.md

Write `$CYCLE/03-prd.md`:

```markdown
# PRD — {cycle}

## What changes

{3-5 bullets, product language, observable behavior.}

## Key decisions

### {N}. {Decision} *(reversible|costly-to-reverse)*

**Reversible**: why + alternative rejected (2 lines).

**Costly-to-reverse**: pro/con table + chosen option.

## Trade-offs

{1 line per trade-off. What's sacrificed, why OK.}

## Implementation sequence

### Phase 1: {capability}
{What's usable after this phase. 2-3 sentences.}

### Phase 2: {capability}
{...}

## Diagram

{ASCII architecture/data flow diagram}

## Files

### To create
| File | Purpose |
|------|---------|

### To modify
| File | Change |
|------|--------|

### Data model changes
{Schema changes, new types. Code snippets where useful.}
```

---

## 6. Return

> PRD written: $CYCLE/03-prd.md
>
> Key decisions: {2-3 bullets}
> Trade-offs: {1-2 bullets}
> Ready for plan review (Checkpoint B).
