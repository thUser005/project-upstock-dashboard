import requests
from config import UPSTOX_ACCESS_TOKEN,SERIAL_NUM,MSG_API_URL


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
        print("❌ Request timed out")

    except requests.exceptions.ConnectionError:
        print("❌ Connection error — API server unreachable")

    except requests.exceptions.HTTPError as e:
        print("❌ HTTP Error:", str(e))
        print("Response Body:", response.text)

    except requests.exceptions.RequestException as e:
        print("❌ Request failed:", str(e))

    except Exception as e:
        print("❌ Unexpected error:", str(e))

    return None


# # Example usage
# if __name__ == "__main__":
#     new_token = "NEW_ACCESS_TOKEN_HERE"
#     update_access_token(new_token)


def is_token_valid():
    url = "https://api.upstox.com/v2/user/get-funds-and-margin"
    headers = {
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code == 200:
            return True, None

        elif r.status_code == 401:
            return False, "❌ Access Token Expired or Invalid. Please regenerate token."

        else:
            return False, f"⚠️ Token validation failed: {r.text}"

    except Exception as e:
        return False, str(e)
