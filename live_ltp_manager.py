import asyncio

class LiveLTPManager:
    def __init__(self):
        self.clients = []
        self.subscribed = set()
        self.streamer = None
        self.loop = None

        # Track only one active instrument at a time
        self.active_instrument = None  

        # Map instrument_key → trading_symbol (for Groww primary)
        self.instrument_to_symbol = {}

        # Reference to MarketFeed (for connection status)
        self.market_feed = None   # 👈 safe addition (already in your code)

    # -------------------------
    # SETTERS
    # -------------------------
    def set_streamer(self, streamer):
        self.streamer = streamer

    def set_loop(self, loop):
        self.loop = loop

    # 👇 MarketFeed connector
    def set_market_feed(self, market_feed):
        self.market_feed = market_feed

    # -------------------------
    # CLIENT HANDLING
    # -------------------------
    def add_client(self, ws):
        self.clients.append(ws)

    def remove_client(self, ws):
        if ws in self.clients:
            self.clients.remove(ws)

    # -------------------------
    # SUBSCRIBE (single active instrument)
    # -------------------------
    def subscribe(self, instrument, trading_symbol=None):

        # Store trading symbol for Groww PRIMARY
        if trading_symbol:
            self.instrument_to_symbol[instrument] = trading_symbol

        # If a different instrument is already active → unsubscribe it
        if self.active_instrument and self.active_instrument != instrument:
            self.unsubscribe(self.active_instrument)

        # Subscribe new one
        if instrument not in self.subscribed:
            self.subscribed.add(instrument)
            self.active_instrument = instrument

            # Groww is PRIMARY
            print(f"🟢 Subscribed to Groww primary for: {trading_symbol or instrument}")

            # ⚠ Do NOT touch Upstox here
            # Upstox is fallback only and will be activated by MarketFeed

    # -------------------------
    # UNSUBSCRIBE
    # -------------------------
    def unsubscribe(self, instrument):
        if instrument in self.subscribed:
            self.subscribed.remove(instrument)

            print(f"🛑 Unsubscribing: {instrument}")

            # Only unsubscribe from Upstox if fallback is active
            if self.market_feed and self.market_feed.upstox_connected:
                if self.streamer:
                    try:
                        self.streamer.unsubscribe([instrument])
                    except Exception as e:
                        print(f"❌ Unsubscribe Error: {e}")

        if self.active_instrument == instrument:
            self.active_instrument = None

    # -------------------------
    # UPDATE LTP (only active instrument)
    # -------------------------
    def update_ltp(self, instrument, ltp):

        # Only broadcast active instrument
        if instrument != self.active_instrument:
            return

        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.broadcast(instrument, ltp),
                self.loop
            )

    # -------------------------
    # BROADCAST TO WS CLIENTS
    # -------------------------
    async def broadcast(self, instrument, ltp):
        for ws in self.clients:
            try:
                await ws.send_json({
                    "instrument": instrument,
                    "ltp": ltp
                })
            except:
                pass

    # -------------------------
    # Groww primary helper
    # -------------------------
    def get_trading_symbol(self, instrument):
        return self.instrument_to_symbol.get(instrument)


# Singleton
ltp_manager = LiveLTPManager()
