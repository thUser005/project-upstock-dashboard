from fastapi import FastAPI, Request, Form, WebSocket, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
import threading
import json
import re
import os
import sys
import time
import asyncio

import upstox_client
from upstox_client.rest import ApiException

from config import UPSTOX_ACCESS_TOKEN, MOBILE_NUM, api_client
from instruments import bootstrap_instruments, FILTERED_INSTRUMENTS, ALL_INSTRUMENTS
from token_validator import is_token_valid,update_access_token
from live_ltp_manager import ltp_manager
from websocket_feed import start_market_feed 

# ✅ Import GTT utility functions
from utils.gtt.place_gtt_order import place_gtt_order
from utils.gtt.modify_gtt_order import modify_gtt_order
from utils.gtt.cancel_gtt_order import cancel_gtt_order
from utils.gtt.get_gtt_order_details import get_gtt_order_details

from datetime import datetime
from config import gtt_collection

# -----------------------
# UPSTOX CONFIG (UNCHANGED)
# -----------------------
order_api = upstox_client.OrderApiV3(api_client)
user_api = upstox_client.UserApi(api_client)


# -----------------------
# FASTAPI INIT
# -----------------------
app = FastAPI(title="Upstox GTT Trading App")

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# -----------------------
# WEBSOCKET CLIENT SETS
# -----------------------
balance_clients = set()

# -----------------------
# UI PAGE
# -----------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/token", response_class=HTMLResponse)
async def token_page():
    with open("templates/token.html", "r", encoding="utf-8") as f:
        html = f.read()
    return html.replace("{{MOBILE_NUM}}", MOBILE_NUM)


@app.post("/save-token")
async def save_token(payload: dict = Body(...)):
    try:
        token = payload.get("access_token")

        if not token or len(token) < 50:
            return {"status": "error", "message": "Invalid access token"}
        update_access_token(token)
      
        def restart_app():
            time.sleep(2)
            os.execv(sys.executable, [sys.executable] + sys.argv)

        threading.Thread(target=restart_app, daemon=True).start()

        return {
            "status": "success",
            "message": "Access token updated. Server restarting..."
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Token save failed: {str(e)}"
        }


# -----------------------
# GTT ROUTES (USING UTIL FILES)
# -----------------------
@app.post("/place-gtt")
async def place_gtt(
    instrument_token: str = Form(...),
    quantity: int = Form(...),
    entry_price: float = Form(...),
    target_price: float = Form(...),
    stoploss_price: float = Form(...)
):
    try:
        result = place_gtt_order(
            instrument_token=instrument_token,
            quantity=quantity,
            entry_price=entry_price,
            target_price=target_price,
            stoploss_price=stoploss_price,
            transaction_type="BUY",
            product="D"
        )
        
        if result["status"] == "success":

            # ✅ Handle both response formats safely
            data_block = result["data"]

            if "gtt_order_ids" in data_block:
                gtt_id = data_block["gtt_order_ids"][0]

            elif "data" in data_block and "gtt_order_ids" in data_block["data"]:
                gtt_id = data_block["data"]["gtt_order_ids"][0]

            else:
                raise Exception("Invalid GTT response format")

            gtt_doc = {
                "gtt_order_id": gtt_id,
                "instrument_token": instrument_token,
                "quantity": quantity,
                "entry_price": entry_price,
                "target_price": target_price,
                "stoploss_price": stoploss_price,
                "status": "ACTIVE",
                "created_at": datetime.utcnow(),
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "broker_response": result
            }

            gtt_collection.insert_one(gtt_doc)

            return {
                "status": "success",
                "gtt_order_id": gtt_id,
                "message": "GTT Order placed successfully"
            }

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": f"GTT placement failed: {str(e)}"
        }


@app.post("/modify-gtt")
async def modify_gtt(
    gtt_order_id: str = Form(...),
    quantity: int = Form(...),
    entry_price: float = Form(None),
    target_price: float = Form(None),
    stoploss_price: float = Form(None),
    modify_entry: bool = Form(False),
    modify_target: bool = Form(False),
    modify_stoploss: bool = Form(False)
):
    try:
        result = modify_gtt_order(
            gtt_order_id=gtt_order_id,
            quantity=quantity,
            entry_price=entry_price,
            target_price=target_price,
            stoploss_price=stoploss_price,
            modify_entry=modify_entry,
            modify_target=modify_target,
            modify_stoploss=modify_stoploss
        )
        return result

    except Exception as e:
        return {
            "status": "error",
            "message": f"GTT modify failed: {str(e)}"
        }


