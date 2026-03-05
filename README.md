# Assistant Demarches Simplifiees (Togo)

Projet monolithe "single deploy": frontend + backend + RAG dans un seul service.

## Objectif MVP
- Aider les jeunes au Togo a comprendre et accomplir des demarches administratives.
- Donner une reponse structuree: etapes, pieces, delais, erreurs frequentes, checklist.
- Citer des sources officielles.

## Structure du projet
```text
assistant-demarches-simplifiees/
  backend/
    app/
      api/routes.py
      core/config.py
      models/schemas.py
      services/rag_service.py
      main.py
    data/
      raw/
      processed/
      chroma/
    scripts/ingest_sources.py
    scripts/build_index.py
    requirements.txt
  frontend/
    src/
      App.jsx
      main.jsx
      styles.css
    public/
    index.html
    package.json
    vite.config.js
  Dockerfile
  render.yaml
  .env.example
  .gitignore
  README.md
```

## Ce qui est deja implemente
1. Backend FastAPI avec endpoints:
   - `GET /api/health`
   - `POST /api/auth/register`
   - `POST /api/auth/login`
   - `GET /api/auth/me`
   - `POST /api/auth/logout`
   - `POST /api/ask`
   - `POST /api/checklist`
   - `GET /api/history`
   - `GET /api/form/catalog`
   - `POST /api/form/assist`
   - `POST /api/form/generate`
   - Historique persistant sur disque (`backend/data/processed/history.json`)
   - Utilisateurs/sessions auth persistants (`backend/data/processed/auth_users.json`, `auth_sessions.json`)
   - Controle mot de passe (8+ caracteres, majuscule, minuscule, chiffre)
   - Rate limit auth (anti brute-force)
2. Frontend React (Vite) avec formulaire de question et affichage de reponse.
   - Page d'authentification (nom, email, mot de passe) avant acces
   - Navigation par onglets (`Assistant`, `Checklist`, `Formulaire`, `Historique`)
   - Champ de question
   - Bouton "Generer checklist"
   - Bouton "Telecharger checklist PDF"
   - Formulaires admin assistes + generation d'exemplaire PDF
   - Affichage des sources
   - Historique des recherches (backend)
   - Etat vide avant premiere recherche
   - Layout responsive mobile/desktop
   - Structure en composants (`AskForm`, `AnswerPanel`, `HistoryPanel`)
   - Horodatage de generation
