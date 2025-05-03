import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

# Load credentials from environment
ROCKET_API_TOKEN = os.environ["ROCKET_API_KEY"]
SPREADSHEET_ID = "13a_IXBNpCDRnSXrFlrxTL7UrmpLYoEQW5ZYQ4ccymQQ"

# Expected column headers
HEADERS = ["Usernames", "Location", "Platform", "AccName", "MatchName", "Engaged"]

# Google Sheets auth setup
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
sheet_file = client.open_by_key(SPREADSHEET_ID)

# RocketAPI call to get followers
def get_followers(username):
    url = "https://v1.rocketapi.io/instagram/user/get_followers"
    headers = {"Authorization": f"Token {ROCKET_API_TOKEN}"}
    data = {"username": username, "limit": 1000}
    res = requests.post(url, headers=headers, json=data)
    
    try:
        res.raise_for_status()
        json_data = res.json()
        if 'data' not in json_data:
            raise ValueError(f"No data field in RocketAPI response: {json_data}")
        return [f['username'] for f in json_data['data']]
    
    except Exception as e:
        print(f"[❌ ERROR] Failed to get followers for '{username}': {e}")
        return []

# Updates a dedicated worksheet for each Instagram account
def update_followers(account_username):
    try:
        worksheet = sheet_file.worksheet(account_username)
    except gspread.exceptions.WorksheetNotFound:
