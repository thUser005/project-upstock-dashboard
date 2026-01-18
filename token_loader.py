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

    response = requests.put(url, json=payload, timeout=10)
    response.raise_for_status()

    return response.json()


def fetch_access_token_from_api():
    """
    Loads token from API.
    If not found, bootstrap from .env and save it.
    """

    url = f"{MSG_API_URL}/get/{SERIAL_NUM}"

    try:
        response = requests.get(url, timeout=10)

        # Token exists in API
        if response.status_code == 200:
            data = response.json()
            return data["message_content"]

        # Token not found → bootstrap from .env
        if response.status_code == 404:
            if not ENV_TOKEN:
                raise Exception("❌ No token in API and no UPSTOX_ACCESS_TOKEN in .env")

            print("⚠ Token not found in API. Bootstrapping from .env...")
            save_token_to_api(ENV_TOKEN)
            return ENV_TOKEN

        # Any other error
        response.raise_for_status()

    except Exception as e:
        raise Exception(f"❌ Token load failed: {str(e)}")
