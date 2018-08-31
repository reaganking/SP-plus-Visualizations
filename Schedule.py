import base64
import csv
import json
import os
import re
from datetime import datetime

import requests

from defs import FBS
from team import Team
from utils import Utils


class Schedule(object):
    def __init__(self, file):
        self.file = file
        with open(file, 'r') as infile:
            self.data = json.load(infile)

    def clean_team_name(self, name):
        # various data sources uses different aliases for the same team (much to my irritation) or special characters
        # this method will try to enforce some kind of sensible naming standard

        result = name.lower()

        # a dictionary of states or other abbreviations
        abbrv = {
            '&': '',
            'ak': 'alaska',
            'al': 'alabama',
            'ar': 'arkansas',
            'as': 'american samoa',
            'az': 'arizona',
            'ca': 'california',
            'caro': 'carolina',
            'co': 'colorado',
            'ct': 'connecticut',
            'conn': 'connecticut',
            'dc': 'district of columbia',
            'de': 'delaware',
            'fl': 'florida',
            '(fla.)': '',
            'ga': 'georgia',
            'gu': 'guam',
            'hi': 'hawaii',
            'ia': 'iowa',
            'id': 'idaho',
            'il': 'illinois',
            'ill': 'illinois',
            'in': 'indiana',
            'ks': 'kansas',
            'ky': 'kentucky',
            'la': 'louisiana',
            'ma': 'massachusetts',
            'md': 'maryland',
            'me': 'maine',
            'mi': 'michigan',
            'miss': 'mississippi',
            'mn': 'minnesota',
            'mo': 'missouri',
            'mp': 'northern mariana islands',
            'ms': 'mississippi',
            'mt': 'montana',
            'na': 'national',
            'nc': 'north caroli;na',
            'nd': 'north dakota',
            'ne': 'nebraska',
            'nh': 'new hampshire',
            'nj': 'new jersey',
            'nm': 'new mexico',
            'n.m.': 'new mexico',
            'nv': 'nevada',
            'ny': 'new york',
            'oh': 'ohio',
            'ok': 'oklahoma',
            'or': 'oregon',
            'pa': 'pennsylvania',
            'pr': 'puerto rico',
            'ri': 'rhode island',
            'sc': 'south carolina',
            'sd': 'south dakota',
            'st': 'state',
            'tn': 'tennessee',
            'tenn': 'tennessee',
            'tx': 'texas',
            'univ': '',
            'ut': 'utah',
            'va': 'virginia',
            'vi': 'virgin islands',
            'vt': 'vermont',
            'wa': 'washington',
            'wi': 'wisconsin',
            'wv': 'west virginia',
            'wy': 'wyoming',
            's': 'south',
            'se': 'southeastern'
        }

        for x in abbrv:
            result = re.sub(r'\b%s\b' % x, abbrv[x], result)

        # trim out any weird special characters (most likely periods) and convert to lower case
        result = re.sub(r'[^\w\s]', ' ', result).lower().strip()

        # remove any leading, trailing, or consecutive whitespaces
        result = re.sub(' +', ' ', result).strip()

        # TODO: build a structure of aliases so we can reference them
        '''
        # take the dictionary of aliases and attempt to find the best match
        for team, alts in enumerate(aliases):
            try:
                if len(get_close_matches(name, alts, n=1, cutoff=1)) > 0:
                    return team
                else:
                    raise Exception("No matches found for {}.".format(name))
            except Exception as error:
                print("An error occured: ".format(error))
                return None
        '''
        return result

    def cull(self):
        new = {}
        for t in self.data:
            # cull any games between fcs schools
            if self.data[t]['conference'] not in FBS:
                for i in range(len(self.data[t]['schedule'])):
                    opp = self.data[t]['schedule'][i]['opponent']
                    oconf = self.data[opp]['conference']
                    if oconf not in FBS:
                        del self.data[t]['schedule'][i]
            # cull any schools with empty schedules
            if len(self.data[t]['schedule']) > 0:
                new[t] = self.data[t]
        self.data = new

    @staticmethod
    def download_schedules(year=datetime.now().year) -> None:
        result = []
        # Quick and dirty method to scrape schedule data
        for week in range(1, 20):
            # Pull the scoreboard, which contains links to the details for each game
            url = "http://data.ncaa.com/jsonp/scoreboard/football/fbs/{}/{}/scoreboard.json".format(year,
                                                                                                    "%02d" % week)
            response = requests.get(url)
            if response.status_code == 404:
                continue
            else:
                # look in the scoreboard dictionary, iterate over the days with games that week
                for day in json.loads(response.text[response.text.index("(") + 1: response.text.rindex(")")])[
                    'scoreboard']:
                    # iterate over the games for that day
                    for game in day['games']:
                        url = "http://data.ncaa.com/jsonp/{}".format(game)
                        response = requests.get(url)
                        if response.status_code == 404:
                            continue
                        else:
                            result += [json.loads(response.text)]
        with open('new schedule.json', 'w+') as file:
            json.dump(result, file, indent=4, sort_keys=True)

    def normalize_schedule(self, method='spplus', week=-1):
        # A method to ensure that all games have a total win probability equal to one

        # local helper function to locate the opponent within the schedule
        def find(lst, team, opp):
            try:
                for i, dict in enumerate(lst[team]['schedule']):
                    if dict['opponent'] == opp:
                        return i
            except KeyError:
                return -2
            return -1

        for team in self.data:
            for i in range(len(self.data[team]['schedule'])):
                try:
                    win_prob = self.data[team]['schedule'][i][method]
                except KeyError:
                    continue
                if len(win_prob) > 0:
                    opponent = self.data[team]['schedule'][i]['opponent']
                    # Is this a opponent even in our json file?
                    if opponent not in self.data:
                        continue
                    opp_win_prob = round(1 - win_prob[week], 3)
                    # We have to find the correct index for the opponent
                    # because they may not play in the same order due to byes
                    j = find(self.data, opponent, team)

                    try:
                        if self.data[opponent]['schedule'][j][method][week] != opp_win_prob:
                            self.data[opponent]['schedule'][j][method][week] = opp_win_prob
                    except IndexError:
                        self.data[opponent]['schedule'][j][method].append(opp_win_prob)
                    except KeyError:
                        self.data[opponent]['schedule'][j][method] = [opp_win_prob]
                    except TypeError:
                        print('problem with {}, {}'.format(team, opponent))

    def populate_expected_wins(self):
        for t in self.data:
            team = Team(name=t, schedule=self.data)
            win_total_probs = team.project_win_totals()[1][-1]
            self.data[t]['sp+ expected wins'] = sum([win_total_probs[i] * i for i in range(len(win_total_probs))])

    def save_to_file(self, file=None):
        if not file:
            file = self.file

        if file == self.file:
            if input('Overwrite existing schedule file? Y/N: ')[0].lower() != 'y':
                file = input('New file name: ')
                if file[-5:] != '.json':
                    file += '.json'

        with open(file, 'w+') as outfile:
            json.dump(self.data, outfile, indent=4, sort_keys=True)

    def populate_URIs(self):
        for file in os.listdir("./Resources"):
            if file.endswith(".jpg"):
                name = file[:-4].lower()
                with open(os.path.join("./Resources/", file), "rb") as imageFile:
                    uri = base64.b64encode(imageFile.read()).decode()
                    try:
                        self.data[name][file[:-4].lower()] = uri
                    except KeyError:
                        print("File for {}, but not found in schedule.".format(name, uri))

    def swap_teams(self, team_a, team_b):
        # TODO: Tidy up this code
        data = dict(self.data)

        for team in self.data:
            if team == team_a:
                data[team_b] = self.data[team]
            elif team == team_b:
                data[team_a] = self.data[team]

        tmp = sp[team_a]['sp+']
        data[team_b]['sp+'] = sp[team_b]['sp+']
        data[team_a]['sp+'] = tmp

        tmp = self.data[team_a]['logoURI']
        data[team_b]['logoURI'] = self.data[team_b]['logoURI']
        data[team_a]['logoURI'] = tmp

        for team in data:
            for game in range(len(data[team]['schedule'])):
                if data[team]['schedule'][game]['opponent'] == team_a:
                    data[team]['schedule'][game]['opponent'] = team_b
                elif data[team]['schedule'][game]['opponent'] == team_b:
                    data[team]['schedule'][game]['opponent'] = team_a
                try:
                    team_a_spplus = sp[team]['sp+']
                except KeyError:
                    team_a_spplus = -10
                try:
                    team_b_spplus = sp[data[team]['schedule'][game]['opponent']]['sp+']
                except KeyError:
                    team_b_spplus = -10
                loc = data[team]['schedule'][game]['home-away']
                if loc == 'home':
                    data[team]['schedule'][game]['sp+'] = [
                        Utils.calculate_win_prob_from_spplus(team_a_spplus, team_b_spplus, 'home')]
                else:
                    data[team]['schedule'][game]['sp+'] = [
                        Utils.calculate_win_prob_from_spplus(team_a_spplus, team_b_spplus, 'away')]

    def update_from_NCAA(self, new=None):
        def find(t):
            for x in self.data:
                if t == self.data[x]['nameRaw']:
                    return x
            return None

        if not new:
            new = Schedule.download_schedules()
        else:
            with open(new, 'r') as infile:
                new = json.load(infile)
        for game in new:
            away = find(game['away']['nameRaw'])
            for i in range(len(self.data[away]['schedule'])):
                if self.data[away]['schedule'][i]['id'] == game['id']:
                    for key in ['startDate', 'startTime']:
                        self.data[away]['schedule'][i][key] = game[key]
                    for key in ['scoreBreakdown', 'teamRank', 'winner']:
                        self.data[away]['schedule'][i][key] = game['away'][key]
                    self.data[away]['schedule'][i]['scoreBreakdown'] = [int(x) for x in self.data[away]['schedule'][i][
                        'scoreBreakdown']]
                    break

            home = find(game['home']['nameRaw'])
            for i in range(len(self.data[home]['schedule'])):
                if self.data[home]['schedule'][i]['id'] == game['id']:
                    for key in ['startDate', 'startTime']:
                        self.data[home]['schedule'][i][key] = game[key]
                    for key in ['scoreBreakdown', 'teamRank', 'winner']:
                        self.data[home]['schedule'][i][key] = game['home'][key]
                    self.data[home]['schedule'][i]['scoreBreakdown'] = [int(x) for x in self.data[home]['schedule'][i][
                        'scoreBreakdown']]
                    break

    def to_csv(self, csv_file):
        with open(csv_file, 'w+', newline='') as outfile:
            csvwriter = csv.writer(outfile)
            count = 0
            for elem in self.data:
                if count == 0:
                    csvwriter.writerow(
                        ['home', 'away', 'startDate', 'startTime', 'location', 'conference', 'url', ])
                    count += 1
                else:
                    row = []
                    for val in ['home', 'away', 'startDate', 'startTime', 'location', 'conference', 'url', ]:
                        if val == 'home' or val == 'away':
                            row.append(elem[val]['nameRaw'])
                        elif val == 'conference':
                            row.append(' vs. '.join(elem[val].split(' ')[1:]))
                        elif val == 'url':
                            row.append('www.ncaa.com' + elem[val])
                        else:
                            row.append(elem[val])
                    csvwriter.writerow(row)
s=Schedule('schedule.json')
for team in s.data:
    s.data[team]['sp+'] = {'2018-08-23': s.data[team]['sp+']['2018-08-23'][0][0]}
s.save_to_file()