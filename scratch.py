import base64
import csv
import json
import os
import re
from difflib import get_close_matches
from colorsys import hls_to_rgb
from datetime import datetime

import requests
from bs4 import BeautifulSoup as bs


class Utils:
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
    def gradient_color(lower, upper, val, method='linear'):
        # Perform linear interpolation on the hue between 0.33 and 0, then convert back to RGB
        # HLS 0.33, 0.65, 1.0 will give green
        # HLS 0, 0.65, 1.0 will give red
        if upper == lower:
            h = 120
        else:
            h = 120 * Utils.interpolate(lower, upper, val, method=method)

        return [int(round(255 * x, 0)) for x in hls_to_rgb(h / 360.0, 0.65, 1)]

    @staticmethod
    def get_logo_URIs():
        with open('Logo URIs.txt', 'r') as infile:
            json_data = infile.read()

        return json.loads(json_data)

    @staticmethod
    def download_images(width=40, height=40):
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
    def clean_team_name(name, aliases):
        # various data sources uses different aliases for the same team (much to my irritation) or special characters
        # this method will try to enforce some kind of sensible naming standard

        # trim out any weird special characters and convert to lower case
        name = re.sub(r'[^\w\s-]', '', name).lower()

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
    def convert_to_URI():
        imagelist = {}
        for file in os.listdir("./Resources"):
            if file.endswith(".jpg"):
                with open(os.path.join("./Resources/", file), "rb") as imageFile:
                    imagelist[file[:-4].lower()] = base64.b64encode(imageFile.read()).decode()
        with open("Logo URIs.txt", 'w', newline='') as outfile:
            outfile.write(json.dumps(imagelist))


