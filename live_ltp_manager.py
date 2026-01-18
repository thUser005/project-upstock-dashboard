import asyncio

class LiveLTPManager:
    def __init__(self):
        self.clients = []
        self.subscribed = set()
        self.streamer = None
        self.loop = None

        # Track only one active instrument at a time
        self.active_instrument = None  

        # Map instrument_key → trading_symbol (for Groww fallback)
        self.instrument_to_symbol = {}

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
    def add_client(self, ws):
        self.clients.append(ws)

    def remove_client(self, ws):
        if ws in self.clients:
            self.clients.remove(ws)

    # -------------------------
    # SUBSCRIBE (single active instrument)
    # -------------------------
    def subscribe(self, instrument, trading_symbol=None):

        # Store trading symbol for Groww fallback
        if trading_symbol:
            self.instrument_to_symbol[instrument] = trading_symbol

        # If a different instrument is already active → unsubscribe it
        if self.active_instrument and self.active_instrument != instrument:
            self.unsubscribe(self.active_instrument)

        # Subscribe new one
        if instrument not in self.subscribed:
            self.subscribed.add(instrument)
            self.active_instrument = instrument

            print(f"📡 Subscribing to Upstox for: {instrument}")

            if self.streamer:
                try:
                    self.streamer.subscribe([instrument], "ltpc")
                except Exception as e:
                    print(f"❌ Subscription Error: {e}")

    # -------------------------
    # UNSUBSCRIBE
    # -------------------------
    def unsubscribe(self, instrument):
        if instrument in self.subscribed:
            self.subscribed.remove(instrument)

            print(f"🛑 Unsubscribing from Upstox for: {instrument}")

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
    # Groww fallback helper
    # -------------------------
    def get_trading_symbol(self, instrument):
        return self.instrument_to_symbol.get(instrument)


# Singleton
ltp_manager = LiveLTPManager()
