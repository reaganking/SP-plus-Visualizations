import json

from cluster import Cluster
from conference import Conference
from defs import FBS, PFIVE, GFIVE
from team import Team


def load_schedule():
    with open("schedule.json", "r") as file:
        global schedule
        schedule = json.load(file)


def make_cluster_graphs(absolute=False, old=None, scale=None):
    groups = {'fbs': FBS, 'pfive': PFIVE, 'gfive': GFIVE, 'independent': ['independent']}
    for cluster in groups:
        current = Cluster(schedule=schedule,
                          teams=[x for x in schedule if schedule[x]['conference'] in groups[cluster]])
        if not scale:
            for color in ['team', 'red-green', 'red-blue']:
                current.make_standings_projection_graph(method='sp+', absolute=absolute, old=old, file=cluster,
                                                        scale=color)
        else:
            current.make_standings_projection_graph(method='sp+', absolute=absolute, old=old, file=cluster, scale=scale)


def make_conf_graphs(absolute=False, old=None, scale=None):
    for conference in PFIVE + GFIVE:
        conf = Conference(name=conference, schedule=schedule)
        if not scale:
            for color in ['team', 'red-green', 'red-blue']:
                try:
                    conf.make_standings_projection_graph(absolute=absolute, method='sp+', file=conference, old=old,
                                                         scale=color)
                except KeyError:
                    print('problem with {}'.format(conf))
        else:
            try:
                conf.make_standings_projection_graph(absolute=absolute, method='sp+', file=conference, old=old,
                                                     scale=scale)
            except KeyError:
                print('problem with {}'.format(conf))


def make_team_graphs(old=True, scale=None, week=-1):
    for team in schedule:
        if schedule[team]['conference'] in FBS:
            val = Team(name=team, schedule=schedule)
            if not scale:
                for color in ['team', 'red-green', 'red-blue']:
                    val.make_win_probability_graph(absolute=False, file=team, old=old, scale=color, method='sp+',
                                                   week=week)
            else:
                val.make_win_probability_graph(absolute=False, file=team, old=old, scale=scale, method='sp+')


load_schedule()
#make_conf_graphs(old=True)
#make_cluster_graphs(old=True)
make_team_graphs(old=True, week=1)
