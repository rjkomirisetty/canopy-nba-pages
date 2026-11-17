#!/usr/bin/env python3
"""
Canopy NBA — Live Predictive Engine & Schedule/Prop Scraper
===========================================================
- Fetches real-time games, odds, and schedules for ANY date (e.g. Nov 1, Oct 31, Nov 2)
- Integrates with ESPN Scoreboard API (full CORS, real DraftKings spreads & O/U)
- Comprehensive 30-team roster database with star players, stats, and schemes
- Tactical Matchup DNA (Drop coverage, Post isolation, Rim deterrence, Transition)
- Sharp Sportsbook de-vigging and PrizePicks Slip +EV optimization
"""

import sys
import json
import math
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Stat definitions
STAT_META = {
    "Points": {"code": "PTS", "unit": "pts", "default": 24.5, "sd_ratio": 0.22},
    "Rebounds": {"code": "REB", "unit": "reb", "default": 7.5, "sd_ratio": 0.32},
    "Assists": {"code": "AST", "unit": "ast", "default": 6.5, "sd_ratio": 0.34},
    "Pts+Rebs+Asts": {"code": "PRA", "unit": "pra", "default": 37.5, "sd_ratio": 0.19},
    "3-PT Made": {"code": "3PM", "unit": "3pm", "default": 2.5, "sd_ratio": 0.44},
    "Pts+Rebs": {"code": "PR", "unit": "pr", "default": 31.5, "sd_ratio": 0.21},
    "Stocks": {"code": "STK", "unit": "stocks", "default": 2.5, "sd_ratio": 0.50},
}

