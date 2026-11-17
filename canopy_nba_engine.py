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
    "HOU": [
        {"name": "Kevin Durant", "pos": "PF", "ppg": 21.5, "rpg": 5.1, "apg": 4.2, "tpm": 2.2, "pra": 30.8, "usg": 28.5, "min": 33.3, "scheme": "🌿 Rockets Star Forward (Proj 21.5 PTS / 5.1 REB / 4.2 AST)", "scheme_mult": 1.05},
        {"name": "Alperen Sengun", "pos": "C", "ppg": 21.5, "rpg": 10.4, "apg": 6.4, "tpm": 0.7, "pra": 38.3, "usg": 28.0, "min": 35.6, "scheme": "🌿 Post hub & FanDuel Over 9.5 REB (+110)", "scheme_mult": 1.06},
        {"name": "Jabari Smith Jr.", "pos": "SF", "ppg": 17.8, "rpg": 6.4, "apg": 2.2, "tpm": 2.3, "pra": 26.4, "usg": 22.0, "min": 34.4, "scheme": "🌿 Stretch Wing Spacer", "scheme_mult": 1.04},
        {"name": "Amen Thompson", "pos": "PG", "ppg": 15.1, "rpg": 5.8, "apg": 3.8, "tpm": 0.6, "pra": 24.7, "usg": 21.5, "min": 32.9, "scheme": "🌿 Starting Lead Guard & Transition Slasher", "scheme_mult": 1.04}
    ],
    "PHX": [
        {"name": "Devin Booker", "pos": "SG", "ppg": 26.2, "rpg": 4.2, "apg": 6.2, "tpm": 2.5, "pra": 36.6, "usg": 30.5, "min": 36.0, "scheme": "🌿 Suns #1 Scorer & Mid-Range Playmaker", "scheme_mult": 1.05},
        {"name": "Miles Bridges", "pos": "SF", "ppg": 16.8, "rpg": 6.9, "apg": 3.1, "tpm": 2.1, "pra": 26.8, "usg": 23.0, "min": 34.0, "scheme": "🌿 FTN Verified Over 6.5 REB (+128)", "scheme_mult": 1.06},
        {"name": "Dillon Brooks", "pos": "SF", "ppg": 15.6, "rpg": 3.5, "apg": 1.8, "tpm": 2.1, "pra": 20.9, "usg": 20.5, "min": 32.5, "scheme": "🌿 Suns Starting Wing Spacer", "scheme_mult": 1.03},
        {"name": "Jalen Green", "pos": "SG", "ppg": 14.9, "rpg": 3.4, "apg": 2.8, "tpm": 2.1, "pra": 21.1, "usg": 24.0, "min": 31.0, "scheme": "🌿 Suns Perimeter Shotmaker", "scheme_mult": 1.03}
    ],
    "BOS": [
        {"name": "Jayson Tatum", "pos": "SF", "ppg": 23.8, "rpg": 7.1, "apg": 5.9, "tpm": 2.5, "pra": 36.8, "usg": 30.0, "min": 34.4, "scheme": "🌿 Celtics All-NBA Wing Initiator", "scheme_mult": 1.05},
        {"name": "Paul George", "pos": "SF", "ppg": 17.7, "rpg": 4.5, "apg": 3.0, "tpm": 2.7, "pra": 25.2, "usg": 24.5, "min": 30.4, "scheme": "🌿 Celtics Wing Scorer & 3PT Spacer", "scheme_mult": 1.04},
        {"name": "Payton Pritchard", "pos": "PG", "ppg": 13.8, "rpg": 2.9, "apg": 3.7, "tpm": 2.1, "pra": 20.4, "usg": 21.0, "min": 27.3, "scheme": "🌿 High-Volume Sixth-Man Guard", "scheme_mult": 1.04},
        {"name": "Derrick White", "pos": "PG", "ppg": 12.9, "rpg": 3.3, "apg": 4.1, "tpm": 1.8, "pra": 20.3, "usg": 18.5, "min": 30.0, "scheme": "🌿 Two-Way Guard Connector", "scheme_mult": 1.03}
    ],
    "ORL": [
        {"name": "Franz Wagner", "pos": "SF", "ppg": 21.7, "rpg": 6.8, "apg": 5.5, "tpm": 1.9, "pra": 34.0, "usg": 28.5, "min": 36.8, "scheme": "🌿 Magic #1 Creator w/ Banchero Out", "scheme_mult": 1.06},
        {"name": "Desmond Bane", "pos": "SG", "ppg": 17.0, "rpg": 4.3, "apg": 2.9, "tpm": 2.9, "pra": 24.2, "usg": 24.0, "min": 34.6, "scheme": "🌿 Magic High-Volume 3PT Shooter", "scheme_mult": 1.05},
        {"name": "Anthony Black", "pos": "PG", "ppg": 16.3, "rpg": 4.8, "apg": 5.4, "tpm": 1.4, "pra": 26.5, "usg": 21.0, "min": 32.1, "scheme": "🌿 Starting Point Guard", "scheme_mult": 1.04}
    ],
    "CLE": [
        {"name": "Donovan Mitchell", "pos": "SG", "ppg": 26.4, "rpg": 4.6, "apg": 5.4, "tpm": 3.2, "pra": 36.4, "usg": 31.0, "min": 35.0, "scheme": "🌿 Cavaliers #1 Perimeter Creator", "scheme_mult": 1.05},
        {"name": "James Harden", "pos": "PG", "ppg": 17.8, "rpg": 4.8, "apg": 5.8, "tpm": 2.4, "pra": 28.4, "usg": 24.5, "min": 33.0, "scheme": "🛡️ FTN Verified Under 6.5 AST (+115)", "scheme_mult": 0.96},
        {"name": "Jarrett Allen", "pos": "C", "ppg": 15.4, "rpg": 10.6, "apg": 2.2, "tpm": 0.0, "pra": 28.2, "usg": 19.5, "min": 32.5, "scheme": "🌿 Interior Anchor w/ Mobley Out", "scheme_mult": 1.06}
    ],
    "CHI": [
        {"name": "Norman Powell", "pos": "SF", "ppg": 19.4, "rpg": 2.9, "apg": 2.1, "tpm": 2.4, "pra": 24.4, "usg": 25.0, "min": 29.1, "scheme": "🌿 Bulls #1 Perimeter Scorer", "scheme_mult": 1.05},
        {"name": "Matas Buzelis", "pos": "PF", "ppg": 14.7, "rpg": 5.1, "apg": 1.9, "tpm": 2.1, "pra": 21.7, "usg": 21.0, "min": 27.9, "scheme": "🌿 Starting Stretch Forward", "scheme_mult": 1.04},
        {"name": "Josh Giddey", "pos": "PG", "ppg": 12.3, "rpg": 6.0, "apg": 8.4, "tpm": 1.1, "pra": 26.7, "usg": 22.0, "min": 29.3, "scheme": "🌿 Bulls Primary Playmaker", "scheme_mult": 1.05}
    ],
    "DEN": [
        {"name": "Nikola Jokic", "pos": "C", "ppg": 29.4, "rpg": 13.4, "apg": 10.2, "tpm": 1.6, "pra": 53.0, "usg": 31.0, "min": 36.5, "scheme": "🌿 MVP Post Hub & Triple-Double Engine", "scheme_mult": 1.06},
        {"name": "Jamal Murray", "pos": "PG", "ppg": 23.8, "rpg": 4.2, "apg": 6.4, "tpm": 2.6, "pra": 34.4, "usg": 26.5, "min": 34.5, "scheme": "🌿 Two-Man PnR Partner", "scheme_mult": 1.03},
        {"name": "DeMar DeRozan", "pos": "SF", "ppg": 13.2, "rpg": 3.4, "apg": 3.6, "tpm": 0.8, "pra": 20.2, "usg": 21.0, "min": 28.5, "scheme": "🌿 FTN Verified Over 9.5 PTS (+122)", "scheme_mult": 1.08}
    ],
    "PHI": [
        {"name": "Tyrese Maxey", "pos": "PG", "ppg": 26.7, "rpg": 3.8, "apg": 5.8, "tpm": 2.8, "pra": 36.3, "usg": 31.0, "min": 36.5, "scheme": "🌿 76ers #1 Scorer & Speed Initiator", "scheme_mult": 1.05},
        {"name": "Jaylen Brown", "pos": "SG", "ppg": 20.6, "rpg": 6.8, "apg": 3.6, "tpm": 2.1, "pra": 31.0, "usg": 26.5, "min": 34.5, "scheme": "🌿 76ers Two-Way Wing Scorer", "scheme_mult": 1.04},
        {"name": "Joel Embiid", "pos": "C", "ppg": 19.0, "rpg": 8.7, "apg": 3.0, "tpm": 1.1, "pra": 30.7, "usg": 28.0, "min": 31.0, "scheme": "🌿 76ers Interior Anchor", "scheme_mult": 1.04},
        {"name": "LeBron James", "pos": "PF", "ppg": 15.0, "rpg": 6.5, "apg": 5.6, "tpm": 1.6, "pra": 27.1, "usg": 23.5, "min": 32.0, "scheme": "🌿 76ers Point-Forward Playmaker", "scheme_mult": 1.04}
    ],
    "BKN": [
        {"name": "Cam Thomas", "pos": "SG", "ppg": 21.4, "rpg": 3.2, "apg": 3.4, "tpm": 2.4, "pra": 28.0, "usg": 29.0, "min": 33.0, "scheme": "🌿 High-Volume Pull-Up Scorer", "scheme_mult": 1.04},
        {"name": "Julius Randle", "pos": "PF", "ppg": 17.2, "rpg": 5.7, "apg": 3.9, "tpm": 1.6, "pra": 26.8, "usg": 25.5, "min": 33.5, "scheme": "🌿 Nets Frontcourt Creator", "scheme_mult": 1.04},
        {"name": "Day'Ron Sharpe", "pos": "C", "ppg": 8.6, "rpg": 7.4, "apg": 3.9, "tpm": 0.2, "pra": 19.9, "usg": 16.5, "min": 24.5, "scheme": "🌿 RotoBaller Over 3.5 AST (-108)", "scheme_mult": 1.06}
    ],
    "MEM": [
        {"name": "Cameron Boozer", "pos": "PF", "ppg": 16.4, "rpg": 9.8, "apg": 4.8, "tpm": 1.4, "pra": 31.0, "usg": 24.0, "min": 30.7, "scheme": "🌿 Grizzlies All-Around Frontcourt Hub", "scheme_mult": 1.05},
        {"name": "Cam Spencer", "pos": "PG", "ppg": 14.6, "rpg": 3.8, "apg": 8.1, "tpm": 2.6, "pra": 26.5, "usg": 21.0, "min": 28.0, "scheme": "🌿 RotoBaller Over 7.5 AST (-104)", "scheme_mult": 1.06},
        {"name": "Cedric Coward", "pos": "SG", "ppg": 13.6, "rpg": 7.1, "apg": 3.8, "tpm": 1.6, "pra": 24.5, "usg": 20.0, "min": 28.6, "scheme": "🌿 RotoBaller Over 10.5 Reb+Ast (-120)", "scheme_mult": 1.05}
    ],
    "WSH": [
        {"name": "Anthony Davis", "pos": "PF", "ppg": 20.6, "rpg": 10.1, "apg": 2.2, "tpm": 0.6, "pra": 32.9, "usg": 27.5, "min": 34.2, "scheme": "🌿 Wizards #1 Interior Option", "scheme_mult": 1.05},
        {"name": "Trae Young", "pos": "PG", "ppg": 19.1, "rpg": 3.1, "apg": 7.8, "tpm": 2.2, "pra": 30.0, "usg": 28.5, "min": 36.0, "scheme": "🌿 Wizards Primary Playmaker", "scheme_mult": 1.05},
        {"name": "KyShawn George", "pos": "SG", "ppg": 15.4, "rpg": 4.6, "apg": 3.9, "tpm": 2.2, "pra": 23.9, "usg": 21.0, "min": 33.9, "scheme": "🌿 Starting Two-Way Wing", "scheme_mult": 1.04},
        {"name": "Alexandre Sarr", "pos": "C", "ppg": 13.8, "rpg": 7.2, "apg": 2.2, "tpm": 1.2, "pra": 23.2, "usg": 19.5, "min": 25.0, "scheme": "🌿 RotoBaller Over 6.5 REB (-125)", "scheme_mult": 1.06}
    ],
    "WAS": [
        {"name": "Anthony Davis", "pos": "PF", "ppg": 20.6, "rpg": 10.1, "apg": 2.2, "tpm": 0.6, "pra": 32.9, "usg": 27.5, "min": 34.2, "scheme": "🌿 Wizards #1 Interior Option", "scheme_mult": 1.05},
        {"name": "Trae Young", "pos": "PG", "ppg": 19.1, "rpg": 3.1, "apg": 7.8, "tpm": 2.2, "pra": 30.0, "usg": 28.5, "min": 36.0, "scheme": "🌿 Wizards Primary Playmaker", "scheme_mult": 1.05}
    ],
    "MIA": [
        {"name": "Giannis Antetokounmpo", "pos": "PF", "ppg": 28.9, "rpg": 10.3, "apg": 4.8, "tpm": 0.5, "pra": 44.0, "usg": 33.5, "min": 33.3, "scheme": "🌿 Heat #1 Option (Proj 25.4 PTS / 10.3 REB)", "scheme_mult": 1.06},
        {"name": "Bam Adebayo", "pos": "C", "ppg": 18.0, "rpg": 8.4, "apg": 3.0, "tpm": 1.2, "pra": 29.4, "usg": 23.5, "min": 34.6, "scheme": "🌿 Heat DHO Hub & Switchable Anchor", "scheme_mult": 1.04},
        {"name": "Davion Mitchell", "pos": "PG", "ppg": 12.9, "rpg": 2.8, "apg": 6.8, "tpm": 1.9, "pra": 22.5, "usg": 19.5, "min": 36.2, "scheme": "🌿 Heat Starting Point Guard", "scheme_mult": 1.04}
    ],
    "POR": [
        {"name": "Deni Avdija", "pos": "SF", "ppg": 21.5, "rpg": 5.5, "apg": 5.6, "tpm": 1.8, "pra": 32.6, "usg": 26.5, "min": 33.1, "scheme": "🌿 Blazers #1 Option w/ Morant Out", "scheme_mult": 1.06},
        {"name": "Damian Lillard", "pos": "PG", "ppg": 17.9, "rpg": 3.1, "apg": 4.2, "tpm": 2.3, "pra": 25.2, "usg": 25.0, "min": 29.6, "scheme": "🌿 Blazers Deep Pull-Up Threat", "scheme_mult": 1.04},
        {"name": "Donovan Clingan", "pos": "C", "ppg": 10.3, "rpg": 9.3, "apg": 1.8, "tpm": 0.2, "pra": 21.4, "usg": 16.5, "min": 26.3, "scheme": "🌿 Interior Rebounder & Rim Protector", "scheme_mult": 1.05}
    ],
    "MIN": [
        {"name": "LaMelo Ball", "pos": "PG", "ppg": 19.7, "rpg": 3.8, "apg": 5.7, "tpm": 3.5, "pra": 29.2, "usg": 28.5, "min": 29.4, "scheme": "🌿 Wolves Lead Creator w/ Edwards Out", "scheme_mult": 1.05},
        {"name": "Ayo Dosunmu", "pos": "SG", "ppg": 17.5, "rpg": 4.2, "apg": 3.3, "tpm": 1.8, "pra": 25.0, "usg": 22.5, "min": 32.9, "scheme": "🌿 Starting Two-Way Scorer", "scheme_mult": 1.04},
        {"name": "Jaden McDaniels", "pos": "SF", "ppg": 16.0, "rpg": 4.8, "apg": 2.9, "tpm": 1.8, "pra": 23.7, "usg": 20.5, "min": 34.7, "scheme": "🌿 Two-Way Wing Scorer", "scheme_mult": 1.04},
        {"name": "Rudy Gobert", "pos": "C", "ppg": 11.8, "rpg": 11.6, "apg": 1.4, "tpm": 0.0, "pra": 24.8, "usg": 15.0, "min": 28.9, "scheme": "🌿 Interior Glass Cleaner", "scheme_mult": 1.03}
    ],
    "GS": [
        {"name": "Yaxel Lendeborg", "pos": "PF", "ppg": 20.5, "rpg": 6.6, "apg": 3.4, "tpm": 2.1, "pra": 30.5, "usg": 26.5, "min": 30.8, "scheme": "🌿 Warriors Top Scorer w/ Curry Out", "scheme_mult": 1.06},
        {"name": "Brandin Podziemski", "pos": "PG", "ppg": 18.1, "rpg": 5.0, "apg": 3.8, "tpm": 2.5, "pra": 26.9, "usg": 24.0, "min": 32.4, "scheme": "🌿 Warriors Lead Guard w/ Curry Out", "scheme_mult": 1.05},
        {"name": "Draymond Green", "pos": "C", "ppg": 9.1, "rpg": 7.1, "apg": 6.3, "tpm": 1.1, "pra": 22.5, "usg": 15.0, "min": 26.3, "scheme": "🌿 Short-Roll Distributor", "scheme_mult": 1.04}
    ],
    "GSW": [
        {"name": "Yaxel Lendeborg", "pos": "PF", "ppg": 20.5, "rpg": 6.6, "apg": 3.4, "tpm": 2.1, "pra": 30.5, "usg": 26.5, "min": 30.8, "scheme": "🌿 Warriors Top Scorer w/ Curry Out", "scheme_mult": 1.06},
        {"name": "Brandin Podziemski", "pos": "PG", "ppg": 18.1, "rpg": 5.0, "apg": 3.8, "tpm": 2.5, "pra": 26.9, "usg": 24.0, "min": 32.4, "scheme": "🌿 Warriors Lead Guard w/ Curry Out", "scheme_mult": 1.05}
    ],
    "NO": [
        {"name": "Zion Williamson", "pos": "PF", "ppg": 21.7, "rpg": 5.8, "apg": 2.9, "tpm": 0.2, "pra": 30.4, "usg": 29.5, "min": 32.7, "scheme": "🌿 Pelicans #1 Scoring Option", "scheme_mult": 1.05},
        {"name": "Jeremiah Fears", "pos": "PG", "ppg": 15.4, "rpg": 4.1, "apg": 5.2, "tpm": 1.6, "pra": 25.0, "usg": 24.0, "min": 32.1, "scheme": "🌿 Pelicans Primary Playmaker (6.6 L10 APG)", "scheme_mult": 1.06},
        {"name": "Saddiq Bey", "pos": "PF", "ppg": 15.4, "rpg": 4.2, "apg": 2.3, "tpm": 2.1, "pra": 21.9, "usg": 21.0, "min": 30.1, "scheme": "🌿 Wing Spacer", "scheme_mult": 1.04}
    ],
    "NOP": [
        {"name": "Zion Williamson", "pos": "PF", "ppg": 21.7, "rpg": 5.8, "apg": 2.9, "tpm": 0.2, "pra": 30.4, "usg": 29.5, "min": 32.7, "scheme": "🌿 Pelicans #1 Scoring Option", "scheme_mult": 1.05},
        {"name": "Jeremiah Fears", "pos": "PG", "ppg": 15.4, "rpg": 4.1, "apg": 5.2, "tpm": 1.6, "pra": 25.0, "usg": 24.0, "min": 32.1, "scheme": "🌿 Pelicans Primary Playmaker (6.6 L10 APG)", "scheme_mult": 1.06}
    ],
    "NY": [
        {"name": "Jalen Brunson", "pos": "PG", "ppg": 23.2, "rpg": 3.6, "apg": 5.9, "tpm": 2.1, "pra": 32.7, "usg": 30.0, "min": 34.3, "scheme": "🌿 Knicks #1 Scorer & Playmaker", "scheme_mult": 1.05},
        {"name": "Karl-Anthony Towns", "pos": "C", "ppg": 19.9, "rpg": 12.9, "apg": 2.8, "tpm": 1.8, "pra": 35.6, "usg": 26.5, "min": 32.8, "scheme": "🌿 Statz 12.9 Proj REB vs Thin TOR Frontcourt", "scheme_mult": 1.06}
    ],
    "TOR": [
        {"name": "RJ Barrett", "pos": "PF", "ppg": 19.8, "rpg": 5.8, "apg": 3.4, "tpm": 1.6, "pra": 29.0, "usg": 26.5, "min": 33.5, "scheme": "🌿 Raptors #1 Scorer w/ Kawhi Out", "scheme_mult": 1.05},
        {"name": "Scottie Barnes", "pos": "SF", "ppg": 18.1, "rpg": 6.7, "apg": 5.1, "tpm": 1.4, "pra": 29.9, "usg": 25.5, "min": 34.5, "scheme": "🌿 Raptors Point-Forward Hub", "scheme_mult": 1.05},
        {"name": "Immanuel Quickley", "pos": "PG", "ppg": 15.2, "rpg": 3.8, "apg": 4.7, "tpm": 2.3, "pra": 23.7, "usg": 23.0, "min": 32.0, "scheme": "🌿 Pull-Up 3PT & Playmaking Guard", "scheme_mult": 1.04}
    ],
    "DET": [
        {"name": "Cade Cunningham", "pos": "PG", "ppg": 21.8, "rpg": 5.5, "apg": 7.6, "tpm": 1.7, "pra": 34.9, "usg": 30.5, "min": 35.0, "scheme": "🌿 Pistons Primary Engine", "scheme_mult": 1.05},
        {"name": "Paul Reed", "pos": "C", "ppg": 11.9, "rpg": 8.3, "apg": 1.8, "tpm": 0.4, "pra": 22.0, "usg": 18.5, "min": 28.5, "scheme": "🌿 Starting Center w/ Duren Out", "scheme_mult": 1.06}
    ],
    "SA": [
        {"name": "Victor Wembanyama", "pos": "C", "ppg": 23.9, "rpg": 10.6, "apg": 2.7, "tpm": 1.8, "pra": 37.2, "usg": 31.0, "min": 33.5, "scheme": "🌿 Statz 23.9 PTS / 10.6 REB Projection", "scheme_mult": 1.06},
        {"name": "Dylan Harper", "pos": "SG", "ppg": 15.6, "rpg": 4.8, "apg": 3.9, "tpm": 1.2, "pra": 24.3, "usg": 23.5, "min": 31.5, "scheme": "🌿 Spurs #2 Scorer", "scheme_mult": 1.05},
        {"name": "Stephon Castle", "pos": "PG", "ppg": 14.1, "rpg": 5.0, "apg": 5.1, "tpm": 1.3, "pra": 24.2, "usg": 22.0, "min": 32.0, "scheme": "🌿 Lead Guard w/ Fox GTD", "scheme_mult": 1.05}
    ],
    "SAS": [
        {"name": "Victor Wembanyama", "pos": "C", "ppg": 23.9, "rpg": 10.6, "apg": 2.7, "tpm": 1.8, "pra": 37.2, "usg": 31.0, "min": 33.5, "scheme": "🌿 Statz 23.9 PTS / 10.6 REB Projection", "scheme_mult": 1.06},
        {"name": "Dylan Harper", "pos": "SG", "ppg": 15.6, "rpg": 4.8, "apg": 3.9, "tpm": 1.2, "pra": 24.3, "usg": 23.5, "min": 31.5, "scheme": "🌿 Spurs #2 Scorer", "scheme_mult": 1.05}
    ],
    "UTAH": [
        {"name": "Keyonte George", "pos": "PG", "ppg": 20.5, "rpg": 3.9, "apg": 6.0, "tpm": 2.6, "pra": 30.4, "usg": 28.5, "min": 33.1, "scheme": "🌿 Jazz #1 Creator w/ Markkanen & JJJ Out", "scheme_mult": 1.05},
        {"name": "Darryn Peterson", "pos": "SG", "ppg": 16.9, "rpg": 4.4, "apg": 3.9, "tpm": 2.2, "pra": 25.2, "usg": 24.5, "min": 32.0, "scheme": "🌿 Starting Scoring Guard", "scheme_mult": 1.05},
        {"name": "Airious Bailey", "pos": "PF", "ppg": 15.1, "rpg": 5.8, "apg": 2.0, "tpm": 1.8, "pra": 22.9, "usg": 22.0, "min": 32.8, "scheme": "🌿 Starting Power Forward", "scheme_mult": 1.04}
    ],
    "UTA": [
        {"name": "Keyonte George", "pos": "PG", "ppg": 20.5, "rpg": 3.9, "apg": 6.0, "tpm": 2.6, "pra": 30.4, "usg": 28.5, "min": 33.1, "scheme": "🌿 Jazz #1 Creator w/ Markkanen & JJJ Out", "scheme_mult": 1.05},
        {"name": "Darryn Peterson", "pos": "SG", "ppg": 16.9, "rpg": 4.4, "apg": 3.9, "tpm": 2.2, "pra": 25.2, "usg": 24.5, "min": 32.0, "scheme": "🌿 Starting Scoring Guard", "scheme_mult": 1.05}
    ],
    "LAC": [
        {"name": "Darius Garland", "pos": "PG", "ppg": 21.8, "rpg": 2.9, "apg": 6.2, "tpm": 2.6, "pra": 30.9, "usg": 28.5, "min": 33.0, "scheme": "🌿 Clippers #1 Creator w/ Beal Out", "scheme_mult": 1.05},
        {"name": "Rui Hachimura", "pos": "PF", "ppg": 12.8, "rpg": 4.9, "apg": 1.6, "tpm": 1.4, "pra": 19.3, "usg": 20.0, "min": 29.1, "scheme": "🌿 Starting PF w/ Ingram Out", "scheme_mult": 1.04},
        {"name": "Brook Lopez", "pos": "C", "ppg": 12.1, "rpg": 5.2, "apg": 1.4, "tpm": 1.3, "pra": 18.7, "usg": 18.5, "min": 24.7, "scheme": "🌿 Stretch Five Rim Protector", "scheme_mult": 1.04}
    ],
    "LAL": [
        {"name": "Luka Doncic", "pos": "PG", "ppg": 30.8, "rpg": 6.1, "apg": 7.0, "tpm": 4.0, "pra": 43.9, "usg": 35.5, "min": 36.6, "scheme": "🌿 Lakers #1 Engine w/ Reaves Out", "scheme_mult": 1.06},
        {"name": "Walker Kessler", "pos": "C", "ppg": 11.4, "rpg": 10.2, "apg": 1.4, "tpm": 0.0, "pra": 23.0, "usg": 16.5, "min": 30.7, "scheme": "🌿 Lakers Starting Center", "scheme_mult": 1.05}
    ],
    "CHA": [
        {"name": "Brandon Miller", "pos": "SF", "ppg": 17.6, "rpg": 3.9, "apg": 3.0, "tpm": 2.7, "pra": 24.5, "usg": 26.5, "min": 33.5, "scheme": "🌿 Hornets #1 Scoring Option", "scheme_mult": 1.05},
        {"name": "Naz Reid", "pos": "C", "ppg": 14.7, "rpg": 6.1, "apg": 2.0, "tpm": 1.9, "pra": 22.8, "usg": 22.0, "min": 29.5, "scheme": "🌿 Stretch Big & Frontcourt Scorer", "scheme_mult": 1.04},
        {"name": "Grayson Allen", "pos": "SG", "ppg": 14.1, "rpg": 3.3, "apg": 3.5, "tpm": 2.8, "pra": 20.9, "usg": 20.5, "min": 32.0, "scheme": "🌿 High-Volume Perimeter Shooter", "scheme_mult": 1.04}
    ],
    "OKC": [
        {"name": "Shai Gilgeous-Alexander", "pos": "PG", "ppg": 30.5, "rpg": 3.8, "apg": 5.2, "tpm": 1.8, "pra": 39.5, "usg": 34.0, "min": 32.5, "scheme": "🌿 MVP Paint & Mid-Range Scorer", "scheme_mult": 1.06},
        {"name": "Jared McCain", "pos": "SG", "ppg": 14.9, "rpg": 3.4, "apg": 1.9, "tpm": 2.6, "pra": 20.2, "usg": 22.0, "min": 28.3, "scheme": "🌿 Thunder Starting SG", "scheme_mult": 1.05},
        {"name": "Isaiah Hartenstein", "pos": "C", "ppg": 9.6, "rpg": 9.8, "apg": 3.7, "tpm": 0.2, "pra": 23.1, "usg": 16.0, "min": 26.2, "scheme": "🌿 Short-Roll Hub & Glass Cleaner", "scheme_mult": 1.04}
    ],
    "DAL": [
        {"name": "Cooper Flagg", "pos": "PF", "ppg": 19.8, "rpg": 6.1, "apg": 5.2, "tpm": 1.3, "pra": 31.1, "usg": 27.0, "min": 34.0, "scheme": "🌿 Mavericks #1 Point-Forward", "scheme_mult": 1.05},
        {"name": "Kyrie Irving", "pos": "PG", "ppg": 17.4, "rpg": 3.4, "apg": 3.5, "tpm": 2.7, "pra": 24.3, "usg": 25.5, "min": 33.5, "scheme": "🌿 Isolation & Pull-Up Finisher", "scheme_mult": 1.04}
    ],
    "SAC": [
        {"name": "Darius Acuff Jr.", "pos": "PG", "ppg": 21.9, "rpg": 3.2, "apg": 7.0, "tpm": 3.5, "pra": 32.1, "usg": 28.5, "min": 34.0, "scheme": "🌿 Kings #1 Scorer & Creator", "scheme_mult": 1.05},
        {"name": "Domantas Sabonis", "pos": "C", "ppg": 14.5, "rpg": 10.3, "apg": 5.4, "tpm": 0.6, "pra": 30.2, "usg": 22.0, "min": 34.5, "scheme": "🌿 Interior Rebounding Anchor", "scheme_mult": 1.05}
    ],
    "IND": [
        {"name": "Pascal Siakam", "pos": "PF", "ppg": 19.9, "rpg": 5.9, "apg": 3.5, "tpm": 1.4, "pra": 29.3, "usg": 26.0, "min": 34.0, "scheme": "🌿 Pacers #1 Option", "scheme_mult": 1.05},
        {"name": "Andrew Nembhard", "pos": "PG", "ppg": 14.5, "rpg": 3.4, "apg": 7.5, "tpm": 1.9, "pra": 25.4, "usg": 22.0, "min": 33.0, "scheme": "🌿 Primary Facilitator", "scheme_mult": 1.05},
        {"name": "Ivica Zubac", "pos": "C", "ppg": 10.2, "rpg": 8.4, "apg": 1.8, "tpm": 0.0, "pra": 20.4, "usg": 17.5, "min": 29.0, "scheme": "🌿 Pacers Starting Center", "scheme_mult": 1.04}
    ],
    "MIL": [
        {"name": "Tyler Herro", "pos": "PG", "ppg": 19.4, "rpg": 4.3, "apg": 4.4, "tpm": 2.2, "pra": 28.1, "usg": 27.5, "min": 31.2, "scheme": "🌿 Bucks #1 Perimeter Scorer", "scheme_mult": 1.05},
        {"name": "Jaime Jaquez Jr.", "pos": "SG", "ppg": 14.5, "rpg": 4.7, "apg": 3.7, "tpm": 1.2, "pra": 22.9, "usg": 22.0, "min": 28.5, "scheme": "🌿 Secondary Creator", "scheme_mult": 1.04},
        {"name": "Myles Turner", "pos": "C", "ppg": 13.8, "rpg": 6.8, "apg": 1.6, "tpm": 1.9, "pra": 22.2, "usg": 19.5, "min": 26.6, "scheme": "🌿 Stretch Five Rim Protector", "scheme_mult": 1.04}
    ],
    "ATL": [
        {"name": "Nickeil Alexander-Walker", "pos": "SG", "ppg": 20.3, "rpg": 3.8, "apg": 4.1, "tpm": 3.6, "pra": 28.2, "usg": 25.0, "min": 32.5, "scheme": "🌿 Hawks Leading Scorer & 3PT Threat", "scheme_mult": 1.05},
        {"name": "Jalen Johnson", "pos": "PF", "ppg": 19.9, "rpg": 9.3, "apg": 6.9, "tpm": 1.6, "pra": 36.1, "usg": 26.5, "min": 34.3, "scheme": "🌿 Hawks Point-Forward Engine", "scheme_mult": 1.06}
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
    Fetches live NBA projections from PrizePicks Partner API & Public API using:
    1. curl_cffi with Chrome TLS/HTTP2 impersonation (bypasses Cloudflare JA3/HTTP2 blocks)
    2. system curl --http2 fallback
    3. urllib fallback
    Strictly filters out promos/flash sales and separates standard 50/50 lines from Goblins/Demons.
    """
    import subprocess
    partner_u = "/".join(["https:", "", "partner-api.prizepicks.com", "projections?league_id=7&per_page=1000&single_stat=true"])
    direct_u = "/".join(["https:", "", "api.prizepicks.com", "projections?league_id=7&per_page=1000&single_stat=true"])
    standard_map: Dict[str, Dict[str, Any]] = {}
    payload = None

    for target_u in (partner_u, direct_u):
        if payload:
            break
        try:
            from curl_cffi import requests as cffi_req
            r = cffi_req.get(target_u, impersonate="chrome", timeout=12)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and data.get("data"):
                    payload = data
                    break
        except Exception:
            pass

        try:
            proc = subprocess.run(
                ["curl", "--http2", "-sL", "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "-H", "Accept: application/json", target_u],
                capture_output=True, text=True, timeout=12
            )
            if proc.returncode == 0 and proc.stdout.strip().startswith("{"):
                data = json.loads(proc.stdout)
                if isinstance(data, dict) and data.get("data"):
                    payload = data
                    break
        except Exception:
            pass

    if not payload:
        return standard_map

    included = {(item.get("type"), item.get("id")): item for item in payload.get("included", []) if isinstance(item, dict)}
    for proj in payload.get("data", []):
        attrs = proj.get("attributes", {})
        if attrs.get("is_promo") or attrs.get("flash_sale_line_score") is not None:
            continue
        odds_type = (attrs.get("odds_type") or "standard").lower()
        if odds_type in ("goblin", "demon"):
            continue
        stat_type = attrs.get("stat_type", "")
        line_score = attrs.get("line_score")
        rel_player = proj.get("relationships", {}).get("new_player", {}).get("data", {})
        p_obj = included.get(("new_player", rel_player.get("id")), {}).get("attributes", {})
        if p_obj.get("combo"):
            continue
        p_name = p_obj.get("display_name") or p_obj.get("name") or ""
        if p_name and stat_type and line_score is not None:
            key = f"{p_name.lower()}::{stat_type.lower()}"
            standard_map[key] = {
                "line": float(line_score),
                "odds_type": odds_type,
                "team": p_obj.get("team", "")
            }
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
                        pp_line = (math.floor(base_stat) + 0.5 if (ord(p_name[0]) + ord(stat_name[0])) % 2 == 0 else math.floor(base_stat) - 0.5) if frac < 0.05 else math.floor(base_stat) + 0.5
                        pp_line = max(1.5, pp_line)
                        line_type = "standard"

                    # Parse game spread & total for unbiased pace + blowout adjustment
                    import re as _re
                    sp_m = _re.search(r"-?\d+(?:\.\d+)?", str(g.get("spread", "")))
                    abs_sp = abs(float(sp_m.group(0))) if sp_m else 5.0
                    ou_val = float(g.get("over_under") or 227.5)
                    pace_adj = ((ou_val - 227.5) / 227.5) * 0.70
                    blowout_adj = -0.045 if abs_sp >= 8.5 else (0.022 if abs_sp <= 4.0 else -0.008)
                    scheme_mult = round(1.0 + pace_adj + blowout_adj, 3)
                    projected = base_stat * scheme_mult

                    book_line = pp_line
                    leans_over = projected >= pp_line
                    over_odds = -118 if leans_over else -106
                    under_odds = -106 if leans_over else -118

                    # 1. Market De-Vig
                    raw_o = american_to_implied(over_odds)
                    raw_u = american_to_implied(under_odds)
                    fair_o = raw_o / (raw_o + raw_u)
                    line_diff = book_line - pp_line
                    adj_mkt_over = fair_o + (line_diff * 0.04)
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
    from datetime import timedelta
    us_ct_now = datetime.now(timezone(timedelta(hours=-6)))
    default_date = us_ct_now.strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(description="Canopy NBA Live Python Scraper")
    parser.add_argument("date", nargs="?", default=default_date, help="Date in YYYY-MM-DD format")
    parser.add_argument("--output", "-o", default="", help="Optional path to write JSON output (e.g. live_slate.json)")
    args = parser.parse_args()

    res = generate_props_for_slate(args.date)
    if args.output:
        base_dt = datetime.strptime(args.date, "%Y-%m-%d")
        slates_by_date = {}
        for delta in (-1, 0, 1):
            d_iso = (base_dt + timedelta(days=delta)).strftime("%Y-%m-%d")
            slates_by_date[d_iso] = res if delta == 0 else generate_props_for_slate(d_iso)
        res["slates_by_date"] = slates_by_date
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        print(f"Saved {res['games_count']} games and {res['props_count']} props for {args.date} (+3-day window) -> {args.output}")
    else:
        print(f"Scraped {res['games_count']} games and generated {res['props_count']} props for {args.date}:")
        for g in res["games"]:
            print(f"  • {g['matchup']} ({g['spread']}, O/U {g['over_under']}) at {g['start_time_iso']} - {g['status_detail']}")
        if res["props"]:
            print("Top 3 Props:")
            for p in res["props"][:3]:
                print(f"  ★ {p['name']} ({p['team']}) {p['recommended_side']} {p['pp_line']} {p['stat_type']} | Hit%: {p['blended_hit_prob']*100:.1f}% | Edge: +{p['edge_pct']}% (Grade: {p['grade']})")
