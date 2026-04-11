import pandas as pd
import requests
from pathlib import Path
from datetime import date
from TeamNameMapper import TeamNameMapper

CACHE_DIR = Path(".fbref_cache")
CACHE_FILE = CACHE_DIR / f"fbref_brasileirao_{date.today()}.parquet"

class FBrefFetcher:
    def __init__(self, season: int = 2025):
        self.season = season
        CACHE_DIR.mkdir(exist_ok=True)
        self.base_url = "https://fbref.com/en/comps/24"

    def fetch(self) -> pd.DataFrame:
        if CACHE_FILE.exists():
            return pd.read_parquet(CACHE_FILE)
        df = self._scrape_and_build()
        if not df.empty:
            df.to_parquet(CACHE_FILE)
        return df

    def _scrape_and_build(self) -> pd.DataFrame:
        """Scrape Brasileirão team stats from FBref"""
        url = f"{self.base_url}/{self.season}/stats/"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            tables = pd.read_html(url, header=0)
            # Find the team stats table (usually the first one with team data)
            df = None
            for table in tables:
                if len(table) > 0 and any(col for col in table.columns if 'Squad' in str(col) or 'Team' in str(col) or 'Rk' in str(col)):
                    df = table
                    break
            
            if df is None and len(tables) > 0:
                # Fallback: use the first table
                df = tables[0]
            
            if df is None:
                print("Warning: No FBref data found. Using empty dataframe.")
                return pd.DataFrame()
            
            # Clean up the dataframe
            df = df.dropna(how='all')
            return df
        except Exception as e:
            print(f"Warning: Error scraping FBref: {e}. Continuing with empty data.")
            return pd.DataFrame()

    def get_team_stats(self, fbref_team_name: str) -> pd.Series | None:
        df = self.fetch()
        if df.empty:
            return None
        team_index = [idx for idx in df.index if fbref_team_name.lower() in str(idx).lower()]
        if not team_index:
            return None
        return df.loc[team_index[0]]

    def get_fbref_team_names(self) -> list[str]:
        df = self.fetch()
        if df.empty:
            # Return default Brasileirão teams if no data available
            return [
                "Flamengo", "Palmeiras", "São Paulo", "Corinthians", "Internacional",
                "Grêmio", "Atlético Mineiro", "Fluminense", "Botafogo", "Santos",
                "Bahia", "Fortaleza", "Cruzeiro", "Athletico Paranaense", "Vasco da Gama",
                "Cuiabá", "Goiás", "América Mineiro", "Bragantino", "Vitória"
            ]
        # Extract team names from the dataframe
        team_names = []
        for col in df.columns:
            if 'Squad' in str(col) or 'Team' in str(col):
                team_names = df[col].tolist()
                break
        if not team_names:
            # Fallback: use index
            team_names = [str(idx) for idx in df.index]
        return [str(name) for name in team_names if pd.notna(name)]

    def build_team_mapper(self) -> TeamNameMapper:
        return TeamNameMapper(self.get_fbref_team_names())
