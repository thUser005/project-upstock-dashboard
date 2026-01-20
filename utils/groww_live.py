# groww_poller.py
import threading
import time
from groww_feed import start_alternative_feed
from live_ltp_manager import ltp_manager

class GrowwPoller:
    def __init__(self):
        self.running = False
        self.interval = 1.0  # seconds

    def start(self):
        if self.running:
            return
        self.running = True
        thread = threading.Thread(target=self.loop, daemon=True)
        thread.start()
        print("[GROWW] Fallback poller started")

    def loop(self):
        while self.running:
            for instrument in list(ltp_manager.subscribed):
                symbol = (
                    ltp_manager.get_trading_symbol(instrument)
                    or instrument.split("|")[-1]
                )

                try:
                    price = start_alternative_feed(symbol)
                    if price:
                        ltp_manager.update_ltp(instrument, float(price))
                except Exception as e:
                    print(f"[GROWW] Poll error {symbol}: {e}")

            time.sleep(self.interval)


groww_poller = GrowwPoller()
