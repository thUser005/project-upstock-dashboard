import upstox_client
from upstox_client.rest import ApiException


def get_upstox_available_balance(access_token: str) -> float:
    """
    Returns available equity margin balance from Upstox
    """

    configuration = upstox_client.Configuration()
    configuration.access_token = access_token

    api_version = "2.0"
    api_instance = upstox_client.UserApi(upstox_client.ApiClient(configuration))

    try:
        response = api_instance.get_user_fund_margin(api_version).to_dict()

        # Extract available margin
        available_balance = response.data["equity"]["available_margin"]

        return float(available_balance)

    except ApiException as e:
        print("Upstox API Error:", e)
        return 0.0


print(get_upstox_available_balance("eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI3QUFIUEoiLCJqdGkiOiI2OTZlN2EwZGU2OWFmYzViYzUzMTc4NTgiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlhdCI6MTc2ODg0Nzg4NSwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxNzY4ODYwMDAwfQ.BAs1LqxdHWjLnD-e0TbmiM_gkR53k4bnOnqF2ku-yR0"))