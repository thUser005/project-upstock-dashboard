import upstox_client
from upstox_client.rest import ApiException
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from config import UPSTOX_ACCESS_TOKEN


def get_gtt_order_details(gtt_order_id: str):
    """
    Fetch GTT order details using GTT Order ID.

    :param gtt_order_id: e.g. "GTT-C25030300128840"
    """

    configuration = upstox_client.Configuration()
    configuration.access_token = str(UPSTOX_ACCESS_TOKEN)

    api_instance = upstox_client.OrderApiV3(
        upstox_client.ApiClient(configuration)
    )

    try:
        response = api_instance.get_gtt_order_details(
            gtt_order_id=gtt_order_id
        )

        return {
            "status": "success",
            "data": response
        }

    except ApiException as e:
        return {
            "status": "error",
            "message": str(e)
        }


# # from utils.gtt.get_gtt_order_details import get_gtt_order_details

# result = get_gtt_order_details("GTT-C26180100002333")
# print(result)
