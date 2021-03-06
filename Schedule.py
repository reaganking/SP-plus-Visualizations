import base64
import csv
import json
import os
import pprint
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup as bs

from defs import FBS, WEEKS
from poll import APPoll
from utils import Utils


class Schedule(object):
    def __init__(self, file):
        self.file = file
        with open(file, 'r', encoding='utf8') as infile:
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
        return result

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

    def save_to_file(self, file=None):
        if not file:
            file = self.file

        if file == self.file:
            if input('Overwrite existing schedule file? Y/N: ')[0].lower() != 'y':
                file = input('New file name: ')
                if file[-5:] != '.json':
                    file += '.json'
                raise TypeError

        with open(file, 'w+', encoding='utf8') as outfile:
            json.dump(self.data, outfile, indent=4, sort_keys=True, ensure_ascii=False)

    @staticmethod
    def scrape_spplus(
            url='https://www.footballoutsiders.com/stats/ncaa2018'):
        result = []

        r = requests.get(url, headers=Utils.headers)

        for row in bs(r.text).findAll('tr')[1:]:
            cells = row.findAll('td')
            if cells[0].text != 'Team':
                result.append({'name': cells[0].text, 'sp+': float(cells[4].text)})

        return result

    def swap_teams(self, team_a, team_b):
        # TODO: Tidy up this code
        data = dict(self.data)

        for team in self.data:
            if team == team_a:
                data[team_b]['schedule'] = self.data[team]['schedule']
            elif team == team_b:
                data[team_a]['schedule'] = self.data[team]['schedule']

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

        keys = {'canceled', 'home-away', 'location', 'opponent', 'scoreBreakdown', 'startDate', 'startTime', 'winner'}
        for game in new:
            away = find(game['away']['nameRaw'])
            if away and self.data[away]['conference'] in FBS:
                found = False
                try:
                    for i in range(len(self.data[away]['schedule'])):
                        if self.data[away]['schedule'][i]['id'] == game['id']:
                            found = True
                            for key in ['startDate', 'startTime']:
                                self.data[away]['schedule'][i][key] = game[key]
                            for key in ['scoreBreakdown', 'teamRank', 'winner']:
                                self.data[away]['schedule'][i][key] = game['away'][key]
                            try:
                                self.data[away]['schedule'][i]['scoreBreakdown'] = [int(x) if len(x) > 0 else 0
                                                                                    for x in
                                                                                    self.data[away]['schedule'][i][
                                                                                        'scoreBreakdown']]
                            except ValueError as e:
                                print("problem with scores for {}".format(away))
                                pass
                            break
                except KeyError as e:
                    print("couldn't find {}".format(e))
                    pass
                if not found:
                    foo = {x: None for x in keys}
                    foo['canceled'] = 'false'
                    foo['home-away'] = 'away'
                    foo['location'] = game['location']
                    foo['opponent'] = game['home']['nameSeo']
                    foo['scoreBreakdown'] = [int(x) if len(x) > 0 else 0 for x in game[away]['scoreBreakdown']]
                    foo['startDate'] = game['startDate']
                    foo['startTime'] = game['startTime']
                    foo['winner'] = game['away']['winner']
                    self.data[away]['schedule'].append(foo)

            home = find(game['home']['nameRaw'])
            if home and self.data[home]['conference'] in FBS:
                found = False
                try:
                    for i in range(len(self.data[home]['schedule'])):
                        if self.data[home]['schedule'][i]['id'] == game['id']:
                            found = True
                            for key in ['startDate', 'startTime']:
                                self.data[home]['schedule'][i][key] = game[key]
                            for key in ['scoreBreakdown', 'teamRank', 'winner']:
                                self.data[home]['schedule'][i][key] = game['home'][key]
                            try:
                                self.data[home]['schedule'][i]['scoreBreakdown'] = [int(x) if len(x) > 0 else 0
                                                                                    for x in
                                                                                    self.data[home]['schedule'][i][
                                                                                        'scoreBreakdown']]
                            except ValueError as e:
                                print("problem with scores for {}".format(away))
                                pass

                            break
                except KeyError as e:
                    print("couldn't find {}".format(e))
                    pass
                if not found:
                    foo = {x: None for x in keys}
                    foo['canceled'] = 'false'
                    foo['home-away'] = 'home'
                    foo['location'] = game['location']
                    foo['opponent'] = game['away']['nameSeo']
                    foo['scoreBreakdown'] = [int(x) if len(x) > 0 else 0 for x in game[home]['scoreBreakdown']]
                    foo['startDate'] = game['startDate']
                    foo['startTime'] = game['startTime']
                    foo['winner'] = game['home']['winner']
                    self.data[away]['schedule'].append(foo)

    def update_game(self, game_id, field, new_val):
        c = 0

        def find_game(t, g):
            for j in range(len(self.data[t]['schedule'])):
                if self.data[t]['schedule'][j]['id'] == str(g):
                    if field in self.data[t]['schedule'][j]:
                        self.data[t]['schedule'][j][field] = new_val
                        return 1
                    else:
                        return -1
            return 0

        for team in self.data:
            res = find_game(team, game_id)
            c += res
            if res >= 0:
                continue
            else:
                print('Not a valid field choice: {}'.format(field))
                return

        print('Found {} occurrences of game id {} '.format(c, game_id))


    def update_rankings(self, year=datetime.now().year, week=None) -> None:
        if not week:
            date = max(
                datetime.strptime(w[1], '%Y-%m-%d') for w in WEEKS if
                datetime.strptime(w[1], '%Y-%m-%d') <= datetime.now()).strftime('%Y-%m-%d')
            week = [x[1] for x in WEEKS].index(date) + 1
        elif 0 < week < len(WEEKS):
            date = WEEKS[week][1]
        else:
            raise ValueError("invalid week")
        print('Retrieving AP poll for {} week {}'.format(year, week))
        ap = APPoll(week=week, year=year)
        ap.scrape()
        date = ap.ballots['date']
        print('poll published on {}'.format(date))
        not_in_poll = []
        copy = dict(ap.ballots['results'])
        for team in self.data:
            if date not in self.data[team]['rankings']['AP'].keys():
                self.data[team]['rankings']['AP'][date] = {'overall': -1, 'voters': {}}

            # cross reference the teams to the keys used by the AP
            if team == 'texas am':
                key = 'Texas A&M'
            elif team == 'byu':
                key = 'Brigham Young'
            elif team == 'ole miss':
                key = 'Mississippi'
            elif team.split()[0] != 'utah' and (team[0] == 'u' or team[-1] == 'u'):
                key = team.upper()
            else:
                key = team.title()

            try:
                self.data[team]['rankings']['AP'][date]['overall'] = ap.ballots['results'][key]['rank']
                for v in ap.ballots['voters']:
                    if key in ap.ballots['voters'][v]['rankings']:
                        self.data[team]['rankings']['AP'][date]['voters'][v] = {
                            'outlet': ap.ballots['voters'][v]['outlet'],
                            'rank': ap.ballots['voters'][v]['rankings'].index(key) + 1}

                del ap.ballots['results'][key]
            except KeyError:
                not_in_poll.append(team)
        pp = pprint.PrettyPrinter(indent=4)
        if len(ap.ballots['results']) > 0:
            print('Portions of the poll couldn\'t be found:')
            pp.pprint(ap.ballots['results'])
        if input('Display the full AP results? (Y/N) ')[0].lower() == 'y':
            pp.pprint(copy)
        if input('Display teams not found in the AP Poll? (Y/N) ')[0].lower() == 'y':
            print('Teams not appearing in the AP poll:')
            pp.pprint(not_in_poll)


    def update_spplus(self):
        new = Schedule.scrape_spplus()

        for team in new:
            try:
                self.data[team['name'].lower()]['sp+'][datetime.now().strftime("%Y-%m-%d")] = team['sp+']
            except KeyError:
                print(team)


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


s = Schedule('schedule.json')
s.update_from_NCAA()
s.save_to_file()
