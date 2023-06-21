import pandas as pd

class Metrics:
    def __init__(self, teams_home, teams_away, rodada_req=None):
        self.predict_round = rodada_req
        self.df_games_info = self._create_dfs(teams_home, teams_away)

    def _create_dfs(self, teams_home, teams_away):
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

        df_game_info = pd.DataFrame(0,columns=columns_game, index=[*teams_home,*teams_away])
        return df_game_info

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
            "V":[], # V: "Vitória do técnico",
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

    @staticmethod
    def calculate_games_info_metrics(df_games_info):

        columns_A = ["SHOTS OT PG H", "TOTAL SHOTS H", "TOTAL SHOTS AGA H", "SHOTS OT AGA H"]
        df_games_info[columns_A] = df_games_info.loc[:, columns_A].div(df_games_info["MATCHES H"], axis=0)

        columns_A = ["SHOTS OT PG A", "TOTAL SHOTS A", "TOTAL SHOTS AGA A", "SHOTS OT AGA A"]
        df_games_info[columns_A] = df_games_info.loc[:, columns_A].div(df_games_info["MATCHES A"], axis=0)
        
        df_games_info["MGF H"] = df_games_info.loc[:, ["GF H"]].div(df_games_info["MATCHES H"], axis=0)
        df_games_info["MGA H"] = df_games_info.loc[:, ["GA H"]].div(df_games_info["MATCHES H"], axis=0)

        df_games_info["MGF A"] = df_games_info.loc[:, ["GF A"]].div(df_games_info["MATCHES A"], axis=0)
        df_games_info["MGA A"] = df_games_info.loc[:, ["GA A"]].div(df_games_info["MATCHES A"], axis=0)

        df_games_info["SHOTS OT PG"] = df_games_info.loc[:, ["SHOTS OT PG H", "SHOTS OT PG A"]].sum(axis=1).div(2)
        df_games_info["TOTAL SHOTS"] = df_games_info.loc[:, ["TOTAL SHOTS H", "TOTAL SHOTS A"]].sum(axis=1).div(2)
        df_games_info["TOTAL SHOTS AGA"] = df_games_info.loc[:, ["TOTAL SHOTS AGA H", "TOTAL SHOTS AGA A"]].sum(axis=1).div(2)
        df_games_info["SHOTS OT AGA TOTAL"] = df_games_info.loc[:, ["SHOTS OT AGA H", "SHOTS OT AGA A"]].sum(axis=1).div(2)
        
        df_mgf_mean = df_games_info.loc[:, ["MGF H", "MGF A"]].sum(axis=1).div(2)
        df_games_info["FIN POR GOL FEITO"] = df_games_info.loc[:,["SHOTS OT PG"]].div(df_mgf_mean, axis=0)
        df_games_info["FIN P GOL F H"] = df_games_info.loc[:,["SHOTS OT PG H"]].div(df_games_info["MGF H"], axis=0)
        df_games_info["FIN P GOL F A"] = df_games_info.loc[:,["SHOTS OT PG A"]].div(df_games_info["MGF A"], axis=0)

        df_mga_mean = df_games_info.loc[:, ["MGA H", "MGA A"]].sum(axis=1).div(2)
        df_games_info["FIN POR GOL TOM"] = df_games_info.loc[:,["SHOTS OT AGA TOTAL"]].div(df_mga_mean, axis=0)
        df_games_info["FIN P GOL T H"] = df_games_info.loc[:,["SHOTS OT AGA H"]].div(df_games_info["MGA H"], axis=0)
        df_games_info["FIN P GOL T A"] = df_games_info.loc[:,["SHOTS OT AGA A"]].div(df_games_info["MGA A"], axis=0)

        df_games_info = df_games_info.round(2)
        df_games_info.to_csv('metrics')

        return df_games_info