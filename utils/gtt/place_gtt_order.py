import upstox_client
from upstox_client.rest import ApiException
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from config import UPSTOX_ACCESS_TOKEN

def print_layout_msg(content,flag=False):
    if flag:            
        print(30*"--")
        print(content)
        print(30*"--")

def place_gtt_order(
    instrument_token: str,
    quantity: int,
    entry_price: float,
    target_price: float,
    stoploss_price: float,
    transaction_type: str = "BUY",
    product: str = "D"
):
    """
    Places a MULTIPLE GTT order with Entry, Target and Stoploss rules.

    :param access_token: Upstox access token
    :param instrument_token: e.g. "NSE_EQ|INE669E01016"
    :param quantity: Order quantity
    :param entry_price: Entry trigger price
    :param target_price: Target trigger price
    :param stoploss_price: Stoploss trigger price
    :param transaction_type: BUY or SELL
    :param product: D / I / etc
    """

    configuration = upstox_client.Configuration()
    configuration.access_token = str(UPSTOX_ACCESS_TOKEN)
    api_instance = upstox_client.OrderApiV3(upstox_client.ApiClient(configuration))

    # Build rules dynamically
    entry_rule = upstox_client.GttRule(
        strategy="ENTRY",
        trigger_type="ABOVE",
        trigger_price=entry_price
    )
    print_layout_msg(entry_rule)
    target_rule = upstox_client.GttRule(
        strategy="TARGET",
        trigger_type="IMMEDIATE",
        trigger_price=target_price
    )
    print_layout_msg(target_rule)
    stoploss_rule = upstox_client.GttRule(
        strategy="STOPLOSS",
        trigger_type="IMMEDIATE",
        trigger_price=stoploss_price
    )
    print_layout_msg(stoploss_rule)
    rules = [entry_rule, target_rule, stoploss_rule]

    body = upstox_client.GttPlaceOrderRequest(
        type="MULTIPLE",
        instrument_token=instrument_token,
        product=product,
        quantity=quantity,
        rules=rules,
        transaction_type=transaction_type
    )
    print_layout_msg(body)
    try:
        response = api_instance.place_gtt_order(body=body).to_dict()
        # s = f"{response}\n{type(response)}\n{dir(response)}"
        # print_layout_msg(s)
        return {
            "status": "success",
            "data": response
        }

    except ApiException as e:
        return {
            "status": "error",
            "message": str(e)
        }


# # from utils.gtt.place_gtt_order import place_gtt_order

# result = place_gtt_order(
#     instrument_token="NSE_FO|65083",
#     quantity=975,
#     entry_price=38,
#     target_price=45,
#     stoploss_price=30,
#     transaction_type="BUY",
#     product="D"
# )

# print(result)