@app.post("/cancel-gtt")
async def cancel_gtt_route(gtt_order_id: str = Form(...)):
    try:
        return cancel_gtt_order(gtt_order_id)

    except Exception as e:
        return {
            "status": "error",
            "message": f"GTT cancel failed: {str(e)}"
        }


@app.get("/gtt-details/{gtt_order_id}")
async def gtt_details(gtt_order_id: str):
    try:
        return get_gtt_order_details(gtt_order_id)

    except Exception as e:
        return {
            "status": "error",
            "message": f"GTT fetch failed: {str(e)}"
        }


# -----------------------
# INSTRUMENT ROUTES (UNCHANGED)
# -----------------------
@app.get("/instruments/all")
async def get_all_instruments():
    return {"status": "success", "count": len(ALL_INSTRUMENTS), "data": ALL_INSTRUMENTS}


@app.get("/instruments/{index_name}")
async def get_instruments(index_name: str):
    index_name = index_name.lower()
    if index_name not in FILTERED_INSTRUMENTS:
        return {"status": "error", "message": "Invalid index name"}

    return {
        "status": "success",
        "count": len(FILTERED_INSTRUMENTS[index_name]),
        "data": FILTERED_INSTRUMENTS[index_name]
    }


# -----------------------
# GET BALANCE (UNCHANGED)
# -----------------------
@app.get("/get-balance")
async def get_balance():
    try:
        valid, msg = is_token_valid()
        if not valid:
            return {"status": "error", "message": msg}

        response = user_api.get_user_fund_margin("2.0")
        return {"status": "success", "data": response.to_dict()}

    except ApiException as e:
        return {"status": "error", "message": str(e.body)}
    except Exception as e:
        return {"status": "error", "message": f"Balance fetch failed: {str(e)}"}

@app.websocket("/ws/balance")
async def websocket_balance(websocket: WebSocket):
    await websocket.accept()
    balance_clients.add(websocket)

    try:
        while True:
            await asyncio.sleep(10)  # send every 10 seconds

            valid, msg = is_token_valid()
            if not valid:
                await websocket.send_json({
                    "status": "error",
                    "message": msg
                })
                continue

            response = user_api.get_user_fund_margin("2.0").to_dict()
            
            avail_bal = response.get("data").get("equity").get("available_margin")
            await websocket.send_json({
                "status": "success",
                "balance": avail_bal
            })

    except Exception as e:
        print("Balance WS closed:", e)

    finally:
        balance_clients.remove(websocket)


# -----------------------
# LIVE LTP WEBSOCKET (UNCHANGED)
# -----------------------
@app.websocket("/ws/ltp")
async def websocket_ltp(websocket: WebSocket):
    await websocket.accept()

    try:
        # First message must contain subscription info
        data = await websocket.receive_json()

        instrument = data.get("instrument")
        trading_symbol = data.get("symbol")

        if not instrument:
            await websocket.close()
            return

        print(f"🔗 LTP WS Client subscribed to: {instrument}")

        # Register this client with its instrument
        ltp_manager.add_client(websocket, instrument, trading_symbol)

        # Keep connection alive
        while True:
            await websocket.receive_text()

    except Exception as e:
        print("❌ LTP WS disconnected:", e)

    finally:
        ltp_manager.remove_client(websocket)


# -----------------------
# LIVE FEED START
# -----------------------
@app.get("/start-live-feed")
async def start_live_feed_route():
    valid, msg = is_token_valid()
    if not valid:
        return {"status": "error", "message": msg}

    try:
        thread = threading.Thread(target=start_market_feed, daemon=True)
        thread.start()
        return {"status": "success", "message": "Live Market Feed Started Successfully"}

    except Exception as e:
        return {"status": "error", "message": f"Feed start failed: {str(e)}"}


# -----------------------
# STARTUP EVENT (UNCHANGED)
# -----------------------
@app.on_event("startup")
async def startup_event():
    bootstrap_instruments()

    loop = asyncio.get_running_loop()
    ltp_manager.set_loop(loop)

    start_market_feed()
    print("🚀 Application and Market Feed initializing...")
