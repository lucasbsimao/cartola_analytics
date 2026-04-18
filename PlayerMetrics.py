import pandas as pd

PLAYER_SCOUTS = [
    "G", "A", "FT", "FD", "FF", "FS", "PS", "DS", "SG",
    "DE", "DP", "GS", "CA", "CV", "FC", "GC", "I", "PP", "PC",
]

IDENTITY_COLUMNS = ["apelido", "clube_id", "posicao_id", "status_id", "preco_num"]

FORM_WINDOW = 3  # rounds considered "recent form" for formMultiplier


def safe_divide(numerator, denominator):
    if denominator == 0:
        return 0
    return numerator / denominator


class PlayerMetrics:
    def __init__(self, rodada_req=None):
        self.predict_round = rodada_req

    def fill_data_frame_with_round_players_info(self, round_games, round_players_info, round_number=None):
        # Map club_id -> is_home for this round
        side_by_club = {}
        for match in round_games.get("partidas", []):
            side_by_club[match["clube_casa_id"]] = True
            side_by_club[match["clube_visitante_id"]] = False

        rows = []
        for player_id, player in round_players_info["atletas"].items():
            if player.get("scout") is None:
                continue
            if player.get("posicao_id") == 6:  # técnico
                continue

            club_id = player.get("clube_id")
            is_home = side_by_club.get(club_id)
            if is_home is None:
                # Player's club didn't play this round in the provided games payload
                continue

            row = {"atleta_id": int(player_id)}
            played = int(bool(player.get("entrou_em_campo", False)))
            row["games"] = 1
            row["played"] = played
            row["games_H"] = 1 if is_home else 0
            row["games_A"] = 0 if is_home else 1
            row["played_H"] = played if is_home else 0
            row["played_A"] = 0 if is_home else played
            row["pontuacao"] = float(player.get("pontuacao", 0) or 0)
            row["round"] = round_number if round_number is not None else -1

            for sc in PLAYER_SCOUTS:
                val = player["scout"].get(sc, 0)
                row[sc] = val
                row[f"{sc}_H"] = val if is_home else 0
                row[f"{sc}_A"] = 0 if is_home else val

            for col in IDENTITY_COLUMNS:
                row[col] = player.get(col)
            rows.append(row)

        if not rows:
            scout_cols = []
            for sc in PLAYER_SCOUTS:
                scout_cols += [sc, f"{sc}_H", f"{sc}_A"]
            columns = [
                "atleta_id", *scout_cols,
                "games", "played", "games_H", "games_A", "played_H", "played_A",
                "pontuacao", "round", *IDENTITY_COLUMNS,
            ]
            return pd.DataFrame(columns=columns).set_index("atleta_id")

        df = pd.DataFrame(rows).set_index("atleta_id")
        return df

    @staticmethod
    def calculate_player_rate_metrics(list_df_players):
        if not list_df_players:
            raise ValueError("list_df_players is empty")

        stacked = pd.concat(list_df_players)
        stacked.index.name = "atleta_id"

        sum_cols = []
        for sc in PLAYER_SCOUTS:
            sum_cols += [sc, f"{sc}_H", f"{sc}_A"]
        sum_cols += ["games", "played", "games_H", "games_A", "played_H", "played_A"]

        agg = {c: "sum" for c in sum_cols}
        for col in IDENTITY_COLUMNS:
            agg[col] = "last"

        df = stacked.groupby(level=0).agg(agg)

        # Per-round pontuacao-derived volatility (only rounds the player actually played)
        def _volatility(sub):
            played_rounds = sub.loc[sub["played"] == 1]
            pts = played_rounds["pontuacao"].astype(float)
            n = len(pts)
            mean = float(pts.mean()) if n else 0.0
            std = float(pts.std(ddof=0)) if n else 0.0
            # Recent-form average over the most recent FORM_WINDOW rounds played
            recent = played_rounds.sort_values("round").tail(FORM_WINDOW)["pontuacao"].astype(float)
            recent_mean = float(recent.mean()) if len(recent) else 0.0
            return pd.Series({
                "points_PG": mean,
                "points_std": std,
                "points_PG_recent": recent_mean,
                "rounds_played": n,
            })

        vol = stacked.groupby(level=0).apply(_volatility)
        df = df.join(vol)

        # Per-game rates (overall + side-split)
        games = df["games"].replace(0, pd.NA)
        games_H = df["games_H"].replace(0, pd.NA)
        games_A = df["games_A"].replace(0, pd.NA)

        for sc in PLAYER_SCOUTS:
            df[f"{sc}_PG"] = df[sc] / games
            df[f"{sc}_PG_H"] = df[f"{sc}_H"] / games_H
            df[f"{sc}_PG_A"] = df[f"{sc}_A"] / games_A

        df["availability"] = df["played"] / games
        df["formMultiplier"] = df["points_PG_recent"] / df["points_PG"].replace(0, pd.NA)

        df = df.fillna(0)

        numeric_cols = df.select_dtypes(include="number").columns
        df[numeric_cols] = df[numeric_cols].round(2)

        return df
