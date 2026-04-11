import pandas as pd
from BaseFetcher import BaseFetcher, FetchBlockedError, CANONICAL_COLUMNS
from TeamNameMapper import TeamNameMapper


class ResilientFetcher(BaseFetcher):
    """Tries each fetcher in order; falls back on FetchBlockedError.

    Usage:
        fetcher = ResilientFetcher([FBrefFetcher(), FotmobFetcher()])
        df = fetcher.fetch()  # uses first source that succeeds
    """
    SOURCE_NAME = "resilient"

    def __init__(self, fetchers: list[BaseFetcher]):
        if not fetchers:
            raise ValueError("ResilientFetcher requires at least one fetcher")
        self._fetchers = fetchers
        # Use the first fetcher's season/cache_dir as own defaults
        first = fetchers[0]
        super().__init__(season=first.season, cache_dir=first._cache_dir)

    def _scrape_and_build(self) -> pd.DataFrame:
        """Not used — fetch() is overridden to delegate to the inner fetchers."""
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    def fetch(self) -> pd.DataFrame:
        last_error: Exception | None = None
        for fetcher in self._fetchers:
            try:
                print(f"[resilient] Trying {fetcher.SOURCE_NAME}…")
                df = fetcher.fetch()
                if not df.empty:
                    print(f"[resilient] Success with {fetcher.SOURCE_NAME}")
                    return df
                print(f"[resilient] {fetcher.SOURCE_NAME} returned empty data, trying next")
            except FetchBlockedError as e:
                print(f"[resilient] {fetcher.SOURCE_NAME} blocked: {e}. Trying next source…")
                last_error = e
            except Exception as e:
                print(f"[resilient] {fetcher.SOURCE_NAME} unexpected error: {e}. Trying next source…")
                last_error = e
        print(f"[resilient] All sources failed. Last error: {last_error}")
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    def get_team_names(self) -> list[str]:
        return [str(idx) for idx in self.fetch().index]

    def build_team_mapper(self) -> TeamNameMapper:
        return TeamNameMapper(self.get_team_names())
