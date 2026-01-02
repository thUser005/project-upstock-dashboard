import os
import secrets
import traceback
from datetime import datetime, timezone, timedelta

from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, ReturnDocument
from dotenv import load_dotenv
import sys
import threading
import time as _time

from gtt_order import place_gtt_order, cancel_gtt_order

# -----------------------------------------------------
# LOAD ENV
# -----------------------------------------------------
load_dotenv()

# -----------------------------------------------------
# FLASK CONFIG
# -----------------------------------------------------
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

UTC = timezone.utc
IST = timezone(timedelta(hours=5, minutes=30))

MAX_TRADES_PER_DAY = 2

# -----------------------------------------------------
# MONGODB CONFIG
# -----------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB", "upstox_gtt")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI env variable not set")

mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]

req_col = db["gtt_requests"]
res_col = db["gtt_responses"]
err_col = db["gtt_errors"]
counter_col = db["trade_counters"]

# -----------------------------------------------------
# HELPERS
# -----------------------------------------------------
def new_request_id() -> str:
    """
    Vercel-safe unique request ID.
    Replaces uuid.uuid4() completely.
    """
    return secrets.token_hex(16)  # 32-char hex string
def shutdown_server():
    """
    Gracefully stop Flask server.
    Works in dev / direct run.
    In Docker / Railway → process exits.
    """
    func = request.environ.get("werkzeug.server.shutdown")
    if func:
        func()
    else:
        # fallback – force exit
        os._exit(0)


def today_key():
    return datetime.now(IST).strftime("%Y-%m-%d")


def get_trade_count():
    doc = counter_col.find_one({"_id": today_key()})
    return doc["count"] if doc else 0


def increment_trade_count():
    return counter_col.find_one_and_update(
        {"_id": today_key()},
        {
            "$inc": {"count": 1},
            "$set": {"updated_at": datetime.now(UTC)}
        },
        upsert=True,
        return_document=ReturnDocument.AFTER
    )


def log_request(request_id, endpoint, payload):
    req_col.insert_one({
        "request_id": request_id,
        "endpoint": endpoint,
        "payload": payload,
        "ts": datetime.now(UTC)
    })


def log_response(request_id, endpoint, response):
    res_col.insert_one({
        "request_id": request_id,
        "endpoint": endpoint,
        "response": response,
        "ts": datetime.now(UTC)
    })


def log_error(request_id, endpoint, payload, err):
    err_col.insert_one({
        "request_id": request_id,
        "endpoint": endpoint,
        "payload": payload,
        "error": str(err),
        "traceback": traceback.format_exc(),
        "ts": datetime.now(UTC)
    })


def get_request_data():
    return request.get_json(silent=True) or request.args.to_dict()


# -----------------------------------------------------
# ROOT
# -----------------------------------------------------
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "running",
        "message": "Server started successfully",
        "service": "Upstox GTT Engine"
    })


# -----------------------------------------------------
# HEALTH
# -----------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "Upstox GTT Engine",
        "today_trade_count": get_trade_count()
    })


# =====================================================
# PLACE GTT (POST + GET)
# =====================================================
@app.route("/api/gtt/place", methods=["POST", "GET"])
def api_place_gtt():
    request_id = new_request_id()
    data = get_request_data()

    required = ["instrument", "symbol_key", "qty", "transaction_type"]
    missing = [k for k in required if k not in data]

    if missing:
        return jsonify({
            "success": False,
            "error": f"Missing fields: {missing}",
            "request_id": request_id
        }), 400

    data["qty"] = int(data["qty"])
    data["force"] = str(data.get("force", "false")).lower() == "true"

    log_request(request_id, "place_gtt", data)

    if not data["force"] and get_trade_count() >= MAX_TRADES_PER_DAY:
        return jsonify({
            "success": False,
            "error": "Daily trade limit reached",
            "trade_count": get_trade_count(),
            "max_allowed": MAX_TRADES_PER_DAY,
            "request_id": request_id
        }), 403

    try:
        kwargs = {
            "instrument": data["instrument"],
            "symbol_key": data["symbol_key"],
            "qty": data["qty"],
            "transaction_type": data["transaction_type"]
        }

        optional_keys = [
            "product",
            "entry_mode", "entry_value",
            "target_type", "target_value",
            "sl_type", "sl_value",
            "trigger_type"
        ]

        for k in optional_keys:
            if k in data:
                kwargs[k] = float(data[k]) if "value" in k else data[k]

        gtt_id = place_gtt_order(**kwargs)
        if not gtt_id:
            raise RuntimeError("GTT placement failed")

        counter_doc = increment_trade_count()

        resp = {
            "success": True,
            "gtt_id": gtt_id,
            "status": "ACTIVE",
            "trade_count": counter_doc["count"],
            "request_id": request_id
        }

        log_response(request_id, "place_gtt", resp)
        return jsonify(resp)

    except Exception as e:
        err_msg = repr(e)
        log_error(request_id, "place_gtt", data, err_msg)

        return jsonify({
            "success": False,
            "error": "GTT placement failed",
            "details": err_msg,
            "request_id": request_id
        }), 500



