import upstox_client
from upstox_client.rest import ApiException
import sys
import os
from typing import Optional

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from config import UPSTOX_ACCESS_TOKEN


def modify_gtt_order(
    gtt_order_id: str,
    quantity: int,
    entry_price: Optional[float] = None,
    target_price: Optional[float] = None,
    stoploss_price: Optional[float] = None,
    modify_entry: bool = False,
    modify_target: bool = False,
    modify_stoploss: bool = False
):
    """
    Modify GTT order with flag-based control.
    """

    if not any([modify_entry, modify_target, modify_stoploss]):
        return {
            "status": "error",
            "message": "No modify flag enabled. Set at least one flag."
        }

    configuration = upstox_client.Configuration()
    configuration.access_token = str(UPSTOX_ACCESS_TOKEN)

    api_instance = upstox_client.OrderApiV3(
        upstox_client.ApiClient(configuration)
    )

    rules = []

    if modify_entry:
        if entry_price is None:
            return {"status": "error", "message": "entry_price required"}
        rules.append(
            upstox_client.GttRule(
                strategy="ENTRY",
                trigger_type="ABOVE",
                trigger_price=entry_price
            )
        )

    if modify_target:
        if target_price is None:
            return {"status": "error", "message": "target_price required"}
        rules.append(
            upstox_client.GttRule(
                strategy="TARGET",
                trigger_type="IMMEDIATE",
                trigger_price=target_price
            )
        )

    if modify_stoploss:
        if stoploss_price is None:
            return {"status": "error", "message": "stoploss_price required"}
        rules.append(
            upstox_client.GttRule(
                strategy="STOPLOSS",
                trigger_type="IMMEDIATE",
                trigger_price=stoploss_price
            )
        )

    gtt_type = "MULTIPLE" if len(rules) > 1 else "SINGLE"

    body = upstox_client.GttModifyOrderRequest(
        type=gtt_type,
        gtt_order_id=gtt_order_id,
        rules=rules,
        quantity=quantity
    )

    try:
        response = api_instance.modify_gtt_order(body=body)
        return {
            "status": "success",
            "modified": {
                "entry": modify_entry,
                "target": modify_target,
                "stoploss": modify_stoploss
            },
            "data": response
        }

    except ApiException as e:
        return {
            "status": "error",
            "message": str(e)
        }
