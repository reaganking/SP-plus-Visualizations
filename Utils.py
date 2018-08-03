import base64
import csv
import json
import os
import re
from colorsys import hls_to_rgb
from datetime import datetime

import requests
from bs4 import BeautifulSoup as bs


class Utils:
    @staticmethod
    def clean_team_name(name, aliases):
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

    @staticmethod
    def convert_to_URI():
        imagelist = {}
        for file in os.listdir("./Resources"):
            if file.endswith(".jpg"):
                with open(os.path.join("./Resources/", file), "rb") as imageFile:
                    imagelist[file[:-4].lower()] = base64.b64encode(imageFile.read()).decode()
        return imagelist

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
            pic_url = 'http://a.espncdn.com/combiner/i?img=/i/teamlogos/ncaa/500/{}.png&h={}&w={}'.format(id, height,
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
            url = "http://data.ncaa.com/jsonp/scoreboard/football/fbs/{}/{}/scoreboard.json".format(year, "%02d" % week)
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
    def gradient_color(lower, upper, val, method='linear', scale='red-green', primaryColor=None, secondaryColor=None):
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
                    csvwriter.writerow(['home', 'away', 'startDate', 'startTime', 'location', 'conference', 'url', ])
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
    def scrape_fpi(data):
        # Quick and dirty method to scrape fpi from ESPN
        r = requests.get('http://www.espn.com/college-football/teams')
        results = bs(r.text).findAll('a', href=re.compile('^http://www.espn.com/college-football/team/_/id/'))
        if not os.path.exists('./Resources/'):
            os.makedirs('./Resources/')

        for link in results:
            url = 'http://www.espn.com/college-football/team/fpi?id={}&year=2018'.format(
                link['href'][47:link['href'].find('/', 47)])
            soup = bs(requests.get(url).text, 'html.parser')
            # Get the team name
            name = soup.find('title').text.split()[0].lower()
            try:
                # The table we want is the 5th table in the document
                table = soup.findAll('table')[4]
                for i in range(2, len(table.contents)):
                    # We want the contents of the 2nd and 3rd columns (the opponent and the FPI win probability)
                    # The opponent will include either "@ " or "vs " at the beginning. Throw out everything up to and including the first space.
                    opponent = " ".join(table.contents[i].contents[1].text.split()[1:])
                    # trim out any weird special characters
                    opponent = re.sub(r'[^\w\s-]', '', opponent).lower()
                    fpi = table.contents[i].contents[2].text[:-1]

                    # local helper function to locate the opponent within the schedule
                    def find(lst, team, opp):
                        for i, dict in enumerate(lst[name]['schedule']):
                            if dict[team] == opp:
                                return i
                        return -1

                    index = find(data, name, opponent)
                    if index > 0:
                        data[name]['schedule'][index]['fpi'] = fpi
            except (KeyError, IndexError) as e:
                pass
        return data
