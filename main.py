# main.py
import asyncio
import logging
import os
import json

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH, WEB_SERVER_HOST, WEB_SERVER_PORT, \
                   FORM_SUBMIT_PATH, FORM_SECRET
from bot_handlers import router as main_router, create_and_notify_new_request
# Import utils to ensure data loading happens on start if needed by handlers
import utils

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


async def handle_form_submit(request: web.Request):
    bot_instance = request.app['bot']
    received_secret = request.headers.get("X-Form-Secret")
    # Use the FORM_SECRET loaded from config (which gets from env var)
    if not received_secret or received_secret != FORM_SECRET:
        logging.warning(f"Form submission rejected: Invalid/missing secret.")
        return web.Response(status=403, text="Forbidden: Invalid Secret")
    try:
        data = await request.json()
        logging.info(f"Received form submission data: {data}")
        if not all(k in data
                   for k in ["timestamp", "name", "phone", "details"]):
            logging.error("Form submission rejected: Missing fields.")
            return web.json_response(
                {
                    "status": "error",
                    "message": "Missing required fields"
                },
                status=400)
        client_data = {
            "timestamp": data.get("timestamp"),
            "name": data.get("name"),
            "phone": data.get("phone"),
            "messenger": data.get("messenger", ""),
            "details": data.get("details")
        }
        req_id = await create_and_notify_new_request(bot_instance, client_data)
        return web.json_response({"status": "ok", "request_id": req_id})
    except json.JSONDecodeError:
        logging.error("Form submission failed: Invalid JSON.")
        return web.json_response(
            {
                "status": "error",
                "message": "Invalid JSON payload"
            }, status=400)
    except Exception as e:
        logging.exception("Error handling form submission:")
        return web.json_response(
            {
                "status": "error",
                "message": "Internal server error"
            },
            status=500)


async def on_startup(bot: Bot):
    # Ensure data is loaded at least once on startup
    utils._load_data()

    if not WEBHOOK_URL:
        logging.error(
            "WEBHOOK_URL is not defined in config (check RENDER_EXTERNAL_URL env var or MANUAL_WEBHOOK_HOST). Cannot set webhook."
        )
        return

    logging.info(
        f"Attempting to set webhook for bot {bot.id} to {WEBHOOK_URL}")
    try:
        success = await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        if success:
            logging.info("Webhook set successfully.")
            webhook_info = await bot.get_webhook_info()
            logging.info(f"Current webhook info: {webhook_info}")
        else:
            logging.error(f"Failed to set webhook to {WEBHOOK_URL}.")
    except Exception as e:
        logging.exception(f"Error setting webhook ({WEBHOOK_URL}): {e}")


async def on_shutdown(bot: Bot):
    logging.warning("Shutting down.. Attempting to delete webhook.")
    # Save data one last time on shutdown
    utils._save_data()
    try:
        await bot.delete_webhook()
        logging.info("Webhook deleted.")
    except Exception as e:
        logging.exception(f"Error deleting webhook: {e}")
    await bot.session.close()
    logging.warning("Bot session closed.")


async def main():
    # Basic config checks on start
    if not BOT_TOKEN:
        logging.critical("BOT_TOKEN not configured. Exiting.")
        return
    if not FORM_SECRET:
        logging.critical("FORM_SECRET not configured. Exiting.")
        return
    if not WEBHOOK_URL:
        logging.critical(
            "WEBHOOK_URL could not be determined from config. Exiting.")
        return

    # Initialize Bot
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

    dp = Dispatcher()
    dp.include_router(main_router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    # Store bot instance for handlers that need it (like form submit)
    app['bot'] = bot

    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    app.router.add_post(FORM_SUBMIT_PATH, handle_form_submit)
    setup_application(app, dp, bot=bot)

    # Use PORT from environment variable provided by Render/Railway
    logging.info(f"Starting web server on {WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
    await web._run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    asyncio.run(main())
