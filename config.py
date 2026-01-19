import os
import requests
from dotenv import load_dotenv
import upstox_client
from pymongo import MongoClient
from token_loader import fetch_access_token_from_api

load_dotenv()

# -----------------------------
# 🔐 Token Validation Helper
# -----------------------------
def validate_upstox_token(token: str):
    url = "https://api.upstox.com/v2/user/get-funds-and-margin"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    try:
        print("🔍 Validating Upstox access token...")

        r = requests.get(url, headers=headers, timeout=10)

        # ✅ Token valid
        if r.status_code == 200:
            print("✅ Token validation successful")
            return True

        # ⚠ Maintenance window (12 AM – 5:30 AM IST)
        if r.status_code == 423:
            print("⚠ Upstox Funds API is locked (maintenance window)")
            print("ℹ Upstox service hours: 5:30 AM – 12:00 AM IST")
            print("ℹ Assuming token is valid for now")
            return True

        # ❌ Token expired or invalid
        if r.status_code == 401:
            print("❌ Token invalid or expired")
            print("➡ Please regenerate token from Upstox dashboard")
            return False

        # 🚫 Rate limit exceeded
        if r.status_code == 429:
            print("🚫 Rate limit exceeded (Too many requests)")
            print("➡ Please slow down API calls")
            return False

        # 🔒 Access forbidden
        if r.status_code == 403:
            print("🔒 Access forbidden — account may be restricted")
            print("➡ Check Upstox account status")
            return False

        # 🔥 Server error
        if r.status_code >= 500:
            print("🔥 Upstox server error")
            print("➡ Try again later")
            return False

        # ⚠ Unexpected response
        print("⚠ Unexpected token validation response")
        print("Status Code:", r.status_code)
        print("Response:", r.text)
        return False

    except requests.exceptions.Timeout:
        print("⏱ Token validation timed out")
        return False

    except requests.exceptions.ConnectionError:
        print("🌐 Network error — cannot reach Upstox servers")
        return False

    except Exception as e:
        print("❌ Token validation failed with exception:", str(e))
        return False


# -----------------------------
# 🔐 Load + Validate Token
# -----------------------------
UPSTOX_ACCESS_TOKEN = str(fetch_access_token_from_api())

# ✅ Validate token at startup
if not validate_upstox_token(UPSTOX_ACCESS_TOKEN):
    print("⚠ Access token expired. Fetching fresh token from API...")

    UPSTOX_ACCESS_TOKEN = str(fetch_access_token_from_api())

    if not validate_upstox_token(UPSTOX_ACCESS_TOKEN):
        raise RuntimeError("❌ Could not fetch valid Upstox token from API. Please update token manually.")

print("✅ Upstox token loaded and validated successfully")


# -----------------------------
# 🔧 Upstox Client Setup (UNCHANGED)
# -----------------------------
configuration = upstox_client.Configuration()
configuration.access_token = str(UPSTOX_ACCESS_TOKEN)
api_client = upstox_client.ApiClient(configuration)


# -----------------------------
# 🔧 ENV CONFIG (UNCHANGED)
# -----------------------------
MOBILE_NUM = os.getenv("MOBILE_NUM")
SERIAL_NUM = os.getenv("SERIAL_NUM")
MSG_API_URL = os.getenv("MSG_API_URL")


# -----------------------------
# 🗄 MongoDB Setup (UNCHANGED)
# -----------------------------
MONGO_URL = os.getenv("MONGO_URL")
mongo_client = MongoClient(MONGO_URL)
mongo_db = mongo_client["gtt_trading"]
gtt_collection = mongo_db["gtt_orders"]

# Collection for live subscribed instruments
subscribed_collection = mongo_db["subscribed_symbols"]
