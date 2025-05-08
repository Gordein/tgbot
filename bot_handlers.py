import logging
import json
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.utils.markdown import hbold
from aiogram.exceptions import TelegramAPIError  # Import specific exceptions if neede

from config import MANAGERS, STATUS_NEW, STATUS_CLAIMED_PREFIX, STATUS_WILL_COME, \
                   STATUS_CANCELED_CLIENT, STATUS_ALERTED, STATUS_COMPLETED
from utils import format_request_message, get_next_request_id, save_request_data, get_request_data

# Setup Router
router = Router()


# --- Keyboard Builders --- (Keep build_initial_claim_keyboard & build_status_update_keyboard as before)
def build_initial_claim_keyboard(req_id):
    buttons = []
    manager_items = list(MANAGERS.items())
    for i in range(0, len(manager_items), 2):
        row = [
            InlineKeyboardButton(text=f"Прыняць ({man_data['name'][0]})",
                                 callback_data=f"claim|{req_id}|{man_id}") for
            man_id, man_data in manager_items[i:min(i + 2, len(manager_items))]
        ]
        if row: buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_status_update_keyboard(req_id):
    keyboard = [
        [
            InlineKeyboardButton(
                text=STATUS_WILL_COME,
                callback_data=f"updateStatus|{req_id}|{STATUS_WILL_COME}"),
            InlineKeyboardButton(
                text=STATUS_ALERTED,
                callback_data=f"updateStatus|{req_id}|{STATUS_ALERTED}")
        ],
        [
            InlineKeyboardButton(
                text=STATUS_CANCELED_CLIENT,
                callback_data=f"updateStatus|{req_id}|{STATUS_CANCELED_CLIENT}"
            )
        ],
        [
            InlineKeyboardButton(text=STATUS_COMPLETED,
                                 callback_data=f"complete|{req_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# --- Reusable Function for Creating and Notifying ---
async def create_and_notify_new_request(bot: Bot, client_data: dict):
    """Creates a new request, saves it, and notifies managers."""
    req_id = await get_next_request_id()
    now_iso = datetime.now().isoformat()

    new_req_data = {
        "form_timestamp": client_data.get("timestamp",
                                          now_iso),  # Use provided or current
        "client_name": client_data.get("name", f"N/A {req_id}"),
        "client_phone": client_data.get("phone", "N/A"),
        "client_messenger": client_data.get("messenger", ""),
        "raw_event_details": client_data.get("details", ""),
        "status": STATUS_NEW,
        "claimed_by_name": None,
        "claimed_timestamp": None,
        "last_updated_by_name": None,
        "last_updated_timestamp": None,
        "messages": []  # Stores {chat_id, message_id} for updates
    }

    message_text = format_request_message(req_id, new_req_data, STATUS_NEW)
    keyboard = build_initial_claim_keyboard(req_id)

    sent_messages_info = []
    for manager_id in MANAGERS.keys():
        try:
            sent_msg = await bot.send_message(chat_id=manager_id,
                                              text=message_text,
                                              reply_markup=keyboard)
            sent_messages_info.append({
                "chat_id": sent_msg.chat.id,
                "message_id": sent_msg.message_id
            })
            logging.info(
                f"Sent new request {req_id} notification to manager {manager_id}"
            )
        except Exception as e:
            logging.error(
                f"Failed to send new request {req_id} to manager {manager_id}: {e}"
            )

    new_req_data["messages"] = sent_messages_info  # Store sent message details
    await save_request_data(req_id, new_req_data)
    logging.info(f"Request #{req_id} created and saved.")
    return req_id


# --- Command Handlers ---
@router.message(CommandStart())
async def handle_start(message: Message):
    user_id = str(message.from_user.id)
    name = message.from_user.first_name or "Невядомы"
    if user_id in MANAGERS:
        await message.answer(f"Прывітанне, {hbold(name)}! Вы менеджэр.")
        logging.info(f"Manager {name} ({user_id}) started.")
    else:
        await message.answer(
            f"Прывітанне, {name}! Для доступу звярніцеся да адміністратара.")
        logging.info(f"Non-manager {name} ({user_id}) started.")


@router.message(Command("new_request"))
async def handle_new_request_command(message: Message, bot: Bot):
    """Simulates a new request arriving (for testing)."""
    user_id = str(message.from_user.id)
    if user_id not in MANAGERS:
        await message.reply("Толькі менеджэры могуць ствараць тэставыя заяўкі."
                            )
        return

    # Sample data for testing command
    test_client_data = {
        "name": f"Test Client via Cmd",
        "phone": "000000000",
        "messenger": "@testcmd",
        "details": "Event via Command",
        "timestamp": datetime.now().isoformat()  # Use current time
    }

    req_id = await create_and_notify_new_request(bot, test_client_data)
    await message.reply(
        f"Тэставая заяўка #{req_id} створана і адпраўлена менеджэрам.")


# --- Callback Query Handler --- (Keep as before, handles button clicks)
@router.callback_query(
    F.data.startswith("claim|") | F.data.startswith("updateStatus|")
    | F.data.startswith("complete|"))
async def handle_request_callbacks(callback: CallbackQuery, bot: Bot):
    user_id = str(callback.from_user.id)
    manager_performing_action = MANAGERS.get(user_id)

    # doPost already did the initial ack

    try:
        action, req_id_str, *params = callback.data.split('|')
        req_id = int(req_id_str)
        param = params[0] if params else None

        logging.info(
            f"Processing callback: Action={action}, ReqID={req_id}, Param={param}, User={user_id}"
        )

        req_data = await get_request_data(req_id)

        if not req_data:
            logging.warning(
                f"Callback ignored: Request ID {req_id} not found in DB.")
            await callback.answer(f"Заяўка #{req_id} не знойдзена!",
                                  show_alert=True)
            try:
                await callback.message.edit_text(callback.message.text +
                                                 "\n\n⚠️ Заяўка не знойдзена.",
                                                 reply_markup=None)
            except:
                pass
            return

        current_status = req_data.get('status')
        now_iso = datetime.now().isoformat()
        update_made = False
        alert_answer_text = "Апрацавана."  # Default answer

        if action == "claim":
            manager_to_assign = MANAGERS.get(
                param)  # param is assignedToManagerId
            if not manager_to_assign:
                await callback.answer(
                    "Памылка: Менеджэр для прызначэння не знойдзен.",
                    show_alert=True)
                return
            if req_data.get('claimed_by_name'):
                await callback.answer(
                    f"Заяўка ўжо апрацоўваецца {req_data.get('claimed_by_name')}.",
                    show_alert=True)
                return

            req_data['claimed_by_name'] = manager_to_assign['name']
            req_data['claimed_timestamp'] = now_iso
            req_data[
                'status'] = f"{STATUS_CLAIMED_PREFIX} {manager_to_assign['nameBy']}"
            req_data['last_updated_by_name'] = manager_performing_action[
                'name']
            req_data['last_updated_timestamp'] = now_iso
            await save_request_data(req_id, req_data)
            update_made = True
            alert_answer_text = f"✅ Заяўка прынята {manager_to_assign['nameBy']}."
            # Notify others after answering callback quickly
            await callback.answer(alert_answer_text)
            notifyOtherManagers(
                user_id,
                f"ℹ️ Заяўка #{req_id} прынята {manager_performing_action['nameBy']} (прызначана {manager_to_assign['nameBy']})."
            )

        elif action == "updateStatus" or action == "complete":
            new_status = STATUS_COMPLETED if action == "complete" else param
            if current_status == STATUS_COMPLETED and action != 'complete':
                await callback.answer(f"Заяўка #{req_id} ўжо завершана.",
                                      show_alert=True)
                return

            req_data['status'] = new_status
            req_data['last_updated_by_name'] = manager_performing_action[
                'name']
            req_data['last_updated_timestamp'] = now_iso
            await save_request_data(req_id, req_data)
            update_made = True
            alert_answer_text = f"🏁 Заяўка #{req_id} завершана." if action == "complete" else f"Статус зменены на \"{new_status}\"."
            # Notify others after answering callback quickly
            await callback.answer(alert_answer_text)
            notifyOtherManagers(
                user_id,
                f"ℹ️ Статус заяўкі #{req_id} -> \"{new_status}\" ({manager_performing_action['nameBy']})."
            )

        # Update all original messages if an update was made
        if update_made:
            new_text = format_request_message(req_id, req_data,
                                              req_data['status'],
                                              req_data['last_updated_by_name'])
            new_keyboard = None if req_data[
                'status'] == STATUS_COMPLETED else build_status_update_keyboard(
                    req_id)

            messages_to_update = req_data.get("messages", [])
            for msg_info in messages_to_update:
                try:
                    await bot.edit_message_text(
                        text=new_text,
                        chat_id=msg_info["chat_id"],
                        message_id=msg_info["message_id"],
                        reply_markup=new_keyboard)
                except TelegramAPIError as e:  # More specific exception
                    logging.error(
                        f"Failed to edit TG msg {msg_info['message_id']} in chat {msg_info['chat_id']} for req {req_id}: {e}"
                    )
                except Exception as e:
                    logging.error(
                        f"Generic err editing TG msg {msg_info['message_id']} / chat {msg_info['chat_id']} for req {req_id}: {e}"
                    )

    except Exception as e:
        logging.exception(f"Error processing callback: {callback.data}")
        try:
            await callback.answer("Адбылася памылка апрацоўкі!",
                                  show_alert=True)
        except:
            pass  # Ignore if answering fails after main error
