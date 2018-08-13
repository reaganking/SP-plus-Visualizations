import json

from cluster import Cluster
from conference import Conference
from team import Team

pfive = ['atlantic coast', 'big ten', 'big 12', 'pac 12', 'southeastern']
gfive = ['american athletic', 'conference usa', 'mid american', 'mountain west', 'sun belt']
fbs = pfive + gfive + ['fbs independent']  # don't forget the independents

with open("schedule.json", "r") as file:
    schedule = json.load(file)

for conference in pfive + gfive:
    conf = Conference(name=conference, schedule=schedule)
    for method in ['spplus', 'fpi']:
        for color in ['team', 'red-green', 'red-blue']:
            try:
                conf.make_standings_projection_graph(absolute=False, file=conference, scale=color)
            except KeyError:
                print('problem with {}'.format(conf))

full_fbs = Cluster(schedule=schedule, teams=[x for x in schedule if schedule[x]['conference'] in fbs])

for team in schedule:
    if schedule[team]['conference'] in fbs:
        val = Team(name=team, schedule=schedule)
        for method in ['spplus', 'fpi']:
            for color in ['team', 'red-green', 'red-blue']:
                try:
                    full_fbs.make_standings_projection_graph(method=method, absolute=False, file='fbs', scale=color)
                    val.make_win_probability_graph(absolute=False, file=team, scale=color, method=method)
                except KeyError:
                    print('problem with {}'.format(team))