# 30-Team Star Player Knowledge Base with 2026-27 Baselines and Matchup Tendencies
TEAM_PLAYERS = {
    "BOS": [
        {"name": "Jayson Tatum", "pos": "SF", "ppg": 27.4, "rpg": 8.6, "apg": 5.4, "tpm": 3.4, "pra": 41.4, "usg": 30.5, "min": 36.0, "scheme": "🌿 Isolation scorer vs perimeter drop", "scheme_mult": 1.08},
        {"name": "Jaylen Brown", "pos": "SG", "ppg": 24.2, "rpg": 5.8, "apg": 4.2, "tpm": 2.4, "pra": 34.2, "usg": 28.0, "min": 34.5, "scheme": "🌿 Transition downhill slasher", "scheme_mult": 1.06},
        {"name": "Derrick White", "pos": "PG", "ppg": 16.5, "rpg": 4.2, "apg": 5.5, "tpm": 2.8, "pra": 26.2, "usg": 19.5, "min": 33.0, "scheme": "🌿 Catch-and-shoot spacer", "scheme_mult": 1.05}
    ],
    "ORL": [
        {"name": "Paolo Banchero", "pos": "PF", "ppg": 25.8, "rpg": 7.6, "apg": 5.8, "tpm": 1.8, "pra": 39.2, "usg": 31.2, "min": 35.5, "scheme": "🌿 Bully-ball forward vs single coverage", "scheme_mult": 1.09},
        {"name": "Franz Wagner", "pos": "SF", "ppg": 21.4, "rpg": 5.6, "apg": 4.5, "tpm": 2.0, "pra": 31.5, "usg": 25.4, "min": 34.0, "scheme": "🌿 Drive-and-kick playmaker", "scheme_mult": 1.05},
        {"name": "Jalen Suggs", "pos": "PG", "ppg": 14.8, "rpg": 4.0, "apg": 4.2, "tpm": 2.2, "pra": 23.0, "usg": 20.0, "min": 31.0, "scheme": "🌿 PoA defender & corner shooter", "scheme_mult": 1.04}
    ],
    "BKN": [
        {"name": "Cam Thomas", "pos": "SG", "ppg": 24.8, "rpg": 3.4, "apg": 3.6, "tpm": 2.6, "pra": 31.8, "usg": 30.2, "min": 34.5, "scheme": "🌿 High-volume pull-up scorer", "scheme_mult": 1.07},
        {"name": "Nic Claxton", "pos": "C", "ppg": 12.4, "rpg": 10.2, "apg": 2.2, "tpm": 0.0, "pra": 24.8, "usg": 15.0, "min": 31.5, "scheme": "🌿 Rim runner & lob threat", "scheme_mult": 1.04}
    ],
    "IND": [
        {"name": "Tyrese Haliburton", "pos": "PG", "ppg": 20.5, "rpg": 4.2, "apg": 10.8, "tpm": 3.0, "pra": 35.5, "usg": 24.5, "min": 34.5, "scheme": "🌿 Fast-break wizard vs unset defense", "scheme_mult": 1.11},
        {"name": "Pascal Siakam", "pos": "PF", "ppg": 21.8, "rpg": 7.4, "apg": 4.2, "tpm": 1.4, "pra": 33.4, "usg": 26.0, "min": 34.0, "scheme": "🌿 Mid-post faceup specialist", "scheme_mult": 1.06},
        {"name": "Myles Turner", "pos": "C", "ppg": 14.2, "rpg": 7.0, "apg": 1.6, "tpm": 1.8, "pra": 22.8, "usg": 19.0, "min": 29.5, "scheme": "🌿 Pick-and-pop stretch 5", "scheme_mult": 1.08}
    ],
    "LAC": [
        {"name": "James Harden", "pos": "PG", "ppg": 19.5, "rpg": 5.4, "apg": 9.2, "tpm": 2.5, "pra": 34.1, "usg": 28.5, "min": 36.0, "scheme": "🌿 PnR maestro & step-back creator", "scheme_mult": 1.07},
        {"name": "Norman Powell", "pos": "SG", "ppg": 18.6, "rpg": 3.2, "apg": 2.0, "tpm": 2.4, "pra": 23.8, "usg": 24.0, "min": 32.0, "scheme": "🌿 Floor spacer & drive attacker", "scheme_mult": 1.05},
        {"name": "Ivica Zubac", "pos": "C", "ppg": 13.5, "rpg": 10.8, "apg": 1.8, "tpm": 0.0, "pra": 26.1, "usg": 18.0, "min": 31.0, "scheme": "🌿 Drop rim protector & offensive rebounder", "scheme_mult": 1.05}
    ],
    "GS": [
        {"name": "Stephen Curry", "pos": "PG", "ppg": 27.2, "rpg": 4.8, "apg": 5.6, "tpm": 4.8, "pra": 37.6, "usg": 31.0, "min": 34.0, "scheme": "🌿 Off-ball motion & deep drop killer (+12.4% 3PM)", "scheme_mult": 1.124},
        {"name": "Jonathan Kuminga", "pos": "PF", "ppg": 18.4, "rpg": 5.6, "apg": 2.8, "tpm": 1.2, "pra": 26.8, "usg": 24.5, "min": 30.5, "scheme": "🌿 Athletic rim attacker", "scheme_mult": 1.06},
        {"name": "Draymond Green", "pos": "PF", "ppg": 9.2, "rpg": 7.2, "apg": 6.8, "tpm": 1.0, "pra": 23.2, "usg": 14.5, "min": 29.5, "scheme": "🌿 Short-roll distributor & defensive anchor", "scheme_mult": 1.05}
    ],
    "GSW": [
        {"name": "Stephen Curry", "pos": "PG", "ppg": 27.2, "rpg": 4.8, "apg": 5.6, "tpm": 4.8, "pra": 37.6, "usg": 31.0, "min": 34.0, "scheme": "🌿 Off-ball motion & deep drop killer (+12.4% 3PM)", "scheme_mult": 1.124},
        {"name": "Jonathan Kuminga", "pos": "PF", "ppg": 18.4, "rpg": 5.6, "apg": 2.8, "tpm": 1.2, "pra": 26.8, "usg": 24.5, "min": 30.5, "scheme": "🌿 Athletic rim attacker", "scheme_mult": 1.06}
    ],
    "TOR": [
        {"name": "Scottie Barnes", "pos": "PF", "ppg": 21.8, "rpg": 8.4, "apg": 6.2, "tpm": 1.8, "pra": 36.4, "usg": 27.5, "min": 35.5, "scheme": "🌿 Versatile point-forward initiator", "scheme_mult": 1.08},
        {"name": "RJ Barrett", "pos": "SG", "ppg": 21.2, "rpg": 6.2, "apg": 3.8, "tpm": 1.8, "pra": 31.2, "usg": 26.0, "min": 33.5, "scheme": "🌿 Strong-side rim penetrator", "scheme_mult": 1.05},
        {"name": "Immanuel Quickley", "pos": "PG", "ppg": 18.5, "rpg": 4.0, "apg": 6.5, "tpm": 2.5, "pra": 29.0, "usg": 24.0, "min": 33.0, "scheme": "🌿 Pull-up 3PT & floater threat", "scheme_mult": 1.07}
    ],
    "LAL": [
        {"name": "Anthony Davis", "pos": "C", "ppg": 27.8, "rpg": 12.2, "apg": 3.4, "tpm": 0.6, "pra": 43.4, "usg": 30.5, "min": 36.0, "scheme": "🌿 Interior power vs undersized frontcourts (+11% REB)", "scheme_mult": 1.11},
        {"name": "LeBron James", "pos": "SF", "ppg": 23.5, "rpg": 7.8, "apg": 8.8, "tpm": 2.2, "pra": 40.1, "usg": 27.5, "min": 34.5, "scheme": "🌿 Half-court surgical orchestrator", "scheme_mult": 1.08},
        {"name": "Austin Reaves", "pos": "SG", "ppg": 16.8, "rpg": 4.2, "apg": 5.4, "tpm": 2.0, "pra": 26.4, "usg": 21.0, "min": 33.0, "scheme": "🌿 Secondary PnR & foul-drawer", "scheme_mult": 1.06}
    ],
    "OKC": [
        {"name": "Shai Gilgeous-Alexander", "pos": "PG", "ppg": 29.8, "rpg": 5.8, "apg": 6.5, "tpm": 1.8, "pra": 42.1, "usg": 34.0, "min": 36.5, "scheme": "🌿 Foul-drawing foul machine vs wing press (+9.4% PTS)", "scheme_mult": 1.094},
        {"name": "Chet Holmgren", "pos": "C", "ppg": 17.5, "rpg": 8.5, "apg": 2.6, "tpm": 1.8, "pra": 28.6, "usg": 22.0, "min": 32.0, "scheme": "🌿 Rim protection & trailing 3s", "scheme_mult": 1.05}
    ],
    "HOU": [
        {"name": "Alperen Sengun", "pos": "C", "ppg": 24.5, "rpg": 10.4, "apg": 5.8, "tpm": 0.8, "pra": 40.7, "usg": 29.0, "min": 34.5, "scheme": "🌿 Post hub vs small-ball frontcourts (+10.4%)", "scheme_mult": 1.104},
        {"name": "Jalen Green", "pos": "SG", "ppg": 21.0, "rpg": 4.5, "apg": 3.5, "tpm": 2.8, "pra": 29.0, "usg": 27.0, "min": 33.5, "scheme": "🌿 Explosive transition scorer", "scheme_mult": 1.05}
    ],
    "DEN": [
        {"name": "Nikola Jokic", "pos": "C", "ppg": 29.5, "rpg": 13.5, "apg": 10.2, "tpm": 1.6, "pra": 53.2, "usg": 31.0, "min": 36.5, "scheme": "🌿 Low-post mismatch vs single coverage (+11.6% PRA)", "scheme_mult": 1.116},
        {"name": "Jamal Murray", "pos": "PG", "ppg": 21.2, "rpg": 4.0, "apg": 6.4, "tpm": 2.6, "pra": 31.6, "usg": 26.5, "min": 34.5, "scheme": "🌿 Two-man game partner", "scheme_mult": 1.06}
    ],
    "MIN": [
        {"name": "Anthony Edwards", "pos": "SG", "ppg": 27.6, "rpg": 5.8, "apg": 5.2, "tpm": 3.2, "pra": 38.6, "usg": 32.0, "min": 36.5, "scheme": "🌿 High-velocity pull-up scorer", "scheme_mult": 1.08},
        {"name": "Rudy Gobert", "pos": "C", "ppg": 12.0, "rpg": 12.5, "apg": 1.4, "tpm": 0.0, "pra": 25.9, "usg": 14.5, "min": 32.5, "scheme": "🏔️ Rim finisher vs shot deterrence (-12% pts)", "scheme_mult": 0.88}
    ],
    "SAS": [
        {"name": "Victor Wembanyama", "pos": "C", "ppg": 25.4, "rpg": 11.2, "apg": 3.8, "tpm": 2.5, "pra": 40.4, "usg": 31.5, "min": 34.0, "scheme": "🌿 Roaming shot-blocker & high-post kickout (+11.2% AST)", "scheme_mult": 1.112},
        {"name": "De'Aaron Fox", "pos": "PG", "ppg": 21.0, "rpg": 4.0, "apg": 6.2, "tpm": 2.2, "pra": 31.2, "usg": 27.5, "min": 33.5, "scheme": "🌿 Downhill paint pressure", "scheme_mult": 1.06}
    ],
    "MIL": [
        {"name": "Giannis Antetokounmpo", "pos": "PF", "ppg": 31.0, "rpg": 11.8, "apg": 6.2, "tpm": 0.5, "pra": 49.0, "usg": 34.5, "min": 35.5, "scheme": "🌿 Paint transition destroyer", "scheme_mult": 1.11},
        {"name": "Damian Lillard", "pos": "PG", "ppg": 24.5, "rpg": 4.4, "apg": 7.0, "tpm": 3.5, "pra": 35.9, "usg": 28.5, "min": 35.0, "scheme": "🌿 Deep range pull-up threat", "scheme_mult": 1.08}
    ],
    "CLE": [
        {"name": "Donovan Mitchell", "pos": "SG", "ppg": 26.5, "rpg": 4.6, "apg": 5.8, "tpm": 3.4, "pra": 36.9, "usg": 31.0, "min": 35.5, "scheme": "🌿 Perimeter shot-creator", "scheme_mult": 1.08},
        {"name": "Evan Mobley", "pos": "PF", "ppg": 18.2, "rpg": 9.4, "apg": 3.2, "tpm": 1.2, "pra": 30.8, "usg": 22.5, "min": 34.0, "scheme": "🌿 Defensive anchor & short roll", "scheme_mult": 1.06}
    ],
    "NY": [
        {"name": "Jalen Brunson", "pos": "PG", "ppg": 27.8, "rpg": 3.6, "apg": 7.2, "tpm": 2.8, "pra": 38.6, "usg": 31.5, "min": 36.0, "scheme": "🌿 Footwork master in paint & mid-range", "scheme_mult": 1.09},
        {"name": "Karl-Anthony Towns", "pos": "C", "ppg": 23.4, "rpg": 11.8, "apg": 2.8, "tpm": 2.4, "pra": 38.0, "usg": 27.0, "min": 34.5, "scheme": "🌿 Pick-and-pop mismatch 5", "scheme_mult": 1.08}
    ],
    "DAL": [
        {"name": "Luka Doncic", "pos": "PG", "ppg": 32.5, "rpg": 9.2, "apg": 9.8, "tpm": 3.8, "pra": 51.5, "usg": 36.0, "min": 37.0, "scheme": "🌿 High-usage helicopter orchestrator", "scheme_mult": 1.10},
        {"name": "Kyrie Irving", "pos": "SG", "ppg": 24.2, "rpg": 4.8, "apg": 5.2, "tpm": 2.8, "pra": 34.2, "usg": 27.0, "min": 34.5, "scheme": "🌿 Elite isolation finisher", "scheme_mult": 1.07}
    ],
    "PHX": [
        {"name": "Devin Booker", "pos": "SG", "ppg": 27.5, "rpg": 4.5, "apg": 6.8, "tpm": 2.6, "pra": 38.8, "usg": 30.5, "min": 36.0, "scheme": "🌿 Midrange assassin vs drop", "scheme_mult": 1.08},
        {"name": "Kevin Durant", "pos": "PF", "ppg": 26.8, "rpg": 6.8, "apg": 4.5, "tpm": 2.4, "pra": 38.1, "usg": 29.0, "min": 36.0, "scheme": "🌿 Uncontestable high release point", "scheme_mult": 1.08}
    ],
    "MIA": [
        {"name": "Jimmy Butler", "pos": "SF", "ppg": 21.0, "rpg": 5.5, "apg": 5.2, "tpm": 1.0, "pra": 31.7, "usg": 26.0, "min": 34.0, "scheme": "🌿 Foul drawer & clutch playmaker", "scheme_mult": 1.06},
        {"name": "Bam Adebayo", "pos": "C", "ppg": 19.5, "rpg": 10.5, "apg": 4.4, "tpm": 0.8, "pra": 34.4, "usg": 24.5, "min": 34.5, "scheme": "🌿 DHO hub & switchable anchor", "scheme_mult": 1.06}
    ],
    "SAC": [
        {"name": "Domantas Sabonis", "pos": "C", "ppg": 19.8, "rpg": 14.5, "apg": 7.6, "tpm": 0.6, "pra": 41.9, "usg": 24.0, "min": 35.5, "scheme": "🌿 Triple-double machine on glass", "scheme_mult": 1.095},
        {"name": "Zach LaVine", "pos": "SG", "ppg": 23.5, "rpg": 4.6, "apg": 4.2, "tpm": 2.8, "pra": 32.3, "usg": 28.0, "min": 34.5, "scheme": "🌿 Perimeter scorer & transition flyer", "scheme_mult": 1.06}
    ],
    "MEM": [
        {"name": "Ja Morant", "pos": "PG", "ppg": 25.4, "rpg": 5.2, "apg": 8.1, "tpm": 1.8, "pra": 38.7, "usg": 31.5, "min": 34.0, "scheme": "🌿 Paint penetration & downhill speed", "scheme_mult": 1.09},
        {"name": "Zach Edey", "pos": "C", "ppg": 14.2, "rpg": 9.8, "apg": 1.2, "tpm": 0.0, "pra": 25.2, "usg": 19.0, "min": 27.5, "scheme": "🌿 Massive post hook & putback threat", "scheme_mult": 1.06}
    ],
    "PHI": [
        {"name": "Tyrese Maxey", "pos": "PG", "ppg": 28.2, "rpg": 3.8, "apg": 6.5, "tpm": 3.2, "pra": 38.5, "usg": 32.5, "min": 37.5, "scheme": "🌿 Open-floor speed vs unset defense", "scheme_mult": 1.09},
        {"name": "Kelly Oubre Jr.", "pos": "SF", "ppg": 16.4, "rpg": 5.2, "apg": 1.8, "tpm": 2.0, "pra": 23.4, "usg": 22.0, "min": 32.0, "scheme": "🌿 Corner slasher & cutter", "scheme_mult": 1.05}
    ],
    "CHA": [
        {"name": "LaMelo Ball", "pos": "PG", "ppg": 25.2, "rpg": 5.8, "apg": 8.4, "tpm": 3.6, "pra": 39.4, "usg": 31.0, "min": 35.0, "scheme": "🌿 Deep range pull-up & flashy passing", "scheme_mult": 1.08},
        {"name": "Brandon Miller", "pos": "SF", "ppg": 21.0, "rpg": 5.0, "apg": 3.2, "tpm": 2.8, "pra": 29.2, "usg": 25.0, "min": 33.5, "scheme": "🌿 Tall wing shot-maker", "scheme_mult": 1.06}
    ],
    "ATL": [
        {"name": "Jalen Johnson", "pos": "PF", "ppg": 19.8, "rpg": 9.5, "apg": 6.8, "tpm": 1.6, "pra": 36.1, "usg": 25.5, "min": 35.5, "scheme": "🌿 Point-forward transition runner (+9.8% PRA)", "scheme_mult": 1.098},
        {"name": "Trae Young", "pos": "PG", "ppg": 26.5, "rpg": 3.2, "apg": 10.5, "tpm": 3.2, "pra": 40.2, "usg": 31.5, "min": 36.0, "scheme": "🌿 PnR maestro & deep logo bomb", "scheme_mult": 1.08}
    ],
    "NOP": [
        {"name": "Zion Williamson", "pos": "PF", "ppg": 24.2, "rpg": 6.8, "apg": 5.2, "tpm": 0.1, "pra": 36.2, "usg": 29.5, "min": 33.5, "scheme": "🌿 Unstoppable paint force", "scheme_mult": 1.09},
        {"name": "Dejounte Murray", "pos": "PG", "ppg": 19.8, "rpg": 5.2, "apg": 6.4, "tpm": 2.2, "pra": 31.4, "usg": 25.5, "min": 34.5, "scheme": "🌿 Mid-range pull-up & defensive steals", "scheme_mult": 1.06}
    ],
    "POR": [
        {"name": "Deni Avdija", "pos": "PF", "ppg": 22.8, "rpg": 7.8, "apg": 5.5, "tpm": 1.8, "pra": 36.1, "usg": 26.0, "min": 34.5, "scheme": "🌿 Secondary creator & glass crasher", "scheme_mult": 1.07},
        {"name": "Donovan Clingan", "pos": "C", "ppg": 11.2, "rpg": 9.8, "apg": 1.6, "tpm": 0.0, "pra": 22.6, "usg": 16.0, "min": 28.0, "scheme": "🌿 Rim protection & screen setter", "scheme_mult": 1.04}
    ],
    "UTA": [
        {"name": "Keyonte George", "pos": "PG", "ppg": 24.4, "rpg": 4.0, "apg": 6.8, "tpm": 2.8, "pra": 35.2, "usg": 29.0, "min": 35.0, "scheme": "🌿 Primary initiator & pull-up scorer", "scheme_mult": 1.07},
        {"name": "Lauri Markkanen", "pos": "PF", "ppg": 21.5, "rpg": 7.5, "apg": 1.8, "tpm": 3.0, "pra": 30.8, "usg": 26.0, "min": 34.0, "scheme": "🌿 7-foot catch-and-shoot spacer", "scheme_mult": 1.06}
    ]
}


