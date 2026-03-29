# HODOOR

> Diagnostiquer, reparer et maintenir les appareils d'un logement, simplement.

Projet developpe en 48h dans le cadre du hackathon **Shift 2026** (Le Palace, Nantes, 28-29 mars 2026).

**Demo live** : [hodoor.cleverapps.io](https://hodoor.cleverapps.io)

---

## Vision produit

Chaque foyer accumule des dizaines d'appareils sans aucun suivi. Les manuels disparaissent, les garanties expirent dans l'oubli, et les pannes arrivent toujours au pire moment.

HODOOR est un assistant IA personnel qui transforme la gestion de la maison :

- **Scanner** un appareil (photo, plaque signaletique) pour l'identifier instantanement via GPT Vision
- **Diagnostiquer** une panne a partir d'un symptome, code erreur ou simple description
- **Guider** la reparation pas a pas avec sourcing des pieces detachees
- **Planifier** la maintenance preventive avant que les choses ne cassent
- **Connecter** les objets domotiques (Jeedom) pour detecter les anomalies en temps reel

L'idee centrale : chaque appareil scanne delivre immediatement un conseil de maintenance. L'onboarding complet d'un logement prend 15 minutes et produit un inventaire avec un plan d'actions prioritaire.

## Architecture

```
                     +------------------+
                     |   React PWA      |
                     |   (Vite + TS)    |
                     +--------+---------+
                              |
                    REST API /api/v1
                              |
                     +--------+---------+
                     |   FastAPI        |
                     |   + Telegram Bot |   <-- co-hosted, single process
                     |   + Bran (IoT)   |
                     +---+---------+----+
                         |         |
              +----------+    +----+------+
              |  Odoo 17 |    |  Jeedom   |
              | (via RPC)|    | (via API) |
              +----+-----+    +-----------+
                   |
              +----+-----+
              | Postgres  |
              +-----------+
```

**Stack technique** :
- **Backend** : Python 3.12, FastAPI, python-telegram-bot, OpenAI (function calling)
- **Frontend** : React 19, TypeScript, Tailwind CSS, PWA (service worker, manifest, installable)
- **Donnees** : Odoo 17 (ERP, source de verite pour appareils et maintenance), SQLite (auth web)
- **IoT** : Jeedom (module "Bran", decouverte et metriques capteurs)
- **TTS** : ElevenLabs (reponses vocales optionnelles)
- **Recherche** : Tavily (documentation produit, pannes courantes)
- **Deploy** : Clever Cloud, Docker

## Deroulement du hackathon

### Phase 1 : Bot Telegram + Backend (samedi matin)

Le socle. Un bot Telegram connecte a OpenAI et Odoo, capable de :
- Recevoir texte, voix, photo, video
- Identifier un appareil par photo (GPT Vision)
- Creer/modifier les fiches dans Odoo via function calling (agentic)
- Repondre en voix (ElevenLabs TTS)
- Rechercher de la documentation technique (Tavily)

L'onboarding est entierement prompt-driven : le LLM suit les instructions du system prompt pour guider l'utilisateur piece par piece, sans machine a etats cote code. Chaque appareil scanne = un conseil de maintenance immediat.

### Phase 2 : Application mobile PWA (samedi apres-midi / nuit)

Une webapp mobile-first construite en React, servie directement par FastAPI :
- **Scan** : inventaire des appareils avec photo, infos produit, historique maintenance
- **Chat** : assistant IA general + fils de discussion par appareil
- **Maintenance** : timeline des taches, health score, generation de plan via IA
- **Auth** : auto-login anonyme pour acces ouvert (login inhibe pour permettre au public de tester l'app pendant le pitch final, avec le scan d'appareils reels du Palace)

Le meme moteur LLM sert Telegram et le web. L'historique de conversation est keye par user ID (int pour Telegram, UUID pour le web), rendant le transport pluggable.

### Phase 3 : Integration Jeedom / IoT (dimanche matin)

Le module "Bran" connecte Jeedom pour :
- Decouvrir les peripheriques connectes (scan radar UX)
- Importer automatiquement les devices dans l'inventaire Odoo
- Afficher les metriques capteurs avec sparklines et detection d'anomalies
- Injecter les alertes domotiques dans le contexte du chat IA et la generation de plans

Un serveur mock Jeedom embarque permet de demontrer l'integration sans hardware reel.

## Installation

### Prerequis

- Python 3.12+
- Node.js 20+ avec pnpm
- Docker et Docker Compose (pour Odoo + PostgreSQL)
- Un compte OpenAI avec acces API

### 1. Cloner et installer

```bash
git clone https://github.com/DorianOuvrard/homeops.git
cd homeops

# Backend Python
uv sync

# Frontend React
cd web && pnpm install && cd ..
```

### 2. Configurer l'environnement

```bash
cp .env.example .env
```

Editer `.env` avec vos cles :

| Variable | Requis | Description |
|----------|--------|-------------|
| `OPENAI_API_KEY` | **Oui** | Cle API OpenAI. Le bot utilise GPT-4o pour le chat, la vision et le function calling. Sans cette cle, rien ne fonctionne. |
| `ELEVENLABS_API_KEY` | Non | Cle API ElevenLabs pour les reponses vocales. Sans elle, le bot repond uniquement en texte. |
| `TELEGRAM_TOKEN` | Non | Token BotFather pour le bot Telegram. Necessaire uniquement si vous voulez le canal Telegram. |
| `TAVILY_API_KEY` | Non | Pour la recherche de documentation produit et pannes courantes. |
| `ODOO_URL` | Oui | URL de l'instance Odoo (par defaut `http://localhost:8069`). |
| `ODOO_DB` / `ODOO_USER` / `ODOO_PASSWORD` | Oui | Identifiants Odoo. Crees au premier lancement de l'instance. |
| `JWT_SECRET` | Oui | Secret pour signer les tokens JWT. Generez-en un : `openssl rand -hex 32` |
| `JEEDOM_MOCK` | Non | Mettre a `true` pour utiliser le mock Jeedom embarque (sans hardware). |

### 3. Lancer les services

```bash
# Demarrer Odoo + PostgreSQL
docker compose up -d odoo db

# Builder le frontend
cd web && pnpm build && cd ..

# Lancer le bot + API
uv run python -m bot.main
```

L'application est disponible sur `http://localhost:8000`.

### Alternative Docker (tout-en-un)

```bash
docker compose up --build
```

## Choix de conception notables

**LLM agentic via function calling** : le bot ne code pas en dur les appels Odoo. Il dispose d'outils (search_records, create_record, update_record...) et decide lui-meme quoi appeler. Ca le rend capable de raisonnement autonome sur les donnees.

**Onboarding prompt-driven** : pas de machine a etats Python. Le system prompt decrit le flow piece par piece, et le LLM le suit. Iteration rapide sur le ton et le flow sans toucher au code.

**Co-hosting FastAPI + Telegram** : un seul process, un seul container. Le polling Telegram tourne en tache asyncio dans le lifespan FastAPI. Simple a deployer, memoire partagee.

**SQLite pour l'auth, Odoo pour le reste** : l'auth web est un detail d'implementation (une table, du SQL brut). La verite metier (appareils, maintenance, historique) vit dans Odoo.

**PWA, pas natif** : service worker + manifest = 90% de l'experience app sans la complexite app store. Installable sur l'ecran d'accueil iOS/Android.

## Equipe

Projet realise par l'equipe HomeOps pour le hackathon Shift 2026.

## Licence

MIT
