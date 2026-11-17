#!/usr/bin/env python3
"""
Canopy NBA Companion Server (`prizepicks_live_server.py`)
=========================================================
Runs on http://0.0.0.0:8765 to serve the Canopy web app and provide
live CORS-free endpoints for:
1. `/api/prizepicks`: Raw PrizePicks projections proxy (bypasses browser CORS).
2. `/api/slate`: Multi-source pre-game predictions.
"""

import os
import sys
import json
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler

try:
    import canopy_nba_engine
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import canopy_nba_engine

PRIZEPICKS_URL = "https://api.prizepicks.com/projections?league_id=7&per_page=250&single_stat=true"
PARTNER_PP_URL = "https://partner-api.prizepicks.com/projections?league_id=7&per_page=250"


class CanopyServerHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/slate") or self.path.startswith("/api/refresh"):
            try:
                from datetime import datetime, timezone, timedelta
                us_ct = datetime.now(timezone(timedelta(hours=-6))).strftime("%Y-%m-%d")
                slate_data = canopy_nba_engine.generate_props_for_slate(us_ct)
                response_bytes = json.dumps(slate_data, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(response_bytes)
                return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        if self.path.startswith("/api/prizepicks"):
            for url in (PARTNER_PP_URL, PRIZEPICKS_URL):
                try:
                    req = urllib.request.Request(
                        url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                            "Accept": "application/json",
                            "Referer": "https://app.prizepicks.com/",
                        },
                    )
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        body = resp.read()
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(body)
                        return
                except Exception:
                    continue
            self.send_response(502)
            self.end_headers()
            self.wfile.write(b'{"error": "PrizePicks upstream temporarily blocked by Cloudflare"}')
            return

        if self.path == "/" or self.path == "":
            self.path = "/index.html"

        return super().do_GET()


if __name__ == "__main__":
    port = 8765
    print(f"🌲 Canopy NBA Live Engine Server running at:")
    print(f"   http://0.0.0.0:{port}/prizepicks_nba_predictor.html")
    print(f"   http://0.0.0.0:{port}/api/slate")
    HTTPServer(("0.0.0.0", port), CanopyServerHandler).serve_forever()