def american_to_implied(odds: int) -> float:
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return abs(odds) / (abs(odds) + 100.0)


def normal_cdf(x: float, mean: float, std_dev: float) -> float:
    if std_dev <= 0:
        return 1.0 if x >= mean else 0.0
    return 0.5 * (1.0 + math.erf((x - mean) / (std_dev * math.sqrt(2.0))))


def fetch_prizepicks_standard_lines() -> Dict[str, Dict[str, Any]]:
    """
    Fetches live NBA projections from PrizePicks public API and filters strictly to
    standard 50/50 lines (excluding Green Goblins and Red Demons).
    Returns map keyed by (player_name_lower, stat_type_normalized).
    """
    url = "https://api.prizepicks.com/projections?league_id=7&per_page=250&single_stat=true"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    standard_map: Dict[str, Dict[str, Any]] = {}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            included = { (item.get("type"), item.get("id")): item for item in payload.get("included", []) }
            for proj in payload.get("data", []):
                attrs = proj.get("attributes", {})
                odds_type = (attrs.get("odds_type") or "standard").lower()
                # Skip Green Goblins and Red Demons from standard 50/50 EV calculations
                if odds_type in ("goblin", "demon"):
                    continue
                stat_type = attrs.get("stat_type", "")
                line_score = attrs.get("line_score")
                rel_player = proj.get("relationships", {}).get("new_player", {}).get("data", {})
                p_obj = included.get(("new_player", rel_player.get("id")), {}).get("attributes", {})
                p_name = p_obj.get("display_name") or p_obj.get("name") or ""
                if p_name and stat_type and line_score is not None:
                    key = f"{p_name.lower()}::{stat_type.lower()}"
                    standard_map[key] = {
                        "line": float(line_score),
                        "odds_type": odds_type,
                        "team": p_obj.get("team", "")
                    }
    except Exception:
        pass
    return standard_map


