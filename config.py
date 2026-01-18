
import os
from dotenv import load_dotenv
import upstox_client
from pymongo import MongoClient
from token_loader import fetch_access_token_from_api

load_dotenv()

UPSTOX_ACCESS_TOKEN = fetch_access_token_from_api()
configuration = upstox_client.Configuration()
configuration.access_token = str(UPSTOX_ACCESS_TOKEN)
api_client = upstox_client.ApiClient(configuration)

MOBILE_NUM = os.getenv("MOBILE_NUM")
SERIAL_NUM = os.getenv("SERIAL_NUM")
MSG_API_URL = os.getenv("MSG_API_URL")



MONGO_URL = os.getenv("MONGO_URL")
mongo_client = MongoClient(MONGO_URL)
mongo_db = mongo_client["gtt_trading"]
gtt_collection = mongo_db["gtt_orders"]
# Collection for live subscribed instruments
subscribed_collection = mongo_db["subscribed_symbols"]