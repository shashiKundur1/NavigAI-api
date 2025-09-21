#!/bin/bash

# Deploy NavigAI API to Google Cloud Run
# Make sure you have gcloud CLI installed and authenticated

# Set your project ID
PROJECT_ID="your-gcp-project-id"
SERVICE_NAME="navigai-api"
REGION="us-central1"

echo "🚀 Deploying NavigAI API to Google Cloud Run..."

# Build and deploy using Cloud Build
echo "📦 Building and deploying with Cloud Build..."
gcloud builds submit --config cloudbuild.yaml \
  --project $PROJECT_ID \
  --region $REGION

echo "🔧 Setting environment variables..."

# Set environment variables (you'll need to run this manually with your values)
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --set-env-vars="CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://navig-ai-client-oegntr6v0-shashidhars-projects-11d35d8d.vercel.app" \
  --set-env-vars="GEMINI_API_KEY=AIzaSyCkaLOOtz6kpt0wIXGHBqPooFhV5oea5Cw" \
  --set-env-vars="FIREBASE_PROJECT_ID=navigai" \
  --set-env-vars="JWT_SECRET_KEY=f6e4bde336bea5e6e9150792645e16264e67dad33ad1f11bxuzz29cca98840907c0c620c9e3c02474e0861b3cab540ada03ab9231dea0df893f8da" \
  --set-env-vars="LIVEKIT_URL=wss://navigai-40iru0ui.livekit.cloud" \
  --set-env-vars="LIVEKIT_API_KEY=APIKtUNfSqF7i5x" \
  --set-env-vars="WHISPER_MODEL=small" \
  --set-env-vars="SAMPLE_RATE=16000" \
  --set-env-vars="RECORDING_TIMEOUT=120" \
  --set-env-vars="SILENCE_THRESHOLD=3" \
  --set-env-vars="MAX_QUESTIONS=20" \
  --set-env-vars="LOG_LEVEL=INFO" \
  --set-env-vars="PYTHONPATH=src"

echo "✅ Deployment completed!"
echo "🌐 Your API should be available at:"
echo "https://$SERVICE_NAME-[random-string]-$REGION.a.run.app"