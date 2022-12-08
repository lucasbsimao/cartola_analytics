import requests
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


    def fill_games_info_with_all_rounds(self, num_rounds_to_calculate):
        round = self.get_round_games_from_api(self.predict_round)
        last_round = round["rodada"] - 1

        # dict_round_df_metrics = pd.DataFrame(0,columns=range(1,last_round, +1), index=[*teams_home,*teams_away])
        dict_round_df_metrics = {}
        for curr_round in range(1, round["rodada"],+1):
            mt = Metrics(self.teams_home, self.teams_away, self.predict_round)
            print("Getting games info from API for round " + str(curr_round))
            round_games = self.get_round_games_from_api(curr_round)
            round_info = self.get_round_info_from_api(curr_round)
            
            print("Calculating unique games info for round " + str(curr_round))
            
            dict_round_df_metrics[str(curr_round)] = mt.fill_data_frame_with_round_games_info(mt.df_games_info, round_games, round_info)

        ##################################
        mt_temp = Metrics(self.teams_home, self.teams_away, self.predict_round)

        for curr_round in range(last_round,last_round-num_rounds_to_calculate,-1):            
            print("Calculating acc games info for round " + str(curr_round))
            
            mt_temp.df_games_info = pd.concat([mt_temp.df_games_info,dict_round_df_metrics[str(curr_round)]]).groupby(level=0).sum()

        print("Calculating metrics")

        mt_temp.df_games_info = mt_temp.calculate_games_info_metrics(mt_temp.df_games_info)

        ind = Indicators(mt_temp.df_games_info, self.teams_home, self.teams_away, self.predict_round)
        df_indicators = ind.calculate_indicators_with_games_info()

        df_indicators.to_csv("indicators")



    def fill_games_info_with_last_rounds(self, num_rounds_to_calculate):
        round = self.get_round_games_from_api(self.predict_round)
        last_round = round["rodada"] - 1

        mt = Metrics(self.teams_home, self.teams_away, self.predict_round)

        # dict_round_df_metrics = {}
        for curr_round in range(last_round,last_round-num_rounds_to_calculate,-1):
            print("Getting games info from API for round " + str(curr_round))
            round_games = self.get_round_games_from_api(curr_round)
            round_info = self.get_round_info_from_api(curr_round)
            
            print("Calculating games info for round " + str(curr_round))
            
            mt.df_games_info = mt.fill_data_frame_with_round_games_info(mt.df_games_info, round_games, round_info)
            # dict_round_df_metrics[str(curr_round)] = self.df_games_info.copy()

        print("Calculating metrics")

        mt.df_games_info = mt.calculate_games_info_metrics(mt.df_games_info)

        ind = Indicators(mt.df_games_info, self.teams_home, self.teams_away, self.predict_round)
        df_indicators = ind.calculate_indicators_with_games_info()

        df_indicators.to_csv("indicators")
    

cartola = Cartola(37)

df_games_info = cartola.fill_games_info_with_all_rounds(10)



