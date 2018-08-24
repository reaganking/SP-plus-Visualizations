import json

from cluster import Cluster
from conference import Conference
from team import Team
from utils import Utils


def make_graphs():
    pfive = ['atlantic coast', 'big ten', 'big 12', 'pac 12', 'southeastern']
    gfive = ['american athletic', 'conference usa', 'mid american', 'mountain west', 'sun belt']
    fbs = pfive + gfive + ['independent']  # don't forget the independents
    with open("schedule.json", "r") as file:
        schedule = json.load(file)

    for conference in pfive + gfive:
        conf = Conference(name=conference, schedule=schedule)
        for color in ['team', 'red-green', 'red-blue']:
            try:
                conf.make_standings_projection_graph(absolute=False, method='sp+', file=conference, scale=color)
            except KeyError:
                print('problem with {}'.format(conf))

    for team in schedule:
        if schedule[team]['conference'] in fbs:
            val = Team(name=team, schedule=schedule)
            for color in ['team', 'red-green', 'red-blue']:
                try:
                    val.make_win_probability_graph(absolute=False, file=team, scale=color, method='sp+')
                except KeyError:
                    print('problem with {}'.format(team))
    confs = {'fbs': fbs, 'pfive': pfive, 'gfive': gfive, 'independent': ['independent']}
    for cluster in confs:
        current = Cluster(schedule=schedule, teams=[x for x in schedule if schedule[x]['conference'] in confs[cluster]])
        for color in ['team', 'red-green', 'red-blue']:
            current.make_standings_projection_graph(method='sp+', absolute=False, file=cluster, scale=color)

make_graphs()