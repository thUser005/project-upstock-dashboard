import json
import upstox_client
from upstox_client.rest import ApiException


# =====================================================
# CONFIG
# =====================================================
def load_access_token():
    with open("keys.json") as f:
        return json.load(f)["access_token"]


# =====================================================
# MODIFY GTT ORDER (OPEN BASED, SAFE)
# =====================================================
def modify_gtt_order_open_based(
    INSTRUMENT,
    SYMBOL_KEY,          # kept for compatibility (not used here)
    GTT_ORDER_ID,
    entry_pct=0.04,
    target_pct=0.02,
    sl_pct=0.02,
    qty=None
):
    """
    ENTRY  = OPEN + OPEN * entry_pct
    TARGET = ENTRY + ENTRY * target_pct
    SL     = ENTRY - ENTRY * sl_pct

    qty=None → uses existing GTT quantity
    """

    # ---------- AUTH ----------
    config = upstox_client.Configuration()
    config.access_token = load_access_token()
    client = upstox_client.ApiClient(config)

    order_api = upstox_client.OrderApiV3(client)
    quote_api = upstox_client.MarketQuoteV3Api(client)

    # =====================================================
    # 1. FETCH GTT DETAILS
    # =====================================================
    try:
        gtt_resp = order_api.get_gtt_order_details(
            gtt_order_id=GTT_ORDER_ID
        ).to_dict()

        if gtt_resp.get("status") != "success":
            print("❌ GTT API FAILED:", gtt_resp)
            return None

        gtt_data = gtt_resp["data"][0]

        rules_state = gtt_data["rules"]
        existing_qty = gtt_data["quantity"]
        trading_symbol = gtt_data["trading_symbol"]   # IDEA
        exchange = gtt_data["exchange"]               # NSE_EQ

        print("GTT ID:", gtt_data["gtt_order_id"])
        print("QTY:", existing_qty)

    except Exception as e:
        print("❌ FAILED TO FETCH GTT DETAILS")
        print(e)
        return None

    # =====================================================
    # 2. CHECK IF GTT IS COMPLETED
    # =====================================================
    gtt_completed = any(
        r["status"] in ("COMPLETED", "EXECUTED", "CANCELLED")
        for r in rules_state
    )

    if gtt_completed:
        print("⛔ GTT already completed → cannot modify")
        return None

    final_qty = qty if qty is not None else existing_qty

    entry_triggered = any(
        r["strategy"] == "ENTRY" and r["status"] == "TRIGGERED"
        for r in rules_state
    )

    # =====================================================
    # 3. FETCH OPEN PRICE (CORRECT WAY)
    # =====================================================
    try:
        ohlc_resp = quote_api.get_market_quote_ohlc(
            instrument_key=INSTRUMENT,
            interval="1d"
        ).to_dict()

        ohlc_key = f"{exchange}:{trading_symbol}"

        open_price = float(
            ohlc_resp["data"][ohlc_key]["live_ohlc"]["open"]
        )

        print(f"OPEN PRICE = {open_price}")

    except Exception as e:
        print("❌ OPEN PRICE ERROR")
        print("Available keys:", ohlc_resp.get("data", {}).keys())
        print(e)
        return None

    # =====================================================
    # 4. PRICE CALCULATION
    # =====================================================
    entry_price = round(open_price * (1 + entry_pct), 2)
    target_price = round(entry_price * (1 + target_pct), 2)
    sl_price = round(entry_price * (1 - sl_pct), 2)

    print(
        f"CALC → ENTRY={entry_price} | "
        f"TARGET={target_price} | "
        f"SL={sl_price} | "
        f"QTY={final_qty}"
    )

    # =====================================================
    # 5. BUILD RULES
    # =====================================================
    rules = []

    if not entry_triggered:
        rules.append(
            upstox_client.GttRule(
                strategy="ENTRY",
                trigger_type="ABOVE",
                trigger_price=entry_price
            )
        )
    else:
        print("⚠️ ENTRY already triggered → skipping ENTRY")

    rules.extend([
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
    ])

    # =====================================================
    # 6. MODIFY GTT
    # =====================================================
    try:
        body = upstox_client.GttModifyOrderRequest(
            type="MULTIPLE",
            gtt_order_id=GTT_ORDER_ID,
            quantity=final_qty,
            rules=rules
        )

        resp = order_api.modify_gtt_order(body=body).to_dict()
        print("✅ GTT MODIFIED SUCCESSFULLY")
        return resp

    except ApiException as e:
        print("❌ MODIFY FAILED")
        print(e.body)
        return None


# # =====================================================
# # CALL
# # =====================================================
# modify_gtt_order_open_based(
#     INSTRUMENT="NSE_EQ|INE669E01016",
#     SYMBOL_KEY="INE669E01016",
#     GTT_ORDER_ID="GTT-C26010100214211",
#     entry_pct=0.04,
#     target_pct=0.02,
#     sl_pct=0.02,
#     qty=4
# )
