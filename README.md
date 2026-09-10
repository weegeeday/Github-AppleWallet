# GitHub Apple Wallet Pass 📱

Automated daily Apple Wallet pass displaying your real-time GitHub contributions, commit streaks, and a high-resolution dark-mode contribution heatmap banner.

Powered 100% free by [WalletWallet](https://www.walletwallet.dev) and GitHub Actions.

![Banner Preview](preview_card.png)

---

## 🚀 Live Pass Ready

Your Apple Wallet pass has been created!

- **Direct Install Page:** [Add to Apple Wallet](https://api.walletwallet.dev/p/883ea5aa-05e0-4968-bb77-aa3a4a6b07fc)
- **Serial Number:** `883ea5aa-05e0-4968-bb77-aa3a4a6b07fc`

> **How to install on your iPhone:**
> 1. Open the [Install Page](https://api.walletwallet.dev/p/883ea5aa-05e0-4968-bb77-aa3a4a6b07fc) on your iPhone Safari, OR scan the QR code displayed on the page from your computer screen using your iPhone Camera.
> 2. Tap **Add to Apple Wallet**.
> 3. Your card is now active and will update automatically everyday in place!

---

## ⚙️ How It Works

1. **Scheduled Daily Trigger**: Every day at 01:00 AM local time (05:00 UTC), GitHub Actions runs [`main.py`](main.py).
2. **Scrapes Public Contributions**: Fetches your public GitHub contribution calendar (no tokens or authentication required).
3. **Renders Heatmap**: Generates a crisp 1080x360 px GitHub dark-mode contribution grid using Pillow.
4. **Pushes Live APNs Update**: Calls WalletWallet's `PUT /api/passes/<serial>` endpoint. WalletWallet sends an Apple Push Notification (APNs) wake signal to your iPhone, refreshing the card silently in your Apple Wallet.

---

## 🛠️ GitHub Repository Setup

When pushing this repository to GitHub:

1. Go to your repository **Settings** → **Secrets and variables** → **Actions**.
2. Under **Repository secrets**, add:
   - `WALLETWALLET_API_KEY`: Your WalletWallet secret key (`ww_live_...`)
3. Under **Variables** (or Secrets), add:
   - `GH_USERNAME`: Your GitHub handle (e.g. `weegeeday`)
4. Make sure GitHub Actions has write access to commit state:
   - Go to **Settings** → **Actions** → **General** → **Workflow permissions**.
   - Select **Read and write permissions** and click **Save**.

---

## 💻 Local Usage

To run or test locally:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure .env
echo "WALLETWALLET_API_KEY=your_key_here" >> .env
echo "GH_USERNAME=your_username" >> .env

# 3. Preview banner image without contacting API
python main.py --preview-only

# 4. Trigger pass update
python main.py

# 5. Force recreate pass with a new serial
python main.py --force-create
```