3. Service RAG connecte a Chroma (`rag_service.py`) avec recherche de chunks pertinents.
   - Generation des champs (etapes, pieces, erreurs, checklist) depuis les passages recuperes
   - Citations multi-sources (jusqu'a 5 URLs uniques)
   - Detection automatique de la categorie de demarche (papiers, justice, emploi, fiscalite) pour guider la recherche
   - Mode LLM grounded optionnel (OpenAI) base strictement sur les passages recuperes
   - Fallback heuristique automatique si la cle API est absente ou en erreur
4. Deploiement unique via `Dockerfile` (frontend build puis servi par FastAPI).
5. Script d'indexation local:
   - `backend/scripts/build_index.py`
   - source d'entree: `backend/data/raw/sources.jsonl`
6. Script d'ingestion web/pdf:
   - `backend/scripts/ingest_sources.py`
   - source d'entree: `backend/data/raw/web_sources.json`
   - filtre securite: URLs `https://` et domaine officiel `*.gouv.tg` uniquement
7. Fiabilite / conformite:
   - disclaimer visible dans Assistant / Checklist / Formulaire
   - affichage des dates de mise a jour des sources
   - logs backend dans `backend/data/processed/app.log`

## Lancer en local
### Option 1: Docker (recommande)
```bash
docker build -t assistant-demarches .
docker run --rm -p 8000:8000 assistant-demarches
```
Ensuite ouvrir `http://localhost:8000`.

### Option 2: Dev separe
Backend:
```bash
cd backend
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```
Le frontend appelle `/api`, donc en dev Vite il faudra ajouter un proxy plus tard si besoin.

## Variables d'environnement
Copier `.env.example` vers `.env` et ajuster:
- `APP_NAME`
- `APP_ENV`
- `PORT`
- `DATABASE_URL` (optionnel, active Postgres pour auth + historique)
- `OPENAI_API_KEY` (recommande pour de meilleures reponses)
- `OPENAI_MODEL` (defaut: `gpt-4o-mini`)
- `TARGET_COUNTRY=Togo`

Sans `DATABASE_URL`, le projet garde un fallback local JSON.

## Workflow RAG actuel
1. Copier `backend/data/raw/web_sources.example.json` vers `backend/data/raw/web_sources.json`.
2. Completer avec tes URLs officielles Togo.
3. Lancer l'ingestion:
```bash
cd backend
python -m scripts.ingest_sources
```
4. Lancer l'indexation:
```bash
cd backend
python -m scripts.build_index
```
5. Lancer l'API puis tester `POST /api/ask`.
6. Reponses plus fiables: garder des URLs tres ciblees et reindexer apres modification.

## Format JSONL des sources
Chaque ligne doit etre un JSON valide:
```json
{
  "id": "tg-xxx-001",
  "title": "Titre de la source",
  "url": "https://...",
  "updated_at": "2026-03-01",
  "category": "entreprise",
  "country": "Togo",
  "text": "Contenu textuel extrait de la source officielle"
}
```

## Format web_sources.json
Le fichier est un tableau JSON:
```json
[
  {
    "id": "tg-service-public-home",
    "title": "Titre lisible",
    "url": "https://service-public.gouv.tg/",
    "category": "general",
    "type": "html",
    "updated_at": "2026-03-04"
  }
]
```

## Deploiement Railway (single service)
Objectif: deployer frontend + backend ensemble via le `Dockerfile` du projet.

### 1. Creer le projet
1. Ouvrir Railway et creer `New Project`.
2. Choisir `Deploy from GitHub Repo`.
3. Selectionner ce repository.
4. Railway detecte le `Dockerfile` a la racine et build automatiquement.

### 2. Ajouter PostgreSQL Railway
1. Dans le meme projet Railway, `New` -> `Database` -> `PostgreSQL`.
2. Dans le service Web, ouvrir `Variables` -> `Add Reference`.
3. Selectionner la base PostgreSQL puis choisir `DATABASE_URL`.

### 3. Variables d'environnement du service Web
Configurer au minimum:
- `APP_NAME=Assistant Demarches Simplifiees`
- `APP_ENV=prod`
- `TARGET_COUNTRY=Togo`
- `DATABASE_URL=<reference railway postgres>`
- `OPENAI_API_KEY=<ta cle>` (recommande)
- `OPENAI_MODEL=gpt-4o-mini`
- `ADMIN_EMAILS=<email_admin_1,email_admin_2>`

Notes:
- Railway fournit `PORT` automatiquement (ne pas forcer).
- La cle OpenAI ameliore la qualite mais ne suffit pas seule: la qualite depend aussi des sources RAG indexees.

### 4. Source ingest / index en production
Important: Railway n'execute pas automatiquement l'ingestion/indexation.
Avant premier usage en prod:
1. Ouvrir shell Railway du service Web (ou local avant deploy).
2. Executer (commande unique):
```bash
python -m scripts.bootstrap_rag
```
Equivalent detaille:
```bash
python -m scripts.ingest_sources
python -m scripts.build_index
```

### 5. Verifications apres deploy
Tester:
- `GET /api/health` -> `{"ok": true}`
- inscription -> connexion
- `POST /api/ask` repond avec `sources` non vide
- onglet `Formulaire` genere un exemplaire PDF

Test automatique (smoke test):
```bash
cd backend
python -m scripts.smoke_test https://<ton-app>.up.railway.app
```

Controle qualite RAG (10 questions):
```bash
cd backend
python -m scripts.qa_rag_questions
```

### 6. Points de fiabilite deja inclus
- logs backend: `backend/data/processed/app.log`
- disclaimers non officiel visibles en UI
- filtrage strict des sources: `https` + `*.gouv.tg`
- fallback JSON si `DATABASE_URL` absent (dev local)
