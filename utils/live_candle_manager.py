import asyncio
import time
from utils.get_nse_bse import get_nse_last_candle, get_bse_last_candle


class CandleManager:
    def __init__(self):
        self.nse_clients = set()
        self.bse_clients = set()
        self.loop = None

    def set_loop(self, loop):
        self.loop = loop

    # ----------------------------
    # SAFE SEND HELPER
    # ----------------------------
    async def safe_send(self, clients, payload):
        dead_clients = set()

        for ws in list(clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead_clients.add(ws)

        # cleanup closed sockets silently
        for ws in dead_clients:
            clients.discard(ws)

    # ----------------------------
    # NSE STREAM
    # ----------------------------
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

                    await self.safe_send(self.nse_clients, payload)

            except Exception as e:
                # only log real errors (not disconnect noise)
                print("❌ NSE candle error:", e)

            await asyncio.sleep(1)   # every second

    # ----------------------------
    # BSE STREAM
    # ----------------------------
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

                    await self.safe_send(self.bse_clients, payload)

            except Exception as e:
                print("❌ BSE candle error:", e)

            await asyncio.sleep(1)   # every second


candle_manager = CandleManager()
