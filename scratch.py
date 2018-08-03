import json

from cluster import Cluster
from conference import Conference
from team import Team

with open("schedule.json", "r") as file:
    schedule = json.load(file)
'''
win_prob = [1.00, .76, .94, .73, .94, .93, .63, .79, .85, .55, .87, .89]

for i in range(len(schedule['georgia']['schedule'])):
    schedule['georgia']['schedule'][i]['spplus'] = [win_prob[i]]
with open('schedule.json', 'w') as file:
    json.dump(schedule, file, indent=4, sort_keys=True)
'''

scale = 'red-green'
conferences = ['atlantic coast', 'big ten', 'big 12', 'pac 12', 'southeastern']

for conference in conferences:
    Conference(name=conference, schedule=schedule).make_standings_projection_graph(absolute=False, file=conference,
                                                                                   scale=scale)

Cluster(schedule=schedule,
        teams=[x for x in schedule if schedule[x]['conference'] in conferences]).make_standings_projection_graph(
    absolute=False, file='p5', scale=scale)
for team in schedule:
    if schedule[team]['conference'] in ['atlantic coast', 'big ten', 'big 12', 'pac 12', 'southeastern']:
        Team(name=team, schedule=schedule).make_win_probability_graph(absolute=False, file=team, scale=scale)