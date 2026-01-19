import upstox_client
import threading
import time
from config import api_client
from live_ltp_manager import ltp_manager
from groww_feed import start_alternative_feed


class MarketFeed:
    def __init__(self):
        self.api_client = api_client
        self.streamer = upstox_client.MarketDataStreamerV3(self.api_client)
        self.connected = False
        self.market_status = {}

        # retry config
        self.max_retries = 3
        self.retry_delay = 2  # seconds

        ltp_manager.set_streamer(self.streamer)

        self.streamer.on("open", self.on_open)
        self.streamer.on("message", self.on_message)
        self.streamer.on("error", self.on_error)
        self.streamer.on("close", self.on_close)

    # -------------------------
    # CONNECTION HANDLING
    # -------------------------
    def connect(self):
        print("[MARKET] Connecting to Upstox feed...")

        for attempt in range(1, self.max_retries + 1):
            try:
                self.streamer.connect()
                return
            except Exception as e:
                print(f"[MARKET] Connection attempt {attempt} failed: {e}")
                time.sleep(self.retry_delay * attempt)

        print("[MARKET] Upstox feed unreachable → switching to Groww fallback")
        self.activate_groww_fallback()

    # -------------------------
    # FEED EVENTS
    # -------------------------
    def on_open(self):
        self.connected = True
        print("[MARKET] Upstox feed connected")

        if ltp_manager.subscribed:
            tokens = list(ltp_manager.subscribed)
            print(f"[MARKET] Resubscribing {len(tokens)} instruments")

            try:
                self.streamer.subscribe(tokens, "ltpc")
            except Exception as e:
                print(f"[MARKET] Resubscribe failed: {e}")
                self.activate_groww_fallback()

    def on_message(self, message):
        try:
            if message.get("type") == "market_info":
                self.handle_market_info(message.get("marketInfo", {}))
                return

            if "feeds" not in message:
                return

            for instrument, data in message["feeds"].items():
                try:
                    if "ltpc" in data:
                        ltpc_data = data["ltpc"]
                        ltp = ltpc_data.get("ltp") or ltpc_data.get("cp")

                        if ltp:
                            ltp_manager.update_ltp(instrument, float(ltp))
                            continue

                    # fallback price
                    symbol = (
                        ltp_manager.get_trading_symbol(instrument)
                        or instrument.split("|")[-1]
                    )

                    price = start_alternative_feed(symbol)
                    if price:
                        ltp_manager.update_ltp(instrument, float(price))

                except Exception as e:
                    print(f"[MARKET] Feed parse error: {e}")
                    symbol = (
                        ltp_manager.get_trading_symbol(instrument)
                        or instrument.split("|")[-1]
                    )
                    start_alternative_feed(symbol)

        except Exception as e:
            print(f"[MARKET] Message handler crashed: {e}")
            self.activate_groww_fallback()

    def on_error(self, error):
        print(f"[MARKET] Feed error → {error}")
        self.connected = False
        self.activate_groww_fallback()

    def on_close(self, close_status_code, close_msg):
        print(f"[MARKET] Feed closed → {close_msg}")
        self.connected = False
        self.reconnect()

    # -------------------------
    # MARKET INFO
    # -------------------------
    def handle_market_info(self, info):
        self.market_status = info.get("segmentStatus", {})

        open_markets = [k for k, v in self.market_status.items() if "OPEN" in v]
        default_market = open_markets[0] if open_markets else "N/A"

        print(f"[MARKET] Default Market : {default_market}")
        print(f"[MARKET] Open Markets   : {', '.join(open_markets)}")

        if not open_markets:
            self.activate_groww_fallback()

    # -------------------------
    # FALLBACK HANDLER
    # -------------------------
    def activate_groww_fallback(self):
        print("[MARKET] Activating Groww fallback feed")

        for instrument in ltp_manager.subscribed:
            try:
                symbol = (
                    ltp_manager.get_trading_symbol(instrument)
                    or instrument.split("|")[-1]
                )
                start_alternative_feed(symbol)
            except Exception as e:
                print(f"[MARKET] Groww fallback failed for {instrument}: {e}")

    # -------------------------
    # AUTO RECONNECT
    # -------------------------
    def reconnect(self):
        print("[MARKET] Attempting reconnect...")
        time.sleep(2)
        self.connect()


# -------------------------
# BOOTSTRAP
# -------------------------
market_feed = MarketFeed()


def start_market_feed():
    thread = threading.Thread(target=market_feed.connect, daemon=True)
    thread.start()
