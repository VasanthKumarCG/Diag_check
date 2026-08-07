import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def required(name):
    value = os.getenv(name)
    if not value or value.startswith("replace_with_"):
        raise RuntimeError(f"Missing or placeholder setting: {name}")
    return value


def main():
    enabled = os.getenv("POWERBI_REFRESH_ENABLED", "0").lower() in {"1", "true", "yes", "on"}
    if not enabled:
        print("Power BI refresh disabled.")
        return 0

    tenant = required("POWERBI_TENANT_ID")
    token_response = requests.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data={
            "client_id": required("POWERBI_CLIENT_ID"),
            "client_secret": required("POWERBI_CLIENT_SECRET"),
            "scope": "https://analysis.windows.net/powerbi/api/.default",
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    token_response.raise_for_status()
    headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
    base = (
        "https://api.powerbi.com/v1.0/myorg/groups/"
        f"{required('POWERBI_WORKSPACE_ID')}/datasets/"
        f"{required('POWERBI_DATASET_ID')}/refreshes"
    )
    submit = requests.post(base, headers=headers, timeout=60)
    if submit.status_code != 202:
        raise RuntimeError(f"Refresh submission failed: {submit.status_code} {submit.text}")

    status_url = submit.headers.get("Location") or (base + "?$top=1")
    deadline = time.time() + int(os.getenv("POWERBI_TIMEOUT_SECONDS", "1800"))
    poll = int(os.getenv("POWERBI_POLL_SECONDS", "15"))
    print("Power BI refresh accepted.")

    while time.time() < deadline:
        response = requests.get(status_url, headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if "value" in payload:
            item = payload["value"][0] if payload["value"] else {}
        else:
            item = payload
        status = item.get("status", "Unknown")
        print(f"Power BI refresh status: {status}")
        if status == "Completed":
            return 0
        if status in {"Failed", "Cancelled", "Disabled"}:
            print(item, file=sys.stderr)
            return 5
        time.sleep(poll)
    print("Power BI refresh timed out.", file=sys.stderr)
    return 5


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Power BI refresh failed: {error}", file=sys.stderr)
        raise SystemExit(5)
