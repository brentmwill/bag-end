"""
Generate / refresh a Google OAuth token for the Bag End dashboard.

Run this on Windows, log in as brentmwill@gmail.com, and it saves token.json
to the project root. Copy it to the server at
/home/eluse/projects/bag-end/backend/token.json

If the original OAuth client secrets JSON is in Downloads, it's used directly.
Otherwise the script falls back to pulling client_id/client_secret from an
existing token.json (lets you re-mint without re-downloading from Cloud Console).
"""
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CLIENT_SECRETS = r"C:\Users\eluse\Downloads\bag-end-calendar-oauth.json"
EXISTING_TOKEN = "token.json"

if Path(CLIENT_SECRETS).exists():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
elif Path(EXISTING_TOKEN).exists():
    with open(EXISTING_TOKEN) as f:
        existing = json.load(f)
    client_config = {
        "installed": {
            "client_id": existing["client_id"],
            "client_secret": existing["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": existing.get("token_uri", "https://oauth2.googleapis.com/token"),
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
else:
    raise SystemExit(
        f"Need either {CLIENT_SECRETS} (download from Google Cloud Console) "
        f"or an existing {EXISTING_TOKEN} to extract client credentials from."
    )

creds = flow.run_local_server(port=0)

token_data = {
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri": creds.token_uri,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
    "scopes": list(creds.scopes),
}

with open("token.json", "w") as f:
    json.dump(token_data, f, indent=2)

print("token.json saved. Copy it to the server:")
print("  scp token.json eluse@100.104.206.14:/home/eluse/projects/bag-end/backend/token.json")
