import asyncio
import aiohttp
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from services import fetch_mongo_data, fetch_live_ltp
from calculations import calculate_breakout, trade_levels
  
app = FastAPI(title="Options Dashboard")

templates = Jinja2Templates(directory="templates")

# =====================================================
# CONFIG
# =====================================================
MAX_LTP_RETRIES = 3
LTP_RETRY_DELAY = 0.8  # seconds
SESSION_TIMEOUT = aiohttp.ClientTimeout(total=10)


# =====================================================
# SAFE LTP FETCH WITH RETRIES
# =====================================================
async def safe_fetch_ltp(option_id: str, session: aiohttp.ClientSession):
    """
    Fetch live LTP with retry + exception safety
    (LOGIC UNCHANGED)
    """
    for attempt in range(1, MAX_LTP_RETRIES + 1):
        try:
            ltp = await fetch_live_ltp(option_id, session)
            if ltp is not None:
                return ltp
        except Exception:
            pass

        if attempt < MAX_LTP_RETRIES:
            await asyncio.sleep(LTP_RETRY_DELAY)

    return None


# =====================================================
# DASHBOARD ROUTE
# =====================================================
@app.get("/")
async def dashboard(request: Request):
    try:
        raw = await fetch_mongo_data()
    except Exception:
        # Mongo API failed
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "rows": [],
                "trade_date": None,   # ✅ added
                "error": "Failed to fetch Mongo options data"
            }
        )

    # 🔹 EXISTING DATA EXTRACTION (UNCHANGED)
    data = raw.get("data", {})
    trade_date = raw.get("trade_date")  # ✅ added
    rows = []

    async with aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as session:
        tasks = []

        for index_name, expiry_map in data.items():

            # 🔹 nearest 3 expiries only (UNCHANGED)
            try:
                expiries = sorted(expiry_map.keys())[:3]
            except Exception:
                continue

            for exp in expiries:
                symbols = expiry_map.get(exp, {}).get("symbols", [])

                for sym in symbols:
                    try:
                        if not sym.get("market_open"):
                            continue

                        open_price = sym.get("open")
                        y_high = sym.get("day_high")
                        y_low = sym.get("day_low")

                        if open_price is None or y_high is None or y_low is None:
                            continue

                        breakout = calculate_breakout(open_price, y_high, y_low)
                        entry, target, sl = trade_levels(breakout)

                        rows.append({
                            "index": index_name,
                            "expiry": exp,
                            "symbol": sym["id"],
                            "type": sym["option_type"],
                            "breakout": breakout,
                            "entry": entry,
                            "target": target,
                            "stoploss": sl,
                            "ltp": None
                        })

                        tasks.append(
                            safe_fetch_ltp(sym["id"], session)
                        )

                    except Exception:
                        # skip malformed symbol safely
                        continue

        # 🔁 fetch all LTPs concurrently (UNCHANGED)
        if tasks:
            ltps = await asyncio.gather(*tasks, return_exceptions=True)

            for row, ltp in zip(rows, ltps):
                if not isinstance(ltp, Exception):
                    row["ltp"] = ltp

    # =====================================================
    # TEMPLATE RESPONSE (ONLY ADD trade_date)
    # =====================================================
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "rows": rows,
            "trade_date": trade_date,  # ✅ added
            "error": None
        }
    )


@app.get("/api/ltp/{option_id}")
async def ltp_proxy(option_id: str):
    async with aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as session:
        ltp = await safe_fetch_ltp(option_id, session)
        return {"ltp": ltp}
