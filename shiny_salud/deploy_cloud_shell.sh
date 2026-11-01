#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-eda-salud-atlantico-2018}"
REGION="${REGION:-us-east1}"
SERVICE_NAME="${SERVICE_NAME:-shiny-salud-atlantico}"

cd "$(dirname "$0")"
for path in app.R data/eda.json data/modelo.json Dockerfile; do
  if [[ ! -f "$path" ]]; then
    echo "Falta $path: suba el paquete completo de la aplicación." >&2
    exit 1
  fi
done

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  --project "$PROJECT_ID"
# Shiny mantiene la sesión por WebSocket: necesita afinidad y un tiempo de espera largo.
gcloud run deploy "$SERVICE_NAME" \
  --project "$PROJECT_ID" --region "$REGION" --source . \
  --platform managed --allow-unauthenticated --port 8080 \
  --cpu 1 --memory 1Gi --min-instances 0 --max-instances 3 \
  --concurrency 40 --timeout 3600 --session-affinity
