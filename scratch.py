import json

from cluster import Cluster
from conference import Conference
from team import Team

with open("schedule.json", "r") as file:
    schedule = json.load(file)

win_prob = [.99, .25, .90, .14, .66, .75, .53, .34, .21, .56, .86, .49]

for i in range(len(schedule['texas am']['schedule'])):
    schedule['texas am']['schedule'][i]['spplus'] = [win_prob[i]]
with open('schedule.json', 'w') as file:
    json.dump(schedule, file, indent=4, sort_keys=True)


scale = 'team'

pfive = ['atlantic coast', 'big ten', 'big 12', 'pac 12', 'southeastern']
gfive = ['american athletic', 'conference usa', 'mid american', 'mountain west', 'sunbelt']
fcs = pfive + gfive

for conference in pfive:
    Conference(name=conference, schedule=schedule).make_standings_projection_graph(absolute=False, file=conference,
                                                                                   scale=scale)

Cluster(schedule=schedule,
        teams=[x for x in schedule if schedule[x]['conference'] in pfive]).make_standings_projection_graph(
    absolute=False, file='p5', scale=scale)

for team in schedule:
    if schedule[team]['conference'] in ['atlantic coast', 'big ten', 'big 12', 'pac 12', 'southeastern']:
        Team(name=team, schedule=schedule).make_win_probability_graph(absolute=False, file=team, scale=scale)
