import aiohttp
import asyncio


async def _get_latest_option_candle_async(option_symbol):
    """
    Async internal candle fetcher
    """

    option_symbol = option_symbol.upper()

    # Detect exchange
    if option_symbol.startswith("SENSEX"):
        exchange = "BSE"
    else:
        exchange = "NSE"

    url = (
        f"https://groww.in/v1/api/stocks_fo_data/v1/charting_service/"
        f"delayed/chart/exchange/{exchange}/segment/FNO/{option_symbol}/daily"
    )

    params = {
        "intervalInMinutes": 1,
        "minimal": "true"
    }

    headers = {
        "accept": "application/json, text/plain, */*",
        "x-app-id": "growwWeb",
        "x-platform": "web"
    }

    timeout = aiohttp.ClientTimeout(total=5)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                return None

            data = await resp.json()
            candles = data.get("candles", [])

            if not candles:
                return None

            last_candle = candles[-1]

            return {
                "symbol": option_symbol,
                "timestamp": last_candle[0],
                "price": last_candle[1]
            }


# ----------------------------
# SYNC WRAPPER (for your engine)
# ----------------------------
def get_latest_option_candle(option_symbol):
    """
    Blocking version used by trading engine
    """
    try:
        return asyncio.run(_get_latest_option_candle_async(option_symbol))
    except RuntimeError:
        # If already inside event loop (FastAPI case)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get_latest_option_candle_async(option_symbol))


# # ---------------- TEST ----------------
# if __name__ == "__main__":
#     symbols = [
#         "NIFTY26JAN26300CE",
#         "NIFTY26JAN27000CE",
#         "SENSEX2612283300CE"
#     ]

#     results = asyncio.run(fetch_multiple(symbols))

#     for r in results:
#         print(r)