# =====================================================
# CANCEL GTT
# =====================================================
@app.route("/api/gtt/cancel", methods=["POST", "GET"])
def api_cancel_gtt():
    request_id = new_request_id()
    data = get_request_data()

    if "gtt_id" not in data:
        return jsonify({
            "success": False,
            "error": "gtt_id required",
            "request_id": request_id
        }), 400

    log_request(request_id, "cancel_gtt", data)

    try:
        cancel_gtt_order(data["gtt_id"])

        res_col.update_one(
            {
                "endpoint": "place_gtt",
                "response.gtt_id": data["gtt_id"],
                "response.status": {"$ne": "CANCELLED"}
            },
            {
                "$set": {
                    "response.status": "CANCELLED",
                    "response.cancelled_at": datetime.now(UTC)
                }
            }
        )

        resp = {
            "success": True,
            "gtt_id": data["gtt_id"],
            "status": "CANCELLED",
            "request_id": request_id
        }

        log_response(request_id, "cancel_gtt", resp)
        return jsonify(resp)

    except Exception as e:
        log_error(request_id, "cancel_gtt", data, e)
        return jsonify({
            "success": False,
            "error": str(e),
            "request_id": request_id
        }), 500


# =====================================================
# LIST GTT ORDERS
# =====================================================
@app.route("/api/gtt/orders", methods=["GET"])
def api_list_gtt_orders():
    status = request.args.get("status")

    query = {
        "endpoint": "place_gtt",
        "response.success": True
    }

    if status:
        query["response.status"] = status.upper()

    try:
        cursor = res_col.find(
            query,
            {
                "_id": 0,
                "response.gtt_id": 1,
                "response.status": 1,
                "response.cancelled_at": 1,
                "request_id": 1,
                "ts": 1
            }
        ).sort("ts", -1)

        orders = []
        for doc in cursor:
            orders.append({
                "gtt_id": doc["response"]["gtt_id"],
                "status": doc["response"].get("status", "ACTIVE"),
                "placed_at": doc["ts"].isoformat(),
                "cancelled_at": (
                    doc["response"].get("cancelled_at").isoformat()
                    if doc["response"].get("cancelled_at") else None
                ),
                "request_id": doc["request_id"]
            })

        return jsonify({
            "success": True,
            "count": len(orders),
            "orders": orders
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# =====================================================
# STOP SERVER (ADMIN / EMERGENCY)
# =====================================================
@app.route("/api/server/stop", methods=["POST", "GET"])
def stop_server():
    request_id = new_request_id()
    data = get_request_data()

    force = str(data.get("force", "false")).lower() == "true"

    log_request(
        request_id,
        "stop_server",
        {"force": force}
    )

    # optional safety check
    if not force:
        return jsonify({
            "success": False,
            "error": "Set force=true to stop server",
            "request_id": request_id
        }), 400

    def delayed_shutdown():
        _time.sleep(1)
        shutdown_server()

    # shutdown in background so response is sent
    threading.Thread(target=delayed_shutdown).start()

    resp = {
        "success": True,
        "message": "Server shutting down",
        "request_id": request_id
    }

    log_response(request_id, "stop_server", resp)
    return jsonify(resp)

# =====================================================
# CANCEL ALL ACTIVE GTT
# =====================================================
@app.route("/api/gtt/cancel-all", methods=["POST", "GET"])
def api_cancel_all_gtt():
    request_id = new_request_id()
    cancelled = []
    failed = []

    try:
        cursor = res_col.find(
            {
                "endpoint": "place_gtt",
                "response.success": True,
                "response.status": {"$ne": "CANCELLED"}
            },
            {
                "_id": 0,
                "response.gtt_id": 1,
                "request_id": 1
            }
        )

        active_orders = list(cursor)

        if not active_orders:
            return jsonify({
                "success": True,
                "message": "No active GTT orders found",
                "cancelled": [],
                "failed": [],
                "request_id": request_id
            })

        for order in active_orders:
            gtt_id = order["response"]["gtt_id"]

            try:
                cancel_gtt_order(gtt_id)

                res_col.update_one(
                    {
                        "endpoint": "place_gtt",
                        "response.gtt_id": gtt_id,
                        "response.status": {"$ne": "CANCELLED"}
                    },
                    {
                        "$set": {
                            "response.status": "CANCELLED",
                            "response.cancelled_at": datetime.now(UTC)
                        }
                    }
                )

                cancelled.append(gtt_id)

            except Exception as e:
                failed.append({
                    "gtt_id": gtt_id,
                    "error": str(e)
                })

        return jsonify({
            "success": True,
            "total_active": len(active_orders),
            "cancelled_count": len(cancelled),
            "failed_count": len(failed),
            "cancelled": cancelled,
            "failed": failed,
            "request_id": request_id
        })

    except Exception as e:
        log_error(request_id, "cancel_all_gtt", {}, e)
        return jsonify({
            "success": False,
            "error": str(e),
            "request_id": request_id
        }), 500

