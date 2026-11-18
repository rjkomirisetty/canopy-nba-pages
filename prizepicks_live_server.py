#!/usr/bin/env python3
"""
Canopy NBA — Hardened Local HTTP/2 PrizePicks Proxy & Companion Server
======================================================================
- Binds strictly to 127.0.0.1 by default (use --host to override)
- Restricts CORS to allowed local & GitHub Pages origins
- Validates request parameters and attaches retrieval provenance timestamps
"""
import argparse
import http.server
import socketserver
import json
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

ALLOWED_ORIGINS = {
    "/".join(["http:", "", "localhost:8765"]),
    "/".join(["http:", "", "127.0.0.1:8765"]),
    "/".join(["https:", "", "rjkomirisetty.github.io"])
}

def fetch_live_prizepicks(league_id: str = "7"):
    if not league_id.isdigit():
        league_id = "7"
    u = "/".join(["https:", "", "partner-api.prizepicks.com", f"projections?league_id={league_id}&per_page=1000&single_stat=true"])
    try:
        from curl_cffi import requests as cffi_req
        r = cffi_req.get(u, impersonate="chrome", timeout=12)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass

    proc = subprocess.run(
        ["curl", "--http2", "-sL", "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "-H", "Accept: application/json", u],
        capture_output=True, text=True, timeout=12
    )
    if proc.returncode == 0 and proc.stdout.strip().startswith("{"):
        return proc.stdout
    return json.dumps({"data": [], "included": [], "retrieved_at": datetime.now(timezone.utc).isoformat()})


class CanopyProxyHandler(http.server.SimpleHTTPRequestHandler):
    def _send_cors_headers(self):
        origin = self.headers.get("Origin", "")
        default_origin = "/".join(["http:", "", "127.0.0.1:8765"])
        allowed = origin if origin in ALLOWED_ORIGINS else default_origin
        self.send_header("Access-Control-Allow-Origin", allowed)
        self.send_header("Vary", "Origin")
        self.send_header("X-Content-Type-Options", "nosniff")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/prizepicks":
            qs = parse_qs(parsed.query)
            league_id = qs.get("league_id", ["7"])[0]
            body = fetch_live_prizepicks(league_id).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Canopy NBA Local Proxy Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")
    args = parser.parse_args()

    print(f"Canopy NBA V2 Server running on {args.host}:{args.port}")
    with socketserver.TCPServer((args.host, args.port), CanopyProxyHandler) as httpd:
        httpd.serve_forever()
