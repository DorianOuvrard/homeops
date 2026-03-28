# Proof — onboarding-discovery

## What was implemented

### bot/history.py
Changed `MAX_MESSAGES` from `20` to `50`. Verified with a Python import check that the module loads correctly and the constant is 50.

### bot/prompts/system.md
Added a full "Onboarding Discovery" section (lines 72-173) covering:
- **Auto-trigger**: on first message, call `search_records` on `maintenance.equipment` with `limit=1`; launch onboarding only if zero results
- **Accueil**: warm intro presenting Hodoor, framing the 10-15 min home scan
- **Boucle de scan** (6 steps per appliance): photo request, identification, optional label/QR scan (with hard rules against asking to move furniture), acquisition date, Odoo `create_record`, `search_common_issues` tip + "Un autre appareil ?"
- **Fin de scan**: reference list of 14 appliances for gap detection, gentle per-item prompts for missing ones, final recap with count and top maintenance priority
- **Gestion des interruptions**: brief acknowledgement then redirect back to scan

## How to verify

1. Clear any existing `maintenance.equipment` records in Odoo (or use a fresh instance)
2. Start the bot (`python -m bot`) and send any first message via Telegram
3. Expected: Hodoor calls `search_records` on `maintenance.equipment`, detects zero results, sends the onboarding welcome message
4. Send a photo of an appliance and follow the flow through steps 1-6
5. To verify history capacity: a full scan of 14 appliances at ~3 messages each (~42 messages) should fit without truncation — the buffer is now 50

Alternatively, verify the constant directly:
```
python -c "import bot.history; print(bot.history.MAX_MESSAGES)"
# Expected: 50
```

## Confidence

| Level | Status | Detail |
|-------|--------|--------|
| code | ✅ | `history.py` imports cleanly, `MAX_MESSAGES = 50` confirmed. `system.md` is valid markdown, no syntax issues. |
| workflow | ⬜ | Not e2e tested (requires live Telegram + Odoo instance). Logic follows the PRD spec exactly. |

## Known gaps

- The "Déclenchement automatique" relies on the LLM reading the system prompt instruction and calling `search_records` before responding. If the LLM skips the check on first message (e.g. answers the user's question directly), onboarding will not trigger. This is an inherent risk of prompt-driven orchestration acknowledged in the PRD.
- The `note` field approach for acquisition date is a plain text approximation. No structured date field is used (none exists in the current schema).
- If the bot restarts mid-scan, onboarding resumes from the Odoo state (already-created equipment will be detected, so onboarding re-triggers only for the remaining gap), which may produce a slightly awkward re-welcome. Acceptable per PRD trade-offs.
