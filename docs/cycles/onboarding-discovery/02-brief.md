# Brief — onboarding-discovery

Add a guided onboarding flow where Hodoor walks a new user through scanning every appliance in their home, one photo at a time, building a full inventory with immediate maintenance value at each step.

## Current state

| Component | Exists | Notes |
|-----------|--------|-------|
| Photo identification (GPT vision) | Yes | `photo_handler` sends base64 to OpenAI |
| Equipment CRUD via Odoo tools | Yes | `create_record`, `search_records` |
| Product doc search (Tavily) | Yes | `search_product_docs` tool |
| Common issues search (Tavily) | Yes | `search_common_issues` tool |
| TTS voice replies | Yes | All handlers |
| Conversation state machine | No | No step tracking, no flow control |
| Onboarding prompt / script | No | System prompt has no discovery sequence |

## Capabilities

- New user receives a warm welcome and clear framing of what Hodoor does
- Hodoor initiates a scan-one-at-a-time photo loop: user sends photo, Hodoor identifies the appliance type
- Hodoor gently asks if a QR code or model label is accessible (no pressure to move furniture)
- Each appliance is confirmed with the user, created in Odoo, and rewarded with a quick maintenance tip
- Hodoor asks when the appliance was acquired to estimate age/warranty
- Hodoor tracks what has been scanned and flags obvious missing appliances ("Pas de frigo ?")
- At the end, Hodoor delivers a prioritized recap: full inventory + top short-term maintenance action

## Decisions

**Orchestration method**: Prompt-driven, not code-level state machine. The LLM already has every tool needed. The onboarding behavior is added as a new section in `system.md` with explicit step-by-step instructions.
**Trigger**: `/start` command (new user) or `/scan` command (re-run discovery). No auto-trigger on first message.
**Appliance checklist**: LLM-maintained in conversation context, not a separate data structure. Hodoor tracks scanned items conversationally and compares against a reference list of common household appliances.
**Friction threshold**: Hodoor never asks the user to move furniture, unplug appliances, or reach behind equipment. If the label is not easily visible, skip model detection and move on.
**Tip source**: Combine `search_common_issues` results with LLM knowledge. One concise tip per appliance, not a full guide.

## Out of scope

Push notifications, recurring scheduler, room/zone data model, multi-user households, warranty claim automation, manufacturer API integrations, persistent state storage beyond conversation history.

## Risks

- **Conversation length.** Scanning 10+ appliances in one session may exceed context window or history buffer (currently 20 messages). Mitigation: increase history limit for onboarding sessions, keep per-appliance exchanges to 2-3 messages.
- **Photo misidentification.** GPT vision may confuse similar appliances or fail on unusual angles. Mitigation: Hodoor always confirms detection with user before creating the record.
- **Flow derailment.** User sends unrelated messages mid-scan. Mitigation: prompt instructs Hodoor to acknowledge then gently steer back to the scan.

## Success

- User completes full home scan in under 15 minutes for a typical household (6-10 appliances)
- Every scanned appliance is created in Odoo with at least: name, category, acquisition date
- Each appliance scan delivers one actionable maintenance tip before moving to the next
- Hodoor flags at least one "missing" appliance if an obvious category is absent
- Final recap message lists all scanned appliances with one prioritized next maintenance action