class Team:
    def __init__(self, name=None, win_probabilities=None, conference=None, division=None):
        if not win_probabilities:
            self.win_probabilities = []  # format for this vector is a [team name::str, win_probability::float]
        else:
            assert isinstance(win_probabilities, (list, set, tuple)), "Vector is not a list, set, or tuple!"
            self.win_probabilities = win_probabilities

        if not name:
            self.name = ""
        else:
            assert isinstance(name, str), "Name is not a string!"
            self.name = name.lower()

        if not conference:
            self.conference = ""
        else:
            assert isinstance(name, str), "Name is not a string!"
            self.conference = conference.lower()

        if not division:
            self.division = ""
        else:
            assert isinstance(name, str), "Name is not a string!"
            self.division = division.lower()

    def win_totals_by_week(self, projection_week=0, method="spplus"):
        # Make a ragged table to store 'games' x 'wins'
        record = [[0 for y in range(0, x + 1)] for x in range(1, len(self.win_probabilities) + 1)]
        record[0][0] = 1 - self.win_probabilities[0][method][projection_week]  # first game was a loss
        record[0][1] = self.win_probabilities[0][method][projection_week]  # first game was a win

        for i in range(1, len(record)):
            for j in range(0, i + 1):
                record[i][j] += record[i - 1][j] * (
                        1 - self.win_probabilities[i][method][projection_week])  # newest game was a loss
                record[i][j + 1] += record[i - 1][j] * (
                    self.win_probabilities[i][method][projection_week])  # newest game was a win

        return record

    def set_win_probabilities(self, vector):
        assert isinstance(vector, (list, set, tuple)), "Vector is not a list, set, or tuple!"
        self.win_probabilities = vector

    def write_win_probability_csv(self, file='out'):
        record = self.win_totals_by_week()
        with open("{}.csv".format(file), 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerows(record)

    def make_win_probability_graph(self, file='out', hstep=40, vstep=40, margin=5, logowidth=30, logoheight=30,
                                   menuheight=40, absolute=False, projectionweek=0, method="spplus",
                                   colorIndividualGameProbs=False):
        record = self.win_totals_by_week(method=method)
        logos = Utils.get_logo_URIs()

        if not os.path.exists("./svg output/"):
            os.makedirs("./svg output/")

        with open(os.path.join("./svg output/", '{}.svg'.format(file)), 'w+') as outfile:
            # The SVG output should generally be divided into 3 leading columns (week, H/A, Opp, Prob) and n=len(self.win_probabilities) + 1 segments
            # and 2 leading rows (Wins and headers) with n=len(self.win_probabilities) vertical segments.
            rows, cols = 2 + len(self.win_probabilities), 4 + len(self.win_probabilities) + 1

            # Write the SVG header; remember to write </svg> to close the file
            outfile.write(
                "<svg version='1.1'\n\tbaseProfile='full'\n\twidth='{}' height='{}'\n\txmlns='http://www.w3.org/2000/svg'\n\txmlns:xlink='http://www.w3.org/1999/xlink'\n\tstyle='shape-rendering:crispEdges;'>\n".format(
                    hstep * cols + 2 * margin, vstep * rows + 3 * margin + menuheight))

            # Fill the background with white
            outfile.write("<rect width='100%' height='100%' style='fill:rgb(255,255,255)' />\n")

            # Add the team logo
            try:
                outfile.write(
                    "<image x='{}' y='{}' height='{}px' width='{}px' xlink:href='data:image/jpg;base64,{}'/>\n".format(
                        margin + (hstep - logowidth) / 2,
                        margin + (vstep - logoheight) / 2, logowidth, logoheight, logos[self.name]))
            except IndexError:
                pass

            # Add the horizontal header label; it is at the very top of the svg and covers the right 16 columns, with centered text
            outfile.write(
                "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}'  style='font-size:12px;font-family:Arial'>Total Wins</text>\n".format(
                    margin + hstep * (cols - (cols - 4) / 2), margin + vstep * 0.5))

            # Add column labels for the H/A and Opp
            outfile.write(
                "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}'  style='font-size:12px;font-family:Arial'>Week</text>\n".format(
                    margin + hstep * 0.5, margin + vstep * 1.5))
            outfile.write(
                "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}'  style='font-size:12px;font-family:Arial'>H/A</text>\n".format(
                    margin + hstep * 1.5, margin + vstep * 1.5))
            outfile.write(
                "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}'  style='font-size:12px;font-family:Arial'>Opp</text>\n".format(
                    margin + hstep * 2.5, margin + vstep * 1.5))

            # writing multiline text is a bit dodgy; this works
            outfile.write(
                "<text text-anchor='middle' alignment-baseline='baseline' x='{}' y='{}'  style='font-size:12px;font-family:Arial'>Win</text>\n".format(
                    margin + hstep * 3.5, margin + vstep * 1.5 - 2))
            outfile.write(
                "<text text-anchor='middle' alignment-baseline='hanging' x='{}' y='{}'  style='font-size:12px;font-family:Arial'>Prob</text>\n".format(
                    margin + hstep * 3.5, margin + vstep * 1.5 + 2))

            outfile.write("<g id='svg_2'>\n")

            for i in range(0, rows - 2):
                # find the max and min in this week to determine color of cell
                # The rows can be color coded by giving scaling to the maximum likelihood within the week (relative)
                # or by absolute likelihood (max=1.0). Default is relative.
                if absolute:
                    upper, lower = 1, 0
                else:
                    upper, lower = max(record[i]), min(record[i])

                for j in range(0, len(record) + 1):

                    # Draw the color-coded box
                    outfile.write(
                        "<rect id='{}_{}' x='{}' y='{}' width='{}' height='{}' style='".format(
                            i, j, margin + hstep * (4 + j), margin + vstep * (2 + i), hstep, vstep))

                    if j < len(record[i]):
                        # We need to fill the absolute color code in the box initially and store the relative and absolute color codes
                        # so that we can use them later to animate the chart
                        ra, ga, ba = Utils.gradient_color(lower, upper, record[i][j])
                        r, g, b = Utils.gradient_color(0, 1, record[i][j])

                        if absolute:
                            ra, ga, ba, r, g, b = r, g, b, ra, ga, ba

                        # Assign the color code.
                        outfile.write("fill:rgb({},{},{})'>\n".format(ra, ga, ba))

                        # The first two animate the colors to change when the user mouses over / off the game box
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='mouseover'/>\n".format(
                                r, g, b, ra, ga, ba))
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='mouseout'/>\n".format(
                                ra, ga, ba, r, g, b))

                        # These next two animate the colors to change when the user mouses over / off the week label
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='week{}.mouseover'/>\n".format(
                                r, g, b, ra, ga, ba, i))
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='week{}.mouseout'/></rect>\n".format(
                                ra, ga, ba, r, g, b, i))
                    else:
                        # Assign the color code.
                        outfile.write(
                            "fill:rgb({},{},{})'/>\n".format(150, 150, 150))

            outfile.write("</g>\n")

            for i in range(0, rows - 2):
                # by default, leave the game win probability cells uncolored. color them by mouseover.
                r, g, b = Utils.gradient_color(0, 1, self.win_probabilities[i][method][projectionweek])

                if colorIndividualGameProbs:
                    # Add the color-coded box in the prob column
                    outfile.write(
                        "<rect x='{}' y='{}' width='{}' height='{}' style='fill:rgb({},{},{})'/>".format(
                            margin + hstep * 3, margin + vstep * (2 + i), hstep, vstep, r, g, b))
                else:
                    outfile.write(
                        "<rect x='{}' y='{}' width='{}' height='{}' style='fill:rgb({},{},{})'>\n".format(
                            margin + hstep * 3, margin + vstep * (2 + i), hstep, vstep, 255, 255, 255))
                    outfile.write(
                        "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='probColHitBox.mouseover'/>\n".format(
                            r, g, b, 255, 255, 255))
                    outfile.write(
                        "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='probColHitBox.mouseout'/></rect>\n".format(
                            255, 255, 255, r, g, b))

                # Add the probability text in the prob column
                outfile.write(
                    "<text text-anchor='middle' alignment-baseline='central' x='{}' y='{}' style='font-size:11px;font-family:Arial;pointer-events:none'>{}%{}".format(
                        margin + hstep * 3.5, margin + vstep * (2.5 + i),
                        round(100 * self.win_probabilities[i][method][projectionweek], 1),
                        "</text>\n"))

                for j in range(0, len(record) + 1):
                    if i == 0:
                        # Add the column label
                        outfile.write(
                            "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}' style='font-size:12px;font-family:Arial'>{}{}".format(
                                margin + hstep * (4.5 + j), margin + vstep * 1.5, j, "</text>\n"))

                # Loop over the body of the table and draw the probability text.
                for j in range(0, len(record) + 1):
                    if j < len(record[i]):
                        # Write the probability in the box
                        outfile.write(
                            "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}' style='font-size:11px;font-family:Arial;pointer-events: none'>{}%{}".format(
                                margin + hstep * (4.5 + j), margin + vstep * (2.5 + i), round(100 * record[i][j], 1),
                                "</text>\n"))
            for i in range(2, rows):
                # add the horizontal lines between the rows
                outfile.write(
                    "<line x1='{}' y1='{}' x2='{}' y2='{}' style='stroke:rgb(0,0,0)'/>\n".format(
                        margin, margin + vstep * i, margin + hstep * cols, vstep * i + margin))
                for j in range(1, cols):
                    # add the vertical lines between the columns
                    outfile.write(
                        "<line x1='{}' y1='{}' x2='{}' y2='{}' style='stroke:rgb(0,0,0)'/>\n".format(
                            margin + hstep * j, margin + vstep, margin + hstep * j, vstep * rows + margin))

            for i in range(0, rows - 2):
                # Add the H/A data
                outfile.write(
                    "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}' style='font-size:12px;font-family:Arial'>{}{}".format(
                        margin + hstep * 1.5, margin + vstep * (2.5 + i), self.win_probabilities[i]["HA"],
                        "</text>\n"))

                # Add the opponent logo
                try:
                    outfile.write(
                        "<image x='{}' y='{}' height='{}px' width='{}px' xlink:href='data:image/jpg;base64,{}'>\n<title>{}</title></image>\n".format(
                            2 * hstep + margin + (hstep - logowidth) / 2,
                            vstep * (2 + i) + margin + (vstep - logoheight) / 2, logowidth, logoheight,
                            logos[self.win_probabilities[i]["team"]], self.win_probabilities[i]["team"].title()))
                except KeyError:
                    pass

                # Add the row week label and a hitbox
                outfile.write(
                    "<rect id='week{}' x='{}' y='{}' width='{}' height='{}' style='stroke:rgb(0,0,0);stroke-width:none;fill:white'/>\n".format(
                        i, margin, margin + vstep * (2 + i), hstep, vstep))
                outfile.write(
                    "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}' style='font-size:12px;font-family:Arial;pointer-events: none'>{}{}".format(
                        margin + hstep * 0.5, margin + vstep * (2.5 + i), i + 1, "</text>\n"))

            # Add the hitbox for the prob column
            outfile.write(
                "<rect id='probColHitBox' x='{}' y='{}' width='{}' height='{}' style='fill-opacity:0'/>".format(
                    margin + hstep * 3, margin + vstep, hstep, vstep * (rows + 1)))

            # Draw the outline box for the table
            outfile.write(
                "<rect x='{}' y='{}' width='{}' height='{}' style='stroke:rgb(0,0,0);stroke-width:2;fill:none'/>\n".format(
                    margin, margin + vstep, hstep * cols, vstep * (rows - 1)))

            # Draw the outline box for the win total sub-table
            outfile.write(
                "<rect x='{}' y='{}' width='{}' height='{}' style='stroke:rgb(0,0,0);stroke-width:2;fill:none'/>\n".format(
                    margin + hstep * 4, margin + vstep, hstep * (cols - 4), vstep * (rows - 1)))

            # Draw the outline box for the column headers
            outfile.write(
                "<rect x='{}' y='{}' width='{}' height='{}' style='stroke:rgb(0,0,0);stroke-width:2;fill:none'/>".format(
                    margin, margin + vstep, hstep * cols, vstep))

            # Draw the outline box for the win total header label
            outfile.write(
                "<rect x='{}' y='{}' width='{}' height='{}' style='stroke:rgb(0,0,0);stroke-width:2;fill:none'/>\n".format(
                    margin + hstep * 4, margin, hstep * (cols - 4), vstep))

            # TODO: research and implement a solution so that we can wholesale toggle relative-contrast and absolute-probability color scales
            """
            # Add a box to toggle contrast and absolute coloration
            outfile.write("<script type='text/javascript'><![CDATA[\n\t")
            outfile.write("function foo() {\n\t")  # user clicks anywhere on the svg
            outfile.write("}\n")  # if group svg_2 is hidden
            outfile.write("")  # change to visible; else
            outfile.write("});\n")  # change it to hidden
            outfile.write("]]>\n</script>\n")
            """
            outfile.write("</svg>")


