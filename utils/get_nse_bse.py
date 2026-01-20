import requests

# ============================
# Groww API URLs
# ============================
NSE_URL = "https://groww.in/v1/api/charting_service/v2/chart/delayed/exchange/NSE/segment/CASH/NIFTY/daily?intervalInMinutes=1&minimal=true"
BSE_URL = "https://groww.in/v1/api/charting_service/v2/chart/delayed/exchange/BSE/segment/CASH/1/daily?intervalInMinutes=1&minimal=true"


# ============================
# Function 1 → NSE NIFTY Last Candle
# ============================
def get_nse_last_candle():
    response = requests.get(NSE_URL, timeout=10)
    response.raise_for_status()

    data = response.json()
    candles = data.get("candles", [])

    if not candles:
        return None

    return candles[-1]   # last candle


# ============================
# Function 2 → BSE Last Candle
# ============================
def get_bse_last_candle():
    response = requests.get(BSE_URL, timeout=10)
    response.raise_for_status()

    data = response.json()
    candles = data.get("candles", [])

    if not candles:
        return None

    return candles[-1]   # last candle


# # ============================
# # Example Usage
# # ============================
# if __name__ == "__main__":
#     nse_last = get_nse_last_candle()
#     bse_last = get_bse_last_candle()

#     print("NSE Last Candle:", nse_last)
#     print("BSE Last Candle:", bse_last)
