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
scale = 'team'

pfive = ['atlantic coast', 'big ten', 'big 12', 'pac 12', 'southeastern']
gfive = ['american athletic', 'conference usa', 'mid american', 'mountain west', 'sun belt']
fbs = pfive + gfive + ['fbs independent'] # don't forget the independents

for conference in pfive+gfive:
    Conference(name=conference, schedule=schedule).make_standings_projection_graph(absolute=False, file=conference,
                                                                                   scale=scale)

Cluster(schedule=schedule,
        teams=[x for x in schedule if schedule[x]['conference'] in fbs]).make_standings_projection_graph(
    absolute=False, file='fbs', scale=scale)

for team in schedule:
    if schedule[team]['conference'] in fbs:
        Team(name=team, schedule=schedule).make_win_probability_graph(absolute=False, file=team, scale=scale)
