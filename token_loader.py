import os
import requests
from dotenv import load_dotenv

load_dotenv()

SERIAL_NUM = os.getenv("SERIAL_NUM")
MSG_API_URL = os.getenv("MSG_API_URL")
ENV_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

if not SERIAL_NUM or not MSG_API_URL:
    raise ValueError("❌ SERIAL_NUM or MSG_API_URL missing in .env file")


def save_token_to_api(token: str):
    url = f"{MSG_API_URL}/update/{SERIAL_NUM}"

    payload = {
        "message_content": token
    }

    print("🔐 Saving token to API...")

    response = requests.put(url, json=payload, timeout=10)
    response.raise_for_status()

    print("✅ Token saved successfully to API")

    return response.json()


def fetch_access_token_from_api():
    """
    Loads token from API.
    If not found, bootstrap from .env and save it.
    """

    url = f"{MSG_API_URL}/get/{SERIAL_NUM}"

    print("🔍 Fetching access token from API...")

    try:
        response = requests.get(url, timeout=10)

        # Token exists in API
        if response.status_code == 200:
            data = response.json()
            print("✅ Token fetched successfully from API")
            return str(data["message_content"])

        # Token not found → bootstrap from .env
        if response.status_code == 404:
            print("⚠ Token not found in API")

            if not ENV_TOKEN:
                raise Exception("❌ No token in API and no UPSTOX_ACCESS_TOKEN in .env")

            print("🔁 Bootstrapping token from .env into API...")
            save_token_to_api(ENV_TOKEN)

            print("✅ Token bootstrapped successfully from .env")
            return ENV_TOKEN

        # Any other error
        print(f"❌ Unexpected API response: {response.status_code}")
        response.raise_for_status()

    except requests.exceptions.Timeout:
        raise Exception("❌ Token API request timed out")

    except requests.exceptions.ConnectionError:
        raise Exception("❌ Cannot connect to Token API server")

    except Exception as e:
        raise Exception(f"❌ Token load failed: {str(e)}")
