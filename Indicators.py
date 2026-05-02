import math
import pandas as pd
import requests

EXPECTED_SCOUTS = ["A", "FT", "FD", "FF", "FS", "PS", "DS", "CA"]

class Indicators:
    def __init__(self, df_games_info, teams_home, teams_away, rodada_req=None, baselines=None):
        self.predict_round = rodada_req
        self.df_games_info = df_games_info
        self.baselines = baselines or {}
        self.df_indicators = self._create_dfs(teams_home, teams_away)

    def _team_totals(self, team_id):
        """Aggregate stats across all games (home + away) for a given team.

        Returns per-game averages computed over the full set of matches the team played,
        not split by venue. SHOTS OT PG / SHOTS OT AGA values are weighted by matches per
        side since the underlying H/A columns are already per-match means.
        """
        row = self.df_games_info.loc[team_id]
        matches_h = row["MATCHES H"]
        matches_a = row["MATCHES A"]
        total_matches = matches_h + matches_a
        if total_matches == 0:
            return {"MGF": 0.0, "MGA": 0.0, "SHOTS_OT_PG": 0.0, "SHOTS_OT_AGA": 0.0}
        return {
            "MGF": (row["GF H"] + row["GF A"]) / total_matches,
            "MGA": (row["GA H"] + row["GA A"]) / total_matches,
            "SHOTS_OT_PG": (row["SHOTS OT PG H"] * matches_h + row["SHOTS OT PG A"] * matches_a) / total_matches,
            "SHOTS_OT_AGA": (row["SHOTS OT AGA H"] * matches_h + row["SHOTS OT AGA A"] * matches_a) / total_matches,
        }

    def _sos_factor(self, opp_value, baseline_key):
        base = self.baselines.get(baseline_key, 0)
        if not base:
            return 1.0
        return max(0.7, min(1.3, opp_value / base))

    def _create_dfs(self, teams_home, teams_away):
        columns_indicators = {
            "HOME": [],
            "shotsMultiOTH": [],
            "shotsMultiTotH": [],
            "goalsMultiH": [],
            "onTargetConvRateH": [],
            "totalShotConvRateH": [],
            "expectedSavesH": [],
            "scoreProbH": [],
            "cleanSheetProbH": [],
            "AWAY": [],
            "shotsMultiOTA": [],
            "shotsMultiTotA": [],
            "goalsMultiA": [],
            "onTargetConvRateA": [],
            "totalShotConvRateA": [],
            "expectedSavesA": [],
            "scoreProbA": [],
            "cleanSheetProbA": [],
            "sosH": [],
            "sosA": [],
        }

        for sc in EXPECTED_SCOUTS:
            columns_indicators[f"exp{sc}_H"] = []
            columns_indicators[f"exp{sc}_A"] = []

        df_indicators = pd.DataFrame(0.0, columns=columns_indicators, index=range(0, 10, 1))
        df_indicators["HOME"] = pd.array(teams_home, dtype=object)
        df_indicators["AWAY"] = pd.array(teams_away, dtype=object)

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
            home = int(row["HOME"])
            away = int(row["AWAY"])

            if home not in self.df_games_info.index or away not in self.df_games_info.index:
                continue  # Skip if team IDs are not found

            sos_goals_h = self._sos_factor(self.df_games_info.loc[away, "MGA A"], "MGA_A")
            sos_goals_a = self._sos_factor(self.df_games_info.loc[home, "MGA H"], "MGA_H")
            sos_shots_h = self._sos_factor(self.df_games_info.loc[away, "SHOTS OT AGA A"], "SHOTS_OT_AGA_A")
            sos_shots_a = self._sos_factor(self.df_games_info.loc[home, "SHOTS OT AGA H"], "SHOTS_OT_AGA_H")

            raw_shots_multi_ot_h = self.df_games_info.loc[home, "SHOTS OT PG H"] * self.df_games_info.loc[away, "SHOTS OT AGA A"]
            raw_shots_multi_ot_a = self.df_games_info.loc[away, "SHOTS OT PG A"] * self.df_games_info.loc[home, "SHOTS OT AGA H"]
            self.df_indicators.loc[index, "shotsMultiOTH"] = raw_shots_multi_ot_h * sos_shots_h
            self.df_indicators.loc[index, "shotsMultiOTA"] = raw_shots_multi_ot_a * sos_shots_a

            self.df_indicators.loc[index, "shotsMultiTotH"] = self.df_games_info.loc[home, "TOTAL SHOTS H"] * self.df_games_info.loc[away, "TOTAL SHOTS AGA A"] / 10
            self.df_indicators.loc[index, "shotsMultiTotA"] = self.df_games_info.loc[away, "TOTAL SHOTS A"] * self.df_games_info.loc[home, "TOTAL SHOTS AGA H"] / 10

            raw_goals_multi_h = (self.df_games_info.loc[home, "MGF H"] + self.df_games_info.loc[away, "MGA A"]) / 2
            raw_goals_multi_a = (self.df_games_info.loc[away, "MGF A"] + self.df_games_info.loc[home, "MGA H"]) / 2
            self.df_indicators.loc[index, "goalsMultiH"] = raw_goals_multi_h * sos_goals_h
            self.df_indicators.loc[index, "goalsMultiA"] = raw_goals_multi_a * sos_goals_a

            self.df_indicators.loc[index, "sosH"] = sos_goals_h
            self.df_indicators.loc[index, "sosA"] = sos_goals_a

            conv_home_att = self.safe_divide(1, self.df_games_info.loc[home, "FIN P GOL F H"])
            conv_away_def = self.safe_divide(1, self.df_games_info.loc[away, "FIN P GOL T A"])
            self.df_indicators.loc[index, "onTargetConvRateH"] = (conv_home_att + conv_away_def) / 2

            conv_away_att = self.safe_divide(1, self.df_games_info.loc[away, "FIN P GOL F A"])
            conv_home_def = self.safe_divide(1, self.df_games_info.loc[home, "FIN P GOL T H"])
            self.df_indicators.loc[index, "onTargetConvRateA"] = (conv_away_att + conv_home_def) / 2

            conv_home_att_tot = self.safe_divide(1, self.df_games_info.loc[home, "FIN POR GOL FEITO"])
            conv_away_def_tot = self.safe_divide(1, self.df_games_info.loc[away, "FIN POR GOL TOM"])
            self.df_indicators.loc[index, "totalShotConvRateH"] = (conv_home_att_tot + conv_away_def_tot) / 2

            conv_away_att_tot = self.safe_divide(1, self.df_games_info.loc[away, "FIN POR GOL FEITO"])
            conv_home_def_tot = self.safe_divide(1, self.df_games_info.loc[home, "FIN POR GOL TOM"])
            self.df_indicators.loc[index, "totalShotConvRateA"] = (conv_away_att_tot + conv_home_def_tot) / 2

            home_totals = self._team_totals(home)
            away_totals = self._team_totals(away)

            save_rate_h = 1 - self.safe_divide(home_totals["MGA"], home_totals["SHOTS_OT_AGA"])
            save_rate_a = 1 - self.safe_divide(away_totals["MGA"], away_totals["SHOTS_OT_AGA"])
            self.df_indicators.loc[index, "expectedSavesH"] = save_rate_h * away_totals["SHOTS_OT_PG"]
            self.df_indicators.loc[index, "expectedSavesA"] = save_rate_a * home_totals["SHOTS_OT_PG"]

            p_home_scores = 1 - math.exp(-home_totals["MGF"])
            p_away_scores = 1 - math.exp(-away_totals["MGF"])
            self.df_indicators.loc[index, "scoreProbH"] = p_home_scores
            self.df_indicators.loc[index, "scoreProbA"] = p_away_scores
            self.df_indicators.loc[index, "cleanSheetProbH"] = 1 - p_away_scores
            self.df_indicators.loc[index, "cleanSheetProbA"] = 1 - p_home_scores

            for sc in EXPECTED_SCOUTS:
                sos_exp_h = self._sos_factor(self.df_games_info.loc[away, f"{sc} AGA A"], f"{sc}_AGA_A")
                sos_exp_a = self._sos_factor(self.df_games_info.loc[home, f"{sc} AGA H"], f"{sc}_AGA_H")
                self.df_indicators.loc[index, f"exp{sc}_H"] = (
                    self.df_games_info.loc[home, f"{sc} H"] + self.df_games_info.loc[away, f"{sc} AGA A"]
                ) / 2 * sos_exp_h
                self.df_indicators.loc[index, f"exp{sc}_A"] = (
                    self.df_games_info.loc[away, f"{sc} A"] + self.df_games_info.loc[home, f"{sc} AGA H"]
                ) / 2 * sos_exp_a

            self.df_indicators.loc[index, "HOME"] = team_abr[str(home)]
            self.df_indicators.loc[index, "AWAY"] = team_abr[str(away)]

        self.df_indicators = self.df_indicators.round(2)

        return self.df_indicators

    @staticmethod
    def safe_divide(numerator, denominator):
        if denominator == 0:
            return 0
        return numerator / denominator