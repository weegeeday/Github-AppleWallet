# GitHub Apple Wallet Pass 📱

Automated Apple Wallet pass displaying real-time GitHub contributions, commit streaks, and a high-resolution dark-mode contribution heatmap banner.

Powered by [WalletWallet](https://www.walletwallet.dev) and GitHub Actions.

![Banner Preview](preview_card.png)

---

## ✨ Features

- **Real-Time GitHub Activity:** Automatically counts today's commits, current streak, and year-to-date totals.
- **Sleek Dark Mode Heatmap:** 20-week tactile contribution grid styled with canonical GitHub greens on a seamless `#0d1117` background.
- **Silent Background Updates:** Refreshes quietly in Apple Wallet everyday via Apple Push Notification service (APNs).
- **Zero-Touch Privacy:** Your pass ID and serial numbers are auto-discovered from your private WalletWallet account and never committed to git.

---

## 🚀 Quick Start (Use for Your Account)

### 1. Fork or Clone this Repository
Fork this repository to your own GitHub account.

### 2. Get a Free WalletWallet API Key
1. Sign up at [walletwallet.dev](https://www.walletwallet.dev/signup/) (free, no credit card required).
2. Copy your API key (`ww_live_...`).

### 3. Add GitHub Secret
In your repository on GitHub:
1. Go to **Settings** → **Secrets and variables** → **Actions**.
2. Under **Repository secrets**, click **New repository secret**:
   - **Name:** `WALLETWALLET_API_KEY`
   - **Value:** `ww_live_your_key_here`
3. *(Optional)* If your GitHub repository owner differs from your GitHub username, add a Repository Variable:
   - **Name:** `GH_USERNAME`
   - **Value:** `your-github-username`
   *(By default, it automatically uses your GitHub repository owner).*

### 4. Generate Your Pass
1. Go to the **Actions** tab in your repository.
2. Select the **Daily Apple Wallet Pass Update** workflow.
3. Click **Run workflow** → **Run workflow**.
4. Once completed (~15 seconds), open the run to view the **Job Summary**.
5. Click **Add to Apple Wallet** or scan the QR code with your iPhone to install your card!

---

## ⚙️ How It Works

1. **Workflow Run:** Running the GitHub Actions workflow executes [`main.py`](main.py).
2. **Public Contribution Scraping:** Fetches your public GitHub contribution calendar (no Personal Access Token required).
3. **Heatmap Generation:** Uses Pillow to render a 1080×360 px retina banner with 2x supersampling and safe margins.
4. **Auto-Discovery & APNs Update:** Detects your existing card on WalletWallet and pushes an in-place silent update via `PUT /api/passes/<serial>`.

---

## 💻 Local Development

To run or test locally:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
echo "WALLETWALLET_API_KEY=ww_live_your_key" > .env
echo "GH_USERNAME=your_username" >> .env

# 3. Preview banner image without contacting API
python main.py --preview-only

# 4. Create or update pass
python main.py
```
