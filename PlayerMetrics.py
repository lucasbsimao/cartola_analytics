import pandas as pd

PLAYER_SCOUTS = [
    "G", "A", "FT", "FD", "FF", "FS", "PS", "DS", "SG",
    "DE", "DP", "GS", "CA", "CV", "FC", "GC", "I", "PP", "PC",
]

IDENTITY_COLUMNS = ["apelido", "clube_id", "posicao_id", "status_id", "preco_num"]


def safe_divide(numerator, denominator):
    if denominator == 0:
        return 0
    return numerator / denominator


class PlayerMetrics:
    def __init__(self, rodada_req=None):
        self.predict_round = rodada_req

    def fill_data_frame_with_round_players_info(self, round_players_info):
        rows = []
        for player_id, player in round_players_info["atletas"].items():
            if player.get("scout") is None:
                continue
            if player.get("posicao_id") == 6:  # técnico
                continue

            row = {"atleta_id": int(player_id)}
            for sc in PLAYER_SCOUTS:
                row[sc] = player["scout"].get(sc, 0)
            row["games"] = 1
            row["played"] = int(bool(player.get("entrou_em_campo", False)))
            for col in IDENTITY_COLUMNS:
                row[col] = player.get(col)
            rows.append(row)

        if not rows:
            columns = ["atleta_id", *PLAYER_SCOUTS, "games", "played", *IDENTITY_COLUMNS]
            return pd.DataFrame(columns=columns).set_index("atleta_id")

        df = pd.DataFrame(rows).set_index("atleta_id")
        return df

    @staticmethod
    def calculate_player_rate_metrics(list_df_players):
        if not list_df_players:
            raise ValueError("list_df_players is empty")

        stacked = pd.concat(list_df_players)
        stacked.index.name = "atleta_id"

        agg = {sc: "sum" for sc in PLAYER_SCOUTS}
        agg["games"] = "sum"
        agg["played"] = "sum"
        for col in IDENTITY_COLUMNS:
            agg[col] = "last"

        df = stacked.groupby(level=0).agg(agg)

        for sc in PLAYER_SCOUTS:
            df[f"{sc}_PG"] = df[sc] / df["games"].replace(0, pd.NA)
        df["availability"] = df["played"] / df["games"].replace(0, pd.NA)

        df = df.fillna(0)

        numeric_cols = [sc for sc in PLAYER_SCOUTS] + [f"{sc}_PG" for sc in PLAYER_SCOUTS] + ["availability"]
        df[numeric_cols] = df[numeric_cols].round(2)

        df.to_csv("players_metrics.csv")
        return df
