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
        "SAVES TOTAL":[],
        "SAVES H":[],
        "SAVES A":[],
        "FIN POR GOL TOM":[],
        "FIN P GOL T H":[],
        "FIN P GOL T A":[]
    }

    rodada = get_round_games_from_api()

    times = [] #dataframe coluna 1 id coluna 2 abreviacao
    confrontos = {} #isso tem que ser um dataframe

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
    # print(round)

    api_columns = {
        "ID_TEAM":[],
        "DE":[],
        "SG":[],
        "FC":[],
        "FT":[],
        "DS":[],
        "PI":[],
        "FF":[],
        "FS":[],
        "CA":[],
        "FD":[],
        "A":[],
        "G":[],
        "I":[],
        "GS":[],
        "CV":[],
        "PC":[],
        "PP":[],
        "GC":[],
        "DP":[],
        "PS":[]
    }

    print("-----------------------------")
    for match in round_games["partidas"]:
        team_home = match["clube_casa_id"]
        team_away = match["clube_visitante_id"]
        print(round_games["clubes"][str(team_home)]["nome"])
        print(round_games["clubes"][str(team_away)]["nome"])


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

                


        print(scouts)
    
        print("+++")

# def _transform_api_data_to_df_columns(df_api_data, df_columns):

    # DE: "Defesa",
    # SG: "Saldo de gols",
    # FC: "Faltas cometidas",
    # FT: "Finalizações na trave",
    # DS: "Desarme",
    # PI: "Passes incompletos",
    # FF: "Finalizações para fora",
    # FS: "Faltas sofridas",
    # CA: "Cartos Amarelos",
    # FD: "Finalizações Defendidas",
    # A: "Assistencias",
    # G: "Gol",
    # I: "Impedimentos",
    # GS: "Gols sofridos",
    # CV: "Cartão vermelho",
    # PC: "Penalti cometido",
    # PP: "Penalti perdido"
    # GC: "Gols contra"
    # DP: "Defesa de Penalti"
    # PS: "Penalti sofrido"
    

    # for column in df_columns:
    #     match column:
    #         case "SHOTS OT PG":
    #             transformed_data["home"][column] = scout_home["FD"] + scout_home["FT"]
    #             break
    #         case "SHOTS OT PG H":
    #             break
    #         case "SHOTS OT PG A":
    #             break
    #         case "TOTAL SHOTS":
    #             break
    #         case "TOTAL SHOTS H":
    #             break
    #         case "TOTAL SHOTS A":
    #             break
    #         case "GF H":
    #             break
    #         case "GA H":
    #             break
    #         case "GF A":
    #             break
    #         case "GA A":
    #             break
    #         case "TOTAL SHOTS AGA":
    #             break
    #         case "TOTAL SHOTS AGA H":
    #             break
    #         case "TOTAL SHOTS AGA A":
    #             break
    #         case "SAVES TOTAL":
    #             break
    #         case "SAVES H":
    #             break
    #         case "SAVES A":
    #             break
    



def fill_data_with_last_5(df_data):
    round = get_round_games_from_api(None)
    last_round = round["rodada"] - 1

    for curr_round in range(last_round,last_round-5,-1):
        round_games = get_round_games_from_api(curr_round)
        round_info = get_round_info_from_api(curr_round)

        fill_data_frame_with_round_games_info(round_games, round_info, df_data)


df_data = create_df_data()

fill_data_with_last_5(df_data)

print()


    

