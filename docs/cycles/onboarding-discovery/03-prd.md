# PRD — onboarding-discovery

## What changes

- Hodoor auto-detects new users (no conversation history) and empty inventories (zero equipment in Odoo) and initiates the onboarding flow without any command
- The system prompt gains a new "Onboarding Discovery" section with step-by-step instructions for the LLM to conduct a room-by-room appliance scan
- Each scanned appliance is confirmed, created in Odoo, and immediately rewarded with a maintenance tip via `search_common_issues`
- After scanning, Hodoor compares the inventory against a reference list of common household appliances and flags obvious gaps
- The conversation history buffer increases from 20 to 50 messages for all sessions, so a full-house scan (10-15 appliances at 3 messages each) fits comfortably

## Key decisions

### 1. Auto-trigger detection strategy *(costly-to-reverse)*

| Option | Pros | Cons |
|--------|------|------|
| A. Check history length == 0 only (new user) | Zero latency, no Odoo call | Misses returning users with empty inventory |
| B. Check history == 0 AND Odoo equipment count == 0 | Catches both new users and users who cleared data | Adds one Odoo call on first message |
| C. Always check Odoo equipment count | Works for any session | Unnecessary Odoo call for every conversation start |

**Chosen: B.** On a user's first message, if their conversation history is empty, Hodoor calls `search_records` on `maintenance.equipment` with `limit=1`. If zero results, the onboarding flow activates. The Odoo call happens once per new conversation (not per message) and takes ~50ms on a local instance. This catches both genuinely new users and users who reset their data.

The detection happens in the system prompt itself: the prompt instructs the LLM to check for equipment when it detects no prior conversation context. No code-level state machine needed.

### 2. History buffer size: 20 to 50 *(reversible)*

**Chosen: 50 messages.** A full onboarding scanning 12 appliances at ~3 messages each (photo + confirmation + tip) produces ~36 messages. 50 provides headroom for derailments and the recap. Memory impact is negligible (in-memory text strings). Rejected 40 (too tight) and 80 (unnecessary for non-onboarding sessions too).

The change is a single constant in `bot/history.py`. Applies globally, not just to onboarding, because there is no per-session mode flag and adding one would be over-engineering.

### 3. Orchestration via prompt vs. code state machine *(costly-to-reverse)*

| Option | Pros | Cons |
|--------|------|------|
| A. Prompt-driven (instructions in system.md) | Zero code change for flow logic, leverages LLM reasoning, easy to iterate | LLM may drift, less deterministic |
| B. Code state machine (Python FSM in handlers.py) | Deterministic step tracking | Heavy code change, rigid, hard to iterate on tone/flow |

**Chosen: A.** The LLM already has every tool it needs (photo identification via GPT vision, `create_record`, `search_records`, `search_common_issues`). Adding explicit step-by-step instructions to the system prompt is sufficient. The prompt includes guardrails for flow derailment (acknowledge then steer back). If the LLM proves unreliable at following the sequence, a code FSM can be added later as a progressive enhancement.

### 4. Reference appliance list: embedded in prompt vs. external file *(reversible)*

**Chosen: embedded in prompt.** The list is ~15 items and changes rarely. Putting it in a separate file and loading it dynamically adds complexity for no benefit. If the list grows past 30 items, extract to a data file.

## Trade-offs

- **Global history increase (50 for all users, not just onboarding)**: wastes ~2x memory per idle user. OK because the bot is single-household, not multi-tenant.
- **No persistent onboarding state**: if the user closes Telegram mid-scan and the bot restarts, onboarding progress is lost. OK because the user can just re-trigger by sending a message (empty inventory will be detected again, Hodoor resumes from where the Odoo data is).
- **LLM may not follow the script perfectly**: prompt-driven flow is less deterministic than a code FSM. OK because the cost of a missed step is low (user just sends another photo) and the benefit of fast iteration on tone/flow is high.
- **One Odoo call per new conversation to check equipment count**: adds ~50ms latency on first message only. Negligible.

## Implementation sequence

### Phase 1: History buffer increase + auto-trigger detection

Increase `MAX_MESSAGES` from 20 to 50 in `bot/history.py`. Add the inventory-check instruction to the system prompt so Hodoor calls `search_records` on `maintenance.equipment` when conversation history is empty. After this phase, Hodoor detects new/empty-inventory users and greets them with the onboarding introduction.

### Phase 2: Full onboarding flow in system prompt

Add the complete onboarding section to `bot/prompts/system.md`: welcome message, photo-scan loop, per-appliance confirmation + tip, acquisition date collection, missing-appliance detection against reference list, and final prioritized recap. After this phase, a user can go through the full guided scan and end up with a complete inventory plus maintenance priorities.

## Diagram

