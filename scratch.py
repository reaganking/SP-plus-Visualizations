import csv
import json

from cluster import Cluster
from conference import Conference
from team import Team

with open("schedule.json", "r") as file:
    schedule = json.load(file)
'''
team = 'louisiana'
win_prob = [0.73, 0.03, 0.53, 0.01, 0.47, 0.43, 0.15, 0.24, 0.20, 0.51, 0.47, 0.35]
for i in range(len(win_prob)):
    schedule[team]['schedule'][i]['spplus'] = [win_prob[i]]

with open('schedule.json', 'w') as file:
    json.dump(schedule, file, indent=4, sort_keys=True)
'''
scale = 'red-green'

pfive = ['atlantic coast', 'big ten', 'big 12', 'pac 12', 'southeastern']
gfive = ['american athletic', 'conference usa', 'mid american', 'mountain west', 'sun belt']
fcs = pfive + gfive

for conference in gfive:
    Conference(name=conference, schedule=schedule).make_standings_projection_graph(absolute=False, file=conference,
                                                                                   scale=scale)

Cluster(schedule=schedule,
        teams=[x for x in schedule if schedule[x]['conference'] in fcs]).make_standings_projection_graph(
    absolute=False, file='fcs', scale=scale)

for team in schedule:
    if schedule[team]['conference'] in ['atlantic coast', 'big ten', 'big 12', 'pac 12', 'southeastern']:
        Team(name=team, schedule=schedule).make_win_probability_graph(absolute=False, file=team, scale=scale)
