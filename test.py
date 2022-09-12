import requests
import re

import pandas as pd
import numpy as np

def get_round_games_from_api(round=None):
    url = "https://api.cartola.globo.com/partidas/"
    if round is not None:
        url += str(round)
    
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.request("GET", url, headers=headers)
    return response.json()

def get_round_info_from_api(round=None):
    url = "https://api.cartola.globo.com/atletas/pontuados/"
    if round is not None:
        url += str(round)
    
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.request("GET", url, headers=headers)
    return response.json()

def create_df_data():
    columns = {
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

    rodada = get_round_games_from_api()

    times = [] #dataframe coluna 1 id coluna 2 abreviacao

    for partida in rodada["partidas"]:
        abreviacao_time_casa = rodada["clubes"][str(partida["clube_casa_id"])]["id"]
        abreviacao_time_fora = rodada["clubes"][str(partida["clube_visitante_id"])]["id"]
        times.append(abreviacao_time_casa)
        times.append(abreviacao_time_fora)

    df = pd.DataFrame(0,columns=columns,index=times)
    return df

def get_info_last_5(text):
    return int(text) if text.isdigit() else text

def fill_data_frame_with_round_games_info(round_games, round_players_info, df_games_info):

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

        _transform_api_data_to_data_frame_data(scouts, df_games_info.columns.values.tolist())
    
def _switch_helper(column, df_api_data):
    shotsOT = lambda index: df_api_data.loc[index,"FD"] + df_api_data.loc[index,"FT"] + df_api_data.loc[index,"G"]
    totalShots = lambda index: shotsOT(index) + df_api_data.loc[index,"FF"]

    switch = { 
        "SHOTS OT PG H": lambda isHomeTeam: shotsOT("home") if isHomeTeam else 0,
        "SHOTS OT PG A": lambda isHomeTeam: shotsOT("away") if not isHomeTeam else 0,
        "TOTAL SHOTS H": lambda isHomeTeam: totalShots("home") if isHomeTeam else 0,
        "TOTAL SHOTS A": lambda isHomeTeam: totalShots("away") if not isHomeTeam else 0,
        "GF H": lambda isHomeTeam: df_api_data.loc["home","G"] if isHomeTeam else 0,
        "GA H": lambda isHomeTeam: df_api_data.loc["away","G"] if isHomeTeam else 0,
        "GF A": lambda isHomeTeam: df_api_data.loc["away","G"] if not isHomeTeam else 0,
        "GA A": lambda isHomeTeam: df_api_data.loc["home","G"] if not isHomeTeam else 0,
        "TOTAL SHOTS AGA H": lambda isHomeTeam: totalShots("away") if isHomeTeam else 0,
        "TOTAL SHOTS AGA A": lambda isHomeTeam: totalShots("home") if not isHomeTeam else 0,
        "SHOTS OT AGA H": lambda isHomeTeam: shotsOT("away") if isHomeTeam else 0,
        "SHOTS OT AGA A": lambda isHomeTeam: shotsOT("home") if not isHomeTeam else 0,
    }

    if column in switch:
        return switch[column]
    else:
        return lambda x: 0  

def _transform_api_data_to_data_frame_data(df_api_data, df_columns):
    team_home_id= df_api_data.loc["home","ID_TEAM"]
    team_away_id= df_api_data.loc["away","ID_TEAM"]

    transformed_data = pd.DataFrame(0, columns=df_columns, index=[team_home_id, team_away_id])    

    for column in df_columns:
        func = _switch_helper(column, df_api_data)
        transformed_data.loc[team_home_id,column] = func(True)
        transformed_data.loc[team_away_id,column] = func(False)

def fill_data_with_last_5(df_data):
    round = get_round_games_from_api(None)
    last_round = round["rodada"] - 1

    for curr_round in range(last_round,last_round-5,-1):
        round_games = get_round_games_from_api(curr_round)
        round_info = get_round_info_from_api(curr_round)
        fill_data_frame_with_round_games_info(round_games, round_info, df_data)

df_data = create_df_data()

fill_data_with_last_5(df_data)


    

