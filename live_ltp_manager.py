import asyncio
from collections import defaultdict
import time


class LiveLTPManager:
    def __init__(self):
        self.clients = {}
        self.instrument_clients = defaultdict(set)
        self.subscribed = set()
        self.streamer = None
        self.loop = None
        self.instrument_to_symbol = {}

        # retry config
        self.max_retries = 3
        self.retry_delay = 1.5  # seconds

    # -------------------------
    # SETTERS
    # -------------------------
    def set_streamer(self, streamer):
        self.streamer = streamer

    def set_loop(self, loop):
        self.loop = loop

    # -------------------------
    # CLIENT HANDLING
    # -------------------------
    def add_client(self, ws, instrument, trading_symbol=None):
        self.clients[ws] = instrument
        self.instrument_clients[instrument].add(ws)

        if trading_symbol:
            self.instrument_to_symbol[instrument] = trading_symbol

        if instrument not in self.subscribed:
            self.subscribe(instrument)

    def remove_client(self, ws):
        instrument = self.clients.get(ws)
        if not instrument:
            return

        del self.clients[ws]
        self.instrument_clients[instrument].discard(ws)

        if not self.instrument_clients[instrument]:
            self.unsubscribe(instrument)

    # -------------------------
    # SUBSCRIBE WITH RETRY
    # -------------------------
    def subscribe(self, instrument):
        if instrument in self.subscribed:
            return

        self.subscribed.add(instrument)
        print(f"📡 Subscribing to Upstox for: {instrument}")

        if not self.streamer:
            print("⚠️ Streamer not ready, skipping subscription")
            return

        for attempt in range(1, self.max_retries + 1):
            try:
                self.streamer.subscribe([instrument], "ltpc")
                print(f"✅ Subscribed: {instrument}")
                return
            except Exception as e:
                print(f"❌ Subscribe attempt {attempt} failed: {e}")
                time.sleep(self.retry_delay)

        print(f"🚨 Failed to subscribe after {self.max_retries} tries → {instrument}")

    # -------------------------
    # UNSUBSCRIBE WITH RETRY
    # -------------------------
    def unsubscribe(self, instrument):
        if instrument not in self.subscribed:
            return

        self.subscribed.remove(instrument)
        print(f"🛑 Unsubscribing from Upstox for: {instrument}")

        if not self.streamer:
            return

        for attempt in range(1, self.max_retries + 1):
            try:
                self.streamer.unsubscribe([instrument])
                print(f"✅ Unsubscribed: {instrument}")
                return
            except Exception as e:
                print(f"❌ Unsubscribe attempt {attempt} failed: {e}")
                time.sleep(self.retry_delay)

        print(f"🚨 Failed to unsubscribe after {self.max_retries} tries → {instrument}")

    # -------------------------
    # UPDATE LTP SAFE
    # -------------------------
    def update_ltp(self, instrument, ltp):
        if not self.loop:
            print("⚠️ Event loop not set — cannot broadcast")
            return

        try:
            asyncio.run_coroutine_threadsafe(
                self.broadcast(instrument, ltp),
                self.loop
            )
        except Exception as e:
            print(f"❌ Broadcast scheduling failed: {e}")

    # -------------------------
    # BROADCAST TO WS CLIENTS
    # -------------------------
    async def broadcast(self, instrument, ltp):
        clients = self.instrument_clients.get(instrument, set())

        for ws in list(clients):
            try:
                await ws.send_json({
                    "instrument": instrument,
                    "ltp": ltp
                })
            except Exception as e:
                print(f"❌ WS send failed → removing client: {e}")
                self.remove_client(ws)

    # -------------------------
    # Groww fallback helper
    # -------------------------
    def get_trading_symbol(self, instrument):
        return self.instrument_to_symbol.get(instrument)


# ✅ Singleton instance
ltp_manager = LiveLTPManager()
