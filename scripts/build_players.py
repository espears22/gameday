#!/usr/bin/env python3
"""Regenerate players.json from Sleeper's full player dump.

Sleeper asks that /players/nfl not be fetched more than once a day, and the raw
dump is ~5MB, so this runs out-of-band (not in the browser) and commits a
trimmed static file. Run manually, weekly, during the season:

    python3 scripts/build_players.py
"""
import json
import subprocess

SRC = "https://api.sleeper.app/v1/players/nfl"
OUT = "players.json"
KEEP_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DEF"}


def main():
    # Shells out to curl rather than urllib: some local Python installs (this
    # one included) don't have a usable CA bundle for HTTPS out of the box.
    raw = subprocess.run(["curl", "-sS", SRC], capture_output=True, check=True).stdout
    data = json.loads(raw)

    trimmed = {}
    for player_id, p in data.items():
        if p.get("position") not in KEEP_POSITIONS:
            continue
        if not p.get("team"):
            continue
        name = p.get("full_name") or (p.get("first_name", "") + " " + p.get("last_name", "")).strip()
        trimmed[player_id] = {"name": name, "team": p["team"], "pos": p["position"]}

    with open(OUT, "w") as f:
        json.dump(trimmed, f, separators=(",", ":"), sort_keys=True)

    print(f"wrote {len(trimmed)} players to {OUT}")


if __name__ == "__main__":
    main()
