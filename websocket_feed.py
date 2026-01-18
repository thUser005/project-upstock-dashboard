import upstox_client
import threading
from config import api_client
from live_ltp_manager import ltp_manager
from groww_feed import start_alternative_feed


class MarketFeed:
    def __init__(self):
        self.api_client = api_client
        
        # Initialize V3 Streamer
        self.streamer = upstox_client.MarketDataStreamerV3(self.api_client)
        self.connected = False
        
        self.market_status = {}

        # Link streamer
        ltp_manager.set_streamer(self.streamer)

        # Bind events
        self.streamer.on("open", self.on_open)
        self.streamer.on("message", self.on_message)
        self.streamer.on("error", self.on_error)
        self.streamer.on("close", self.on_close)

    def on_open(self):
        self.connected = True
        print("✅ Upstox Market Feed Connected")
        if ltp_manager.subscribed:
            tokens = list(ltp_manager.subscribed)
            print(f"📡 Resubscribing to existing tokens: {tokens}")
            self.streamer.subscribe(tokens, "ltpc")

    def on_message(self, message):

        if message.get("type") == "market_info":
            self.handle_market_info(message.get("marketInfo", {}))
            return

        if "feeds" in message:
            for instrument, data in message["feeds"].items():
                try:
                    if "ltpc" in data:
                        ltpc_data = data["ltpc"]

                        ltp = ltpc_data.get("ltp")
                        if not ltp or ltp == 0:
                            ltp = ltpc_data.get("cp")

                        if ltp:
                            ltp_manager.update_ltp(instrument, float(ltp))
                            return

                        # 🔁 Fallback using trading_symbol
                        print(f"⚠️ No LTP from Upstox for {instrument}, switching to Groww...")
                        symbol = ltp_manager.get_trading_symbol(instrument) or instrument.split("|")[-1]
                        price = start_alternative_feed(symbol)

                        if price:
                            ltp_manager.update_ltp(instrument, float(price))

                except Exception as e:
                    print(f"❌ Feed error for {instrument}: {e}")
                    print("🔁 Switching to Groww fallback...")
                    symbol = ltp_manager.get_trading_symbol(instrument) or instrument.split("|")[-1]
                    start_alternative_feed(symbol)

    def handle_market_info(self, info):
        self.market_status = info.get("segmentStatus", {})
        print("\n" + "="*40)
        print("📊 MARKET STATUS VALIDATION")
        print("="*40)

        for segment, status in self.market_status.items():
            indicator = "🔴" if "CLOSE" in status else "🟢"
            print(f"{indicator} {segment.ljust(10)} : {status}")

            if "CLOSE" in status:
                for instrument in ltp_manager.subscribed:
                    symbol = ltp_manager.get_trading_symbol(instrument) or instrument.split("|")[-1]
                    print(f"🔁 Market closed for {segment}, using Groww fallback for {symbol}")
                    start_alternative_feed(symbol)

        print("="*40 + "\n")

    def on_error(self, error):
        print(f"❌ Market Feed Error: {error}")
        print("🔁 Switching to Groww fallback feed for all active symbols...")

        for instrument in ltp_manager.subscribed:
            symbol = ltp_manager.get_trading_symbol(instrument) or instrument.split("|")[-1]
            start_alternative_feed(symbol)

    def on_close(self, close_status_code, close_msg):
        self.connected = False
        print(f"🔌 Market Feed Closed: {close_status_code} - {close_msg}")

        print("🔁 Switching to Groww fallback feed for all active symbols...")
        for instrument in ltp_manager.subscribed:
            symbol = ltp_manager.get_trading_symbol(instrument) or instrument.split("|")[-1]
            start_alternative_feed(symbol)

    def connect(self):
        try:
            print("🔗 Connecting to Upstox Market Feed...")
            self.streamer.connect()
        except Exception as e:
            print(f"❌ Connection attempt failed: {e}")
            print("🔁 Switching to Groww fallback feed for all active symbols...")

            for instrument in ltp_manager.subscribed:
                symbol = ltp_manager.get_trading_symbol(instrument) or instrument.split("|")[-1]
                start_alternative_feed(symbol)


# Singleton
market_feed = MarketFeed()


def start_market_feed():
    thread = threading.Thread(target=market_feed.connect, daemon=True)
    thread.start()
