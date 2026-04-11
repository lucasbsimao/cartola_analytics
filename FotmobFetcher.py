from pathlib import Path
import fotmob
import pandas as pd

from BaseFetcher import BaseFetcher, FetchBlockedError, CANONICAL_COLUMNS

# Fotmob league ID for Brasileirão Série A
BRASILEIRAO_LEAGUE_ID = 325

# Mapping from Fotmob stat keys → canonical column pairs (home, away)
# Adjust key names after inspecting live API response in the human checkpoint below.
_FOTMOB_STAT_MAP = {
    "expected_goals":         ("xg_home",           "xg_away"),
    "expected_goals_against": ("xga_home",           "xga_away"),
    "np_expected_goals":      ("npxg_home",          "npxg_away"),
    "pressures":              ("pressures_home",     "pressures_away"),
    "tackles":                ("tackles_home",       "tackles_away"),
    "yellow_cards":           ("yellow_cards_home",  "yellow_cards_away"),
    "progressive_passes":     ("prog_passes_home",   "prog_passes_away"),
}


class FotmobFetcher(BaseFetcher):
    SOURCE_NAME = "fotmob"

    def __init__(self, season: int = 2026):
        super().__init__(season=season, cache_dir=Path(".stats_cache"))

    def _scrape_and_build(self) -> pd.DataFrame:
        try:
            client = fotmob.FotMob()
            self._inter_request_delay()   # BaseFetcher: random 3-8 s + rotates UA
            league = client.get_league(
                id=BRASILEIRAO_LEAGUE_ID,
                ccode3="BRA",
                tab="table",
                type="league",
            )
        except Exception as e:
            msg = str(e).lower()
            if "403" in msg or "forbidden" in msg or "429" in msg or "blocked" in msg:
                raise FetchBlockedError(f"Fotmob blocked: {e}") from e
            raise FetchBlockedError(f"Fotmob unavailable: {e}") from e

        # Build result dict: team_name → {canonical_col: value}
        result: dict[str, dict[str, float]] = {}

        try:
            # The `table` response has a top-level "table" key with an "all" list.
            # Each entry has "name", "played", "wins", "draws", "losses",
            # "scoresStr", "goalConDiff" — but NOT xG at this endpoint.
            # We need the "stats" tab instead.
            self._inter_request_delay()   # BaseFetcher: random 3-8 s + rotates UA
            stats = client.get_league(
                id=BRASILEIRAO_LEAGUE_ID,
                ccode3="BRA",
                tab="stats",
                type="league",
            )
            # Parse stats — structure depends on fotmob version.
            # Print and inspect first time; adjust key paths in human checkpoint.
            top_stats = stats.get("stats", {}).get("stats", [])
            for stat_block in top_stats:
                stat_name = str(stat_block.get("header", "")).lower().replace(" ", "_")
                canonical_pair = next(
                    (v for k, v in _FOTMOB_STAT_MAP.items() if k in stat_name),
                    None,
                )
                if canonical_pair is None:
                    continue
                home_col, away_col = canonical_pair
                for participant in stat_block.get("participants", []):
                    team_name = participant.get("teamName", {}).get("fallback", "")
                    if not team_name:
                        continue
                    if team_name not in result:
                        result[team_name] = {}
                    # Fotmob stats endpoint returns season total, not home/away split.
                    # Use the same value for both until a per-split endpoint is confirmed.
                    val = float(participant.get("statValue", 0) or 0)
                    result[team_name][home_col] = val
                    result[team_name][away_col] = val
        except FetchBlockedError:
            raise
        except Exception as e:
            print(f"[fotmob] Warning parsing stats: {e}")

        if not result:
            return pd.DataFrame(columns=CANONICAL_COLUMNS)

        df = pd.DataFrame.from_dict(result, orient="index")
        for col in CANONICAL_COLUMNS:
            if col not in df.columns:
                df[col] = 0.0
        return df[CANONICAL_COLUMNS]
