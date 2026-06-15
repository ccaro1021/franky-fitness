# Deployment Runbook — Google Cloud (temporary demo)

This is a one-off, temporary deployment so a couple of interviewers can use
Franky Fitness over the web. It's designed to be torn down completely after
~2 months (see [Teardown](#teardown)). Architecture and rationale are in
`docs/IMPLEMENTATION_PLAN.md`'s decision log; the short version:

- **Backend**: `backend/Dockerfile` → Cloud Run service `franky-backend`
- **Frontend**: `frontend/Dockerfile` (nginx, static build + reverse proxy
  `/api/*` → backend) → Cloud Run service `franky-frontend`
- **Database**: Cloud SQL for Postgres 17, smallest tier
- **Secrets**: API keys + `DATABASE_URL` in Secret Manager

The nginx reverse proxy makes the frontend and backend appear same-origin to
the browser, so the existing cookie-based auth and CORS config need **no
changes**.

Replace `PROJECT_ID` below with your actual GCP project ID throughout.

## 1. Tooling & project setup

```bash
brew install --cask google-cloud-sdk
gcloud auth login
gcloud projects create PROJECT_ID --name="Franky Fitness Demo"
gcloud config set project PROJECT_ID
# Link a billing account (one-time, via console or):
#   gcloud billing projects link PROJECT_ID --billing-account=BILLING_ACCOUNT_ID

gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com

gcloud artifacts repositories create franky \
  --repository-format=docker \
  --location=us-central1
```

## 2. Cloud SQL (Postgres)

```bash
gcloud sql instances create franky-fitness-db \
  --database-version=POSTGRES_17 \
  --tier=db-f1-micro \
  --region=us-central1

gcloud sql databases create franky_fitness --instance=franky-fitness-db

gcloud sql users create appuser \
  --instance=franky-fitness-db \
  --password=CHOOSE_A_PASSWORD

# Note this for step 3:
gcloud sql instances describe franky-fitness-db \
  --format="value(connectionName)"
# -> PROJECT_ID:us-central1:franky-fitness-db
```

## 3. Secrets

```bash
# Pull values from your local .env
echo -n "$ANTHROPIC_API_KEY" | gcloud secrets create ANTHROPIC_API_KEY --data-file=-
echo -n "$SPOONACULAR_API_KEY" | gcloud secrets create SPOONACULAR_API_KEY --data-file=-
echo -n "$RAPIDAPI_KEY" | gcloud secrets create RAPIDAPI_KEY --data-file=-

# Cloud SQL Auth Proxy (built into Cloud Run via --add-cloudsql-instances)
# exposes the DB over a unix socket at /cloudsql/<connectionName>
echo -n "postgresql://appuser:CHOOSE_A_PASSWORD@/franky_fitness?host=/cloudsql/PROJECT_ID:us-central1:franky-fitness-db" \
  | gcloud secrets create DATABASE_URL --data-file=-
```

## 4. Build & deploy the backend

The backend `Dockerfile` needs the repo root as its build context (it copies
top-level modules like `models.py`, `grocery.py`, etc.). Build it with Cloud
Build (no local Docker required) using `cloudbuild.backend.yaml`, which points
at `backend/Dockerfile` while using the repo root as context:

```bash
cd /Users/chriscaro/code/franky-fitness

gcloud builds submit . \
  --config=cloudbuild.backend.yaml \
  --substitutions=_IMAGE=us-central1-docker.pkg.dev/PROJECT_ID/franky/backend:latest

gcloud run deploy franky-backend \
  --image us-central1-docker.pkg.dev/PROJECT_ID/franky/backend:latest \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances PROJECT_ID:us-central1:franky-fitness-db \
  --set-secrets=ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,SPOONACULAR_API_KEY=SPOONACULAR_API_KEY:latest,RAPIDAPI_KEY=RAPIDAPI_KEY:latest,DATABASE_URL=DATABASE_URL:latest

# Capture the service URL for step 5:
gcloud run services describe franky-backend --region us-central1 --format="value(status.url)"
```

`setup_tables()` runs automatically on startup (see `backend/database.py`),
so the schema gets created in Cloud SQL on first boot — no manual migration.

## 5. Build & deploy the frontend

`frontend/Dockerfile` is at the root of the `frontend/` directory, so it can
be built directly with `gcloud builds submit`:

```bash
cd /Users/chriscaro/code/franky-fitness/frontend

gcloud builds submit . \
  --tag us-central1-docker.pkg.dev/PROJECT_ID/franky/frontend:latest

gcloud run deploy franky-frontend \
  --image us-central1-docker.pkg.dev/PROJECT_ID/franky/frontend:latest \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars BACKEND_URL=https://franky-backend-xxxx.run.app

gcloud run services describe franky-frontend --region us-central1 --format="value(status.url)"
```

The frontend URL is what you send to interviewers.

## 6. Verify

```bash
# Should return 401 (proves the nginx proxy reaches the backend + Cloud SQL is wired up)
curl -i https://FRONTEND_URL/api/auth/me
```

Then in a browser:
1. Open the frontend URL
2. Sign up a test account
3. Send a chat message (e.g. "build me a meal plan")
4. Save the plan, view the grocery list
5. Log out / log back in

This exercises the full path: nginx proxy → backend → Cloud SQL + Anthropic/Spoonacular/ExerciseDB APIs, and confirms session cookies survive the proxy.

## Running one-off scripts/migrations against the cloud DB

The Cloud SQL instance has no public-network access configured, and `DATABASE_URL`
in Secret Manager uses a unix-socket connection string that only works from inside
Cloud Run (where `--add-cloudsql-instances` mounts `/cloudsql/...`). To run a local
script (e.g. `python -m backend.migrate_grocery_categories`) against the cloud DB
from a dev machine, tunnel through the Cloud SQL Auth Proxy:

```bash
# One-time per machine: download the proxy (darwin/arm64 — adjust for your platform)
curl -sL -o /tmp/cloud-sql-proxy \
  https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.2/cloud-sql-proxy.darwin.arm64
chmod +x /tmp/cloud-sql-proxy

# Start the tunnel (uses your `gcloud auth` token — no ADC setup needed)
TOKEN=$(gcloud auth print-access-token)
/tmp/cloud-sql-proxy --port 5433 --token "$TOKEN" \
  franky-fitness-demo:us-central1:franky-fitness-db &

# Get the appuser password (the host/socket part of the secret doesn't apply locally)
gcloud secrets versions access latest --secret=DATABASE_URL
# -> postgresql://appuser:PASSWORD@/franky_fitness?host=/cloudsql/...

# Run the script against the tunnel
source venv/bin/activate
DATABASE_URL="postgresql://appuser:PASSWORD@127.0.0.1:5433/franky_fitness" \
  python -m backend.migrate_grocery_categories

# Stop the tunnel
pkill -f cloud-sql-proxy
```

**Caution:** this connects directly to the production database — verify the
script (and its `DATABASE_URL` override) carefully before running, since there's
no staging environment.

## Teardown

When the demo period ends (~2 months):

```bash
gcloud run services delete franky-backend franky-frontend --region us-central1
gcloud sql instances delete franky-fitness-db
gcloud artifacts repositories delete franky --location=us-central1

# Removes everything (Artifact Registry images, secrets, etc.) and stops all billing:
gcloud projects delete PROJECT_ID
```
