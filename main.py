import os
import json
import traceback
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- ENV VARIABLES ---
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")
ROCKETAPI_TOKEN = os.environ.get("ROCKETAPI_TOKEN")
ROCKETAPI_URL = "https://v1.rocketapi.io/instagram/user/get_followers"

if not GOOGLE_CREDENTIALS_JSON:
    raise EnvironmentError("❌ GOOGLE_CREDENTIALS_JSON is not set. Please define it in GitHub Secrets.")

# --- CONFIG ---
AIRTABLE_BASE_ID = "appTxTTXPTBFwjelH"
AIRTABLE_TABLE_NAME = "Accounts"
AIRTABLE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

# --- INIT SERVICES ---
headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}

try:
    credentials_info = json.loads(GOOGLE_CREDENTIALS_JSON)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    sheets_service = build("sheets", "v4", credentials=credentials)
except Exception:
    print("❌ Failed to initialize Google Sheets API:")
    traceback.print_exc()
    exit(1)

# --- FUNCTIONS ---
def get_all_accounts():
    print("📦 Fetching ALL Airtable records (no status filter)...")
    response = requests.get(AIRTABLE_URL, headers=headers)
    response.raise_for_status()
    return response.json().get("records", [])

def extract_sheet_id(sheet_url):
    try:
        return sheet_url.split("/d/")[1].split("/")[0]
    except (IndexError, AttributeError):
        return None

def get_followers(username):
    followers = []
    end_cursor = ''
    print(f"🔄 Processing @{username} (IG)...")

    while True:
        response = requests.post(
            url=ROCKETAPI_URL,
            headers={"Authorization": f"Token {ROCKETAPI_TOKEN}"},
            json={"username": username, "next_max_id": end_cursor or None}
        )

        if response.status_code != 200:
            print(f"❌ API request failed for @{username} with status {response.status_code}: {response.text}")
            break

        try:
            data = response.json()

            if "data" not in data or "user" not in data["data"]:
                print(f"❌ 'data.user' field missing in response for @{username}: {json.dumps(data, indent=2)}")
                break

            user_data = data["data"]["user"]

            if "edge_followed_by" not in user_data or "edges" not in user_data["edge_followed_by"]:
                print(f"❌ 'edge_followed_by.edges' missing for @{username}")
                break

            edges = user_data["edge_followed_by"]["edges"]
            page_info = user_data["edge_followed_by"].get("page_info", {})

            followers.extend([edge["node"]["username"] for edge in edges])

            if not page_info.get("has_next_page"):
                break
            end_cursor = page_info.get

def update_google_sheet(sheet_id, followers, username):
    try:
        range_name = f"{username}!A:A"
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()

        existing = result.get("values", [])
        existing_usernames = {row[0] for row in existing if row}

        new_followers = [[f] for f in followers if f not in existing_usernames]

        if new_followers:
            sheets_service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range=f"{username}!A1",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": new_followers}
            ).execute()
            print(f"✅ Synced {len(new_followers)} new followers from @{username} → Sheet tab: {username}")
        else:
            print(f"✅ No new followers to sync from @{username} → Sheet tab: {username}")
    except Exception as e:
        print(f"❌ Failed to update Google Sheet tab {username} in {sheet_id}: {e}")

# --- MAIN ---
def main():
    try:
        records = get_all_accounts()
    except Exception:
        print("❌ Error fetching Airtable records:")
        traceback.print_exc()
        return

    print(f"\n🔍 Found {len(records)} total records in Airtable.\n")

    for record in records:
        fields = record.get("fields", {})
        username = fields.get("Username")
        sheet_url = fields.get("Google Sheets")

        if not username:
            print("⚠️ Skipping: no Username provided.")
            continue
        if not sheet_url:
            print(f"⚠️ Skipping @{username}: no Google Sheets URL.")
            continue

        sheet_id = extract_sheet_id(sheet_url)
        if not sheet_id:
            print(f"⚠️ Skipping @{username}: invalid sheet URL.")
            continue

        followers = get_followers(username)
        if not followers:
            print(f"⚠️ Skipping @{username}: no followers returned.")
            continue

        update_google_sheet(sheet_id, followers, username)

    print("\n✅ Follower sync completed.")

if __name__ == "__main__":
    main()
