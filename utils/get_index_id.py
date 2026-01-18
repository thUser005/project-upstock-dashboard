import requests

def search_groww_option(query):
    url = "https://groww.in/v1/api/search/v3/query/global/st_p_query"

    params = {
        "page": 0,
        "query": query,
        "size": 6,
        "web": "true"
    }

    headers = {
        "accept": "application/json, text/plain, */*",
        "x-app-id": "growwWeb",
        "x-device-type": "desktop",
        "x-platform": "web"
    }

    response = requests.get(url, params=params, headers=headers, timeout=10)

    response.raise_for_status()
    data = response.json()

    # Extract first 3 results
    content = data.get("data", {}).get("content", [])
    return content[:3]


# # Example usage
# if __name__ == "__main__":
#     query = "NIFTY 27000 CE 30 JUN 26"
#     results = search_groww_option(query)

#     for i, item in enumerate(results, 1):
#         print(f"\nResult {i}")
#         print("ID:", item.get("id"))
#         print("Title:", item.get("title"))
#         print("Expiry:", item.get("expiry"))
#         print("Search ID:", item.get("search_id"))
