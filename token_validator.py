import requests
from config import UPSTOX_ACCESS_TOKEN, SERIAL_NUM, MSG_API_URL


def update_access_token(access_token: str):
    """
    Updates access token in MongoDB via Vercel API using serial number
    Returns API response dict on success, None on failure
    """

    if not access_token:
        raise ValueError("❌ access_token cannot be empty")

    url = f"{MSG_API_URL}/update/{SERIAL_NUM}"

    payload = {
        "message_content": access_token
    }

    headers = {
        "Content-Type": "application/json"
    }

    print("🔐 Updating access token to API...")

    try:
        response = requests.put(url, json=payload, headers=headers, timeout=10)

        # Raise error for 4xx / 5xx
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            print("❌ Invalid JSON response from server")
            print("Raw Response:", response.text)
            return None

        print("✅ Token updated successfully")
        print("Status Code:", response.status_code)
        print("Response:", data)

        return data

    except requests.exceptions.Timeout:
        print("⏱ Token update request timed out")

    except requests.exceptions.ConnectionError:
        print("🌐 Connection error — API server unreachable")

    except requests.exceptions.HTTPError as e:
        print("❌ HTTP Error while updating token:", str(e))
        print("Response Body:", response.text)

    except requests.exceptions.RequestException as e:
        print("❌ Token update request failed:", str(e))

    except Exception as e:
        print("❌ Unexpected error while updating token:", str(e))

    return None


def is_token_valid():
    url = "https://api.upstox.com/v2/user/get-funds-and-margin"
    headers = {
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    try:
        print("🔍 Validating Upstox access token...")

        r = requests.get(url, headers=headers, timeout=10)

        # ✅ Valid token
        if r.status_code == 200:
            print("✅ Token is valid")
            return True, None

        # ⚠ Maintenance window
        if r.status_code == 423:
            print("⚠ Upstox Funds API locked (maintenance window)")
            print("ℹ Service hours: 5:30 AM – 12:00 AM IST")
            return True, "⚠ Upstox service temporarily unavailable (maintenance window)"

        # ❌ Token expired / invalid
        if r.status_code == 401:
            print("❌ Token expired or invalid")
            return False, "❌ Access Token Expired or Invalid. Please regenerate token."

        # 🔒 Forbidden / restricted
        if r.status_code == 403:
            print("🔒 Access forbidden — account restricted")
            return False, "🔒 Access forbidden. Check Upstox account status."

        # 🚫 Rate limit
        if r.status_code == 429:
            print("🚫 Rate limit exceeded")
            return False, "🚫 Rate limit exceeded. Please slow down requests."

        # 🔥 Server error
        if r.status_code >= 500:
            print("🔥 Upstox server error")
            return False, "🔥 Upstox server error. Try again later."

        # ⚠ Unexpected response
        print("⚠ Unexpected token validation response")
        print("Status Code:", r.status_code)
        print("Response:", r.text)

        return False, f"⚠ Token validation failed: {r.text}"

    except requests.exceptions.Timeout:
        print("⏱ Token validation request timed out")
        return False, "⏱ Token validation timed out"

    except requests.exceptions.ConnectionError:
        print("🌐 Network error — cannot reach Upstox servers")
        return False, "🌐 Network error — cannot reach Upstox servers"

    except requests.exceptions.RequestException as e:
        print("❌ Token validation request failed:", str(e))
        return False, str(e)

    except Exception as e:
        print("❌ Unexpected token validation error:", str(e))
        return False, str(e)
