import pandas as pd

SHARE_SCOUTS = ["G", "A", "FT", "FD", "FF", "FS", "PS", "DS", "CA"]

# Position IDs per Cartola API: 1=GK, 2=LAT, 3=ZAG, 4=MEI, 5=ATK, 6=TEC
CLEAN_SHEET_POSITIONS = {1, 2, 3}
GK_POSITION = 1


def safe_divide(numerator, denominator):
    if denominator == 0 or pd.isna(denominator):
        return 0
    return numerator / denominator


class PlayerIndicators:
    def __init__(
        self,
        df_players_rates,
        df_team_indicators,
        df_games_info,
        teams_home,
        teams_away,
        team_abr,
        rodada_req=None,
    ):
        self.predict_round = rodada_req
        self.df_players_rates = df_players_rates
        self.df_team_indicators = df_team_indicators
        self.df_games_info = df_games_info
        self.team_abr = team_abr

        # club_id -> (opponent_id, is_home, fixture_row_index)
        self.club_fixture = {}
        for idx, (home_id, away_id) in enumerate(zip(teams_home, teams_away)):
            self.club_fixture[home_id] = (away_id, True, idx)
            self.club_fixture[away_id] = (home_id, False, idx)

    def _team_total(self, club_id, scout):
        if club_id not in self.df_games_info.index:
            return 0
        row = self.df_games_info.loc[club_id]
        return row[f"{scout} H"] * row["MATCHES H"] + row[f"{scout} A"] * row["MATCHES A"]

    def calculate_player_indicators(self):
        records = []
        for atleta_id, player in self.df_players_rates.iterrows():
            club_id = player.get("clube_id")
            if club_id is None or club_id not in self.club_fixture:
                continue

            opponent_id, is_home, fixture_idx = self.club_fixture[club_id]
            side = "H" if is_home else "A"
            opposite = "A" if is_home else "H"
            fixture = self.df_team_indicators.loc[fixture_idx]
            availability = float(player.get("availability", 0) or 0)
            position = player.get("posicao_id")

            shares = {}
            for sc in SHARE_SCOUTS:
                if sc == "G":
                    team_total = (
                        self.df_games_info.loc[club_id, "GF H"]
                        + self.df_games_info.loc[club_id, "GF A"]
                    )
                else:
                    team_total = self._team_total(club_id, sc)
                shares[sc] = safe_divide(float(player.get(sc, 0) or 0), float(team_total))

            goals_multi_side = float(fixture[f"goalsMulti{side}"])
            goals_multi_opposite = float(fixture[f"goalsMulti{opposite}"])
            clean_sheet_side = float(fixture[f"cleanSheetProb{side}"])
            expected_saves_side = float(fixture[f"expectedSaves{side}"])

            expG = goals_multi_side * shares["G"] * availability
            expA = float(fixture[f"expA_{side}"]) * shares["A"] * availability
            expFT = float(fixture[f"expFT_{side}"]) * shares["FT"] * availability
            expFD = float(fixture[f"expFD_{side}"]) * shares["FD"] * availability
            expFF = float(fixture[f"expFF_{side}"]) * shares["FF"] * availability
            expFS = float(fixture[f"expFS_{side}"]) * shares["FS"] * availability
            expPS = float(fixture[f"expPS_{side}"]) * shares["PS"] * availability
            expDS = float(fixture[f"expDS_{side}"]) * shares["DS"] * availability
            expCA = float(fixture[f"expCA_{side}"]) * shares["CA"] * availability

            expSG = clean_sheet_side * availability if position in CLEAN_SHEET_POSITIONS else 0.0
            expDE = expected_saves_side * availability if position == GK_POSITION else 0.0
            expGS = goals_multi_opposite * availability if position == GK_POSITION else 0.0

            xCPA = expG * 8 + expFT * 3 + expFD * 1.2 + expFF * 0.8
            cardLiability = expCA * 1
            expCartolaTotal = (
                expG * 8
                + expA * 5
                + expFT * 3
                + expFD * 1.2
                + expFF * 0.8
                + expFS * 0.5
                + expPS * 1
                + expDS * 1.5
                + expSG * 5
                + expDE * 1.3
                - expGS * 1
                - expCA * 1
            )
            preco = float(player.get("preco_num", 0) or 0)
            costEfficiency = safe_divide(expCartolaTotal, preco)

            records.append(
                {
                    "atleta_id": atleta_id,
                    "apelido": player.get("apelido"),
                    "position": position,
                    "status_id": player.get("status_id"),
                    "preco": preco,
                    "games": int(player.get("games", 0) or 0),
                    "availability": availability,
                    "club": self.team_abr.get(str(club_id), str(club_id)),
                    "opponent": self.team_abr.get(str(opponent_id), str(opponent_id)),
                    "is_home": is_home,
                    "G_share": shares["G"],
                    "A_share": shares["A"],
                    "FT_share": shares["FT"],
                    "FD_share": shares["FD"],
                    "FF_share": shares["FF"],
                    "FS_share": shares["FS"],
                    "PS_share": shares["PS"],
                    "DS_share": shares["DS"],
                    "CA_share": shares["CA"],
                    "expG": expG,
                    "expA": expA,
                    "expFT": expFT,
                    "expFD": expFD,
                    "expFF": expFF,
                    "expFS": expFS,
                    "expPS": expPS,
                    "expDS": expDS,
                    "expCA": expCA,
                    "expSG": expSG,
                    "expDE": expDE,
                    "expGS": expGS,
                    "xCPA": xCPA,
                    "cardLiability": cardLiability,
                    "expCartolaTotal": expCartolaTotal,
                    "costEfficiency": costEfficiency,
                }
            )

        df = pd.DataFrame(records).set_index("atleta_id")

        numeric_cols = df.select_dtypes(include="number").columns
        df[numeric_cols] = df[numeric_cols].round(2)

        df.to_csv("players.csv")
        return df
