import os
import json
import requests
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- ENV VARIABLES ---
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")
ROCKETAPI_TOKEN = os.environ.get("ROCKETAPI_TOKEN")
ROCKETAPI_FOLLOWERS_URL = "https://v1.rocketapi.io/instagram/user/get_followers"
ROCKETAPI_INFO_URL = "https://v1.rocketapi.io/instagram/user/get_info"

# --- CHECK ENV CREDS ---
if not AIRTABLE_API_KEY or not ROCKETAPI_TOKEN or not GOOGLE_CREDENTIALS_JSON:
    print("❌ Missing one or more API credentials in environment variables.")
    exit(1)

# --- CONFIG ---
AIRTABLE_BASE_ID = "appTxTTXPTBFwjelH"
AIRTABLE_TABLE_NAME = "Accounts"
AIRTABLE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

# --- HEADERS ---
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}

rocketapi_headers = {
    "Authorization": f"Token {ROCKETAPI_TOKEN}",
    "Content-Type": "application/json"
}

# --- INIT GOOGLE SHEETS SERVICE ---
credentials = service_account.Credentials.from_service_account_info(
    json.loads(GOOGLE_CREDENTIALS_JSON),
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheets_service = build("sheets", "v4", credentials=credentials)

# --- FUNCTIONS ---
def get_all_accounts():
    print("📦 Fetching ALL Airtable records (no status filter)...")
    response = requests.get(AIRTABLE_URL, headers=airtable_headers)
    response.raise_for_status()
    return response.json().get("records", [])

def extract_sheet_id(sheet_url):
    try:
        return sheet_url.split("/d/")[1].split("/")[0]
    except (IndexError, AttributeError):
        return None

def safe_post_request(url, headers, payload, retries=3):
    for i in range(retries):
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            return resp
        time.sleep(2 ** i)  # exponential backoff
    return None

def get_followers(username):
    followers = []
    max_id = ""
    seen_ids = set()

    print(f"🔄 Processing @{username} (IG)...")

    # Step 1: Get IG ID
    info_resp = safe_post_request(
        url=ROCKETAPI_INFO_URL,
        headers=rocketapi_headers,
        payload={"username": username}
    )

    try:
        info_data = info_resp.json()
        user_data = info_data["response"]["body"]["data"]["user"]
        user_id = user_data.get("id") or user_data.get("pk")
        if not user_id:
            raise KeyError("Missing 'id' or 'pk'")
    except Exception as e:
        print(f"❌ Failed to get ID for @{username}: {e}")
        print("🔍 Full response:", json.dumps(info_data, indent=2))
        return []

    # Step 2: Get followers
    while True:
        follower_resp = safe_post_request(
            url=ROCKETAPI_FOLLOWERS_URL,
            headers=rocketapi_headers,
            payload={"id": user_id, "max_id": max_id or None}
        )

        try:
            data = follower_resp.json()
        except Exception as e:
            print(f"❌ Failed to parse JSON: {e}")
            print("🔍 Raw response:", follower_resp.text)
            break

        if not data.get("success") or "data" not in data or "users" not in data["data"]:
            print(f"❌ RocketAPI error for @{username}:")
            print(json.dumps(data, indent=2))
            break

        try:
            users = data["data"]["users"]
            followers.extend([u["username"] for u in users])
            next_id = data["data"].get("next_max_id")
            if not next_id or next_id in seen_ids:
                break
            seen_ids.add(next_id)
            max_id = next_id
        except Exception as e:
            print(f"❌ Error extracting followers for @{username}: {e}")
            break

    print(f"📊 Pulled {len(followers)} followers from @{username}")
    return followers

def update_google_sheet(sheet_id, followers, username):
    try:
        # Check if sheet tab exists
        sheets_metadata = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheet_titles = [s["properties"]["title"] for s in sheets_metadata["sheets"]]
        if username not in sheet_titles:
            print(f"❌ Sheet tab '{username}' not found in sheet {sheet_id}")
            return

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
    records = get_all_accounts()
    print(f"\n🔍 Found {len(records)} total records in Airtable.\n")
    success_count = 0

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
        success_count += 1

    print(f"\n✅ Follower sync completed. {success_count}/{len(records)} updated.\n")

if __name__ == "__main__":
    main()
