import pandas as pd
import soccerdata as sd
from pathlib import Path

from BaseFetcher import BaseFetcher, FetchBlockedError, CANONICAL_COLUMNS

# soccerdata stat_type → {metric_substring: (canonical_home_col, canonical_away_col)}
# Confirm exact column names from the human checkpoint below before finalising.
_COLUMN_MAP: dict[str, dict[str, tuple[str, str]]] = {
    "shooting": {
        "xg":   ("xg_home",  "xg_away"),
        "xga":  ("xga_home", "xga_away"),
        "npxg": ("npxg_home","npxg_away"),
    },
    "misc": {
        "yellow_cards": ("yellow_cards_home", "yellow_cards_away"),
    },
    "defense": {
        "tackles":   ("tackles_home",   "tackles_away"),
        "pressures": ("pressures_home", "pressures_away"),
    },
    "possession": {
        "prgp": ("prog_passes_home", "prog_passes_away"),
    },
}


class SofascoreFetcher(BaseFetcher):
    SOURCE_NAME = "sofascore"

    def __init__(self, season: int = 2026):
        super().__init__(season=season, cache_dir=Path(".stats_cache"))

    def _scrape_and_build(self) -> pd.DataFrame:
        try:
            sofascore = sd.Sofascore(leagues="BRA-Série A", seasons=self.season)
        except Exception as e:
            raise FetchBlockedError(f"Sofascore init failed: {e}") from e

        result: dict[str, dict[str, float]] = {}

        for stat_type, col_map in _COLUMN_MAP.items():
            self._inter_request_delay()
            try:
                raw = sofascore.read_team_season_stats(stat_type=stat_type)
            except Exception as e:
                msg = str(e).lower()
                if "403" in msg or "forbidden" in msg or "429" in msg or "rate" in msg:
                    raise FetchBlockedError(f"Sofascore blocked on {stat_type}: {e}") from e
                print(f"[sofascore] Warning: could not fetch {stat_type}: {e}")
                continue

            if isinstance(raw.index, pd.MultiIndex):
                idx_names = raw.index.names
                team_level = next(
                    (n for n in idx_names if n and "team" in str(n).lower()), None
                )
                drop_levels = [n for n in idx_names if n != team_level]
                raw = raw.reset_index(level=drop_levels, drop=True)

            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = ["_".join(str(p) for p in col if str(p) != "nan").lower()
                               for col in raw.columns]
            else:
                raw.columns = [str(c).lower() for c in raw.columns]

            for team_name in raw.index:
                row = raw.loc[team_name]
                if team_name not in result:
                    result[team_name] = {}
                for metric_key, (home_col, away_col) in col_map.items():
                    home_val, away_val = 0.0, 0.0
                    for col in raw.columns:
                        if metric_key in col:
                            if "home" in col or "_h_" in col or col.endswith("_h"):
                                v = row[col]
                                home_val = float(v) if pd.notna(v) else 0.0
                            elif "away" in col or "_a_" in col or col.endswith("_a"):
                                v = row[col]
                                away_val = float(v) if pd.notna(v) else 0.0
                    result[team_name][home_col] = home_val
                    result[team_name][away_col] = away_val

        if not result:
            return pd.DataFrame(columns=CANONICAL_COLUMNS)

        df = pd.DataFrame.from_dict(result, orient="index")
        for col in CANONICAL_COLUMNS:
            if col not in df.columns:
                df[col] = 0.0
        return df[CANONICAL_COLUMNS]