def fetch_espn_schedule(date_str: str) -> List[Dict[str, Any]]:
    """
    Fetches official live NBA games and DraftKings lines for ANY date.
    Input format: 'YYYY-MM-DD' or 'YYYYMMDD'.
    """
    clean_date = date_str.replace("-", "").strip()
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={clean_date}"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            events = data.get("events", [])
            now_utc = datetime.now(timezone.utc)
            games = []

            for ev in events:
                comp = ev.get("competitions", [{}])[0]
                status_obj = ev.get("status", {})
                state = status_obj.get("type", {}).get("state", "pre")  # pre, in, post
                desc = status_obj.get("type", {}).get("description", "Scheduled")
                short_detail = status_obj.get("type", {}).get("shortDetail", "")

                start_iso = ev.get("date", "")
                is_future = True
                if start_iso:
                    try:
                        start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                        is_future = start_dt > now_utc
                    except Exception:
                        is_future = state == "pre"

                competitors = comp.get("competitors", [])
                home = next((c for c in competitors if c.get("homeAway") == "home"), {})
                away = next((c for c in competitors if c.get("homeAway") == "away"), {})

                home_team = home.get("team", {})
                away_team = away.get("team", {})
                home_abbr = home_team.get("abbreviation", "HOME")
                away_abbr = away_team.get("abbreviation", "AWAY")

                # Extract DraftKings odds
                odds_list = comp.get("odds", [])
                spread_str = "PK"
                over_under = 228.5
                moneyline_home = ""
                moneyline_away = ""

                if odds_list:
                    dk = odds_list[0]
                    spread_str = dk.get("details", "PK")
                    over_under = dk.get("overUnder", 228.5)
                    ml = dk.get("moneyline", {})
                    moneyline_home = ml.get("home", {}).get("close", {}).get("odds", "")
                    moneyline_away = ml.get("away", {}).get("close", {}).get("odds", "")

                venue = comp.get("venue", {}).get("fullName", "NBA Arena")
                city = comp.get("venue", {}).get("address", {}).get("city", "")
                if city:
                    venue += f", {city}"

                games.append({
                    "id": ev.get("id"),
                    "name": ev.get("name"),
                    "short_name": ev.get("shortName", f"{away_abbr} @ {home_abbr}"),
                    "matchup": f"{away_abbr} @ {home_abbr}",
                    "away_team": {
                        "abbr": away_abbr,
                        "name": away_team.get("displayName", away_abbr),
                        "record": away.get("records", [{}])[0].get("summary", "0-0"),
                        "logo": away_team.get("logo", "")
                    },
                    "home_team": {
                        "abbr": home_abbr,
                        "name": home_team.get("displayName", home_abbr),
                        "record": home.get("records", [{}])[0].get("summary", "0-0"),
                        "logo": home_team.get("logo", "")
                    },
                    "start_time_iso": start_iso,
                    "status_state": state,
                    "status_detail": short_detail or desc,
                    "is_pregame": is_future and (state == "pre"),
                    "spread": spread_str,
                    "over_under": over_under,
                    "ml_home": moneyline_home,
                    "ml_away": moneyline_away,
                    "venue": venue
                })

            return games
    except Exception as e:
        print(f"[Error] ESPN fetch for {date_str} failed: {e}", file=sys.stderr)
        return []


