import os
import logging
from dotenv import load_dotenv

# Load .env file for local development if it exists
load_dotenv()

# --- Core Secrets (Set these in Railway Environment Variables) ---
# Make sure these EXACT names (BOT_TOKEN, FORM_SECRET) are used in Railway Variables tab
BOT_TOKEN = os.environ.get('BOT_TOKEN')
FORM_SECRET = os.environ.get('FORM_SECRET')

# --- Manager Config ---
MANAGERS = {
    '675120396': {'name': 'Даша', 'nameBy': 'Дашай'},
    '8153757571': {'name': 'Юля', 'nameBy': 'Юляй'}
}

# --- Status Constants ---
STATUS_NEW = "Новая"
STATUS_CLAIMED_PREFIX = "Апрацоўваецца"
STATUS_WILL_COME = "✅ Прыедзе"
STATUS_CANCELED_CLIENT = "❌ Адмена"
STATUS_ALERTED = "🔔 Апавешчаны"
STATUS_COMPLETED = "🏁 Завершана"

# --- Data Storage (Simple JSON file) ---
DATA_FILE_PATH = "bot_data.json" # Data stored in this file relative to script

# --- Webhook Settings ---
# Try to get the URL automatically from Railway first
RAILWAY_PUBLIC_URL = os.environ.get('RAILWAY_STATIC_URL') # Railway might inject this

# !!! YOUR SPECIFIC RAILWAY URL AS FALLBACK !!!
MANUAL_WEBHOOK_HOST = "https://tgbot-production-ce54.up.railway.app"

if RAILWAY_PUBLIC_URL:
    # Prepend https:// if Railway provides only the domain
    if not RAILWAY_PUBLIC_URL.startswith(('http://', 'https://')):
        WEBHOOK_HOST = f"https://{RAILWAY_PUBLIC_URL}"
    else:
        WEBHOOK_HOST = RAILWAY_PUBLIC_URL
    logging.info(f"Using RAILWAY_STATIC_URL for webhook host: {WEBHOOK_HOST}")
elif MANUAL_WEBHOOK_HOST:
     WEBHOOK_HOST = MANUAL_WEBHOOK_HOST
     logging.info(f"Using manually set WEBHOOK_HOST: {WEBHOOK_HOST}")
else:
     WEBHOOK_HOST = None
     # This case should ideally not happen if MANUAL_WEBHOOK_HOST is set
     logging.error("Webhook Host URL could not be determined. Check RENDER_EXTERNAL_URL env var or MANUAL_WEBHOOK_HOST in config.py")

# Construct the final webhook URL
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}" # Obscure webhook path
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST and BOT_TOKEN else None

# --- Web Server Settings ---
# Railway injects the PORT variable. Default needed for local testing.
WEB_SERVER_HOST = "0.0.0.0" # Listen on all interfaces
WEB_SERVER_PORT = int(os.environ.get('PORT', 8080)) # Use Railway's port or 8080 locally

# --- Form Submission Endpoint ---
FORM_SUBMIT_PATH = "/formsubmit"
