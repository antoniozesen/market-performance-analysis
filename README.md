# Global Market Monitor

Institutional-style Streamlit app for date-range cross-asset performance analysis, narrative report generation (English/Spanish), and SMTP email delivery.

## What this app does

- Compares market assets across categories (indices, sectors, FX, commodities, bond ETFs, styles, yields).
- Supports **normalized (base 100)** and **absolute price** views.
- Computes key metrics:
  - Total Return %
  - Annualized Return %
  - Volatility (annualized)
  - Max Drawdown
  - Best/Worst day
  - Correlation heatmap
- Builds an editable narrative report with deterministic templates.
- Sends report by email (HTML/plain text) using SMTP secrets.

---

## Data sources

- **yfinance** for daily market prices.
- **FRED** (`fredapi`) for optional US yield series.

No paid sources are used.

---

## Repository structure

```text
app.py
src/
  config_loader.py
  data/
    universe.yaml
  data_sources/
    yfinance_client.py
    fred_client.py
  analytics/
    align.py
    metrics.py
    transforms.py
  reporting/
    narrative.py
    html_builder.py
  email/
    smtp_sender.py
requirements.txt
.gitignore
secrets.example.toml
LICENSE
README.md
```

---

## 1) Create a public GitHub repository (browser only)

1. Go to [https://github.com](https://github.com) and sign in.
2. Click the **+** icon (top-right) → **New repository**.
3. Repository name: `global-market-monitor` (or your preferred name).
4. Set visibility to **Public**.
5. Click **Create repository**.

---

## 2) Upload files to GitHub (browser only, no terminal)

1. Open your new repository page.
2. Click **Add file** → **Upload files**.
3. Drag-and-drop all project files/folders from this repo.
4. Scroll down to **Commit changes**.
5. Add commit message, e.g. `Initial Global Market Monitor app`.
6. Click **Commit changes**.

---

## 3) Deploy on Streamlit Community Cloud (click-by-click)

1. Go to [https://share.streamlit.io](https://share.streamlit.io).
2. Sign in with your GitHub account.
3. Click **New app**.
4. Select:
   - **Repository**: your uploaded repo
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. Click **Deploy**.

If deployment asks for dependencies, Streamlit will install from `requirements.txt` automatically.

---

## 4) Add secrets in Streamlit Cloud

1. In your deployed app dashboard, open **Settings** → **Secrets**.
2. Paste TOML values using this exact key set:

```toml
FRED_API_KEY = "YOUR_FRED_KEY"

SMTP_HOST = "smtp.example.com"
SMTP_PORT = 587
SMTP_USERNAME = "your_username"
SMTP_PASSWORD = "your_password"
SMTP_SENDER = "monitor@example.com"
SMTP_USE_TLS = true

DEFAULT_RECIPIENTS = "first@example.com,second@example.com"
```

3. Click **Save**.
4. Reboot/redeploy app if prompted.

Notes:
- `FRED_API_KEY` is optional; app still runs without yields.
- SMTP keys are only needed for the **Email** tab send action.

---

## 5) Edit market universe from GitHub UI

The default asset universe is editable in:

- `src/data/universe.yaml`

To modify via browser:
1. Open that file in GitHub.
2. Click the pencil icon (**Edit this file**).
3. Add/remove labels and tickers under any category.
4. Click **Commit changes**.
5. Streamlit app updates after refresh/redeploy.

---

## 6) Security notes

- Never hardcode credentials in source files.
- Use Streamlit Cloud Secrets only.
- `.gitignore` excludes local `.streamlit/secrets.toml`.

---

## 7) Optional local run (if you want)

Not required for deployment.

1. Install Python 3.11+.
2. Install packages from `requirements.txt`.
3. Run Streamlit app with `app.py`.

---

## App limitations

- Free data providers can have delays or symbol gaps.
- Non-trading days create missing rows; optional forward-fill is provided.
- Credit “spread change” values are ETF return proxies, not direct OAS measurements.

---

## License

MIT
