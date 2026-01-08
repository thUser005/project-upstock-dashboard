import aiohttp
import asyncio

MONGO_API = "https://mongo-api-fetch.vercel.app/api/options/today"
LIVE_API = "https://get-option-latest.up.railway.app/option/live"

TIMEOUT = aiohttp.ClientTimeout(total=8)


async def fetch_mongo_data():
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.get(MONGO_API) as resp:
            return await resp.json()


async def fetch_live_ltp(option_id: str, session: aiohttp.ClientSession):
    try:
        async with session.get(f"{LIVE_API}/{option_id}") as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("ltp") or data.get("last_price")
    except Exception:
        return None
