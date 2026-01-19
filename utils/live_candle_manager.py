import asyncio
import time
from get_nse_bse import get_nse_last_candle, get_bse_last_candle

class CandleManager:
    def __init__(self):
        self.nse_clients = set()
        self.bse_clients = set()
        self.loop = None

    def set_loop(self, loop):
        self.loop = loop

    async def start_nse_stream(self):
        while True:
            try:
                candle = get_nse_last_candle()
                if candle:
                    ts, price = candle
                    payload = {
                        "exchange": "NSE",
                        "timestamp": ts,
                        "price": price
                    }

                    for ws in list(self.nse_clients):
                        await ws.send_json(payload)

            except Exception as e:
                print("❌ NSE candle error:", e)

            await asyncio.sleep(1)   # every second

    async def start_bse_stream(self):
        while True:
            try:
                candle = get_bse_last_candle()
                if candle:
                    ts, price = candle
                    payload = {
                        "exchange": "BSE",
                        "timestamp": ts,
                        "price": price
                    }

                    for ws in list(self.bse_clients):
                        await ws.send_json(payload)

            except Exception as e:
                print("❌ BSE candle error:", e)

            await asyncio.sleep(1)   # every second


candle_manager = CandleManager()
