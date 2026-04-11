from rapidfuzz import process, fuzz

# Maps Cartola abbreviation → FBref team name (Brasileirão Série A 2025)
# Extend this dict as teams are promoted/relegated each season
CARTOLA_TO_FBREF: dict[str, str] = {
    "FLA": "Flamengo",
    "PAL": "Palmeiras",
    "SAO": "São Paulo",
    "COR": "Corinthians",
    "INT": "Internacional",
    "GRE": "Grêmio",
    "ATM": "Atlético Mineiro",
    "FLU": "Fluminense",
    "BOT": "Botafogo",
    "SAN": "Santos",
    "BAH": "Bahia",
    "FOR": "Fortaleza",
    "CRU": "Cruzeiro",
    "CAP": "Athletico Paranaense",
    "VAS": "Vasco da Gama",
    "CUI": "Cuiabá",
    "GOI": "Goiás",
    "AME": "América Mineiro",
    "BRA": "Bragantino",
    "VIT": "Vitória",
}

class TeamNameMapper:
    def __init__(self, fbref_team_names: list[str]):
        self._fbref_names = fbref_team_names

    def cartola_to_fbref(self, cartola_abbrev: str) -> str | None:
        if cartola_abbrev in CARTOLA_TO_FBREF:
            candidate = CARTOLA_TO_FBREF[cartola_abbrev]
            match = process.extractOne(candidate, self._fbref_names, scorer=fuzz.token_sort_ratio)
            if match and match[1] >= 70:
                return match[0]
        result = process.extractOne(cartola_abbrev, self._fbref_names, scorer=fuzz.token_sort_ratio)
        if result and result[1] >= 70:
            return result[0]
        return None