```
Message flow (onboarding auto-trigger):

  User sends first message
       |
       v
  +------------------+
  | history empty?   |--NO--> normal conversation flow
  +------------------+
       | YES
       v
  +------------------+     search_records
  | LLM checks Odoo  |---> maintenance.equipment
  | equipment count   |     domain=[], limit=1
  +------------------+
       |
       v
  +------------------+
  | count == 0?      |--NO--> "Tu as deja des equipements. Besoin d'aide ?"
  +------------------+
       | YES
       v
  +------------------+
  | Onboarding flow  |
  | (prompt-driven)  |
  +------------------+
       |
       v

  Onboarding loop (per appliance):

  +---> Hodoor: "Envoie une photo de ton prochain appareil"
  |          |
  |          v
  |    User sends photo
  |          |
  |          v
  |    GPT Vision identifies appliance
  |          |
  |          v
  |    Hodoor: "C'est un [type]. Tu l'as depuis quand ?"
  |          |
  |          v
  |    User replies with date (or "je sais pas")
  |          |
  |          v
  |    create_record (maintenance.equipment)
  |          |
  |          v
  |    search_common_issues --> maintenance tip
  |          |
  |          v
  |    Hodoor: "[Tip]. Un autre appareil ?"
  |          |
  +----YES---+
       |
       NO (user says done)
       |
       v
  +---------------------------+
  | Missing appliance check   |
  | Compare inventory vs      |
  | reference list             |
  +---------------------------+
       |
       v
  +---------------------------+
  | Final recap               |
  | - All scanned appliances  |
  | - Top maintenance action  |
  +---------------------------+


Component ownership:

  +-------------------+     +-------------------+     +------------------+
  |  bot/prompts/     |     |  bot/history.py   |     |  bot/tools.py    |
  |  system.md        |     |                   |     |                  |
  |                   |     |  MAX_MESSAGES=50  |     |  search_records  |
  |  + Onboarding     |     |  (was 20)         |     |  create_record   |
  |    Discovery      |     |                   |     |  search_common_  |
  |    section        |     +-------------------+     |  issues          |
  |  + Reference      |                               +------------------+
  |    appliance list |            |                          |
  +-------------------+            |                          |
         |                         v                          v
         +-----------------> bot/llm.py <--------------------+
                             get_response()
                             (unchanged)
```

## Files

### To create

| File | Purpose |
|------|---------|
| (none) | All changes are modifications to existing files |

### To modify

| File | Change |
|------|--------|
| `bot/prompts/system.md` | Add "Onboarding Discovery" section with: auto-trigger logic (check equipment when history is empty), welcome script, photo-scan loop instructions, per-appliance confirmation + tip pattern, acquisition date collection, missing-appliance detection with reference list, final recap instructions, derailment handling |
| `bot/history.py` | Change `MAX_MESSAGES` from `20` to `50` |

### Data model changes

None. No new Odoo models, fields, or Python types. The onboarding flow uses existing `maintenance.equipment` and `maintenance.equipment.category` models with their current fields (`name`, `category_id`, `serial_no`, `model`, `note`, `cost`).

### System prompt additions (detailed structure)

The new section in `bot/prompts/system.md` follows this structure:

```markdown
## Onboarding Discovery

### Declenchement automatique
Si la conversation vient de commencer (pas d'historique) :
1. Cherche les equipements existants : search_records sur maintenance.equipment, limit=1
2. Si aucun equipement : lance le parcours onboarding ci-dessous
3. Si des equipements existent : conversation normale

### Accueil
Presente-toi brievement. Explique que tu vas aider a faire l'inventaire de la maison,
appareil par appareil, en envoyant des photos. Mentionne que ca prend 10-15 min.

### Boucle de scan (repeter pour chaque appareil)
1. Demande une photo du prochain appareil
2. A la reception de la photo, identifie l'appareil (type, marque si visible)
3. Demande si une etiquette ou un QR code est facilement accessible
   (ne demande JAMAIS de bouger des meubles ou debrancher)
4. Si oui et que l'utilisateur envoie une 2e photo : extrais modele/reference
5. Demande la date d'acquisition approximative ("tu l'as depuis quand ?")
   Si l'utilisateur ne sait pas, estime "plus de 5 ans" et continue
6. Cree l'equipement dans Odoo avec : name, category_id, model (si connu),
   note (date acquisition)
7. Cherche un conseil maintenance via search_common_issues
8. Donne UN conseil concis (1-2 lignes), puis "Un autre appareil ?"

### Liste de reference (appareils courants)
Apres que l'utilisateur dit avoir fini, compare l'inventaire avec cette liste :
- Refrigerateur / congelateur
- Lave-linge
- Seche-linge
- Lave-vaisselle
- Four
- Plaques de cuisson
- Hotte aspirante
- Micro-ondes
- Chaudiere / pompe a chaleur
- Chauffe-eau / ballon d'eau chaude
- Climatiseur (si pertinent)
- VMC
- Cumulus / adoucisseur d'eau (si pertinent)
- Tableau electrique

Si un appareil courant manque, demande gentiment :
"Au fait, tu n'as pas de [appareil] ? Ou tu n'as pas eu l'occasion de le prendre en photo ?"
Ne pas insister si l'utilisateur dit non.

### Recap final
Quand le scan est termine :
1. Liste tous les appareils scannes avec leur categorie
2. Identifie le conseil maintenance le plus urgent (appareil le plus ancien
   ou probleme le plus courant)
3. Formule : "Ton inventaire est complet ! [N] appareils enregistres.
   Ma recommandation prioritaire : [conseil]. On s'en occupe quand tu veux."

### Gestion des interruptions
Si l'utilisateur envoie un message hors sujet pendant le scan :
- Reponds brievement a sa question
- Ramene la conversation : "Pour revenir a l'inventaire, envoie la photo
  du prochain appareil quand tu veux."
```