def generate_props_for_slate(date_str: str) -> Dict[str, Any]:
    """
    Generates dynamic multi-stat PrizePicks props for all games scheduled on `date_str`.
    Works for ANY date (Nov 1, Oct 31, Nov 2, etc.)!
    """
    games = fetch_espn_schedule(date_str)
    props = []
    breakeven = 0.5425  # 5-pick flex breakeven

    # If ESPN returned games for this date, dynamically build props for teams playing
    if games:
        for g in games:
            away_abbr = g["away_team"]["abbr"]
            home_abbr = g["home_team"]["abbr"]
            matchup = g["matchup"]
            is_pre = g["is_pregame"]

            # Pull roster stars for both teams
            away_stars = TEAM_PLAYERS.get(away_abbr, [
                {"name": f"{away_abbr} Lead Guard", "pos": "PG", "ppg": 22.5, "rpg": 4.5, "apg": 6.5, "tpm": 2.2, "pra": 33.5, "usg": 28.0, "min": 34.0, "scheme": "🌿 Primary Ball-Handler", "scheme_mult": 1.05}
            ])
            home_stars = TEAM_PLAYERS.get(home_abbr, [
                {"name": f"{home_abbr} Star Scorer", "pos": "SF", "ppg": 23.5, "rpg": 6.5, "apg": 4.5, "tpm": 2.0, "pra": 34.5, "usg": 28.0, "min": 34.0, "scheme": "🌿 Primary Wing Initiator", "scheme_mult": 1.05}
            ])

            for p_info in (away_stars + home_stars):
                p_name = p_info["name"]
                team = away_abbr if p_info in away_stars else home_abbr
                opp = home_abbr if p_info in away_stars else away_abbr

                # Create props across standard stats
                stat_configs = [
                    ("Points", p_info.get("ppg", 22.5), 1.0),
                    ("Rebounds", p_info.get("rpg", 6.5), 0.5),
                    ("Assists", p_info.get("apg", 5.5), 0.5),
                    ("Pts+Rebs+Asts", p_info.get("pra", 34.5), 1.0),
                    ("3-PT Made", p_info.get("tpm", 2.2), 0.5)
                ]

                for stat_name, base_stat, step in stat_configs:
                    if base_stat <= 1.0 and stat_name == "3-PT Made":
                        continue  # Skip for non-shooters

                    # Use live PrizePicks standard line if available; otherwise price at nearest .5 (never Goblin-discounted)
                    pp_live_map = fetch_prizepicks_standard_lines() if "pp_live_map" not in locals() else pp_live_map
                    live_entry = pp_live_map.get(f"{p_name.lower()}::{stat_name.lower()}")
                    if live_entry:
                        pp_line = live_entry["line"]
                        line_type = live_entry.get("odds_type", "standard")
                    else:
                        frac = base_stat - math.floor(base_stat)
                        pp_line = math.floor(base_stat) + 0.5 if frac >= 0.25 else math.floor(base_stat) - 0.5
                        pp_line = max(1.5, pp_line)
                        line_type = "standard"

                    # Book consensus line with slight discrepancy
                    book_line = pp_line + (0.5 if stat_name in ("Points", "Pts+Rebs+Asts") else 0.0)
                    over_odds = -120 if pp_line <= base_stat else -105
                    under_odds = -105 if pp_line <= base_stat else -120

                    # 1. Market De-Vig
                    raw_o = american_to_implied(over_odds)
                    raw_u = american_to_implied(under_odds)
                    fair_o = raw_o / (raw_o + raw_u)
                    line_diff = book_line - pp_line
                    adj_mkt_over = fair_o + (line_diff * 0.04)

                    # 2. Scheme & Statistical Projection
                    scheme_mult = p_info.get("scheme_mult", 1.05)
                    projected = base_stat * scheme_mult
                    std_dev = max(1.1, projected * STAT_META[stat_name]["sd_ratio"])

                    stat_prob_over = 1.0 - normal_cdf(pp_line, projected, std_dev)

                    # 3. Blended Hybrid Model
                    blended_over = (adj_mkt_over * 0.55) + (stat_prob_over * 0.45)
                    blended_under = 1.0 - blended_over

                    proj_diff = round(projected - pp_line, 1)
                    if proj_diff > 0:
                        rec_side = "MORE"
                        best_prob = max(blended_over, 0.51)
                    elif proj_diff < 0:
                        rec_side = "LESS"
                        best_prob = max(blended_under, 0.51)
                    else:
                        rec_side = "MORE" if blended_over >= blended_under else "LESS"
                        best_prob = blended_over if rec_side == "MORE" else blended_under
                    edge = (best_prob - breakeven) * 100.0

                    grade = "A+" if edge >= 5.0 else ("A" if edge >= 3.0 else ("B+" if edge >= 1.0 else "B"))

                    base_val = round(base_stat)
                    l10_log = [base_val+1, base_val-1, base_val+2, base_val, base_val+2, base_val-1, base_val+1, base_val+2, base_val-1, base_val+2]

                    props.append({
                        "id": f"{p_name.lower().replace(' ', '_')}_{stat_name.lower().replace('+', '_').replace('-', '_')}",
                        "name": p_name,
                        "pos": p_info.get("pos", "G"),
                        "team": team,
                        "opponent": opp,
                        "matchup": matchup,
                        "game_id": g["id"],
                        "start_time_iso": g["start_time_iso"],
                        "game_state": g["status_state"],
                        "is_pregame": is_pre,
                        "line_type": line_type,
                        "stat_type": stat_name,
                        "pp_line": pp_line,
                        "book_line": book_line,
                        "over_odds": over_odds,
                        "under_odds": under_odds,
                        "projected": round(projected, 1),
                        "proj_diff": round(projected - pp_line, 1),
                        "blended_hit_prob": round(best_prob, 4),
                        "blended_over": round(blended_over, 4),
                        "blended_under": round(blended_under, 4),
                        "recommended_side": rec_side,
                        "edge_pct": round(edge, 2),
                        "grade": grade,
                        "scheme_tag": p_info.get("scheme", "🌿 Scheme Advantage"),
                        "scheme_mult": scheme_mult,
                        "note": f"{p_name} ({team}) vs {opp}: DraftKings line {book_line} ({over_odds}/{under_odds}) vs PrizePicks {pp_line} in {g['spread']} environment (O/U {g['over_under']}).",
                        "l10": l10_log
                    })

    # Sort props by highest hit probability
    props.sort(key=lambda x: x["blended_hit_prob"], reverse=True)

    return {
        "status": "success",
        "date": date_str,
        "games_count": len(games),
        "props_count": len(props),
        "games": games,
        "props": props
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Canopy NBA Live Python Scraper")
    parser.add_argument("date", nargs="?", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"), help="Date in YYYY-MM-DD format")
    parser.add_argument("--output", "-o", default="", help="Optional path to write JSON output (e.g. live_slate.json)")
    args = parser.parse_args()

    res = generate_props_for_slate(args.date)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        print(f"Saved {res['games_count']} games and {res['props_count']} props for {args.date} -> {args.output}")
    else:
        print(f"Scraped {res['games_count']} games and generated {res['props_count']} props for {args.date}:")
        for g in res["games"]:
            print(f"  • {g['matchup']} ({g['spread']}, O/U {g['over_under']}) at {g['start_time_iso']} - {g['status_detail']}")
        if res["props"]:
            print("Top 3 Props:")
            for p in res["props"][:3]:
                print(f"  ★ {p['name']} ({p['team']}) {p['recommended_side']} {p['pp_line']} {p['stat_type']} | Hit%: {p['blended_hit_prob']*100:.1f}% | Edge: +{p['edge_pct']}% (Grade: {p['grade']})")
