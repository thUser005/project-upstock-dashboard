import os
import json
import gzip
import shutil
import requests
from datetime import datetime

BASE_DATA_DIR = "data"

INSTRUMENT_URL = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"

# 🔁 Overwrite control flag
OVERWRITE_TODAY_FILES = False   # set True to force re-download

# Global caches
FILTERED_INSTRUMENTS = {
    "nifty": [],
    "banknifty": [],
    "sensex": []
}

ALL_INSTRUMENTS = []
INSTRUMENT_BY_KEY = {}
INSTRUMENT_BY_SYMBOL = {}


def get_today_dir():
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(BASE_DATA_DIR, today)


def get_file_paths():
    today_dir = get_today_dir()
    gz_file = os.path.join(today_dir, "complete.json.gz")
    json_file = os.path.join(today_dir, "complete.json")
    return today_dir, gz_file, json_file


def download_and_extract(overwrite=False):
    today_dir, gz_file, json_file = get_file_paths()

    os.makedirs(today_dir, exist_ok=True)

    # ---------- DOWNLOAD ----------
    if overwrite or not os.path.exists(gz_file):
        print(f"⬇ Downloading instruments file for {today_dir} ...")

        r = requests.get(INSTRUMENT_URL, stream=True, timeout=30)
        r.raise_for_status()

        with open(gz_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    else:
        print(f"✅ Instruments file already exists for today: {gz_file}")

    # ---------- EXTRACT ----------
    if overwrite or not os.path.exists(json_file):
        print("📦 Extracting complete.json...")

        with gzip.open(gz_file, "rb") as f_in:
            with open(json_file, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
    else:
        print("✅ Extracted JSON already exists")


def load_and_filter():
    print("📊 Loading instruments data...")

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
        inst_type = item.get("instrument_type")
        asset_type = item.get("asset_type")
        underlying_type = item.get("underlying_type")

        # ✅ Strict Index Options Filter
        if (
            segment in ["NSE_FO", "BSE_FO"]
            # and inst_type in ["CE", "PE"]
            # and asset_type == "INDEX"
            # and underlying_type == "INDEX"
        ):

            if name == "NIFTY":
                nifty.append(item)
            elif name == "BANKNIFTY":
                banknifty.append(item)
            elif name == "SENSEX":
                sensex.append(item)
            else:
                continue   # ❌ Skip stock options

            key = item.get("instrument_key")
            symbol = item.get("trading_symbol")

            if key:
                by_key[key] = item

            if symbol:
                by_symbol[symbol.upper()] = item

    # Store filtered groups
    FILTERED_INSTRUMENTS["nifty"] = nifty
    FILTERED_INSTRUMENTS["banknifty"] = banknifty
    FILTERED_INSTRUMENTS["sensex"] = sensex

    # Combine only index options into ALL_INSTRUMENTS
    ALL_INSTRUMENTS.clear()
    ALL_INSTRUMENTS.extend(nifty)
    ALL_INSTRUMENTS.extend(banknifty)
    ALL_INSTRUMENTS.extend(sensex)

    INSTRUMENT_BY_KEY.clear()
    INSTRUMENT_BY_KEY.update(by_key)

    INSTRUMENT_BY_SYMBOL.clear()
    INSTRUMENT_BY_SYMBOL.update(by_symbol)

    print(f"✅ NIFTY Options     : {len(nifty)}")
    print(f"✅ BANKNIFTY Options : {len(banknifty)}")
    print(f"✅ SENSEX Options    : {len(sensex)}")
    print(f"✅ TOTAL INDEX OPTS : {len(ALL_INSTRUMENTS)}")


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

    print("💾 Filtered index option files saved")


def cleanup_raw_files():
    today_dir, gz_file, json_file = get_file_paths()

    if os.path.exists(gz_file):
        os.remove(gz_file)
        print("🗑 Removed complete.json.gz")

    if os.path.exists(json_file):
        # keep file but reformat JSON
        with open(json_file, encoding='utf-8') as f:
            data = json.load(f)

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

        print("🗑 Removed complete.json")


def bootstrap_instruments(overwrite=False):
    download_and_extract(overwrite=overwrite)
    load_and_filter()
    save_filtered_files()
    cleanup_raw_files()
