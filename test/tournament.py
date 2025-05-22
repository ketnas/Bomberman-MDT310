# create matches of each round and save to csv files
import random
import pandas as pd
from itertools import combinations

def createTournament_table():
    players = ["G-1", "G-2", "G-3", "G-4", "G-5", "G-6", "G-7", "G-8","G-9","G-10","G-11","G-12","G-13","G-14","G-15","G-16"]
    num = len(players)
    data = {'team':players,
            'match': [0]*num,
            'win':[0]*num,
            'loss': [0]*num,
            'draw': [0]*num,
            'score': [0]*num}
    df = pd.DataFrame(data)
    df_sorted = df.sort_values(by='team', ascending=False)
    print(df_sorted)
    saveCSV(df,"tournament_table.csv")

def updateTournament_list(index,round,winner):
    df = readCSV("tournament_list.csv")
    if round == 1:
        df.loc[index, 'result_winner_1'] = winner
    elif round == 2:
        df.loc[index, 'result_winner_2'] = winner
    else:
        df.loc[index, 'result_winner_3'] = winner

    saveCSV(df,"tournament_list.csv")

def updateTournament_table(winner,loser):
    df = readCSV("tournament_table.csv")
    df.loc[df["team"]==winner,"score"] += 3
    df.loc[df["team"]==winner,"match"] += 1
    df.loc[df["team"]==winner,"win"] += 1

    df.loc[df["team"]==loser,"match"] += 1
    df.loc[df["team"]==loser,"loss"] += 1
    df_sorted = sortingCSV(df)
    saveCSV(df_sorted,"tournament_table.csv")

def randomMatch():
    teams = ["G-1", "G-2", "G-3", "G-4", "G-5", "G-6", "G-7", "G-8","G-9","G-10","G-11","G-12","G-13","G-14","G-15","G-16"]
    mat = list(combinations(teams,2))

    newmat = []
    for pair in mat:
        listpair = list(pair)
        random.shuffle(listpair)
        tup = tuple(listpair)
        newmat.append(tup)

    random.shuffle(newmat)
    print(len(newmat))
    data = {'index':[],
                'team1':[],
                'team2':[],
                'result_winner_1':[],
                'result_winner_2':[],
                'result_winner_3':[]}

    for index in range(len(newmat)):
        players = newmat[index]
        data['index'].append(index)
        data['team1'].append(players[0])
        data['team2'].append(players[1])
        data['result_winner_1'].append(None)
        data['result_winner_2'].append(None)
        data['result_winner_3'].append(None)

    df = pd.DataFrame(data)
    print(df)
    saveCSV(df,'tournament_list.csv')
    # print(matchUps)

# def randomMatch():
#     players = ["G-1", "G-2", "G-3", "G-4", "G-5", "G-6", "G-7", "G-8","G-9","G-10","G-11","G-12"]
#     num_rounds = 11
#     data = {'round':[],
#             'team1':[],
#             'team2':[],
#             'result_winner_1':[],
#             'result_winner_2':[],
#             'result_winner_3':[]}
    
#     for round in range(num_rounds):
#         print(f"Round {round + 1}:")
#         random.shuffle(players)
#         for i in range(0, len(players), 2):
#             print(f"Match: {players[i]} vs. {players[i+1]}")
#             data['round'].append(round+1)
#             data['team1'].append(players[i])
#             data['team2'].append(players[i+1])
#             data['result_winner_1'].append(None)
#             data['result_winner_2'].append(None)
#             data['result_winner_3'].append(None)
#         print()
#     print(data)
#     df = pd.DataFrame(data)

#     saveCSV(df,'tournament_list.csv')

# Create a DataFrame
# data = {'name': ['Alice', 'Bob', 'Charlie'], 'age': [25, 30, 35]}
# df = pd.DataFrame(data)

# # Get data from a specific row and column
# age_of_bob = df.loc[1, 'age']

# print(age_of_bob) # Output: 30

def readCSV(filename):
    # Read a CSV file into a DataFrame
    df = pd.read_csv(filename)
    return df

def saveCSV(df,filename):

    # Save the DataFrame as a CSV file
    df.to_csv(filename, index=False)

def sortingCSV(df):
    
    # df = readCSV('tournament_list.csv')
    # Sort the DataFrame by age in descending order
    df_sorted = df.sort_values(by='score', ascending=False)

    # print(df_sorted)
    return df_sorted

def main():
    randomMatch()
    createTournament_table()
    # df = readCSV('tournament_list.csv')
    # for i in range(0,df.shape[0]):
    #     team1 = df.loc[i, 'team1']
    #     team2 = df.loc[i, 'team2']
    #     print(team1)
    #     print(team2)
    #     updateTournament_table(team1,team2)
    

main()
