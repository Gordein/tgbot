# utils.py
import json
import logging
import os
from datetime import datetime
from config import DATA_FILE_PATH, STATUS_NEW  # Import constants if needed


# --- Date Formatting --- (Keep as before)
def format_datetime(dt=None):
    if dt is None: dt = datetime.now()
    try:
        if isinstance(dt, str): dt = datetime.fromisoformat(dt)
        return dt.strftime('%d.%m.%Y %H:%M:%S')
    except (ValueError, TypeError):
        return str(dt)


# --- Data Storage (JSON File) ---
_data_cache = None  # Simple in-memory cache


def _load_data():
    """Loads data from the JSON file, initializes if not found/corrupt."""
    global _data_cache
    if _data_cache is not None:
        return _data_cache

    if not os.path.exists(DATA_FILE_PATH):
        logging.warning(
            f"Data file '{DATA_FILE_PATH}' not found. Initializing empty data."
        )
        _data_cache = {"requests": {}, "counter": 0}
        _save_data()  # Create the file
        return _data_cache
    try:
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            _data_cache = json.load(f)
            # Ensure basic structure exists after loading
            if "requests" not in _data_cache: _data_cache["requests"] = {}
            if "counter" not in _data_cache: _data_cache["counter"] = 0
            logging.info(f"Data loaded successfully from {DATA_FILE_PATH}")
            return _data_cache
    except (json.JSONDecodeError, IOError, TypeError) as e:
        logging.error(
            f"Error loading data from {DATA_FILE_PATH}: {e}. Initializing empty data."
        )
        _data_cache = {"requests": {}, "counter": 0}
        return _data_cache


def _save_data():
    """Saves the current data cache to the JSON file."""
    global _data_cache
    if _data_cache is None:
        logging.warning("Attempted to save data, but cache is None.")
        return
    try:
        with open(DATA_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(_data_cache, f, indent=2,
                      ensure_ascii=False)  # Use indent=2 for readability
    except IOError as e:
        logging.error(f"Error saving data to {DATA_FILE_PATH}: {e}")


# --- Public Data Access Functions ---
async def get_request_data(req_id):
    """Fetches request data."""
    data_store = _load_data()
    req_id_str = str(req_id)  # Use string keys for JSON consistency
    return data_store["requests"].get(req_id_str)


async def save_request_data(req_id, data_dict):
    """Saves request data."""
    data_store = _load_data()
    req_id_str = str(req_id)
    data_store["requests"][req_id_str] = data_dict
    _save_data()  # Write changes to file


async def get_next_request_id():
    """Gets and increments the request counter."""
    data_store = _load_data()
    try:
        current_id = int(data_store.get("counter", 0))
    except (ValueError, TypeError):  # Handle if counter is corrupt
        logging.warning(
            f"Counter in {DATA_FILE_PATH} was not an integer. Resetting to 0.")
        current_id = 0
    next_id = current_id + 1
    data_store["counter"] = next_id
    _save_data()  # Save updated counter
    return next_id


# --- Message Formatting --- (Keep format_request_message as before)
def format_request_message(req_id,
                           req_data,
                           target_status=None,
                           processed_by_name=None):
    client_name = req_data.get('client_name', 'N/A')
    client_phone = req_data.get('client_phone', 'N/A')
    client_messenger = req_data.get('client_messenger', '—')
    raw_event_details = req_data.get('raw_event_details', '')
    form_timestamp_iso = req_data.get('form_timestamp')
    sheet_status = req_data.get('status', STATUS_NEW)
    claimed_by = req_data.get('claimed_by_name')
    claimed_ts_iso = req_data.get('claimed_timestamp')
    last_upd_by = req_data.get('last_updated_by_name')
    last_upd_ts_iso = req_data.get('last_updated_timestamp')

    current_display_status = target_status if target_status is not None else sheet_status

    if processed_by_name:
        if current_display_status == STATUS_COMPLETED:
            display_status_line = f"{STATUS_COMPLETED} ({processed_by_name})"
        elif current_display_status not in [
                STATUS_NEW
        ] and not current_display_status.startswith(STATUS_CLAIMED_PREFIX):
            display_status_line = f"{current_display_status} ({processed_by_name})"
        else:
            display_status_line = current_display_status
    else:
        display_status_line = current_display_status

    events_fmt = '\n'.join([
        f"● {c.strip()}" for c in raw_event_details.split(',')
    ]) if raw_event_details else "N/A"

    text = f"<b>Заяўка #{req_id}</b>\n👤 {client_name}\n📞 {client_phone}\n📲 Tg/Viber: {client_messenger}\n\nМерапрыемства:\n{events_fmt}\n\n⏰ Заяўка ад: {format_datetime(form_timestamp_iso)}\n<b>Статус: {display_status_line}</b>\n"
    if claimed_by and claimed_ts_iso:
        text += f"🔑 Замацавана за: {claimed_by} ({format_datetime(claimed_ts_iso)})\n"
    if last_upd_by and last_upd_ts_iso and not (
            processed_by_name == last_upd_by
            and current_display_status == sheet_status):
        text += f"📝 Апошняе абнаўленне: {last_upd_by} ({format_datetime(last_upd_ts_iso)})\n"
    return text
