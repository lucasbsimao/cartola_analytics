import requests
import pandas as pd

from Metrics import Metrics
from Indicators import Indicators
from PlayerMetrics import PlayerMetrics
from PlayerIndicators import PlayerIndicators

class Cartola:
    def __init__(self, rodada_req=None):
        self.predict_round = rodada_req
        self.teams_home, self.teams_away = self._create_teams_array()
    
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
        
    def get_round_info_from_api(self, round=None):
        url = "https://api.cartola.globo.com/atletas/pontuados/"
        return self._request(url, round)

    def get_market_info_from_api(self):
        """Current mercado snapshot: latest status_id and preco_num per athlete."""
        return self._request("https://api.cartola.globo.com/atletas/mercado", None)

    def _create_teams_array(self):
        round_games = self.get_round_games_from_api(self.predict_round)
        if self.predict_round is None:
            self.predict_round = round_games["rodada"]
        print("Creating dataframes round " + str(self.predict_round))

        teams_home = []
        teams_away = []

        for partida in round_games["partidas"]:
            abreviacao_time_casa = round_games["clubes"][str(partida["clube_casa_id"])]["id"]
            abreviacao_time_fora = round_games["clubes"][str(partida["clube_visitante_id"])]["id"]
            teams_home.append(abreviacao_time_casa)
            teams_away.append(abreviacao_time_fora)

        return teams_home, teams_away


    def _fetch_rounds(self, num_rounds):
        round = self.get_round_games_from_api(self.predict_round)
        last_round = round["rodada"] - 1

        payloads = {}
        for curr_round in range(last_round, last_round - num_rounds, -1):
            print("Getting games info from API for round " + str(curr_round))
            round_games = self.get_round_games_from_api(curr_round)
            round_info = self.get_round_info_from_api(curr_round)
            payloads[curr_round] = (round_games, round_info)
        return payloads

    def fill_games_info_with_last_rounds(self, num_rounds_to_calculate):
        self.round_payloads = self._fetch_rounds(num_rounds_to_calculate)

        dict_games_info = {}
        for curr_round, (round_games, round_info) in self.round_payloads.items():
            round_mt = Metrics(self.teams_home, self.teams_away, self.predict_round)

            print("Calculating games info for round " + str(curr_round))

            dict_games_info[str(curr_round)] = round_mt.fill_data_frame_with_round_games_info(round_games, round_info)

        print("Calculating metrics")

        self.df_games_info = Metrics.calculate_games_info_metrics(dict_games_info.values())
        ind = Indicators(self.df_games_info, self.teams_home, self.teams_away, self.predict_round)
        self.df_indicators = ind.calculate_indicators_with_games_info()

        self.df_indicators.to_csv("indicators.csv")

        self._run_player_pipeline()

    def _run_player_pipeline(self):
        print("Calculating player metrics")
        list_df_players = []
        for curr_round, (round_games, round_info) in self.round_payloads.items():
            pm = PlayerMetrics(self.predict_round)
            list_df_players.append(
                pm.fill_data_frame_with_round_players_info(round_games, round_info, curr_round)
            )

        df_players_rates = PlayerMetrics.calculate_player_rate_metrics(list_df_players)

        print("Fetching current mercado snapshot for status_id / preco_num")
        mercado = self.get_market_info_from_api()
        mercado_rows = []
        for a in mercado.get("atletas", []):
            mercado_rows.append({
                "atleta_id": a.get("atleta_id"),
                "status_id_mkt": a.get("status_id"),
                "preco_num_mkt": a.get("preco_num"),
            })
        if mercado_rows:
            df_mkt = pd.DataFrame(mercado_rows).set_index("atleta_id")
            df_players_rates = df_players_rates.join(df_mkt, how="left")
            # Prefer fresh mercado values where available
            df_players_rates["status_id"] = df_players_rates["status_id_mkt"].combine_first(
                df_players_rates["status_id"]
            )
            df_players_rates["preco_num"] = df_players_rates["preco_num_mkt"].combine_first(
                df_players_rates["preco_num"]
            )
            df_players_rates = df_players_rates.drop(columns=["status_id_mkt", "preco_num_mkt"])

        df_players_rates.to_csv("players_metrics.csv")

        team_abr = {}
        for i, (h, a) in enumerate(zip(self.teams_home, self.teams_away)):
            team_abr[str(h)] = self.df_indicators.loc[i, "HOME"]
            team_abr[str(a)] = self.df_indicators.loc[i, "AWAY"]

        print("Calculating player indicators")
        pi = PlayerIndicators(
            df_players_rates,
            self.df_indicators,
            self.df_games_info,
            self.teams_home,
            self.teams_away,
            team_abr,
            self.predict_round,
        )
        self.df_players = pi.calculate_player_indicators()
        self.df_players.to_csv("players.csv")


cartola = Cartola()

df_games_info = cartola.fill_games_info_with_last_rounds(8)



