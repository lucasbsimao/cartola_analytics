import pandas as pd

SHARE_SCOUTS = ["G", "A", "FT", "FD", "FF", "FS", "PS", "DS", "CA"]

# Position IDs per Cartola API: 1=GK, 2=LAT, 3=ZAG, 4=MEI, 5=ATK, 6=TEC
CLEAN_SHEET_POSITIONS = {1, 2, 3}
GK_POSITION = 1

# Minimum games observed in the window before shares are fully trusted.
# Below this, shares are shrunk linearly toward 0 via sample_weight.
MIN_GAMES = 3

# Cartola status_id gating (from /atletas/mercado):
#   2 = Dúvida, 3 = Suspenso, 5 = Contundido, 6 = Nulo, 7 = Provável
STATUS_WEIGHT = {7: 1.0, 2: 0.5, 3: 0.0, 5: 0.0, 6: 0.0}

# Captain multiplier in standard Cartola scoring (dobra = 1.5x)
CAPTAIN_MULTIPLIER = 1.5


def safe_divide(numerator, denominator):
    if denominator == 0 or pd.isna(denominator):
        return 0
    return numerator / denominator


def _status_weight(status_id):
    if status_id is None or pd.isna(status_id):
        # Unknown status: do not gate. User can filter downstream.
        return 1.0
    try:
        sid = int(status_id)
    except (TypeError, ValueError):
        return 1.0
    return STATUS_WEIGHT.get(sid, 0.0)


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

    def _team_side_total(self, club_id, scout, side):
        """Total team production of `scout` on the given side (H/A) over the window."""
        if club_id not in self.df_games_info.index:
            return 0
        row = self.df_games_info.loc[club_id]
        return row[f"{scout} {side}"] * row[f"MATCHES {side}"]

    def _player_share(self, player, club_id, scout, side):
        """Side-aware share = player scout on side / team scout on side."""
        if scout == "G":
            team_total = self.df_games_info.loc[club_id, f"GF {side}"] if club_id in self.df_games_info.index else 0
        else:
            team_total = self._team_side_total(club_id, scout, side)
        player_val = float(player.get(f"{scout}_{side}", 0) or 0)
        return safe_divide(player_val, float(team_total))

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
            games = int(player.get("games", 0) or 0)

            # Sample-size shrinkage: low-data players get down-weighted shares.
            sample_weight = min(1.0, games / float(MIN_GAMES)) if MIN_GAMES > 0 else 1.0

            # Status gating (from /atletas/mercado); 1.0 if unknown.
            status_id = player.get("status_id")
            status_weight = _status_weight(status_id)

            effective_availability = availability * sample_weight

            # Side-aware shares using player H/A split vs team H/A totals.
            shares = {sc: self._player_share(player, club_id, sc, side) for sc in SHARE_SCOUTS}

            goals_multi_side = float(fixture[f"goalsMulti{side}"])
            goals_multi_opposite = float(fixture[f"goalsMulti{opposite}"])
            clean_sheet_side = float(fixture[f"cleanSheetProb{side}"])
            expected_saves_side = float(fixture[f"expectedSaves{side}"])

            expG = goals_multi_side * shares["G"] * effective_availability
            expA = float(fixture[f"expA_{side}"]) * shares["A"] * effective_availability
            expFT = float(fixture[f"expFT_{side}"]) * shares["FT"] * effective_availability
            expFD = float(fixture[f"expFD_{side}"]) * shares["FD"] * effective_availability
            expFF = float(fixture[f"expFF_{side}"]) * shares["FF"] * effective_availability
            expFS = float(fixture[f"expFS_{side}"]) * shares["FS"] * effective_availability
            expPS = float(fixture[f"expPS_{side}"]) * shares["PS"] * effective_availability
            expDS = float(fixture[f"expDS_{side}"]) * shares["DS"] * effective_availability
            expCA = float(fixture[f"expCA_{side}"]) * shares["CA"] * effective_availability

            expSG = clean_sheet_side * effective_availability if position in CLEAN_SHEET_POSITIONS else 0.0
            expDE = expected_saves_side * effective_availability if position == GK_POSITION else 0.0
            expGS = goals_multi_opposite * effective_availability if position == GK_POSITION else 0.0

            # Attacking / defensive decomposition of expected Cartola points.
            # xCPA now includes assists (assists are an offensive scout).
            xCPA = expG * 8 + expA * 5 + expFT * 3 + expFD * 1.2 + expFF * 0.8
            xCPD = expDS * 1.5 + expSG * 5 + expFS * 0.5 - expCA * 1
            # GK-specific value (only meaningful for position == GK).
            gkDefenseValue = (expSG * 5 + expDE * 1.3 - expGS * 1) if position == GK_POSITION else 0.0

            cardLiability = expCA * 1
            expCartolaTotal_raw = (
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
            # Apply status gating to final projection only (keeps component exp* readable).
            expCartolaTotal = expCartolaTotal_raw * status_weight

            # Volatility-derived pick-mode columns (scaled by same status gate).
            # points_std is measured on rounds actually played, so no availability scaling.
            points_std = float(player.get("points_std", 0) or 0) * status_weight
            floorCartola = expCartolaTotal - points_std
            ceilingCartola = expCartolaTotal + points_std
            captainValue = ceilingCartola * CAPTAIN_MULTIPLIER
            consistency = safe_divide(expCartolaTotal, points_std + 1.0)

            preco = float(player.get("preco_num", 0) or 0)
            costEfficiency = safe_divide(expCartolaTotal, preco)

            records.append(
                {
                    "atleta_id": atleta_id,
                    "apelido": player.get("apelido"),
                    "position": position,
                    "status_id": status_id,
                    "status_weight": status_weight,
                    "preco": preco,
                    "games": games,
                    "rounds_played": int(player.get("rounds_played", 0) or 0),
                    "availability": availability,
                    "sample_weight": sample_weight,
                    "formMultiplier": float(player.get("formMultiplier", 0) or 0),
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
                    "xCPD": xCPD,
                    "gkDefenseValue": gkDefenseValue,
                    "cardLiability": cardLiability,
                    "points_PG": float(player.get("points_PG", 0) or 0),
                    "points_std": float(player.get("points_std", 0) or 0),
                    "expCartolaTotal": expCartolaTotal,
                    "floorCartola": floorCartola,
                    "ceilingCartola": ceilingCartola,
                    "captainValue": captainValue,
                    "consistency": consistency,
                    "costEfficiency": costEfficiency,
                }
            )

        df = pd.DataFrame(records).set_index("atleta_id")

        # Value-vs-replacement: per-position median of expCartolaTotal among eligible players.
        if not df.empty:
            eligible = df[df["status_weight"] > 0]
            if not eligible.empty:
                medians = eligible.groupby("position")["expCartolaTotal"].median()
            else:
                medians = df.groupby("position")["expCartolaTotal"].median()
            df["valueVsReplacement"] = df.apply(
                lambda r: r["expCartolaTotal"] - float(medians.get(r["position"], 0.0)),
                axis=1,
            )

        numeric_cols = df.select_dtypes(include="number").columns
        df[numeric_cols] = df[numeric_cols].round(2)

        return df
