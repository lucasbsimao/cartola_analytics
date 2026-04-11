import random
import time
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import date

import pandas as pd
import requests
from fake_useragent import UserAgent
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
    RetryError,
)

from TeamNameMapper import TeamNameMapper

# Canonical output columns — every fetcher MUST produce these exact names.
# Indexed by team name (string), one row per team.
CANONICAL_COLUMNS = [
    "xg_home", "xg_away",
    "xga_home", "xga_away",
    "npxg_home", "npxg_away",
    "pressures_home", "pressures_away",
    "tackles_home", "tackles_away",
    "yellow_cards_home", "yellow_cards_away",
    "prog_passes_home", "prog_passes_away",
]

_ua = UserAgent()

def _is_retryable(exc: BaseException) -> bool:
    """Retry on 429/503 (rate-limited); propagate 403 (blocked) immediately."""
    if isinstance(exc, requests.HTTPError):
        return exc.response is not None and exc.response.status_code in (429, 503)
    return False


class FetchBlockedError(Exception):
    """Raised when a data source blocks the request (403, 429 exhausted, captcha, etc.)."""


class BaseFetcher(ABC):
    SOURCE_NAME: str = "unknown"

    def __init__(self, season: int = 2026, cache_dir: Path = Path(".stats_cache")):
        self.season = season
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(exist_ok=True)
        self._cache_file = cache_dir / f"{self.SOURCE_NAME}_{season}_{date.today()}.parquet"
        self._mem_cache: pd.DataFrame | None = None
        self._session = requests.Session()
        self._session.headers.update(self._browser_headers())

    # ------------------------------------------------------------------
    # Anti-blocking HTTP helper — used by FotmobFetcher & SofascoreFetcher.
    # FBrefFetcher delegates to soccerdata which manages its own session,
    # but calls _inter_request_delay() between stat-type fetches.
    # ------------------------------------------------------------------

    def _browser_headers(self) -> dict:
        return {
            "User-Agent": _ua.chrome,          # rotated real Chrome UA each call
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8",
            "Referer": "https://www.google.com/",
        }

    def _inter_request_delay(self) -> None:
        """Random human-paced delay between requests. Call between stat-type fetches."""
        time.sleep(random.uniform(3, 8))

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential_jitter(initial=30, max=120),   # jitter avoids thundering herd
        stop=stop_after_attempt(3),
        reraise=False,   # on exhaustion we raise FetchBlockedError ourselves below
    )
    def _http_get(self, url: str, **kwargs) -> dict:
        """GET `url`, rotate UA on every call, retry on 429/503, raise FetchBlockedError on 403."""
        self._session.headers["User-Agent"] = _ua.chrome   # rotate per request
        self._inter_request_delay()
        try:
            resp = self._session.get(url, timeout=30, **kwargs)
        except requests.ConnectionError as e:
            raise FetchBlockedError(f"Connection failed: {url} — {e}") from e
        if resp.status_code == 403:
            raise FetchBlockedError(f"403 Forbidden: {url}")
        if resp.status_code == 429:
            resp.raise_for_status()   # triggers tenacity retry
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Cache + lifecycle
    # ------------------------------------------------------------------

    def fetch(self) -> pd.DataFrame:
        """Return a DataFrame with CANONICAL_COLUMNS indexed by team name."""
        if self._mem_cache is not None:
            return self._mem_cache
        if self._cache_file.exists():
            print(f"[{self.SOURCE_NAME}] Loading from cache: {self._cache_file}")
            self._mem_cache = pd.read_parquet(self._cache_file)
            return self._mem_cache
        for path in sorted(self._cache_dir.glob(f"{self.SOURCE_NAME}_{self.season}_*.parquet"), reverse=True):
            cached = pd.read_parquet(path)
            if not cached.empty:
                print(f"[{self.SOURCE_NAME}] Loading stale cache: {path}")
                self._mem_cache = cached
                return self._mem_cache
        df = self._scrape_and_build()
        if not df.empty:
            df.to_parquet(self._cache_file)
        self._mem_cache = df
        return df

    @abstractmethod
    def _scrape_and_build(self) -> pd.DataFrame:
        """Scrape source and return a DataFrame with CANONICAL_COLUMNS.
        Must raise FetchBlockedError on unrecoverable blocks."""

    def get_team_stats(self, team_name: str) -> pd.Series | None:
        df = self.fetch()
        if df.empty:
            return None
        matches = [idx for idx in df.index if team_name.lower() in str(idx).lower()]
        return df.loc[matches[0]] if matches else None

    def get_team_names(self) -> list[str]:
        df = self.fetch()
        return [str(idx) for idx in df.index] if not df.empty else []

    def build_team_mapper(self) -> TeamNameMapper:
        return TeamNameMapper(self.get_team_names())
