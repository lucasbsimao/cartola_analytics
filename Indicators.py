import math
import pandas as pd
import requests

class Indicators:
    def __init__(self, df_games_info, teams_home, teams_away, rodada_req=None):
        self.predict_round = rodada_req
        self.df_games_info = df_games_info
        self.df_indicators = self._create_dfs(teams_home, teams_away)

    def _create_dfs(self, teams_home, teams_away):
        columns_indicators = {
            "HOME": [],
            "shotsMultiOTH": [],
            "shotsMultiTotH": [],
            "goalsMultiH": [],
            "convRateH": [],
            "convRateTotalH": [],
            "saveRateH": [],
            "AWAY": [],
            "shotsMultiOTA": [],
            "shotsMultiTotA": [],
            "goalsMultiA": [],
            "convRateA": [],
            "convRateTotalA": [],
            "saveRateA": [],
            "scoreProbH": [],
            "scoreProbA": [],
            "cleanSheetProbH": [],
            "cleanSheetProbA": [],
        }

        df_indicators = pd.DataFrame(0, columns=columns_indicators, index=range(0, 10, 1))
        df_indicators["HOME"] = teams_home
        df_indicators["AWAY"] = teams_away

        return df_indicators

    def _request(self, url, round):
        if round is not None:
            url += str(round)

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.request("GET", url, headers=headers)
        return response.json()

    def get_round_games_from_api(self, round=None):
        url = "https://api.cartola.globo.com/partidas/"
        return self._request(url, round)

    def _team_id_to_abreviation_helper(self):
        rodada = self.get_round_games_from_api(self.predict_round)

        teams_abr = {}

        for partida in rodada["partidas"]:
            team_home_id = rodada["clubes"][str(partida["clube_casa_id"])]["id"]
            team_away_id = rodada["clubes"][str(partida["clube_visitante_id"])]["id"]

            team_home_abr = rodada["clubes"][str(partida["clube_casa_id"])]["abreviacao"]
            team_away_abr = rodada["clubes"][str(partida["clube_visitante_id"])]["abreviacao"]

            teams_abr[str(team_home_id)] = team_home_abr
            teams_abr[str(team_away_id)] = team_away_abr

        return teams_abr

    def calculate_indicators_with_games_info(self):
        team_abr = self._team_id_to_abreviation_helper()

        for index, row in self.df_indicators.iterrows():
            home = row["HOME"]
            away = row["AWAY"]

            if home not in self.df_games_info.index or away not in self.df_games_info.index:
                continue  # Skip if team IDs are not found

            self.df_indicators.loc[index, "shotsMultiOTH"] = self.df_games_info.loc[home, "SHOTS OT PG H"] * self.df_games_info.loc[away, "SHOTS OT AGA A"]
            self.df_indicators.loc[index, "shotsMultiOTA"] = self.df_games_info.loc[away, "SHOTS OT PG A"] * self.df_games_info.loc[home, "SHOTS OT AGA H"]

            self.df_indicators.loc[index, "shotsMultiTotH"] = self.df_games_info.loc[home, "TOTAL SHOTS H"] * self.df_games_info.loc[away, "TOTAL SHOTS AGA A"] / 10
            self.df_indicators.loc[index, "shotsMultiTotA"] = self.df_games_info.loc[away, "TOTAL SHOTS A"] * self.df_games_info.loc[home, "TOTAL SHOTS AGA H"] / 10

            self.df_indicators.loc[index, "goalsMultiH"] = (self.df_games_info.loc[home, "MGF H"] + self.df_games_info.loc[away, "MGA A"]) / 2
            self.df_indicators.loc[index, "goalsMultiA"] = (self.df_games_info.loc[away, "MGF A"] + self.df_games_info.loc[home, "MGA H"]) / 2

            conv_home_att = self.safe_divide(1, self.df_games_info.loc[home, "FIN P GOL F H"])
            conv_away_def = self.safe_divide(1, self.df_games_info.loc[away, "FIN P GOL T A"])
            self.df_indicators.loc[index, "convRateH"] = (conv_home_att + conv_away_def) / 2

            conv_away_att = self.safe_divide(1, self.df_games_info.loc[away, "FIN P GOL F A"])
            conv_home_def = self.safe_divide(1, self.df_games_info.loc[home, "FIN P GOL T H"])
            self.df_indicators.loc[index, "convRateA"] = (conv_away_att + conv_home_def) / 2

            conv_home_att_tot = self.safe_divide(1, self.df_games_info.loc[home, "FIN POR GOL FEITO"])
            conv_away_def_tot = self.safe_divide(1, self.df_games_info.loc[away, "FIN POR GOL TOM"])
            self.df_indicators.loc[index, "convRateTotalH"] = (conv_home_att_tot + conv_away_def_tot) / 2

            conv_away_att_tot = self.safe_divide(1, self.df_games_info.loc[away, "FIN POR GOL FEITO"])
            conv_home_def_tot = self.safe_divide(1, self.df_games_info.loc[home, "FIN POR GOL TOM"])
            self.df_indicators.loc[index, "convRateTotalA"] = (conv_away_att_tot + conv_home_def_tot) / 2

            self.df_indicators.loc[index, "saveRateH"] = 1 - self.safe_divide(self.df_games_info.loc[home, "MGA H"], self.df_games_info.loc[home, "SHOTS OT AGA H"])
            self.df_indicators.loc[index, "saveRateA"] = 1 - self.safe_divide(self.df_games_info.loc[away, "MGA A"], self.df_games_info.loc[away, "SHOTS OT AGA A"])

            p_home_scores = 1 - math.exp(-self.df_games_info.loc[home, "MGF H"])
            p_away_scores = 1 - math.exp(-self.df_games_info.loc[away, "MGF A"])
            self.df_indicators.loc[index, "scoreProbH"] = p_home_scores
            self.df_indicators.loc[index, "scoreProbA"] = p_away_scores
            self.df_indicators.loc[index, "cleanSheetProbH"] = 1 - p_away_scores
            self.df_indicators.loc[index, "cleanSheetProbA"] = 1 - p_home_scores

            self.df_indicators.loc[index, "HOME"] = team_abr[str(home)]
            self.df_indicators.loc[index, "AWAY"] = team_abr[str(away)]

        self.df_indicators = self.df_indicators.round(2)

        return self.df_indicators

    @staticmethod
    def safe_divide(numerator, denominator):
        if denominator == 0:
            return 0
        return numerator / denominator