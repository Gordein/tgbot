# config.py
import os
import logging
from dotenv import load_dotenv

# Load .env file for local development if it exists
load_dotenv()

# --- Core Secrets (Set these in Railway Environment Variables) ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
FORM_SECRET = os.environ.get('FORM_SECRET')

# --- Manager Config (Keep this hardcoded or load from env vars too if preferred) ---
MANAGERS = {
    '675120396': {
        'name': 'Даша',
        'nameBy': 'Дашай'
    },
    '8153757571': {
        'name': 'Юля',
        'nameBy': 'Юляй'
    }
}

# --- Status Constants ---
STATUS_NEW = "Новая"
STATUS_CLAIMED_PREFIX = "Апрацоўваецца"
STATUS_WILL_COME = "✅ Прыедзе"
STATUS_CANCELED_CLIENT = "❌ Адмена"
STATUS_ALERTED = "🔔 Апавешчаны"
STATUS_COMPLETED = "🏁 Завершана"

# --- Data Storage (Simple JSON file for Railway) ---
# Note: File storage on Railway's free tier might not be fully persistent across restarts/deployments.
# For better persistence, consider Railway's Postgres/Redis add-ons or external DBs.
DATA_FILE_PATH = "bot_data.json"

# --- Webhook Settings ---
# Railway typically injects the public URL via RAILWAY_STATIC_URL
# or you find it manually after the first deployment.
RAILWAY_PUBLIC_URL = os.environ.get(
    'RAILWAY_STATIC_URL')  # Check if Railway provides this

# !!! IMPORTANT: Set this MANUALLY after your first Railway deploy if RAILWAY_STATIC_URL is not available !!!
MANUAL_WEBHOOK_HOST = "PASTE_YOUR_RAILWAY_APP_URL_HERE"  # e.g., "https://mybot-prod.up.railway.app"

if RAILWAY_PUBLIC_URL:
     WEBHOOK_HOST = RAILWAY_PUBLIC_URL
     logging.info(f"Using RAILWAY_STATIC_URL for webhook host: {WEBHOOK_HOST}")
elif MANUAL_WEBHOOK_HOST != "PASTE_YOUR_RAILWAY_APP_URL_HERE":
     WEBHOOK_HOST = MANUAL_WEBHOOK_HOST
     logging.warning(f"Using manually set WEBHOOK_HOST: {WEBHOOK_HOST}")
else:
     WEBHOOK_HOST = None
     logging.error(
         "Webhook Host URL could not be determined. Set RAILWAY_STATIC_URL env var or MANUAL_WEBHOOK_HOST in config.py"
     )

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"  # Obscure webhook path with token
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST and BOT_TOKEN else None

# --- Web Server Settings ---
# Railway injects the PORT variable. Default needed for local testing.
WEB_SERVER_HOST = "0.0.0.0"  # Necessary for Railway/Docker
WEB_SERVER_PORT = int(os.environ.get('PORT', 8080))

# --- Form Submission Endpoint ---
FORM_SUBMIT_PATH = "/formsubmit"
