import base64
import csv
import json
import os
import re
from colorsys import hls_to_rgb

import requests
from bs4 import BeautifulSoup as bs


class Utils:
    @staticmethod
    def interpolate(lower, upper, val, method="linear"):
        if upper == lower:
            return 1
        elif method.lower() == "cubic":
            x = (val - lower) / (upper - lower)
            return x ** 3 * (10 + x * (-15 + 6 * x))
        else:
            return (val - lower) / (upper - lower)

    @staticmethod
    def gradient_color(lower, upper, val, method="linear"):
        # Perform linear interpolation on the hue between 0.33 and 0, then convert back to RGB
        # HLS 0.33, 0.65, 1.0 will give green
        # HLS 0, 0.65, 1.0 will give red
        if upper == lower:
            h = 120
        else:
            h = 120 * Utils.interpolate(lower, upper, val, method=method)

        return [255 * x for x in hls_to_rgb(h / 360.0, 0.65, 1)]

    @staticmethod
    def get_logo_URIs():
        with open("Logo URIs.txt", 'r') as infile:
            json_data = infile.read()

        return json.loads(json_data)

    @staticmethod
    def download_images(width=40, height=40):
        # Quick and dirty method to scrape logos from ESPN; they need minor editorial cleanup afterward
        r = requests.get("http://www.espn.com/college-football/teams")
        results = bs(r.text).findAll('a', href=re.compile('^http://www.espn.com/college-football/team/_/id/'))
        if not os.path.exists("./Resources/"):
            os.makedirs("./Resources/")

        for link in results:
            id = link['href'][47:link['href'].find('/', 47)]
            name = link['href'][link['href'].find('/', 47) + 1:link['href'].rfind('-')]
            name = name.replace('-', ' ').title()
            pic_url = "http://a.espncdn.com/combiner/i?img=/i/teamlogos/ncaa/500/{}.png&h={}&w={}".format(id, height,
                                                                                                          width)
            with open(os.path.join("./Resources/", '{}.jpg'.format(name.lower())), 'wb') as handle:
                response = requests.get(pic_url, stream=True)

                if not response.ok:
                    print(response)

                for block in response.iter_content(1024):
                    if not block:
                        break

                    handle.write(block)

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

    def win_totals_by_week(self, projection_week=0):
        # Make a ragged table to store 'games' x 'wins'
        record = [[0 for y in range(0, x + 1)] for x in range(1, len(self.win_probabilities) + 1)]
        foo = self.win_probabilities[0]["winprob"][projection_week]
        record[0][0] = 1 - self.win_probabilities[0]["winprob"][projection_week]  # first game was a loss
        record[0][1] = self.win_probabilities[0]["winprob"][projection_week]  # first game was a win

        for i in range(1, len(record)):
            for j in range(0, i + 1):
                record[i][j] += record[i - 1][j] * (
                        1 - self.win_probabilities[i]["winprob"][projection_week])  # newest game was a loss
                record[i][j + 1] += record[i - 1][j] * (
                    self.win_probabilities[i]["winprob"][projection_week])  # newest game was a win

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
                                   menuheight=40, absolute=False, projectionweek=0):
        record = self.win_totals_by_week()
        logos = Utils.get_logo_URIs()

        if not os.path.exists("./svg output/"):
            os.makedirs("./svg output/")

        with open(os.path.join("./svg output/", '{}.svg'.format(file)), 'w+') as outfile:
            # The SVG output should generally be divided into 3 leading columns (week, H/A, Opp, Prob) and n=len(self.win_probabilities) + 1 segments
            # and 2 leading rows (Wins and headers) with n=len(self.win_probabilities) vertical segments.
            rows, cols = 2 + len(self.win_probabilities), 4 + len(self.win_probabilities) + 1

            # Write the SVG header; remember to write </svg> to close the file
            outfile.write(
                "<svg version=\"1.1\"\n\tbaseProfile=\"full\"\n\twidth=\"{}\" height=\"{}\"\n\txmlns=\"http://www.w3.org/2000/svg\"\n\txmlns:xlink=\"http://www.w3.org/1999/xlink\"\n\tstyle=\"shape-rendering:crispEdges;\">\n".format(
                    hstep * cols + 2 * margin, vstep * rows + 3 * margin + menuheight))

            # Fill the background with white
            outfile.write("<rect width=\"100%\" height=\"100%\" style=\"fill:rgb(255,255,255)\" />\n")

            # Add the team logo
            outfile.write(
                "<image x=\"{}\" y=\"{}\" height=\"{}px\" width=\"{}px\" xlink:href=\"data:image/jpg;base64,{}\"/>\n".format(
                    margin + (hstep - logowidth) / 2,
                    margin + (vstep - logoheight) / 2, logowidth, logoheight, logos[self.name]))

            # Add the horizontal header label; it is at the very top of the svg and covers the right 16 columns, with centered text
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:12px;font-family:Arial\">Total Wins</text>\n".format(
                    margin + hstep * (cols - (cols - 4) / 2), margin + vstep * 0.5))

            # Add column labels for the H/A and Opp
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:12px;font-family:Arial\">Week</text>\n".format(
                    margin + hstep * 0.5, margin + vstep * 1.5))
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:12px;font-family:Arial\">H/A</text>\n".format(
                    margin + hstep * 1.5, margin + vstep * 1.5))
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:12px;font-family:Arial\">Opp</text>\n".format(
                    margin + hstep * 2.5, margin + vstep * 1.5))

            # writing multiline text is a bit dodgy; this works
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"baseline\" x=\"{}\" y=\"{}\"  style=\"font-size:12px;font-family:Arial\">Win</text>\n".format(
                    margin + hstep * 3.5, margin + vstep * 1.5 - 2))
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"hanging\" x=\"{}\" y=\"{}\"  style=\"font-size:12px;font-family:Arial\">Prob</text>\n".format(
                    margin + hstep * 3.5, margin + vstep * 1.5 + 2))

            outfile.write("<g id=\"probBoxes\">\n")

            for i in range(0, rows - 2):
                # find the max and min in this week to determine color of cell
                # The rows can be color coded by giving scaling to the maximum likelihood within the week (relative)
                # or by absolute likelihood (max=1.0). Default is relative.
                if absolute:
                    upper, lower = 1, 0
                else:
                    upper, lower = max(record[i]), min(record[i])

                for j in range(0, len(record) + 1):
                    if i == 0:
                        # Add the column label
                        outfile.write(
                            "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\" style=\"font-size:12px;font-family:Arial\">{}{}".format(
                                margin + hstep * (4.5 + j), margin + vstep * 1.5, j, "</text>\n"))

                    if j < len(record[i]):
                        # We need to fill the relative color code in the box initially and store the relative and absolute color codes
                        # so that we can use them later to animate the chart
                        r, g, b = Utils.gradient_color(lower, upper, record[i][j])

                    else:
                        r, g, b = 150, 150, 150

                    # Draw the color-coded box
                    outfile.write(
                        "<rect id=\"{},{}\" x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" style=\"fill:rgb({},{},{})\"".format(
                            i, j, margin + hstep * (4 + j), margin + vstep * (2 + i), hstep, vstep, r, g, b))
                    if j < len(record[i]):
                        r_absolute, g_absolute, b_absolute = Utils.gradient_color(0, 1, record[i][j])
                        outfile.write(
                            ">\n<set attributeName =\"fill\" from=\"rgb({},{},{})\" to=\"rgb({},{},{})\" begin=\"absoluteScale.mouseover\" end=\"absoluteScale.mouseout\"/></rect>\n".format(
                                r, g, b, r_absolute, g_absolute, b_absolute))
                    else:
                        outfile.write("/>")

            outfile.write("</g>\n")

            for i in range(0, rows - 2):
                # Add the color-coded box in the prob column with its text
                r, g, b = Utils.gradient_color(0, 1, self.win_probabilities[i]["winprob"][projectionweek])
                outfile.write(
                    "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" style=\"fill:rgb({},{},{})\"/>".format(
                        margin + hstep * 3, margin + vstep * (2 + i), hstep, vstep, r, g, b))
                outfile.write(
                    "<text text-anchor=\"middle\" alignment-baseline=\"central\" x=\"{}\" y=\"{}\" style=\"font-size:11px;font-family:Arial\">{}%{}".format(
                        margin + hstep * 3.5, margin + vstep * (2.5 + i),
                        round(100 * self.win_probabilities[i]["winprob"][projectionweek], 1),
                        "</text>\n"))

                for j in range(0, len(record) + 1):
                    if j < len(record[i]):
                        # Write the probability in the box
                        outfile.write(
                            "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:11px;font-family:Arial\">{}%{}".format(
                                margin + hstep * (4.5 + j), margin + vstep * (2.5 + i), round(100 * record[i][j], 1),
                                "</text>\n"))
            for i in range(2, rows):
                # add the horizontal lines between the rows
                outfile.write(
                    "<line x1=\"{}\" y1=\"{}\" x2=\"{}\" y2=\"{}\" style=\"stroke:rgb(0,0,0)\"/>\n".format(
                        margin, margin + vstep * i, margin + hstep * cols, vstep * i + margin))
                for j in range(1, cols):
                    # add the vertical lines between the columns
                    outfile.write(
                        "<line x1=\"{}\" y1=\"{}\" x2=\"{}\" y2=\"{}\" style=\"stroke:rgb(0,0,0)\"/>\n".format(
                            margin + hstep * j, margin + vstep, margin + hstep * j, vstep * rows + margin))

            # Draw the outline box for the table
            outfile.write(
                "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" style=\"stroke:rgb(0,0,0);stroke-width:2;fill-opacity:0\"/>\n".format(
                    margin, margin + vstep, hstep * cols, vstep * (rows - 1)))

            # Draw the outline box for the win total sub-table
            outfile.write(
                "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" style=\"stroke:rgb(0,0,0);stroke-width:2;fill-opacity:0\"/>\n".format(
                    margin + hstep * 4, margin + vstep, hstep * (cols - 4), vstep * (rows - 1)))

            # Draw the outline box for the column headers
            outfile.write(
                "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" style=\"stroke:rgb(0,0,0);stroke-width:2;fill-opacity:0\"/>".format(
                    margin, margin + vstep, hstep * cols, vstep))

            # Draw the outline box for the win total header label
            outfile.write(
                "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" style=\"stroke:rgb(0,0,0);stroke-width:2;fill-opacity:0\"/>".format(
                    margin + hstep * 4, margin, hstep * (cols - 4), vstep))

            # Add the color changing text at the bottom of the svg
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"middle\" id=\"absoluteScale\" x=\"{}\" y=\"{}\" font-size=\"30\" fill=\"black\" >Absolute Color Scale</text>\n".format(
                    (hstep * cols + 2 * margin) / 2, vstep * rows + 3 * margin + menuheight / 2))

            for i in range(0, rows - 2):
                # Add the H/A data
                outfile.write(
                    "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\" style=\"font-size:12px;font-family:Arial\">{}{}".format(
                        margin + hstep * 1.5, margin + vstep * (2.5 + i), self.win_probabilities[i]["HA"],
                        "</text>\n"))

                # Add the opponent logo
                outfile.write(
                    "<image x=\"{}\" y=\"{}\" height=\"{}px\" width=\"{}px\" xlink:href=\"data:image/jpg;base64,{}\">\n<title>{}</title></image>\n".format(
                        2 * hstep + margin + (hstep - logowidth) / 2,
                        vstep * (2 + i) + margin + (vstep - logoheight) / 2, logowidth, logoheight,
                        logos[self.win_probabilities[i]["team"]], self.win_probabilities[i]["team"].title()))

                # Add the row week label
                outfile.write(
                    "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\" style=\"font-size:12px;font-family:Arial\">{}{}".format(
                        margin + hstep * 0.5, margin + vstep * (2.5 + i), i + 1, "</text>\n"))

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
                                        logoheight=30,
                                        absolute=False):
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
                "<svg version=\"1.1\"\n\tbaseProfile=\"full\"\n\twidth=\"{}\" height=\"{}\"\n\txmlns=\"http://www.w3.org/2000/svg\"\n\txmlns:xlink=\"http://www.w3.org/1999/xlink\"\n\tstyle=\"shape-rendering:crispEdges;\">\n".format(
                    hstep * cols + 2 * margin, vstep * rows + 2 * margin))

            # Fill the background with white
            outfile.write("<rect width=\"100%\" height=\"100%\" style=\"fill:rgb(255,255,255)\" />")

            # Add the horizontal header label; it is at the very top of the svg and covers all but the first column, with centered text
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:12px;font-family:Arial\">Total Wins</text>\n".format(
                    margin + hstep * (cols - (cols - 1) / 2), margin + vstep * 0.5))

            # Add column labels for the Team Name
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:12px;font-family:Arial\">Team</text>\n".format(
                    margin + hstep * 0.5, margin + vstep * 1.5))

            for i in range(0, rows - 2):
                # Add the team logo
                outfile.write(
                    "<image x=\"{}\" y=\"{}\" height=\"{}px\" width=\"{}px\" xlink:href=\"data:image/jpg;base64,{}\"/>".format(
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
                            "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\" style=\"font-size:12px;font-family:Arial\">{}{}".format(
                                margin + hstep * (1.5 + j), margin + vstep * 1.5, j, "</text>\n"))

                    r, g, b = Utils.gradient_color(lower, upper, record[i][1][j])
                    # Draw the color-coded box
                    outfile.write(
                        "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" style=\"fill:rgb({},{},{})\"/>\n".format(
                            margin + hstep * (1 + j), margin + vstep * (2 + i), hstep, vstep, r, g, b))

                    if j < len(record[i][1]):
                        # Write the probability in the box
                        outfile.write(
                            "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:11px;font-family:Arial\">{}%{}".format(
                                margin + hstep * (1.5 + j), margin + vstep * (2.5 + i), round(100 * record[i][1][j], 1),
                                "</text>\n"))
            for i in range(2, rows):
                for j in range(1, cols):
                    # add the vertical lines between the columns
                    outfile.write(
                        "<line x1=\"{}\" y1=\"{}\" x2=\"{}\" y2=\"{}\" style=\"stroke:rgb(0,0,0)\"/>\n".format(
                            margin + hstep * j, margin + vstep, margin + hstep * j, margin + vstep * rows))
                    # add the horizontal lines between the rows
                    outfile.write(
                        "<line x1=\"{}\" y1=\"{}\" x2=\"{}\" y2=\"{}\" style=\"stroke:rgb(0,0,0)\"/>\n".format(
                            margin, margin + vstep * i, margin + hstep * cols, margin + vstep * i))
            # add the horizontal line between the divisions
            outfile.write(
                "<line x1=\"{}\" y1=\"{}\" x2=\"{}\" y2=\"{}\" style=\"stroke:rgb(0,0,0);stroke-width:3\"/>\n".format(
                    margin, margin + vstep * (2 + len(self.teams) / len(self.divisions)), margin + hstep * cols,
                            margin + vstep * (2 + len(self.teams) / len(self.divisions))))
            # Draw the outline box for the table
            outfile.write(
                "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" style=\"stroke:rgb(0,0,0);stroke-width:2;fill-opacity:0\"/>\n".format(
                    margin, margin + vstep, hstep * cols, vstep * (rows - 1)))

            # Draw the outline box for the win total sub-table
            outfile.write(
                "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" style=\"stroke:rgb(0,0,0);stroke-width:2;fill-opacity:0\"/>\n".format(
                    margin + hstep, margin + vstep, hstep * (cols - 1), vstep * (rows - 1)))

            # Draw the outline box for the column headers
            outfile.write(
                "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" style=\"stroke:rgb(0,0,0);stroke-width:2;fill-opacity:0\"/>".format(
                    margin, margin + vstep, hstep * cols, vstep))

            # Draw the outline box for the win total header label
            outfile.write(
                "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" style=\"stroke:rgb(0,0,0);stroke-width:2;fill-opacity:0\"/>".format(
                    margin + hstep, margin, hstep * (cols - 1), vstep))

            outfile.write("</svg>")


# Conference Win Probabilities. Teams are alphabetical; dimensions are week, team, win total
# These effectively constitute a weighted adjacency matrix
# although it doesn't include win probabilities for every other node in the graph nor are the nodes labeled

bigten = {"east": {
    "indiana": [{"team": "florida international", "winprob": [.77], "HA": "at"},
                {"team": "virginia", "winprob": [.62], "HA": "vs"},
                {"team": "ball state", "winprob": [.83], "HA": "vs"},
                {"team": "michigan state", "winprob": [.22], "HA": "vs"},
                {"team": "rutgers", "winprob": [.56], "HA": "at"},
                {"team": "ohio state", "winprob": [.06], "HA": "at"},
                {"team": "iowa", "winprob": [.44], "HA": "vs"},
                {"team": "penn state", "winprob": [.19], "HA": "vs"},
                {"team": "minnesota", "winprob": [.47], "HA": "at"},
                {"team": "maryland", "winprob": [.64], "HA": "vs"},
                {"team": "michigan", "winprob": [.14], "HA": "at"},
                {"team": "purdue", "winprob": [.53], "HA": "vs"}],
    "maryland": [{"team": "texas", "winprob": [.26], "HA": "vs"},
                 {"team": "bowling green", "winprob": [.55], "HA": "at"},
                 {"team": "temple", "winprob": [.56], "HA": "vs"},
                 {"team": "minnesota", "winprob": [.50], "HA": "vs"},
                 {"team": "michigan", "winprob": [.10], "HA": "at"},
                 {"team": "rutgers", "winprob": [.59], "HA": "vs"},
                 {"team": "iowa", "winprob": [.25], "HA": "at"},
                 {"team": "illinois", "winprob": [.69], "HA": "vs"},
                 {"team": "michigan state", "winprob": [.16], "HA": "vs"},
                 {"team": "indiana", "winprob": [.36], "HA": "at"},
                 {"team": "ohio state", "winprob": [.06], "HA": "vs"},
                 {"team": "penn state", "winprob": [.08], "HA": "at"}],
    "michigan": [{"team": "notre dame", "winprob": [.38], "HA": "at"},
                 {"team": "western michigan", "winprob": [.92], "HA": "vs"},
                 {"team": "smu", "winprob": [.90], "HA": "vs"},
                 {"team": "nebraska", "winprob": [.86], "HA": "vs"},
                 {"team": "northwestern", "winprob": [.71], "HA": "vs"},
                 {"team": "maryland", "winprob": [.90], "HA": "vs"},
                 {"team": "wisconsin", "winprob": [.57], "HA": "vs"},
                 {"team": "michigan state", "winprob": [.45], "HA": "at"},
                 {"team": "penn state", "winprob": [.51], "HA": "vs"},
                 {"team": "rutgers", "winprob": [.86], "HA": "at"},
                 {"team": "indiana", "winprob": [.86], "HA": "vs"},
                 {"team": "ohio state", "winprob": [.26], "HA": "at"}],
    "michigan state": [{"team": "utah state", "winprob": [.89], "HA": "vs"},
                       {"team": "arizona state", "winprob": [.78], "HA": "at"},
                       {"team": "indiana", "winprob": [.78], "HA": "at"},
                       {"team": "central michigan", "winprob": [.97], "HA": "vs"},
                       {"team": "northwestern", "winprob": [.79], "HA": "vs"},
                       {"team": "penn state", "winprob": [.39], "HA": "at"},
                       {"team": "michigan", "winprob": [.55], "HA": "vs"},
                       {"team": "purdue", "winprob": [.84], "HA": "vs"},
                       {"team": "maryland", "winprob": [.84], "HA": "at"},
                       {"team": "ohio state", "winprob": [.35], "HA": "vs"},
                       {"team": "nebraska", "winprob": [.78], "HA": "at"},
                       {"team": "rutgers", "winprob": [.91], "HA": "vs"}],
    "ohio state": [{"team": "oregon state", "winprob": [.99], "HA": "vs"},
                   {"team": "rutgers", "winprob": [.97], "HA": "vs"},
                   {"team": "tcu", "winprob": [.78], "HA": "at"},
                   {"team": "tulane", "winprob": [.98], "HA": "vs"},
                   {"team": "penn state", "winprob": [.60], "HA": "at"},
                   {"team": "indiana", "winprob": [.94], "HA": "vs"},
                   {"team": "minnesota", "winprob": [.95], "HA": "vs"},
                   {"team": "purdue", "winprob": [.89], "HA": "at"},
                   {"team": "nebraska", "winprob": [.94], "HA": "vs"},
                   {"team": "michigan state", "winprob": [.65], "HA": "at"},
                   {"team": "maryland", "winprob": [.94], "HA": "at"},
                   {"team": "michigan", "winprob": [.74], "HA": "vs"}],
    "penn state": [{"team": "appalachian state", "winprob": [.89], "HA": "vs"},
                   {"team": "pittsburgh", "winprob": [.77], "HA": "at"},
                   {"team": "kent state", "winprob": [.99], "HA": "vs"},
                   {"team": "illinois", "winprob": [.93], "HA": "at"},
                   {"team": "ohio state", "winprob": [.40], "HA": "vs"},
                   {"team": "michigan state", "winprob": [.61], "HA": "vs"},
                   {"team": "indiana", "winprob": [.81], "HA": "at"},
                   {"team": "iowa", "winprob": [.81], "HA": "vs"},
                   {"team": "michigan", "winprob": [.49], "HA": "at"},
                   {"team": "wisconsin", "winprob": [.61], "HA": "vs"},
                   {"team": "rutgers", "winprob": [.89], "HA": "at"},
                   {"team": "maryland", "winprob": [.92], "HA": "vs"}],
    "rutgers": [{"team": "texas state", "winprob": [.79], "HA": "vs"},
                {"team": "ohio state", "winprob": [.03], "HA": "at"},
                {"team": "kansas", "winprob": [.56], "HA": "at"},
                {"team": "buffalo", "winprob": [.61], "HA": "vs"},
                {"team": "indiana", "winprob": [.44], "HA": "vs"},
                {"team": "illinois", "winprob": [.66], "HA": "vs"},
                {"team": "maryland", "winprob": [.41], "HA": "at"},
                {"team": "northwestern", "winprob": [.34], "HA": "vs"},
                {"team": "wisconsin", "winprob": [.09], "HA": "at"},
                {"team": "michigan", "winprob": [.14], "HA": "vs"},
                {"team": "penn state", "winprob": [.11], "HA": "vs"},
                {"team": "michigan state", "winprob": [.09], "HA": "at"}],

}, "west": {
    "illinois": [{"team": "kent state", "winprob": [.72], "HA": "vs"},
                 {"team": "western illinois", "winprob": [.71], "HA": "vs"},
                 {"team": "south florida", "winprob": [.28], "HA": "vs"},
                 {"team": "penn state", "winprob": [.07], "HA": "vs"},
                 {"team": "rutgers", "winprob": [.34], "HA": "at"},
                 {"team": "purdue", "winprob": [.32], "HA": "vs"},
                 {"team": "wisconsin", "winprob": [.05], "HA": "at"},
                 {"team": "maryland", "winprob": [.31], "HA": "at"},
                 {"team": "minnesota", "winprob": [.37], "HA": "vs"},
                 {"team": "nebraska", "winprob": [.24], "HA": "at"},
                 {"team": "iowa", "winprob": [.24], "HA": "vs"},
                 {"team": "northwestern", "winprob": [.17], "HA": "at"}],
    "iowa": [{"team": "northern illinois", "winprob": [.71], "HA": "vs"},
             {"team": "iowa state", "winprob": [.62], "HA": "vs"},
             {"team": "northern iowa", "winprob": [.92], "HA": "vs"},
             {"team": "wisconsin", "winprob": [.32], "HA": "vs"},
             {"team": "minnesota", "winprob": [.59], "HA": "at"},
             {"team": "indiana", "winprob": [.56], "HA": "at"},
             {"team": "maryland", "winprob": [.75], "HA": "vs"},
             {"team": "penn state", "winprob": [.19], "HA": "at"},
             {"team": "purdue", "winprob": [.54], "HA": "at"},
             {"team": "northwestern", "winprob": [.57], "HA": "vs"},
             {"team": "illinois", "winprob": [.76], "HA": "at"},
             {"team": "nebraska", "winprob": [.67], "HA": "vs"}],
    "minnesota": [{"team": "new mexico state", "winprob": [.74], "HA": "vs"},
                  {"team": "fresno state", "winprob": [.46], "HA": "vs"},
                  {"team": "miami (ohio)", "winprob": [.62], "HA": "vs"},
                  {"team": "maryland", "winprob": [.50], "HA": "at"},
                  {"team": "iowa", "winprob": [.41], "HA": "vs"},
                  {"team": "ohio state", "winprob": [.05], "HA": "at"},
                  {"team": "nebraska", "winprob": [.42], "HA": "at"},
                  {"team": "indiana", "winprob": [.53], "HA": "vs"},
                  {"team": "illinois", "winprob": [.63], "HA": "at"},
                  {"team": "purdue", "winprob": [.50], "HA": "vs"},
                  {"team": "northwestern", "winprob": [.43], "HA": "vs"},
                  {"team": "wisconsin", "winprob": [.13], "HA": "at"}],
    "nebraska": [{"team": "akron", "winprob": [.84], "HA": "vs"},
                 {"team": "colorado", "winprob": [.70], "HA": "vs"},
                 {"team": "troy", "winprob": [.63], "HA": "vs"},
                 {"team": "michigan", "winprob": [.14], "HA": "at"},
                 {"team": "purdue", "winprob": [.53], "HA": "vs"},
                 {"team": "wisconsin", "winprob": [.14], "HA": "at"},
                 {"team": "northwestern", "winprob": [.34], "HA": "at"},
                 {"team": "minnesota", "winprob": [.58], "HA": "vs"},
                 {"team": "ohio state", "winprob": [.06], "HA": "at"},
                 {"team": "illinois", "winprob": [.76], "HA": "vs"},
                 {"team": "michigan state", "winprob": [.22], "HA": "vs"},
                 {"team": "iowa", "winprob": [.33], "HA": "at"}],
    "northwestern": [{"team": "purdue", "winprob": [.52], "HA": "at"},
                     {"team": "duke", "winprob": [.57], "HA": "vs"},
                     {"team": "akron", "winprob": [.89], "HA": "vs"},
                     {"team": "michigan", "winprob": [.29], "HA": "vs"},
                     {"team": "michigan state", "winprob": [.21], "HA": "at"},
                     {"team": "nebraska", "winprob": [.66], "HA": "vs"},
                     {"team": "rutgers", "winprob": [.66], "HA": "at"},
                     {"team": "wisconsin", "winprob": [.31], "HA": "vs"},
                     {"team": "notre dame", "winprob": [.24], "HA": "vs"},
                     {"team": "iowa", "winprob": [.43], "HA": "at"},
                     {"team": "minnesota", "winprob": [.57], "HA": "at"},
                     {"team": "illinois", "winprob": [.83], "HA": "vs"}],
    "purdue": [{"team": "northwestern", "winprob": [.48], "HA": "vs"},
               {"team": "eastern michigan", "winprob": [.75], "HA": "vs"},
               {"team": "missouri", "winprob": [.43], "HA": "vs"},
               {"team": "boston college", "winprob": [.54], "HA": "vs"},
               {"team": "nebraska", "winprob": [.47], "HA": "at"},
               {"team": "illinois", "winprob": [.68], "HA": "at"},
               {"team": "ohio state", "winprob": [.11], "HA": "vs"},
               {"team": "michigan state", "winprob": [.16], "HA": "at"},
               {"team": "iowa", "winprob": [.46], "HA": "vs"},
               {"team": "minnesota", "winprob": [.50], "HA": "at"},
               {"team": "wisconsin", "winprob": [.24], "HA": "vs"},
               {"team": "indiana", "winprob": [.47], "HA": "at"}],
    "wisconsin": [{"team": "western kentucky", "winprob": [.92], "HA": "vs"},
                  {"team": "new mexico", "winprob": [.96], "HA": "vs"},
                  {"team": "byu", "winprob": [.89], "HA": "vs"},
                  {"team": "iowa", "winprob": [.68], "HA": "at"},
                  {"team": "nebraska", "winprob": [.86], "HA": "vs"},
                  {"team": "michigan", "winprob": [.43], "HA": "at"},
                  {"team": "illinois", "winprob": [.95], "HA": "vs"},
                  {"team": "northwestern", "winprob": [.69], "HA": "at"},
                  {"team": "rutgers", "winprob": [.91], "HA": "vs"},
                  {"team": "penn state", "winprob": [.39], "HA": "at"},
                  {"team": "purdue", "winprob": [.76], "HA": "at"},
                  {"team": "minnesota", "winprob": [.87], "HA": "vs"}]
}
}

acc = {
    "atlantic": {
        "boston college": [{"team": "umass", "winprob": [.79], "HA": "vs"},
                           {"team": "holy cross", "winprob": [.98], "HA": "vs"},
                           {"team": "wake forest", "winprob": [.37], "HA": "vs"},
                           {"team": "purdue", "winprob": [.46], "HA": "vs"},
                           {"team": "temple", "winprob": [.69], "HA": "vs"},
                           {"team": "nc state", "winprob": [.37], "HA": "vs"},
                           {"team": "louisville", "winprob": [.44], "HA": "vs"},
                           {"team": "miami", "winprob": [.26], "HA": "vs"},
                           {"team": "virginia tech", "winprob": [.28], "HA": "vs"},
                           {"team": "clemson", "winprob": [.14], "HA": "vs"},
                           {"team": "florida state", "winprob": [.27], "HA": "vs"},
                           {"team": "syracuse", "winprob": [.66], "HA": "vs"}],
        "clemson": [],
        "florida state": [],
        "louisville": [],
        "nc state": [],
        "syracuse": [],
        "wake forest": []
    },
    "coastal": {
        "duke": [],
        "georgia tech": [{"team": "alcorn state", "winprob": [.98], "HA": "vs"},
                         {"team": "south florida", "winprob": [.47], "HA": "at"},
                         {"team": "pittsburgh", "winprob": [.42], "HA": "at"},
                         {"team": "clemson", "winprob": [.13], "HA": "vs"},
                         {"team": "bowling green", "winprob": [.76], "HA": "vs"},
                         {"team": "louisville", "winprob": [.32], "HA": "at"},
                         {"team": "duke", "winprob": [.51], "HA": "vs"},
                         {"team": "virginia tech", "winprob": [.27], "HA": "at"},
                         {"team": "north carolina", "winprob": [.44], "HA": "at"},
                         {"team": "miami", "winprob": [.26], "HA": "vs"},
                         {"team": "virginia", "winprob": [.65], "HA": "vs"},
                         {"team": "georgia", "winprob": [.11], "HA": "at"}],
        "miami": [],
        "north carolina": [],
        "pitt": [],
        "virginia": [],
        "virginia tech": []
    }
}

# Conference(bigten).make_standings_projection_graph(absolute=False, file="bigten")
# for division in bigten:
#    for team in bigten[division]:
#        Team(name=team, win_probabilities=bigten[division][team]).make_win_probability_graph(absolute=False, file = team)
team = "boston college"
division = "atlantic"
Team(name=team, win_probabilities=acc[division][team]).make_win_probability_graph(absolute=False, file=team)
