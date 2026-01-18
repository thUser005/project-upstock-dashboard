import requests
import os
from dotenv import load_dotenv
load_dotenv()
API_ID = os.getenv("API_ID")
url = f'https://api.upstox.com/v3/login/auth/token/request/{API_ID}'
headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json',
}

data = {
    'client_secret': os.getenv("API_SECRET")
}

response = requests.post(url, headers=headers, data=data)

print(response.status_code)
print(response.json())