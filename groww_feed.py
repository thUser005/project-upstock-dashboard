from utils.get_index_id import search_groww_option
from utils.latest_candle import get_latest_option_candle


def start_alternative_feed(trading_symbol):
    """
    trading_symbol example:
    NIFTY26JAN26300CE
    """

    try:
        # print(f"🔁 Switching to Groww fallback feed for {trading_symbol}")

        # Search Groww option
        possible_options = search_groww_option(trading_symbol)

        if not possible_options:
            print("❌ Groww: No matching option found")
            return None

        option_id = possible_options[0].get("id")

        if not option_id:
            print("❌ Groww: Option ID not found")
            return None

        # Fetch latest candle
        candle = get_latest_option_candle(option_id)
        if candle:
            # print(f"📊 Groww Fallback Price: {option_id} @ {candle['price']}")
            return candle["price"]

        print("❌ Groww: Candle data not available")

    except Exception as e:
        print(f"❌ Groww fallback error: {e}")

    return None
