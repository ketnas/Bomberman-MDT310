'''
Bomberman game - 2 players
Coded by: Kejkaew Thanasuan
Date: 2025-04-16

เริ่มเล่นเกมโดยการรัน main.py
$ python3 main.py
'''
'''
อันนี้เป็น main.py file
ใช้สำหรับกำหนดค่าพื้นฐานของเกม และเรียกใช้งาน game.py
สามารถตั้งค่า map ที่จะใช้ และเลือก algorithm ของผู้เล่นและศัตรูได้
'''
import pygame
import game
from enums.algorithm import Algorithm
from layout import *
import pandas as pd
import os, sys

WINDOW_SCALE = 0.75

#set frame rate
FPS = 20

classFile = {"G-0":"g0_submission","G-1":"g1_submission", "G-2":"g2_submission","G-3":"g3_submission","G-4":"g4_submission",
             "G-5":"g5_submission","G-6":"g6_submission","G-7":"g7_submission","G-8":"g8_submission",
             "G-9":"g9_submission","G-10":"g10_submission","G-11":"g11_submission","G-12":"g12_submission",
             "G-13":"g13_submission","G-14":"g14_submission","G-15":"g15_submission","G-16":"g16_submission"}

# เลือก map ที่จะใช้ จาก map folder
# map_file = './map/grid_test.txt'
map_file = ['./map/grid_test.txt','./map/grid_test.txt','./map/grid_circle.txt']

# set algorithm ของ player
'''
Algorithm ที่ใช้ในการเล่นของ bomberman สามารถเลือกได้ 3 แบบ
1. RANDOM สุ่มอย่างเดียว
2. PLAYER = คุณควบคุมเองโดยใช้ keyboard
3. YourAlgorithm = อันที่คุณเขียนเอง

Algorithm ที่ใช้ในการเล่นของ enemy สามารถเลือกได้ 2 แบบ
1. MANHATTAN = Manhattan distance
2. RANDOM = Random

ตัวอย่างการ setting
player_alg1 = Algorithm.DFS
player_alg1 = Algorithm.YourAlgorithm
player_alg2 = Algorithm.RANDOM
player_alg1 = Algorithm.PLAYER (อันนี้คือบอกว่าเล่นเองโดยใช้ keyboard : ปุ่มลูกศรขึ้นลงซ้ายขวา และ spacebar สำหรับวางระเบิด)

Note: เราต้องสามารถเล่นเองโดยใช้ keyboard ได้แค่ bomberman player 1 เท่านั้น
'''

player_alg1 = Algorithm.YourAlgorithm
player_alg2 = Algorithm.YourAlgorithm
en1_alg = Algorithm.MANHATTAN
en2_alg = Algorithm.RANDOM

clock = None

show_path = True
# เอา algorithm ใสใน list เพื่อส่งให้ game.py
en_alg = [en1_alg,en2_alg] 

def run_game(player1,player2,title,match):
    # before running the game, initialize pygame
    GRID_BASE = create_map(read_line(map_file[match]))
    w = len(GRID_BASE)
    h = len(GRID_BASE[0])

    # set window size to be 612x510
    pygame.display.init()
    current_h = 982
    TILE_SIZE = int(current_h * 0.035)
    WINDOW_SIZE = (w * TILE_SIZE, (h+2) * TILE_SIZE)
    surface = pygame.display.set_mode(WINDOW_SIZE)

    pygame.init()
    pygame.display.set_caption('Bomberman: '+title)
    
    # clock = pygame.time.Clock()
    winner = game.game_init(surface, show_path, player_alg1,player_alg2, en_alg, TILE_SIZE,GRID_BASE,player1,player2,match, FPS)
    return winner

def readCSV(filename):
    # Read a CSV file into a DataFrame
    df = pd.read_csv(filename)
    return df

def saveCSV(df,filename):

    # Save the DataFrame as a CSV file
    df.to_csv(filename, index=False)

def sortingCSV(df):
    # Sort the DataFrame by age in descending order
    df_sorted = df.sort_values(by='score', ascending=False)

    # print(df_sorted)
    return df_sorted

def updateTournament_table(winner,loser):
    df = readCSV("game_data/tournament_table.csv")
    if winner != None and loser != None:
        df.loc[df["team"]==winner,"score"] += 3
        df.loc[df["team"]==winner,"match"] += 1
        df.loc[df["team"]==winner,"win"] += 1

        df.loc[df["team"]==loser,"match"] += 1
        df.loc[df["team"]==loser,"loss"] += 1
        df_sorted = sortingCSV(df)
        saveCSV(df_sorted,"game_data/tournament_table.csv")
    else:
        df.loc[df["team"]==winner,"draw"] += 1
        df.loc[df["team"]==loser,"draw"] += 1
        df.loc[df["team"]==winner,"match"] += 1
        df.loc[df["team"]==loser,"match"] += 1
        df.loc[df["team"]==winner,"score"] += 1
        df.loc[df["team"]==loser,"score"] += 1
        df_sorted = sortingCSV(df)
        saveCSV(df_sorted,"game_data/tournament_table.csv")

def updateTournament_list(df,index,winner_list):
    
    for i in range(0,len(winner_list)):
        round = 'result_winner_'+str(i+1)
        df.loc[index, round] = winner_list[i]

    saveCSV(df,"game_data/tournament_list.csv")

if __name__ == "__main__":
    #run the game directly
    # os.chdir('/Users/kejkaew/Documents/python/Bomberman-MDT310-tournament/test')
    cwd = os.getcwd()
    sys.path.append('/Users/kejkaew/Documents/Programming-class/python-ai-class/Bomberman-MDT310-tournament/game_data/file')
    # sys.path.append('/Users/kejkaew/Documents/Programming-class/python-ai-class/Bomberman-MDT310-tournament/game_data')

    print("Current working directory: {0}".format(cwd))
    df = readCSV("game_data/tournament_list.csv")
    for i in range(0,3):
        round = 'result_winner_'+str(i+1)
        df[round] = df[round].astype(object)

    # start here --------
    nummatch = df.shape[0]
    # nummatch = 2
    index = 0
    for i in range(index,nummatch):
        team1 = df.loc[i,"team1"]
        team2 = df.loc[i,"team2"]
        title = team1 + " vs " + team2
        winner_list = []
        for match in range(3):
            player1 = __import__(classFile[team1])
            player2 = __import__(classFile[team2])
            winner_match = run_game(player1,player2,title,match)
            print("Match winner: ",winner_match)
            winner_list.append(winner_match)
            if match == 1 and winner_list[0] == winner_list[1]:
                winner_list.append(None)
                break
        
        updateTournament_list(df,i,winner_list)
        print(winner_list)
        win_team1 = sum(i=="team1" for i in winner_list)
        win_team2 = sum(i=="team2" for i in winner_list)
        if win_team1 > win_team2:
            winner = team1
            loser = team2
        elif win_team1 < win_team2:
            winner = team2
            loser = team1
        else:
            winner = None
            loser = None
        print("Round winner: ",winner)
        updateTournament_table(winner,loser)