class Conference:
    def __init__(self, data=None):
        if not data:
            self.teams = []
        else:
            self.divisions = [x for x in data]
            self.teams = [Team(name=i, win_probabilities=data[x][i], conference=self.__str__(), division=x) for x in
                          self.divisions for i in data[x]]

    def make_standings_projection_graph(self, file='out', week=None, hstep=40, vstep=40, margin=5, logowidth=30,
                                        logoheight=30, absolute=False):
        logos = Utils.get_logo_URIs()

        # get the records for the final week for each team
        record = []
        # sort teams by their weighted average number of wins and division
        if (not week) or (week < 1) or (week > max([len(x.win_probabilities) for x in self.teams])):
            week = -1
        for i in self.divisions:
            record.extend(
                sorted([(x, x.win_totals_by_week()[week]) for x in self.teams if x.division == i],
                       key=lambda team: sum([team[1][x] * x for x in range(len(team[1]))]), reverse=True))
        if not os.path.exists("./svg output/"):
            os.makedirs("./svg output/")

        with open(os.path.join("./svg output/", '{}.svg'.format(file)), 'w+') as outfile:
            # The SVG output should generally be divided into 3 leading columns (week, H/A, Opp, Prob) and n=len(self.win_probabilities) + 1 segments
            # and 2 leading rows (Wins and headers) with n=len(self.win_probabilities) vertical segments.
            rows, cols = len(record) + 2, max([len(x[1]) for x in record]) + 1

            # Write the SVG header; remember to write </svg> to close the file
            outfile.write(
                "<svg version='1.1'\n\tbaseProfile='full'\n\twidth='{}' height='{}'\n\txmlns='http://www.w3.org/2000/svg'\n\txmlns:xlink='http://www.w3.org/1999/xlink'\n\tstyle='shape-rendering:crispEdges;'>\n".format(
                    hstep * cols + 2 * margin, vstep * rows + 2 * margin))

            # Fill the background with white
            outfile.write("<rect width='100%' height='100%' style='fill:rgb(255,255,255)' />")

            # Add the horizontal header label; it is at the very top of the svg and covers all but the first column, with centered text
            outfile.write(
                "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}'  style='font-size:12px;font-family:Arial'>Total Wins</text>\n".format(
                    margin + hstep * (cols - (cols - 1) / 2), margin + vstep * 0.5))

            # Add column labels for the Team Name
            outfile.write(
                "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}'  style='font-size:12px;font-family:Arial'>Team</text>\n".format(
                    margin + hstep * 0.5, margin + vstep * 1.5))

            # This set of loops fills in the body of the table
            for i in range(0, rows - 2):
                # Add the team logo
                outfile.write(
                    "<image x='{}' y='{}' height='{}px' width='{}px' xlink:href='data:image/jpg;base64,{}'/>".format(
                        margin + (hstep - logowidth) / 2,
                        vstep * (2 + i) + margin + (vstep - logoheight) / 2, logowidth, logoheight,
                        logos[record[i][0].name]))

                # find the max and min in this week to determine color of cell
                if absolute:
                    upper, lower = 1, 0
                else:
                    upper, lower = max(record[i][1]), min(record[i][1])

                for j in range(0, cols - 1):
                    if i == 0:
                        # Add the column label
                        outfile.write(
                            "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}' style='font-size:12px;font-family:Arial'>{}{}".format(
                                margin + hstep * (1.5 + j), margin + vstep * 1.5, j, "</text>\n"))
                    if j < len(record[i][1]):
                        r, g, b = Utils.gradient_color(lower, upper, record[i][1][j])
                    else:
                        r, g, b = 150, 150, 150

                    # Draw the color-coded box
                    outfile.write(
                        "<rect x='{}' y='{}' width='{}' height='{}' style='fill:rgb({},{},{})'/>\n".format(
                            margin + hstep * (1 + j), margin + vstep * (2 + i), hstep, vstep, r, g, b))

                    if j < len(record[i][1]):
                        # Write the probability in the box
                        outfile.write(
                            "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}'  style='font-size:11px;font-family:Arial'>{}%{}".format(
                                margin + hstep * (1.5 + j), margin + vstep * (2.5 + i), round(100 * record[i][1][j], 1),
                                "</text>\n"))

            # This set of loops draws the grid over the table.
            for i in range(2, rows):
                for j in range(1, cols):
                    # add the vertical lines between the columns
                    outfile.write(
                        "<line x1='{}' y1='{}' x2='{}' y2='{}' style='stroke:rgb(0,0,0)'/>\n".format(
                            margin + hstep * j, margin + vstep, margin + hstep * j, margin + vstep * rows))
                    # add the horizontal lines between the rows
                    outfile.write(
                        "<line x1='{}' y1='{}' x2='{}' y2='{}' style='stroke:rgb(0,0,0)'/>\n".format(
                            margin, margin + vstep * i, margin + hstep * cols, margin + vstep * i))
            # add the horizontal line between the divisions
            outfile.write(
                "<line x1='{}' y1='{}' x2='{}' y2='{}' style='stroke:rgb(0,0,0);stroke-width:3'/>\n".format(
                    margin, margin + vstep * (2 + len(self.teams) / len(self.divisions)), margin + hstep * cols,
                            margin + vstep * (2 + len(self.teams) / len(self.divisions))))
            # Draw the outline box for the table
            outfile.write(
                "<rect x='{}' y='{}' width='{}' height='{}' style='stroke:rgb(0,0,0);stroke-width:2;fill-opacity:0'/>\n".format(
                    margin, margin + vstep, hstep * cols, vstep * (rows - 1)))

            # Draw the outline box for the win total sub-table
            outfile.write(
                "<rect x='{}' y='{}' width='{}' height='{}' style='stroke:rgb(0,0,0);stroke-width:2;fill-opacity:0'/>\n".format(
                    margin + hstep, margin + vstep, hstep * (cols - 1), vstep * (rows - 1)))

            # Draw the outline box for the column headers
            outfile.write(
                "<rect x='{}' y='{}' width='{}' height='{}' style='stroke:rgb(0,0,0);stroke-width:2;fill-opacity:0'/>".format(
                    margin, margin + vstep, hstep * cols, vstep))

            # Draw the outline box for the win total header label
            outfile.write(
                "<rect x='{}' y='{}' width='{}' height='{}' style='stroke:rgb(0,0,0);stroke-width:2;fill-opacity:0'/>".format(
                    margin + hstep, margin, hstep * (cols - 1), vstep))

            outfile.write("</svg>")


#Utils.download_schedules()

with open("schedule.json", "r") as file:
    conferences = json.load(file)


Conference(conferences['bigten']).make_standings_projection_graph(absolute=False, file="bigten")
Conference(conferences['bigxii']).make_standings_projection_graph(absolute=False, file="bigxii")
Conference(conferences['pac12']).make_standings_projection_graph(absolute=False, file="pac12")
Conference(conferences['cusa']).make_standings_projection_graph(absolute=False, file="cusa")
Conference(conferences['acc']).make_standings_projection_graph(absolute=False, file="acc")

for conference in conferences:
    for division in conferences[conference]:
        for team in conferences[conference][division]:
            if len(conferences[conference][division][team]) > 0: \
                    Team(name=team,
                         win_probabilities=conferences[conference][division][team]).make_win_probability_graph(
                        absolute=False, file=team)
