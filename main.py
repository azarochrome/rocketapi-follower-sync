import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

ROCKET_API_TOKEN = os.environ["ROCKET_API_KEY"]
SPREADSHEET_ID = "13a_IXBNpCDRnSXrFlrxTL7UrmpLYoEQW5ZYQ4ccymQQ"

HEADERS = ["Usernames", "Location", "Platform", "AccName", "MatchName", "Engaged"]

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
sheet_file = client.open_by_key(SPREADSHEET_ID)

def get_followers(username):
    url = "https://v1.rocketapi.io/instagram/user/get_followers"
    headers = {"Authorization": f"Token {ROCKET_API_TOKEN}"}
    data = {"username": username, "limit": 1000}
    res = requests.post(url, headers=headers, json=data)
    res.raise_for_status()
    return [f['username'] for f in res.json()['data']]

def update_followers(account_username):
    try:
        worksheet = sheet_file.worksheet(account_username)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet_file.add_worksheet(title=account_username, rows="1000", cols="10")
        worksheet.append_row(HEADERS)

    all_rows = worksheet.get_all_values()
    existing_usernames = set(row[0] for row in all_rows[1:])

    new_followers = get_followers(account_username)
    to_add = [f for f in new_followers if f not in existing_usernames]

    for f in to_add:
        row = [f, "", "", "", "", ""]
        worksheet.append_row(row)
        print(f"Added follower '{f}' to sheet '{account_username}'")

accounts = [
    "lilyahh07x",
    "liilyy2007",
    "lilydelle19",
    "lilyserenex",
    "lilycitirine",
    "emilyaurorasky",
    "emilynyxshadow",
    "emilysilvarra",
    "emilyavayah",
    "emilyzoeyyy",
    "emilylarkss",
    "emilysserenax",
    "emilyarwen32",
    "emilyvortesxx",
    "emilybeauuu",
    "lilyvellichor",
    "lilyhalcyonex",
    "lilyzarielle",
    "lilyduskie",
    "lilytitanias",
    "lilygarnette32",
    "lilyluminaa",
    "lilylollii07",
    "lilywispie",
    "lilytulipzz",
    "emilylucianax",
    "emilyvixendream",
    "emilyshariex",
    "lilyrosenaaxx",
    "lilyanniii2",
    "emilybellee7",
    "emilyroseveil",
    "lilyfaylin16",
    "emilyshaelynn",
    "lilypicnic07",
    "lilyinlace07",
    "lilytalesxo07",
    "lilybunnee07",
    "lilyfayeth",
    "lilyiriswave",
    "lilyaurelline",
    "lilynirvaa",
    "lilydelphia21",
    "lilytempestt",
    "lilydaydreem",
    "lilyfeelsxo07",
    "lilybluebellz",
    "lilystellaris"
]  # Replace with real Instagram usernames
for acc in accounts:
    update_followers(acc)
