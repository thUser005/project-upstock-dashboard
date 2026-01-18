import upstox_client
from upstox_client.rest import ApiException
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from config import UPSTOX_ACCESS_TOKEN


def cancel_gtt_order(gtt_order_id: str):
    """
    Cancels a GTT order using GTT Order ID.

    :param gtt_order_id: e.g. "GTT-C250303008840"
    """

    configuration = upstox_client.Configuration()
    configuration.access_token = str(UPSTOX_ACCESS_TOKEN)

    api_instance = upstox_client.OrderApiV3(
        upstox_client.ApiClient(configuration)
    )

    body = upstox_client.GttCancelOrderRequest(
        gtt_order_id=gtt_order_id
    )

    try:
        response = api_instance.cancel_gtt_order(body=body)
        return {
            "status": "success",
            "data": response
        }

    except ApiException as e:
        return {
            "status": "error",
            "message": str(e)
        }


# # from utils.gtt.cancel_gtt_order import cancel_gtt_order

# result = cancel_gtt_order("GTT-C26180100002333")
# print(result)
