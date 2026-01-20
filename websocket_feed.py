import threading
import time
from config import api_client
from live_ltp_manager import ltp_manager
from utils.groww_live import groww_poller


class MarketFeed:
    def __init__(self):
        self.api_client = api_client

        # Groww is PRIMARY and ONLY feed
        self.connected = True
        self.market_status = {}
        self.running = False

        # retry & health config
        self.max_restarts = 5
        self.restart_delay = 3  # seconds
        self.health_check_interval = 5

        # Link to ltp manager
        ltp_manager.set_market_feed(self)

    # -------------------------
    # START GROWW POLLER
    # -------------------------

    def start_groww_primary(self):
        print("🟢 Groww primary feed started (ONLY source)")

        try:
            groww_poller.start()
        except Exception as e:
            print(f"❌ Groww poller failed to start: {e}")
            self.connected = False
            self.restart_groww_poller()

    # -------------------------
    # HEALTH MONITOR
    # -------------------------

    def health_monitor(self):
        restart_count = 0

        while self.running:
            try:
                if not groww_poller.running:
                    print("⚠️ Groww poller stopped — attempting restart")

                    if restart_count >= self.max_restarts:
                        print("❌ Groww poller restart limit reached — feed marked DOWN")
                        self.connected = False
                        return

                    restart_count += 1
                    self.restart_groww_poller()
                else:
                    # feed healthy
                    self.connected = True

            except Exception as e:
                print(f"❌ Health monitor error: {e}")

            time.sleep(self.health_check_interval)

    # -------------------------
    # RESTART LOGIC
    # -------------------------

    def restart_groww_poller(self):
        try:
            print("🔁 Restarting Groww poller...")
            time.sleep(self.restart_delay)
            groww_poller.start()
            print("✅ Groww poller restarted successfully")
            self.connected = True
        except Exception as e:
            print(f"❌ Groww restart failed: {e}")
            self.connected = False

    # -------------------------
    # HEALTH CHECK API
    # -------------------------

    def is_feed_healthy(self):
        return self.running and groww_poller.running and self.connected

    # -------------------------
    # STOP SYSTEM
    # -------------------------

    def stop(self):
        print("🛑 Stopping Groww market feed...")
        self.running = False
        self.connected = False

    # -------------------------
    # START SYSTEM
    # -------------------------

    def start(self):
        if self.running:
            print("⚠️ Groww feed already running")
            return

        self.running = True
        self.connected = True

        # Start Groww poller thread
        feed_thread = threading.Thread(
            target=self.start_groww_primary, daemon=True
        )
        feed_thread.start()

        # Start health monitor thread
        health_thread = threading.Thread(
            target=self.health_monitor, daemon=True
        )
        health_thread.start()

        print("✅ Groww feed thread started")
        print("🩺 Groww health monitor started")


# Singleton
market_feed = MarketFeed()


def start_market_feed():
    market_feed.start()
