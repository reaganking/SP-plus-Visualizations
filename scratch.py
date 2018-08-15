import json
import os

from cluster import Cluster
from conference import Conference
from team import Team
from utils import Utils

pfive = ['atlantic coast', 'big ten', 'big 12', 'pac 12', 'southeastern']
gfive = ['american athletic', 'conference usa', 'mid american', 'mountain west', 'sun belt']
fbs = pfive + gfive + ['fbs independent']  # don't forget the independents

with open("schedule.json", "r") as file:
    schedule = json.load(file)

for conference in pfive + gfive:
    conf = Conference(name=conference, schedule=schedule)
    for method in ['sp+', 'fpi']:
        for color in ['team', 'red-green', 'red-blue']:
            try:
                conf.make_standings_projection_graph(absolute=False, file=conference, scale=color)
            except KeyError:
                print('problem with {}'.format(conf))

full_fbs = Cluster(schedule=schedule, teams=[x for x in schedule if schedule[x]['conference'] in fbs])
power_five = Cluster(schedule=schedule,
                     teams=[x for x in schedule if schedule[x]['conference'] in pfive + ['fbs independent']])
group_of_five = Cluster(schedule=schedule, teams=[x for x in schedule if schedule[x]['conference'] in gfive])

for team in schedule:
    if schedule[team]['conference'] in fbs:
        val = Team(name=team, schedule=schedule)
        for method in ['sp+', 'fpi']:
            for color in ['team', 'red-green', 'red-blue']:
                try:
                    val.make_win_probability_graph(absolute=False, file=team, scale=color, method=method)
                except KeyError:
                    print('problem with {}'.format(team))

for method in ['sp+', 'fpi']:
    for color in ['team', 'red-green', 'red-blue']:
        power_five.make_standings_projection_graph(method=method, absolute=False, file='p5', scale=color)
        group_of_five.make_standings_projection_graph(method=method, absolute=False, file='g5', scale=color)
        full_fbs.make_standings_projection_graph(method=method, absolute=False, file='fbs', scale=color)
