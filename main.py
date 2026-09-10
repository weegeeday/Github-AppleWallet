"""
Main pipeline orchestrator for GitHub Apple Wallet Pass.
Fetches contributions, renders the heatmap banner, and issues/updates the pass via WalletWallet.
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, Any

# Add src to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fetch_github import fetch_contributions
from generate_card import generate_banner_image
from wallet_client import WalletWalletClient

STATE_FILE = "pass_state.json"

def load_env_file():
    """Load key-value pairs from .env if it exists and variables aren't already set."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    if k not in os.environ:
                        os.environ[k] = v

def build_pass_payload(data: Dict[str, Any], banner_data_uri: str) -> Dict[str, Any]:
    username = data["username"]
    current_streak = data["current_streak"]
    year_commits = data["year_commits"]
    today_commits = data["today_commits"]
    total_last_year = data["total_last_year"]
    longest_streak = data["longest_streak"]
    now_str = datetime.now(timezone.utc).strftime("%b %d, %Y %H:%M UTC")

    streak_display = f"🔥 {current_streak} DAYS" if current_streak > 0 else "0 DAYS"

    payload = {
        "logoText": "GitHub",
        "organizationName": "GitHub Contributions",
        "description": f"@{username}'s GitHub Contribution Pass",
        "colorPreset": "dark",
        "color": "#0d1117",
        "stripURL": banner_data_uri,
        "primaryFields": [
            {
                "label": "USER",
                "value": f"@{username}"
            }
        ],
        "headerFields": [
            {
                "label": "STREAK",
                "value": streak_display
            }
        ],
        "secondaryFields": [
            {
                "label": "THIS YEAR",
                "value": str(year_commits)
            },
            {
                "label": "TODAY",
                "value": str(today_commits)
            }
        ],
        "backFields": [
            {
                "label": "GitHub Profile",
                "value": f"https://github.com/{username}"
            },
            {
                "label": "Contributions (Past Year)",
                "value": f"{total_last_year}"
            },
            {
                "label": "Longest Streak",
                "value": f"{longest_streak} days"
            },
            {
                "label": "Last Updated",
                "value": now_str
            }
        ],
        "barcodeValue": f"https://github.com/{username}",
        "barcodeFormat": "QR",
        "barcodeAltText": "Scan to view GitHub profile",
        "sharingProhibited": False
    }

    return payload

def run():
    parser = argparse.ArgumentParser(description="GitHub Apple Wallet Pass Manager")
    parser.add_argument("--force-create", action="store_true", help="Force creating a brand new pass instead of updating")
    parser.add_argument("--preview-only", action="store_true", help="Only generate preview_card.png banner image without contacting API")
    parser.add_argument("--username", help="Override GitHub username")
    args = parser.parse_args()

    load_env_file()

    api_key = os.environ.get("WALLETWALLET_API_KEY")
    username = args.username or os.environ.get("GH_USERNAME")

    if not username:
        print("Error: GH_USERNAME must be set in .env, environment variable, or via --username", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Fetching GitHub activity for @{username}...")
    contrib_data = fetch_contributions(username)
    print(f"    - Total last year: {contrib_data['total_last_year']}")
    print(f"    - This year: {contrib_data['year_commits']}")
    print(f"    - Today: {contrib_data['today_commits']}")
    print(f"    - Current streak: {contrib_data['current_streak']} days")

    print("[*] Generating contribution heatmap banner...")
    banner_uri = generate_banner_image(contrib_data, output_path="preview_card.png")
    print(f"    - Banner generated (saved to preview_card.png, {len(banner_uri)} chars)")

    if args.preview_only:
        print("[*] Preview-only mode: done.")
        return

    if not api_key:
        print("Error: WALLETWALLET_API_KEY must be set in .env or environment variable", file=sys.stderr)
        sys.exit(1)

    client = WalletWalletClient(api_key)
    payload = build_pass_payload(contrib_data, banner_uri)

    # Check state file
    state = {}
    if os.path.exists(STATE_FILE) and not args.force_create:
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    serial_number = state.get("serialNumber")

    # If no local state but not explicitly force-creating, check if pass already exists on the account
    if not serial_number and not args.force_create:
        try:
            passes_resp = client.list_passes()
            for p in passes_resp.get("passes", []):
                if p.get("title") == "GitHub":
                    serial_number = p.get("serialNumber")
                    print(f"[*] Found existing pass on account: {serial_number}. Adopting it.")
                    state["serialNumber"] = serial_number
                    state["shareUrl"] = f"https://api.walletwallet.dev/p/{serial_number}"
                    break
        except Exception as e:
            print(f"[!] Warning: Could not check existing passes ({e})")

    if serial_number and not args.force_create:
        print(f"[*] Updating existing pass (Serial: {serial_number})...")
        res = client.update_pass(serial_number, payload)
        unchanged = res.get("unchanged", False)
        devices = res.get("notifiedDevices", 0)
        print(f"    [+] Update successful! (Unchanged: {unchanged}, Devices notified: {devices})")
        
        state["lastUpdated"] = datetime.now(timezone.utc).isoformat()
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    else:
        print("[*] Creating new Apple Wallet pass...")
        res = client.create_pass(payload)
        new_serial = res.get("serialNumber")
        share_url = res.get("shareUrl")
        google_url = res.get("googleSaveUrl")

        # Save state immediately
        state = {
            "serialNumber": new_serial,
            "username": username,
            "shareUrl": share_url,
            "googleSaveUrl": google_url,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        # Save pkpass binary locally if available
        apple_pass_b64 = res.get("applePass")
        if apple_pass_b64:
            import base64
            with open("github_contributions.pkpass", "wb") as f:
                f.write(base64.b64decode(apple_pass_b64))

        print("\n" + "="*60)
        print("[SUCCESS] Pass created successfully!")
        print(f"Serial Number: {new_serial}")
        print(f"Install Page:  {share_url}")
        print("="*60 + "\n")
        print("Open the install page on your iPhone to add the pass to Apple Wallet:")
        print(f"   {share_url}\n")
        if apple_pass_b64:
            print("Saved local binary: github_contributions.pkpass\n")

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    run()
