import requests

import pandas as pd
import numpy as np

class Cartola:
    def __init__(self, rodada_req=None):
        self.predict_round = rodada_req
        self.df_games_info, self.df_indicators = self._create_dfs()
    
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

    def _create_dfs(self):
        columns_game = {
            "SHOTS OT PG":[],
            "SHOTS OT PG H":[],
            "SHOTS OT PG A":[],
            "TOTAL SHOTS":[],
            "TOTAL SHOTS H":[],
            "TOTAL SHOTS A":[],
            "MATCHES H":[],
            "GF H":[],
            "GA H":[],
            "MGF H":[],
            "MGA H":[],
            "MATCHES A":[],
            "GF A":[],
            "GA A":[],
            "MGF A":[],
            "MGA A":[],
            "FIN POR GOL FEITO":[],
            "FIN P GOL F H":[],
            "FIN P GOL F A":[],
            "TOTAL SHOTS AGA":[],
            "TOTAL SHOTS AGA H":[],
            "TOTAL SHOTS AGA A":[],
            "SHOTS OT AGA TOTAL":[],
            "SHOTS OT AGA H":[],
            "SHOTS OT AGA A":[],
            "FIN POR GOL TOM":[],
            "FIN P GOL T H":[],
            "FIN P GOL T A":[]
        }

        columns_indicators = {
            "HOME":[],
            "shotsMultiOTH":[],
            "shotsMultiTotH":[],
            "shotsMultiH":[],
            "goalsMultiH":[],
            "goalsMultiTH":[],
            "taxFinH":[],
            "taxFinTotalH":[],
            "resultShotsDivFinH":[],
            "AWAY":[],
            "shotsMultiOTA":[],
            "shotsMultiTotA":[],
            "shotsMultiA":[],
            "goalsMultiA":[],
            "goalsMultiTA":[],
            "taxFinA":[],
            "taxFinTotalA":[],
            "resultShotsDivFinA":[]
        }


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

        df_indicators = pd.DataFrame(0,columns=columns_indicators, index=range(0,10,1))
        df_indicators["HOME"] = teams_home
        df_indicators["AWAY"] = teams_away

        df_game_info = pd.DataFrame(0,columns=columns_game, index=[*teams_home,*teams_away])
        return df_game_info, df_indicators

    def fill_data_frame_with_round_games_info(self, round_games, round_players_info):
        if self.df_games_info is None:
            raise Exception("df_games_info not provided")

        api_columns = {
            "ID_TEAM":[],
            "DE":[], # DE: "Defesa",
            "SG":[], # SG: "Saldo de gols",
            "FC":[], # FC: "Faltas cometidas",
            "FT":[], # FT: "Finalizações na trave",
            "DS":[], # DS: "Desarme",
            "PI":[], # PI: "Passes incompletos",
            "FF":[], # FF: "Finalizações para fora",
            "FS":[], # FS: "Faltas sofridas",
            "CA":[], # CA: "Cartos Amarelos",
            "FD":[], # FD: "Finalizações Defendidas",
            "A":[], # A: "Assistencias",
            "G":[], # G: "Gol",
            "I":[], # I: "Impedimentos",
            "GS":[], # GS: "Gols sofridos",
            "CV":[], # CV: "Cartão vermelho",
            "PC":[], # PC: "Penalti cometido",
            "PP":[], # PP: "Penalti perdido"
            "GC":[], # GC: "Gols contra"
            "DP":[], # DP: "Defesa de Penalti"
            "PS":[] # PS: "Penalti sofrido"
        }

        aggr_df_games_info = self.df_games_info.copy()
        for match in round_games["partidas"]:
            team_home = match["clube_casa_id"]
            team_away = match["clube_visitante_id"]

            scouts = pd.DataFrame(0, columns=api_columns, index=["home", "away"])
            scouts.loc[["home"],["ID_TEAM"]] = team_home
            scouts.loc[["away"],["ID_TEAM"]] = team_away

            for playerId in round_players_info["atletas"]:
                player = round_players_info["atletas"][str(playerId)]

                if player["scout"] is None:
                    continue
                
                if player["clube_id"] == team_home:
                    for sc in player["scout"]:
                        scouts.loc[["home"],[sc]] += player["scout"][sc]

                
                if player["clube_id"] == team_away:
                    for sc in player["scout"]:
                        scouts.loc[["away"],[sc]] += player["scout"][sc]

            transformed_data = self._transform_api_data_to_data_frame_data(scouts, self.df_games_info.columns.values.tolist())
            aggr_df_games_info = pd.concat([aggr_df_games_info,transformed_data]).groupby(level=0).sum()
        return aggr_df_games_info
        
    def _switch_helper(self, column, df_api_data):
        shotsOT = lambda index: df_api_data.loc[index,"FD"] + df_api_data.loc[index,"FT"] + df_api_data.loc[index,"G"]
        totalShots = lambda index: shotsOT(index) + df_api_data.loc[index,"FF"]

        switch = {
            "SHOTS OT PG H": lambda isHomeTeam: shotsOT("home") if isHomeTeam else 0,
            "SHOTS OT PG A": lambda isHomeTeam: shotsOT("away") if not isHomeTeam else 0,
            "TOTAL SHOTS H": lambda isHomeTeam: totalShots("home") if isHomeTeam else 0,
            "TOTAL SHOTS A": lambda isHomeTeam: totalShots("away") if not isHomeTeam else 0,
            "GF H": lambda isHomeTeam: df_api_data.loc["home","G"] + df_api_data.loc["away","GC"] if isHomeTeam else 0,
            "GA H": lambda isHomeTeam: df_api_data.loc["away","G"] + df_api_data.loc["home","GC"] if isHomeTeam else 0,
            "GF A": lambda isHomeTeam: df_api_data.loc["away","G"] + df_api_data.loc["home","GC"] if not isHomeTeam else 0,
            "GA A": lambda isHomeTeam: df_api_data.loc["home","G"] + df_api_data.loc["away","GC"] if not isHomeTeam else 0,
            "TOTAL SHOTS AGA H": lambda isHomeTeam: totalShots("away") if isHomeTeam else 0,
            "TOTAL SHOTS AGA A": lambda isHomeTeam: totalShots("home") if not isHomeTeam else 0,
            "SHOTS OT AGA H": lambda isHomeTeam: shotsOT("away") if isHomeTeam else 0,
            "SHOTS OT AGA A": lambda isHomeTeam: shotsOT("home") if not isHomeTeam else 0,
            "MATCHES H": lambda isHomeTeam: 1 if isHomeTeam else 0,
            "MATCHES A": lambda isHomeTeam: 1 if not isHomeTeam else 0,
        }

        if column in switch:
            return switch[column]
        else:
            return lambda x: 0  

    def _transform_api_data_to_data_frame_data(self, df_api_data, df_columns):
        team_home_id= df_api_data.loc["home","ID_TEAM"]
        team_away_id= df_api_data.loc["away","ID_TEAM"]

        transformed_data = pd.DataFrame(0, columns=df_columns, index=[team_home_id, team_away_id])    

        for column in df_columns:
            func = self._switch_helper(column, df_api_data)
            transformed_data.loc[team_home_id,column] = func(True)
            transformed_data.loc[team_away_id,column] = func(False)
        
        return transformed_data

    def calculate_games_info_metrics(self, df_metrics):

        columns_A = ["SHOTS OT PG H", "TOTAL SHOTS H", "TOTAL SHOTS AGA H", "SHOTS OT AGA H"]
        df_metrics[columns_A] = df_metrics.loc[:, columns_A].div(df_metrics["MATCHES H"], axis=0)

        columns_A = ["SHOTS OT PG A", "TOTAL SHOTS A", "TOTAL SHOTS AGA A", "SHOTS OT AGA A"]
        df_metrics[columns_A] = df_metrics.loc[:, columns_A].div(df_metrics["MATCHES A"], axis=0)
        
        df_metrics["MGF H"] = df_metrics.loc[:, ["GF H"]].div(df_metrics["MATCHES H"], axis=0)
        df_metrics["MGA H"] = df_metrics.loc[:, ["GA H"]].div(df_metrics["MATCHES H"], axis=0)

        df_metrics["MGF A"] = df_metrics.loc[:, ["GF A"]].div(df_metrics["MATCHES A"], axis=0)
        df_metrics["MGA A"] = df_metrics.loc[:, ["GA A"]].div(df_metrics["MATCHES A"], axis=0)

        df_metrics["SHOTS OT PG"] = df_metrics.loc[:, ["SHOTS OT PG H", "SHOTS OT PG A"]].sum(axis=1).div(2)
        df_metrics["TOTAL SHOTS"] = df_metrics.loc[:, ["TOTAL SHOTS H", "TOTAL SHOTS A"]].sum(axis=1).div(2)
        df_metrics["TOTAL SHOTS AGA"] = df_metrics.loc[:, ["TOTAL SHOTS AGA H", "TOTAL SHOTS AGA A"]].sum(axis=1).div(2)
        df_metrics["SHOTS OT AGA TOTAL"] = df_metrics.loc[:, ["SHOTS OT AGA H", "SHOTS OT AGA A"]].sum(axis=1).div(2)
        
        df_mgf_mean = df_metrics.loc[:, ["MGF H", "MGF A"]].sum(axis=1).div(2)
        df_metrics["FIN POR GOL FEITO"] = df_metrics.loc[:,["SHOTS OT PG"]].div(df_mgf_mean, axis=0)
        df_metrics["FIN P GOL F H"] = df_metrics.loc[:,["SHOTS OT PG H"]].div(df_metrics["MGF H"], axis=0)
        df_metrics["FIN P GOL F A"] = df_metrics.loc[:,["SHOTS OT PG A"]].div(df_metrics["MGF A"], axis=0)

        df_mga_mean = df_metrics.loc[:, ["MGA H", "MGA A"]].sum(axis=1).div(2)
        df_metrics["FIN POR GOL TOM"] = df_metrics.loc[:,["SHOTS OT AGA TOTAL"]].div(df_mga_mean, axis=0)
        df_metrics["FIN P GOL T H"] = df_metrics.loc[:,["SHOTS OT AGA H"]].div(df_metrics["MGA H"], axis=0)
        df_metrics["FIN P GOL T A"] = df_metrics.loc[:,["SHOTS OT AGA A"]].div(df_metrics["MGA A"], axis=0)

        df_metrics = df_metrics.round(2)
        df_metrics.to_csv('metrics')

        return df_metrics

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

            self.df_indicators.loc[index,"shotsMultiOTH"] = self.df_games_info.loc[home,"SHOTS OT PG H"] * self.df_games_info.loc[away,"SHOTS OT AGA A"]
            self.df_indicators.loc[index,"shotsMultiOTA"] = self.df_games_info.loc[away,"SHOTS OT PG A"] * self.df_games_info.loc[home,"SHOTS OT AGA H"]

            self.df_indicators.loc[index,"shotsMultiH"] = self.df_games_info.loc[home,"TOTAL SHOTS"] * self.df_games_info.loc[away,"TOTAL SHOTS AGA"]/10
            self.df_indicators.loc[index,"shotsMultiA"] = self.df_games_info.loc[away,"TOTAL SHOTS"] * self.df_games_info.loc[home,"TOTAL SHOTS AGA"]/10

            self.df_indicators.loc[index,"shotsMultiTotH"] = self.df_games_info.loc[home,"TOTAL SHOTS H"] * self.df_games_info.loc[away,"TOTAL SHOTS AGA H"]/10
            self.df_indicators.loc[index,"shotsMultiTotA"] = self.df_games_info.loc[away,"TOTAL SHOTS A"] * self.df_games_info.loc[home,"TOTAL SHOTS AGA A"]/10

            self.df_indicators.loc[index,"goalsMultiH"] = self.df_games_info.loc[home,"MGF H"] * self.df_games_info.loc[away,"MGA A"]
            self.df_indicators.loc[index,"goalsMultiA"] = self.df_games_info.loc[away,"MGF A"] * self.df_games_info.loc[home,"MGA H"]

            self.df_indicators.loc[index,"goalsMultiTH"] = (self.df_games_info.loc[home,"MGF H"] + self.df_games_info.loc[home,"MGF A"])/2  * (self.df_games_info.loc[away,"MGA A"] + self.df_games_info.loc[away,"MGA H"])/2
            self.df_indicators.loc[index,"goalsMultiTA"] = (self.df_games_info.loc[away,"MGF H"] + self.df_games_info.loc[away,"MGF A"])/2  * (self.df_games_info.loc[home,"MGA A"] + self.df_games_info.loc[home,"MGA H"])/2

            self.df_indicators.loc[index,"taxFinTotalH"] = self.df_games_info.loc[home,"FIN POR GOL FEITO"] * self.df_games_info.loc[away,"FIN POR GOL TOM"]
            self.df_indicators.loc[index,"taxFinTotalA"] = self.df_games_info.loc[away,"FIN POR GOL FEITO"] * self.df_games_info.loc[home,"FIN POR GOL TOM"]

            self.df_indicators.loc[index,"taxFinH"] = self.df_games_info.loc[home,"FIN P GOL F H"] * self.df_games_info.loc[away,"FIN P GOL T A"]
            self.df_indicators.loc[index,"taxFinA"] = self.df_games_info.loc[away,"FIN P GOL F A"] * self.df_games_info.loc[home,"FIN P GOL T H"]

            shotsDivFinH = self.df_games_info.loc[home,"SHOTS OT PG H"] / self.df_games_info.loc[away,"FIN P GOL T A"]
            shotsDivFinA = self.df_games_info.loc[away,"SHOTS OT PG A"] / self.df_games_info.loc[home,"FIN P GOL T H"]

            savesDivFinH = self.df_games_info.loc[away,"SHOTS OT AGA A"] / self.df_games_info.loc[home,"FIN P GOL F H"]
            savesDivFinA = self.df_games_info.loc[home,"SHOTS OT AGA H"] / self.df_games_info.loc[away,"FIN P GOL F A"]

            self.df_indicators.loc[index,"resultShotsDivFinH"] = (shotsDivFinH + savesDivFinH)/2
            self.df_indicators.loc[index,"resultShotsDivFinA"] = (shotsDivFinA + savesDivFinA)/2

            self.df_indicators.loc[index,"HOME"] = team_abr[str(home)]
            self.df_indicators.loc[index,"AWAY"] = team_abr[str(away)]
        
        self.df_indicators = self.df_indicators.round(2)

        return self.df_indicators


    def fill_games_info_with_last_rounds(self, num_rounds_to_calculate):
        round = self.get_round_games_from_api(self.predict_round)
        last_round = round["rodada"] - 1

        # dict_round_df_metrics = {}
        for curr_round in range(last_round,last_round-num_rounds_to_calculate,-1):
            print("Getting games info from API for round " + str(curr_round))
            round_games = self.get_round_games_from_api(curr_round)
            round_info = self.get_round_info_from_api(curr_round)
            
            print("Calculating games info for round " + str(curr_round))
            self.df_games_info = self.fill_data_frame_with_round_games_info(round_games, round_info)
            # dict_round_df_metrics[str(curr_round)] = self.df_games_info.copy()

        print("Calculating metrics")

        self.df_games_info = self.calculate_games_info_metrics(self.df_games_info)
        return self.df_games_info
    

cartola = Cartola()

cartola.fill_games_info_with_last_rounds(10)
df_indicators = cartola.calculate_indicators_with_games_info()

df_indicators.to_csv("indicators")


