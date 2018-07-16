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
        for link in results:
            id = link['href'][47:link['href'].find('/', 47)]
            name = link['href'][link['href'].find('/', 47) + 1:link['href'].rfind('-')]
            name = name.replace('-', ' ').title()
            pic_url = "http://a.espncdn.com/combiner/i?img=/i/teamlogos/ncaa/500/{}.png&h={}&w={}".format(id, height,
                                                                                                          width)
            with open('{}.jpg'.format(name.lower()), 'wb') as handle:
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

    def win_totals_by_week(self):
        # Make a ragged table to store 'games' x 'wins'
        record = [[0 for y in range(0, x + 1)] for x in range(1, len(self.win_probabilities) + 1)]

        record[0][0] = 1 - self.win_probabilities[0][1]  # first game was a loss
        record[0][1] = self.win_probabilities[0][1]  # first game was a win

        for i in range(1, len(record)):
            for j in range(0, i + 1):
                record[i][j] += record[i - 1][j] * (1 - self.win_probabilities[i][1])  # newest game was a loss
                record[i][j + 1] += record[i - 1][j] * (self.win_probabilities[i][1])  # newest game was a win

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
                                   menuheight=40, absolute=False):
        record = self.win_totals_by_week()
        logos = Utils.get_logo_URIs()

        with open('{}.svg'.format(file), 'w+') as outfile:
            # The SVG output should generally be divided into 3 leading columns (week, H/A, Opp, Prob) and n=len(self.win_probabilities) + 1 segments
            # and 2 leading rows (Wins and headers) with n=len(self.win_probabilities) vertical segments.
            rows, cols = 2 + len(self.win_probabilities), 4 + len(self.win_probabilities) + 1

            # Write the SVG header; remember to write </svg> to close the file
            outfile.write(
                "<svg version=\"1.1\"\n\tbaseProfile=\"full\"\n\twidth=\"{}\" height=\"{}\"\n\txmlns=\"http://www.w3.org/2000/svg\"\n\txmlns:xlink=\"http://www.w3.org/1999/xlink\"\n\tstyle=\"shape-rendering:crispEdges;\">\n".format(
                    hstep * cols + 2 * margin, vstep * rows + 3 * margin + menuheight))

            # Fill the background with white
            outfile.write("<rect width=\"100%\" height=\"100%\" style=\"fill:rgb(255,255,255)\" />")

            # Add the team logo
            outfile.write(
                "<image x=\"{}\" y=\"{}\" height=\"{}px\" width=\"{}px\" xlink:href=\"data:image/jpg;base64,{}\"/>".format(
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
                            "><set attributeName =\"fill\" from=\"rgb({},{},{})\" to=\"rgb({},{},{})\" begin=\"absoluteScale.mouseover\" end=\"absoluteScale.mouseout\"/></rect>\n".format(
                                r, g, b, r_absolute, g_absolute, b_absolute))
                    else:
                        outfile.write("/>")

            outfile.write("</g>\n")

            for i in range(0, rows - 2):
                # Add the H/A data
                outfile.write(
                    "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\" style=\"font-size:12px;font-family:Arial\">{}{}".format(
                        margin + hstep * 1.5, margin + vstep * (2.5 + i), self.win_probabilities[i][2],
                        "</text>\n"))

                # Add the opponent logo
                outfile.write(
                    "<image x=\"{}\" y=\"{}\" height=\"{}px\" width=\"{}px\" xlink:href=\"data:image/jpg;base64,{}\"/>".format(
                        2 * hstep + margin + (hstep - logowidth) / 2,
                        vstep * (2 + i) + margin + (vstep - logoheight) / 2, logowidth, logoheight,
                        logos[self.win_probabilities[i][0]]))

                # Add the row week label
                outfile.write(
                    "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\" style=\"font-size:12px;font-family:Arial\">{}{}".format(
                        margin + hstep * 0.5, margin + vstep * (2.5 + i), i + 1, "</text>\n"))

                # Add the color-coded box in the prob column with its text
                r, g, b = Utils.gradient_color(0, 1, self.win_probabilities[i][1])
                outfile.write(
                    "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" style=\"fill:rgb({},{},{})\"/>".format(
                        margin + hstep * 3, margin + vstep * (2 + i), hstep, vstep, r, g, b))
                outfile.write(
                    "<text text-anchor=\"middle\" alignment-baseline=\"central\" x=\"{}\" y=\"{}\" style=\"font-size:11px;font-family:Arial\">{}%{}".format(
                        margin + hstep * 3.5, margin + vstep * (2.5 + i),
                        round(100 * self.win_probabilities[i][1], 1),
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

        with open('{}.svg'.format(file), 'w+') as outfile:
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

bigten = [  # pre-season
    {"east": {
        "indiana": [["florida international", .77, "at"], ["virginia", .62, "vs"], ["ball state", .83, "vs"],
                    ["michigan state", .22, "vs"], ["rutgers", .56, "at"], ["ohio state", .06, "at"],
                    ["iowa", .44, "vs"], ["penn state", .19, "vs"], ["minnesota", .47, "at"],
                    ["maryland", .64, "vs"], ["michigan", .14, "at"], ["purdue", .53, "vs"]],
        "maryland": [["texas", .26, "vs"], ["bowling green", .55, "at"], ["temple", .56, "vs"],
                     ["minnesota", .50, "vs"], ["michigan", .10, "at"], ["rutgers", .59, "vs"],
                     ["iowa", .25, "at"], ["illinois", .69, "vs"], ["michigan state", .16, "vs"],
                     ["indiana", .36, "at"], ["ohio state", .06, "vs"], ["penn state", .08, "at"]],
        "michigan": [["notre dame", .38, "at"], ["western michigan", .92, "vs"], ["smu", .90, "vs"],
                     ["nebraska", .86, "vs"], ["northwestern", .71, "vs"], ["maryland", .90, "vs"],
                     ["wisconsin", .57, "vs"], ["michigan state", .45, "at"], ["penn state", .51, "vs"],
                     ["rutgers", .86, "at"], ["indiana", .86, "vs"], ["ohio state", .26, "at"]],
        "michigan state": [["utah state", .89, "vs"], ["arizona state", .78, "at"], ["indiana", .78, "at"],
                           ["central michigan", .97, "vs"], ["northwestern", .79, "vs"], ["penn state", .39, "at"],
                           ["michigan", .55, "vs"], ["purdue", .84, "vs"], ["maryland", .84, "at"],
                           ["ohio state", .35, "vs"], ["nebraska", .78, "at"], ["rutgers", .91, "vs"]],
        "ohio state": [["oregon state", .99, "vs"], ["rutgers", .97, "vs"], ["tcu", .78, "at"],
                       ["tulane", .98, "vs"], ["penn state", .60, "at"], ["indiana", .94, "vs"],
                       ["minnesota", .95, "vs"], ["purdue", .89, "at"], ["nebraska", .94, "vs"],
                       ["michigan state", .65, "at"], ["maryland", .94, "at"], ["michigan", .74, "vs"]],
        "penn state": [["appalachian state", .89, "vs"], ["pittsburgh", .77, "at"], ["kent state", .99, "vs"],
                       ["illinois", .93, "at"], ["ohio state", .40, "vs"], ["michigan state", .61, "vs"],
                       ["indiana", .81, "at"], ["iowa", .81, "vs"], ["michigan", .49, "at"],
                       ["wisconsin", .61, "vs"], ["rutgers", .89, "at"], ["maryland", .92, "vs"]],
        "rutgers": [["texas state", .79, "vs"], ["ohio state", .03, "at"], ["kansas", .56, "at"],
                    ["buffalo", .61, "vs"], ["indiana", .44, "vs"], ["illinois", .66, "vs"],
                    ["maryland", .41, "at"], ["northwestern", .34, "vs"], ["wisconsin", .09, "at"],
                    ["michigan", .14, "vs"], ["penn state", .11, "vs"], ["michigan state", .09, "at"]],

    }, "west": {
        "illinois": [["kent state", .72, "vs"], ["western illinois", .71, "vs"], ["usf", .28, "vs"],
                     ["penn state", .07, "vs"], ["rutgers", .34, "at"], ["purdue", .32, "vs"],
                     ["wisconsin", .05, "at"], ["maryland", .31, "at"], ["minnesota", .37, "vs"],
                     ["nebraska", .24, "at"], ["iowa", .24, "vs"], ["northwestern", .17, "at"]],
        "iowa": [["northern illinois", .71, "vs"], ["iowa state", .62, "vs"], ["north iowa", .92, "vs"],
                 ["wisconsin", .32, "vs"], ["minnesota", .59, "at"], ["indiana", .56, "at"],
                 ["maryland", .75, "vs"], ["penn state", .19, "at"], ["purdue", .54, "at"],
                 ["northwestern", .57, "vs"], ["illinois", .76, "at"], ["nebraska", .67, "vs"]],
        "minnesota": [["new mexico state", .74, "vs"], ["fresno state", .46, "vs"], ["miami (ohio)", .62, "vs"],
                      ["maryland", .50, "at"], ["iowa", .41, "vs"], ["ohio state", .05, "at"],
                      ["nebraska", .42, "at"], ["indiana", .53, "vs"], ["illinois", .63, "at"],
                      ["purdue", .50, "vs"], ["northwestern", .43, "vs"], ["wisconsin", .13, "at"]],
        "nebraska": [["akron", .84, "vs"], ["colorado", .70, "vs"], ["troy", .63, "vs"],
                     ["michigan", .14, "at"], ["purdue", .53, "vs"], ["wisconsin", .14, "at"],
                     ["northwestern", .34, "at"], ["minnesota", .58, "vs"], ["ohio state", .06, "at"],
                     ["illinois", .76, "vs"], ["michigan state", .22, "vs"], ["iowa", .33, "at"]],
        "northwestern": [["purdue", .52, "at"], ["duke", .57, "vs"], ["akron", .89, "vs"], ["michigan", .29, "vs"],
                         ["michigan state", .21, "at"],
                         ["nebraska", .66, "vs"], ["rutgers", .66, "at"], ["wisconsin", .31, "vs"],
                         ["notre dame", .24, "vs"], ["iowa", .43, "at"],
                         ["minnesota", .57, "at"], ["illinois", .83, "vs"]],
        "purdue": [["northwestern", .48, "vs"], ["eastern michigan", .75, "vs"], ["missouri", .43, "vs"],
                   ["boston college", .54, "vs"],
                   ["nebraska", .47, "at"], ["illinois", .68, "at"], ["ohio state", .11, "vs"],
                   ["michigan state", .16, "at"], ["iowa", .46, "vs"],
                   ["minnesota", .50, "at"], ["wisconsin", .24, "vs"], ["indiana", .47, "at"]],
        "wisconsin": [["western kentucky", .92, "vs"], ["new mexico", .96, "vs"], ["byu", .89, "vs"],
                      ["iowa", .68, "at"], ["nebraska", .86, "vs"],
                      ["michigan", .43, "at"], ["illinois", .95, "vs"], ["northwestern", .69, "at"],
                      ["rutgers", .91, "vs"],
                      ["penn state", .39, "at"], ["purdue", .76, "at"], ["minnesota", .87, "vs"]]
    }}
]

acc = [  # pre-season
    {
        "atlantic": {
            "boston college": [],
            "clemson": [],
            "florida state": [],
            "louisville": [],
            "north carolina state": [],
            "syracuse": [],
            "wake forest": []
        },
        "coastal": {
            "duke": [],
            "georgia tech": [["alcorn state", .98, "vs"], ["south florida", .47, "at"], ["pittsburgh", .42, "at"],
                             ["clemson", .13, "vs"], ["bowling green", .76, "vs"], ["louisville", .32, "at"],
                             ["duke", .51, "vs"], ["virginia tech", .27, "at"], ["north carolina", .44, "at"],
                             ["miami", .26, "vs"], ["virginia", .65, "vs"], ["georgia", .11, "at"]],
            "miami": [],
            "north carolina": [],
            "pitt": [],
            "virginia": [],
            "virginia tech": []
        }
    }
]

# Utils.download_images()
# Utils.convert_to_URI(width=30, height=30)
name = "michigan"
conference = bigten
division = "east"
# foo = Conference(conference[0]).make_standings_projection_graph(absolute=False)
foo = Team(name=name, win_probabilities=conference[0][division][name])
foo.make_win_probability_graph(absolute=False)
# foo.write_win_probability_csv()
