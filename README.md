# Canopy NBA — Live Multi-Source PrizePicks & Sportsbook Predictor

This repository powers an independent mobile-ready web app hosted on **GitHub Pages** (`index.html`) paired with an automated Python multi-source scraper (`canopy_nba_engine.py`).

## How It Works on GitHub
1. **Instant Mobile Web App (`index.html`)**: Served via **GitHub Pages** at `https://<your-username>.github.io/<your-repo-name>/`. Every time you open the link or change the date on your phone, the built-in 4-source browser engine fetches live schedules, DraftKings/FanDuel Pickcenter odds, 30-team injury reports, and active player box scores in real time.
2. **Automated Cloud Python Scraping (`canopy_nba_engine.py` + `.github/workflows/deploy.yml`)**: Because GitHub Pages hosts static files rather than a persistent Python server, **GitHub Actions** runs `canopy_nba_engine.py` automatically in the cloud every 30 minutes (or whenever you tap **Run workflow**), saves the fresh multi-source output to `live_slate.json`, and publishes the updated site.

## 2-Minute Setup on GitHub
1. Create a new repository on [GitHub](https://github.com/new) (for example, `canopy-nba`).
2. Upload or push the files in this folder (`index.html`, `canopy_nba_engine.py`, `prizepicks_live_server.py`, and `.github/workflows/deploy.yml`).
3. In your GitHub repository, go to **Settings → Pages**, and under **Build and deployment → Source**, select **GitHub Actions** (or **Deploy from a branch → `main` / `/ (root)`**).
4. Your permanent mobile web link will be live at `https://<your-username>.github.io/canopy-nba/`.
