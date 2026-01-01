import json,os
import upstox_client
from upstox_client.rest import ApiException
from dotenv import load_dotenv
load_dotenv()

keys_file = "keys.json"
# =====================================================
# AUTH
# =====================================================
def load_access_token():
    try:
        if os.path.exists(keys_file):
                
            with open(keys_file) as f:
                return json.load(f)["access_token"]
        return os.getenv("ACCESS_TOKEN",None)
    except Exception as e:
        raise RuntimeError(f"Access token error: {e}")


# =====================================================
# SMART GTT PLACE FUNCTION (DEFAULT STRATEGY ENABLED)
# =====================================================
def place_gtt_order(
    *,
    instrument,                 # NSE_EQ|INE669E01016
    symbol_key,                 # NSE_EQ:IDEA
    qty,
    transaction_type,           # BUY / SELL (MANDATORY)

    # ---------- OPTIONAL ----------
    product=None,               # default → Intraday
    entry_mode=None,
    entry_value=None,
    target_type=None,
    target_value=None,
    sl_type=None,
    sl_value=None,
    trigger_type=None
):
    """
    DEFAULT AUTO STRATEGY (when params not provided):

    PRODUCT  = INTRADAY (I)

    ENTRY    = OPEN + OPEN * 0.04
    TARGET   = ENTRY + ENTRY * 0.01
    SL       = ENTRY - ENTRY * 0.01
    """

    # =====================================================
    # DEFAULTS
    # =====================================================
    product = product or "I"

    entry_mode   = entry_mode   or "open_pct"
    entry_value  = entry_value  or 0.04

    target_type  = target_type  or "pct"
    target_value = target_value or 0.01

    sl_type      = sl_type      or "pct"
    sl_value     = sl_value     or 0.01

    # =====================================================
    # AUTH
    # =====================================================
    config = upstox_client.Configuration()
    config.access_token = load_access_token()
    client = upstox_client.ApiClient(config)

    order_api = upstox_client.OrderApiV3(client)
    quote_api = upstox_client.MarketQuoteV3Api(client)

    # =====================================================
    # FETCH LTP
    # =====================================================
    quote = quote_api.get_ltp(instrument_key=instrument).to_dict()
    ltp = float(quote["data"][symbol_key]["last_price"])

    # =====================================================
    # FETCH OPEN (SAFE)
    # =====================================================
    open_price = None
    try:
        ohlc = quote_api.get_market_quote_ohlc(
            instrument_key=instrument,
            interval="1d"
        ).to_dict()

        open_price = float(
            list(ohlc["data"].values())[0]["live_ohlc"]["open"]
        )
    except Exception:
        open_price = 0

    if not open_price or open_price <= 0:
        open_price = ltp  # fallback

    # =====================================================
    # ENTRY PRICE
    # =====================================================
    if entry_mode == "manual":
        entry_price = float(entry_value)

    elif entry_mode == "open_pct":
        entry_price = open_price * (
            1 + entry_value if transaction_type == "BUY"
            else 1 - entry_value
        )

    else:  # ltp_pct
        entry_price = ltp * (
            1 + entry_value if transaction_type == "BUY"
            else 1 - entry_value
        )

    entry_price = round(entry_price, 2)

    # =====================================================
    # TARGET
    # =====================================================
    if target_type == "pct":
        target_price = entry_price * (
            1 + target_value if transaction_type == "BUY"
            else 1 - target_value
        )
    else:
        target_price = float(target_value)

    # =====================================================
    # STOP LOSS
    # =====================================================
    if sl_type == "pct":
        sl_price = entry_price * (
            1 - sl_value if transaction_type == "BUY"
            else 1 + sl_value
        )
    else:
        sl_price = float(sl_value)

    target_price = round(target_price, 2)
    sl_price = round(sl_price, 2)

    # =====================================================
    # VALIDATION (CRITICAL)
    # =====================================================
    if transaction_type == "BUY":
        if not (sl_price < entry_price < target_price):
            raise ValueError("Invalid BUY prices (SL < ENTRY < TARGET)")
    else:
        if not (target_price < entry_price < sl_price):
            raise ValueError("Invalid SELL prices (TARGET < ENTRY < SL)")

    # =====================================================
    # TRIGGER TYPE
    # =====================================================
    trigger_type = trigger_type or (
        "ABOVE" if transaction_type == "BUY" else "BELOW"
    )

    # =====================================================
    # BUILD GTT RULES
    # =====================================================
    rules = [
        upstox_client.GttRule(
            strategy="ENTRY",
            trigger_type=trigger_type,
            trigger_price=entry_price
        ),
        upstox_client.GttRule(
            strategy="TARGET",
            trigger_type="IMMEDIATE",
            trigger_price=target_price
        ),
        upstox_client.GttRule(
            strategy="STOPLOSS",
            trigger_type="IMMEDIATE",
            trigger_price=sl_price
        )
    ]

    # =====================================================
    # PLACE GTT
    # =====================================================
    body = upstox_client.GttPlaceOrderRequest(
        instrument_token=instrument,
        transaction_type=transaction_type,
        product=product,
        quantity=int(qty),
        type="MULTIPLE",
        rules=rules
    )

    try:
        resp = order_api.place_gtt_order(body).to_dict()
        gtt_id = resp["data"]["gtt_order_ids"][-1]

        print("✅ GTT PLACED (AUTO MODE)")
        print(
            f"OPEN={open_price} | "
            f"ENTRY={entry_price} | "
            f"TARGET={target_price} | "
            f"SL={sl_price} | "
            f"QTY={qty}"
        )
        print("GTT ID:", gtt_id)

        return gtt_id

    except ApiException as e:
        print("❌ GTT PLACE FAILED")
        print(e.body)
        return None


# =====================================================
# CANCEL GTT
# =====================================================
def cancel_gtt_order(gtt_id):
    if not gtt_id:
        print("⚠️ GTT ID missing")
        return None

    config = upstox_client.Configuration()
    config.access_token = load_access_token()
    client = upstox_client.ApiClient(config)

    order_api = upstox_client.OrderApiV3(client)

    try:
        body = upstox_client.GttCancelOrderRequest(
            gtt_order_id=gtt_id
        )
        resp = order_api.cancel_gtt_order(body).to_dict()
        print("✅ GTT CANCELLED")
        return resp

    except ApiException as e:
        print("❌ CANCEL FAILED")
        print(e.body)
        return None
