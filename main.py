import requests
import functools
import pandas as pd

from Metrics import Metrics
from Indicators import Indicators

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


    def fill_games_info_with_last_rounds(self, num_rounds_to_calculate):
        round = self.get_round_games_from_api(self.predict_round)
        last_round = round["rodada"] - 1

        dict_games_info = {}
        for curr_round in range(last_round,last_round-num_rounds_to_calculate,-1):
            print("Getting games info from API for round " + str(curr_round))
            round_mt = Metrics(self.teams_home, self.teams_away, self.predict_round)
            round_games = self.get_round_games_from_api(curr_round)
            round_info = self.get_round_info_from_api(curr_round)
            
            print("Calculating games info for round " + str(curr_round))
            
            dict_games_info[str(curr_round)] = round_mt.fill_data_frame_with_round_games_info(round_games, round_info)

        print("Calculating metrics")

        acc_games_info = functools.reduce(lambda first_games_info, sec_games_info: pd.concat([first_games_info,sec_games_info]).groupby(level=0).sum(), dict_games_info.values())
        
        ind = Indicators(Metrics.calculate_games_info_metrics(acc_games_info), self.teams_home, self.teams_away, self.predict_round)
        df_indicators = ind.calculate_indicators_with_games_info()

        df_indicators.to_csv("indicators")
    

cartola = Cartola(8)

df_games_info = cartola.fill_games_info_with_last_rounds(8)



