  
    
import os
import json
import gzip
import shutil
import requests
from datetime import datetime

BASE_DATA_DIR = "data"
INSTRUMENT_URL = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"

OVERWRITE_TODAY_FILES = False

FILTERED_INSTRUMENTS = {
    "nifty": [],
    "banknifty": [],
    "sensex": []
}

ALL_INSTRUMENTS = []
INSTRUMENT_BY_KEY = {}
INSTRUMENT_BY_SYMBOL = {}


# ===========================
# Utils
# ===========================

def log(msg):
    print(f"[INFO] {msg}")

def get_today_dir():
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(BASE_DATA_DIR, today)

def get_file_paths():
    today_dir = get_today_dir()
    gz_file = os.path.join(today_dir, "complete.json.gz")
    json_file = os.path.join(today_dir, "complete.json")
    return today_dir, gz_file, json_file


# ===========================
# Cleanup old data folders
# ===========================

def cleanup_old_data_folders():
    today = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(BASE_DATA_DIR):
        return

    for folder in os.listdir(BASE_DATA_DIR):
        folder_path = os.path.join(BASE_DATA_DIR, folder)

        if os.path.isdir(folder_path) and folder != today:
            shutil.rmtree(folder_path, ignore_errors=True)
            log(f"Deleted old data folder: {folder}")


# ===========================
# Download & Extract
# ===========================

def download_and_extract(overwrite=False):
    today_dir, gz_file, json_file = get_file_paths()
    os.makedirs(today_dir, exist_ok=True)

    if overwrite or not os.path.exists(gz_file):
        log("Downloading instrument master...")
        r = requests.get(INSTRUMENT_URL, stream=True, timeout=30)
        r.raise_for_status()

        with open(gz_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    else:
        log("Instrument master already exists")

    if overwrite or not os.path.exists(json_file):
        log("Extracting instrument master...")
        with gzip.open(gz_file, "rb") as f_in:
            with open(json_file, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
    else:
        log("Instrument JSON already extracted")


# ===========================
# Load & Filter
# ===========================

def load_and_filter():
    _, _, json_file = get_file_paths()

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    nifty = []
    banknifty = []
    sensex = []

    by_key = {}
    by_symbol = {}

    for item in data:
        name = item.get("name", "").upper()
        segment = item.get("segment", "")

        if segment in ["NSE_FO", "BSE_FO"]:
            if name == "NIFTY":
                nifty.append(item)
            elif name == "BANKNIFTY":
                banknifty.append(item)
            elif name == "SENSEX":
                sensex.append(item)
            else:
                continue

            key = item.get("instrument_key")
            symbol = item.get("trading_symbol")

            if key:
                by_key[key] = item
            if symbol:
                by_symbol[symbol.upper()] = item

    FILTERED_INSTRUMENTS["nifty"] = nifty
    FILTERED_INSTRUMENTS["banknifty"] = banknifty
    FILTERED_INSTRUMENTS["sensex"] = sensex

    ALL_INSTRUMENTS.clear()
    ALL_INSTRUMENTS.extend(nifty)
    ALL_INSTRUMENTS.extend(banknifty)
    ALL_INSTRUMENTS.extend(sensex)

    INSTRUMENT_BY_KEY.clear()
    INSTRUMENT_BY_KEY.update(by_key)

    INSTRUMENT_BY_SYMBOL.clear()
    INSTRUMENT_BY_SYMBOL.update(by_symbol)

    print(
        f"[INSTRUMENTS] Loaded → "
        f"NIFTY:{len(nifty)} | "
        f"BANKNIFTY:{len(banknifty)} | "
        f"SENSEX:{len(sensex)} | "
        f"TOTAL:{len(ALL_INSTRUMENTS)}"
    )


# ===========================
# Save
# ===========================

def save_filtered_files():
    today_dir, _, _ = get_file_paths()

    with open(os.path.join(today_dir, "nifty_options.json"), "w", encoding="utf-8") as f:
        json.dump(FILTERED_INSTRUMENTS["nifty"], f, indent=2)

    with open(os.path.join(today_dir, "banknifty_options.json"), "w", encoding="utf-8") as f:
        json.dump(FILTERED_INSTRUMENTS["banknifty"], f, indent=2)

    with open(os.path.join(today_dir, "sensex_options.json"), "w", encoding="utf-8") as f:
        json.dump(FILTERED_INSTRUMENTS["sensex"], f, indent=2)

    with open(os.path.join(today_dir, "all_index_options.json"), "w", encoding="utf-8") as f:
        json.dump(ALL_INSTRUMENTS, f, indent=2)

    log("Filtered index option files saved")


# ===========================
# Cleanup Raw
# ===========================

def cleanup_raw_files():
    today_dir, gz_file, json_file = get_file_paths()

    if os.path.exists(gz_file):
        os.remove(gz_file)

    if os.path.exists(json_file):
        with open(json_file, encoding='utf-8') as f:
            data = json.load(f)

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    log("Raw instrument files formatted")


# ===========================
# Bootstrap
# ===========================

def bootstrap_instruments(overwrite=False):
    log("Instrument bootstrap started")

    cleanup_old_data_folders()
    download_and_extract(overwrite=overwrite)
    load_and_filter()
    save_filtered_files()
    cleanup_raw_files()

    log("Instrument bootstrap completed")