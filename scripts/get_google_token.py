"""
One-time script to generate a Google OAuth token for the Bag End dashboard.
Run this on Windows, log in as brentmwill@gmail.com, and it saves token.json.
Copy token.json to the server at /home/eluse/projects/bag-end/backend/token.json
"""
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CLIENT_SECRETS = r"C:\Users\eluse\Downloads\bag-end-calendar-oauth.json"

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
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
