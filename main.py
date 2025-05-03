import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import time

# RocketAPI and Google Sheets setup
ROCKET_API_TOKEN = os.environ["ROCKET_API_KEY"]
SPREADSHEET_ID = "13a_IXBNpCDRnSXrFlrxTL7UrmpLYoEQW5ZYQ4ccymQQ"
HEADERS = ["Usernames", "Location", "Platform", "AccName", "MatchName", "Engaged"]

# Authorize Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
sheet_file = client.open_by_key(SPREADSHEET_ID)

# Get Instagram user ID from RocketAPI
def get_user_id(username):
    url = "https://v1.rocketapi.io/instagram/user/get_info"
    headers = {"Authorization": f"Token {ROCKET_API_TOKEN}"}
    data = {"username": username}
    res = requests.post(url, headers=headers, json=data)
    res.raise_for_status()
    result = res.json()
    return result["data"]["id"]

# Get followers from RocketAPI using account ID
def get_followers(username):
    try:
        user_id = get_user_id(username)
    except Exception as e:
        print(f"❌ Failed to fetch user ID for {username}: {e}")
        return []

    url = "https://v1.rocketapi.io/instagram/user/get_followers"
    headers = {"Authorization": f"Token {ROCKET_API_TOKEN}"}
    data = {"id": user_id, "limit": 1000}
    res = requests.post(url, headers=headers, json=data)

    try:
        res.raise_for_status()
        result = res.json()
        if "data" not in result:
            print(f"❌ No 'data' returned for {username}: {result}")
            return []
        return [f['username'] for f in result["data"]]
    except Exception as e:
        print(f"❌ Error fetching followers for {username}: {e}")
        print(f"Response: {res.text}")
        return []

# Create or update followers in Google Sheets
def update_followers(account_username):
    try:
        worksheet = sheet_file.worksheet(account_username)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet_file.add_worksheet(title=account_username, rows="1000", cols="10")
        worksheet.append_row(HEADERS)

    time.sleep(2)  # delay to avoid Google Sheets quota limits

    all_rows = worksheet.get_all_values()
    existing_usernames = set(row[0] for row in all_rows[1:])
    new_followers = get_followers(account_username)
    to_add = [f for f in new_followers if f not in existing_usernames]

    for f in to_add:
        row = [f, "", "", "", "", ""]
        worksheet.append_row(row)
        print(f"✅ Added follower '{f}' to sheet '{account_username}'")

# List of usernames to process
accounts = [
    "lilyahh07x", "liilyy2007", "lilydelle19", "lilyserenex", "lilycitirine",
    "emilyaurorasky", "emilynyxshadow", "emilysilvarra", "emilyavayah", "emilyzoeyyy",
    "emilylarkss", "emilysserenax", "emilyarwen32", "emilyvortesxx", "emilybeauuu",
    "lilyvellichor", "lilyhalcyonex", "lilyzarielle", "lilyduskie", "lilytitanias",
    "lilygarnette32", "lilyluminaa", "lilylollii07", "lilywispie", "lilytulipzz",
    "emilylucianax", "emilyvixendream", "emilyshariex", "lilyrosenaaxx", "lilyanniii2",
    "emilybellee7", "emilyroseveil", "lilyfaylin16", "emilyshaelynn", "lilypicnic07",
    "lilyinlace07", "lilytalesxo07", "lilybunnee07", "lilyfayeth", "lilyiriswave",
    "lilyaurelline", "lilynirvaa", "lilydelphia21", "lilytempestt", "lilydaydreem",
    "lilyfeelsxo07", "lilybluebellz", "lilystellaris"
]

# Run for all accounts
for acc in accounts:
    update_followers(acc)
