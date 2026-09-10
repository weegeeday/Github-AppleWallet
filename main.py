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
        "headerFields": [
            {
                "label": "STREAK",
                "value": streak_display
            }
        ],
        "secondaryFields": [
            {
                "label": "USER",
                "value": f"@{username}"
            },
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
        "barcodeAltText": "",
        "sharingProhibited": False
    }

    return payload

def run():
    parser = argparse.ArgumentParser(description="GitHub Apple Wallet Pass Manager")
    parser.add_argument("--force-create", action="store_true", help="Force creating a brand new pass instead of updating")
    parser.add_argument("--preview-only", action="store_true", help="Only generate preview_card.png banner image without contacting API")
    parser.add_argument("--username", help="Override GitHub username")
    parser.add_argument("--serial", help="Explicitly specify pass serial number to update")
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

    # 1. Check if serial passed explicitly via argument or env
    serial_number = args.serial or os.environ.get("WALLET_PASS_SERIAL")

    # 2. Check local state file (if available locally)
    state = {}
    if not serial_number and os.path.exists(STATE_FILE) and not args.force_create:
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                serial_number = state.get("serialNumber")
        except Exception:
            state = {}

    # 3. If still unknown and not force-creating, auto-discover pass on WalletWallet account
    if not serial_number and not args.force_create:
        try:
            passes_resp = client.list_passes()
            for p in passes_resp.get("passes", []):
                if p.get("title") == "GitHub":
                    serial_number = p.get("serialNumber")
                    masked = serial_number[:8] + "..." + serial_number[-4:] if len(serial_number) > 12 else serial_number
                    print(f"[*] Discovered existing GitHub pass on account ({masked}). Adopting it.")
                    state["serialNumber"] = serial_number
                    state["shareUrl"] = f"https://api.walletwallet.dev/p/{serial_number}"
                    break
        except Exception as e:
            print(f"[!] Warning: Could not check existing passes ({e})")

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")

    if serial_number and not args.force_create:
        masked = serial_number[:8] + "..." + serial_number[-4:] if len(serial_number) > 12 else serial_number
        print(f"[*] Updating existing pass (Serial: {masked})...")
        res = client.update_pass(serial_number, payload)
        unchanged = res.get("unchanged", False)
        devices = res.get("notifiedDevices", 0)
        print(f"    [+] Update successful! (Unchanged: {unchanged}, Devices notified: {devices})")

        share_url = state.get("shareUrl", f"https://api.walletwallet.dev/p/{serial_number}")
        
        # Save local state if not in CI
        if not os.environ.get("CI"):
            state["serialNumber"] = serial_number
            state["lastUpdated"] = datetime.now(timezone.utc).isoformat()
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

        if step_summary:
            try:
                with open(step_summary, "a", encoding="utf-8") as f:
                    f.write("### 📱 GitHub Apple Wallet Pass\n\n")
                    f.write(f"- **User:** `@{username}`\n")
                    f.write(f"- **Status:** ✅ Pass updated successfully\n")
                    f.write(f"- **Devices Notified:** {devices}\n")
                    f.write(f"- **Install / View:** [Open in Wallet]({share_url})\n")
            except Exception:
                pass
    else:
        print("[*] Creating new Apple Wallet pass...")
        res = client.create_pass(payload)
        new_serial = res.get("serialNumber")
        share_url = res.get("shareUrl")
        google_url = res.get("googleSaveUrl")

        # Save local state if not in CI
        if not os.environ.get("CI"):
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
        if apple_pass_b64 and not os.environ.get("CI"):
            import base64
            with open("github_contributions.pkpass", "wb") as f:
                f.write(base64.b64decode(apple_pass_b64))

        print("\n" + "="*60)
        print("[SUCCESS] Pass created successfully!")
        print(f"Install Page:  {share_url}")
        print("="*60 + "\n")
        print("Open the install page on your iPhone to add the pass to Apple Wallet:")
        print(f"   {share_url}\n")

        if step_summary:
            try:
                with open(step_summary, "a", encoding="utf-8") as f:
                    f.write("### 📱 GitHub Apple Wallet Pass\n\n")
                    f.write(f"- **User:** `@{username}`\n")
                    f.write(f"- **Status:** 🎉 Pass created successfully!\n")
                    f.write(f"- **Install Link:** [Add to Apple Wallet]({share_url})\n\n")
                    f.write("Open the link or scan the QR code on the page from your iPhone to add the pass.\n")
            except Exception:
                pass

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    run()
