import base64
import csv
import json
import os
import re
import urllib.parse
from colorsys import hls_to_rgb
from datetime import datetime
from subprocess import Popen

import requests
from bs4 import BeautifulSoup as bs
from scipy.stats import norm


class Utils:
    headers = {'User-Agent': 'Mozilla/5.0'}

    @staticmethod
    def calculate_win_prob_from_spplus(a, b, loc):
        if loc == 'home':
            return norm.cdf((a - b + 2.5) / 17)
        else:
            return norm.cdf((a - b - 2.5) / 17)

    @staticmethod
    def convert_to_URI():
        imagelist = {}
        for file in os.listdir("./Resources"):
            if file.endswith(".jpg"):
                with open(os.path.join("./Resources/", file), "rb") as imageFile:
                    imagelist[file[:-4].lower()] = base64.b64encode(imageFile.read()).decode()
        return imagelist

    @staticmethod
    def convert_to_png(path):
        path = os.path.abspath(path)
        Popen("svg2png convert.bat", cwd=path)

    @staticmethod
    def download_logos(width=40, height=40):
        # Quick and dirty method to scrape logos from ESPN; they need minor editorial cleanup afterward
        r = requests.get('http://www.espn.com/college-football/teams')
        results = bs(r.text).findAll('a', href=re.compile('^http://www.espn.com/college-football/team/_/id/'))
        if not os.path.exists('./Resources/'):
            os.makedirs('./Resources/')

        for link in results:
            id = link['href'][47:link['href'].find('/', 47)]
            name = link['href'][link['href'].find('/', 47) + 1:link['href'].rfind('-')]
            name = name.replace('-', ' ').title()
            pic_url = 'http://a.espncdn.com/combiner/i?img=/i/teamlogos/ncaa/500/{}.png&h={}&w={}'.format(id,
                                                                                                          height,
                                                                                                          width)
            with open(os.path.join('./Resources/', '{}.jpg'.format(name.lower())), 'wb') as handle:
                response = requests.get(pic_url, stream=True)

                if not response.ok:
                    print(response)

                for block in response.iter_content(1024):
                    if not block:
                        break

                    handle.write(block)

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
            json.dump(result, file)

    @staticmethod
    def get_color_brightness(red, green, blue):
        """Return (float) representing the color brightness as calculated using the standard W3C formula."""
        return (red * 299 + green * 587 + blue * 114) / 1000

    @staticmethod
    def get_text_contrast_color(red, green, blue):
        # Should the text be white or black?
        if Utils.get_color_brightness(red, green, blue) > 123:
            return 0, 0, 0
        else:
            return 255, 255, 255

    @staticmethod
    def get_logo_URIs():
        result = {}
        with open('Schedule.json', 'r') as infile:
            teams = json.load(infile)

        for team in teams:
            if 'logoURI' in teams[team].keys():
                result[team] = teams[team]['logoURI']
        return result

    @staticmethod
    def gradient_color(lower, upper, val, method='linear', scale='red-green', primaryColor=None,
                       secondaryColor=None):
        """ Return (red, green, blue) interpolated along the color scale specified."""
        # Perform linear interpolation on the hue between 0.33 and 0, then convert back to RGB
        # HLS 0.33, 0.65, 1.0 will give green
        # HLS 0, 0.65, 1.0 will give red
        inter = Utils.interpolate(lower, upper, val, method=method)

        if scale == 'team':
            if not (primaryColor and secondaryColor):
                pass
            else:
                # brighter colors should mean higher probabilities, as a general rule
                # convert the hex values to rgb then order the colors by brightness
                colors = sorted([x for x in [primaryColor, secondaryColor]],
                                key=lambda y: Utils.get_color_brightness(*y))
                return [colors[0][i] + inter * (colors[1][i] - colors[0][i]) for i in (0, 1, 2)]

        if scale == 'red-green':
            if upper == lower:
                h = 120
            else:
                h = 120 * inter

            return [int(round(255 * x, 0)) for x in hls_to_rgb(h / 360.0, 0.65, 1)]

        if scale == 'red-blue':
            # interpolate 0-0.5 as red-white, 0.5-1 as white-blue
            if inter > 0.5:
                return [int(round(255 * x, 0)) for x in hls_to_rgb(0.66, 1.5 - inter, 0.4)]
            else:
                return [int(round(255 * x, 0)) for x in hls_to_rgb(0, 0.5 + inter, 0.75)]

        if scale == 'black-red':
            return [int(round(255 * x, 0)) for x in hls_to_rgb(0, 0.5 * inter, 1)]

    @staticmethod
    def hex_to_rgb(value):
        """Return (red, green, blue) for the color given as #rrggbb."""
        value = value.lstrip('#')
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

    @staticmethod
    def normalize_schedule(data, method='spplus', week=-1):
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

        for team in data:
            for i in range(len(data[team]['schedule'])):
                try:
                    win_prob = data[team]['schedule'][i][method]
                except KeyError:
                    continue
                if len(win_prob) > 0:
                    opponent = data[team]['schedule'][i]['opponent']
                    # Is this a opponent even in our json file?
                    if opponent not in data:
                        continue
                    opp_win_prob = round(1 - win_prob[week], 3)
                    # We have to find the correct index for the opponent
                    # because they may not play in the same order due to byes
                    j = find(data, opponent, team)

                    try:
                        if data[opponent]['schedule'][j][method][week] != opp_win_prob:
                            data[opponent]['schedule'][j][method][week] = opp_win_prob
                    except IndexError:
                        data[opponent]['schedule'][j][method].append(opp_win_prob)
                    except KeyError:
                        data[opponent]['schedule'][j][method] = [opp_win_prob]
                    except TypeError:
                        print('problem with {}, {}'.format(team, opponent))

        return data

    @staticmethod
    def interpolate(lower, upper, val, method='linear'):
        if upper == lower:
            return 1
        elif method.lower() == 'cubic':
            x = (val - lower) / (upper - lower)
            return x ** 3 * (10 + x * (-15 + 6 * x))
        else:
            return (val - lower) / (upper - lower)

    @staticmethod
    def schedule_to_csv(schedule_file, csv_file):
        with open(schedule_file, 'r') as infile:
            data = json.load(infile)
        with open(csv_file, 'w+', newline='') as outfile:
            csvwriter = csv.writer(outfile)
            count = 0
            for elem in data:
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

    @staticmethod
    def scrape_png_links(format='reddit'):
        with open("schedule.json", "r") as file:
            schedule = json.load(file)

        pfive = ['atlantic coast', 'big ten', 'big 12', 'pac 12', 'southeastern']
        gfive = ['american athletic', 'conference usa', 'mid american', 'mountain west', 'sun belt']
        fbs = pfive + gfive + ['fbs independent']
        method = ['sp+']

        scale = ['red-green', 'red-blue', 'team']
        result = {}

        if format == 'reddit':
            header = '|' + 'Name'

        for i in method:
            for j in scale:
                if format == 'reddit':
                    header += '|{} in {}'.format(i.upper(), j.title())

                url = 'https://github.com/EvRoHa/SP-plus-Visualizations/tree/master/png output/{} - {}/'.format(i, j)
                r = requests.get(url, headers=Utils.headers)

                search_url = urllib.parse.quote(
                    '/EvRoHa/SP-plus-Visualizations/blob/master/png output/{} - {}/'.format(i, j))
                links = bs(r.text).findAll('a', href=re.compile(search_url + '*'))

                for x in links:
                    name = x.text.split('-')[0].strip().title()
                    url = re.sub('/blob', '', 'https://raw.githubusercontent.com' + x.attrs['href'])
                    try:
                        result[name].extend([{'method': i.upper(), 'scale': j.title(), 'url': url}])
                    except KeyError:
                        result[name] = [{'method': i.upper(), 'scale': j.title(), 'url': url}]

        header += '\n' + ':--|:-:|:-:|:-:|:-:|:-:|:-:\n'
        for conf in fbs:
            out = header
            with open('{} reddit table.txt'.format(conf), 'w+') as outfile:
                for team in result:
                    try:
                        if team.lower() == conf:
                            out += '|' + team + '|' + '|'.join(
                                ['[{} in {}]({})'.format(x['method'], x['scale'], x['url']) for x in
                                 result[team]]) + '\n'
                        elif schedule[team.lower()]['conference'] == conf:
                            out += '|' + team + '|' + '|'.join(
                                ['[{} in {}]({})'.format(x['method'], x['scale'], x['url']) for x in result[team]])
                            out += '\n'
                    except KeyError:
                        pass
                outfile.write(out)

        with open('Aggregate reddit table.txt', 'w+') as outfile:
            out = header
            for val in ['p5', 'g5', 'fbs']:
                for team in result:
                    if team.lower() == val:
                        out += '|' + team + '|' + '|'.join(
                            ['[{} in {}]({})'.format(x['method'], x['scale'], x['url']) for x in result[team]]) + '\n'
            outfile.write(out)

        return out

    @staticmethod
    def scrape_spplus(
            url='https://www.sbnation.com/college-football/2018/8/24/17768218/2018-college-football-rankings-projections-strength-schedule'):
        result = []

        r = requests.get(url, headers=Utils.headers)

        table = bs(r.text).find('table', {'class': 'p-data-table'})

        for row in table.findAll('tr')[2:]:
            cells = row.findAll('td')
            result.append({'name': cells[0].text, 'sp+': float(cells[1].text)})

        return result

    @staticmethod
    def get_spplus_stdv(
            url='https://www.sbnation.com/college-football/2018/2/9/16994486/2018-college-football-rankings-projections',
            schedule=None):
        '''
        The STDEV is needed for win probability calculations.
        :param url: the url to pull S&P+ from
        :param schedule: if specified, the local file that holds the S&P+ values
        :return: a float that represents the stdev of the S&P+ values.
        '''
        if schedule:
            # TODO: if the schedule file is specified, use those values
            pass
        else:
            spplus = [x['s&p+'] for x in Utils.scrape_spplus(url)]
        return (sum([(x - sum(spplus) / len(spplus)) ** 2 for x in spplus]) / len(spplus)) ** 0.5


def temp():
    url = 'https://www.sbnation.com/college-football/2018/2/9/16994486/2018-college-football-rankings-projections'
    result = {}

    r = requests.get(url, headers=Utils.headers)

    table = bs(r.text).find('table')

    for row in table.findAll('tr')[2:]:
        cells = row.findAll('td')
        result[cells[1].text.lower()] = float(cells[6].text)

    return result
