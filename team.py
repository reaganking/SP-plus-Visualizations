import csv
import os

from utils import Utils


class Team:
    def __init__(self, name=None, schedule=None, method=('spplus', 'fpi')):
        self.schedule = schedule
        if not name:
            self.name = ""
        else:
            assert isinstance(name, str), "Name is not a string!"
            self.name = name.lower()
            self.conference = self.schedule[self.name]['conference']
            self.win_probabilities = {y: [x[y] for x in self.schedule[self.name]['schedule']] for y in method}
            self.logo_URI = self.schedule[self.name]['logoURI']
            try:
                self.primary_color = Utils.hex_to_rgb(self.schedule[self.name]['primaryColor'])
                self.secondary_color = Utils.hex_to_rgb(self.schedule[self.name]['secondaryColor'])
            except KeyError:
                self.primary_color = Utils.hex_to_rgb(self.schedule[self.name]['color'])
                self.secondary_color = Utils.hex_to_rgb(self.schedule[self.name]['color'])
            # Not all teams have a conference, not all conferences have divisions
            try:
                self.division = self.schedule[self.name]['division']
            except KeyError:
                pass

    def win_totals_by_week(self, projectionweek=0, method='spplus'):
        # first check to make sure the projection week has all the games projected
        try:
            win_probs = [x[projectionweek] for x in self.win_probabilities[method]]
        except IndexError:
            win_probs = [0 for x in range(12)]

        # Make a ragged table to store 'games' x 'wins'
        record = [[0 for y in range(0, x + 1)] for x in range(1, len(self.win_probabilities[method]) + 1)]
        record[0][0] = 1 - win_probs[0]  # first game was a loss
        record[0][1] = win_probs[0]  # first game was a win

        for i in range(1, len(record)):
            for j in range(0, i + 1):
                record[i][j] += record[i - 1][j] * (1 - win_probs[i])  # newest game was a loss
                record[i][j + 1] += record[i - 1][j] * (win_probs[i])  # newest game was a win

        return win_probs, record

    def write_win_probability_csv(self, file='out'):
        record = self.win_totals_by_week()
        with open("{}.csv".format(file), 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerows(record)

    def make_win_probability_graph(self, file='out', hstep=40, vstep=40, margin=5, logowidth=30, logoheight=30,
                                   menuheight=40, absolute=False, projectionweek=0, method="spplus",
                                   colorIndividualGameProbs=False, scale='red-green'):
        win_probs, record = self.win_totals_by_week(projectionweek=projectionweek, method=method)
        logos = Utils.get_logo_URIs()

        if not os.path.exists(".\svg output\{} - {}".format(method, scale)):
            os.makedirs(".\svg output\{} - {}".format(method, scale))
        path = os.path.join(".\svg output\{} - {}".format(method, scale),
                            '{} - {} - {}.svg'.format(file, method, scale))

        with open(path, 'w+') as outfile:
            # The SVG output should generally be divided into 3 leading columns (week, H/A, Opp, Prob) and n=len(self.win_probabilities) + 1 segments
            # and 2 leading rows (Wins and headers) with n=len(self.win_probabilities) vertical segments.
            rows, cols = 2 + len(self.win_probabilities[method]), 4 + len(self.win_probabilities[method]) + 1

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
                    margin + hstep * 3.5, margin + vstep * 1.5 - 3))
            outfile.write(
                "<text text-anchor='middle' alignment-baseline='hanging' x='{}' y='{}'  style='font-size:12px;font-family:Arial'>Prob</text>\n".format(
                    margin + hstep * 3.5, margin + vstep * 1.5 + 9))

            outfile.write("<g id='svg_2'>\n")

            # Make the color-coded body of the table
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

                    # where wins <= games played, make the table
                    if j < len(record[i]):
                        # We need to fill the absolute color code in the box initially and store the relative and absolute color codes
                        # so that we can use them later to animate the chart
                        ra, ga, ba = Utils.gradient_color(lower, upper, record[i][j], scale=scale,
                                                          primaryColor=self.primary_color,
                                                          secondaryColor=self.secondary_color)
                        r, g, b = Utils.gradient_color(0, 1, record[i][j], scale=scale, primaryColor=self.primary_color,
                                                       secondaryColor=self.secondary_color)

                        if absolute:
                            ra, ga, ba, r, g, b = r, g, b, ra, ga, ba

                        # Assign the color code.
                        outfile.write("fill:rgb({},{},{})'>\n".format(ra, ga, ba))

                        # These two animate the colors to change when the user mouses over / off the game box
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='mouseover'/>\n".format(
                                r, g, b, ra, ga, ba))
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='mouseout'/>\n</rect>".format(
                                ra, ga, ba, r, g, b))

                        # Should the text be white or black?
                        text_color = Utils.get_text_contrast_color(ra, ga, ba)

                        # set the alt color to the opposite of the text color
                        alt_color = Utils.get_text_contrast_color(r, g, b)

                        # Write the probability in the box
                        outfile.write(
                            "<text text-anchor='middle' alignment-baseline='bottom' x='{}' y='{}' style='font-size:11px;fill:rgb({},{},{});font-family:Arial;pointer-events: none'>{}%".format(
                                margin + hstep * (4.5 + j), margin + vstep * (2.5 + i), *text_color,
                                round(100 * record[i][j], 1)))

                        # These next two animate the colors to change when the user mouses over / off the week label
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='{}_{}.mouseover'/>\n".format(
                                *alt_color, *text_color, i, j))
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='{}_{}.mouseout'/></text>\n".format(
                                *text_color, *alt_color, i, j))

                        # Add text for the cumulative probability
                        # Should the text be white or black?
                        text_color = Utils.get_text_contrast_color(ra, ga, ba)

                        # set the alt color to the opposite of the text color
                        alt_color = Utils.get_text_contrast_color(r, g, b)

                        # Write the probability in the box
                        outfile.write(
                            "<text text-anchor='right' alignment-baseline='middle' x='{}' y='{}' style='font-size:8px;fill:rgb({},{},{});font-family:Arial;pointer-events: none'>{}%".format(
                                margin * 1.5 + hstep * (4 + j), vstep * (3 + i), *text_color,
                                round(abs(100 * (1 - sum(record[i][x] for x in range(0, j)))), 1)))

                        # These next two animate the colors to change when the user mouses over / off the week label
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='{}_{}.mouseover'/>\n".format(
                                *alt_color, *text_color, i, j))
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='{}_{}.mouseout'/></text>\n".format(
                                *text_color, *alt_color, i, j))

                    # if wins exceeds games played, gray out the box
                    else:
                        # Assign the color code.
                        outfile.write(
                            "fill:rgb({},{},{})'/>\n".format(150, 150, 150))

            outfile.write("</g>\n")

            for i in range(0, rows - 2):
                # by default, leave the game win probability cells uncolored. color them by mouseover.
                r, g, b = Utils.gradient_color(0, 1, win_probs[i], scale=scale, primaryColor=self.primary_color,
                                               secondaryColor=self.secondary_color)

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

                # Should the mouseover text be white or black?
                alt_color = Utils.get_text_contrast_color(r, g, b)

                # Add the probability text in the prob column
                outfile.write(
                    "<text text-anchor='middle' alignment-baseline='central' x='{}' y='{}' style='font-size:11px;fill:rgb({},{},{});font-family:Arial;pointer-events:none'>{}%".format(
                        margin + hstep * 3.5, margin + vstep * (2.5 + i), 0, 0, 0,
                        round(100 * win_probs[i], 1)))

                outfile.write(
                    "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='probColHitBox.mouseover'/>\n".format(
                        *alt_color, 0, 0, 0))
                outfile.write(
                    "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='probColHitBox.mouseout'/></text>\n".format(
                        0, 0, 0, *alt_color))

                for j in range(0, len(record) + 1):
                    if i == 0:
                        # Add the column label
                        outfile.write(
                            "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}' style='font-size:12px;font-family:Arial'>{}{}".format(
                                margin + hstep * (4.5 + j), margin + vstep * 1.5, j, "</text>\n"))

            # add the horizontal lines between the rows
            for i in range(2, rows):

                outfile.write(
                    "<line x1='{}' y1='{}' x2='{}' y2='{}' style='stroke:rgb(0,0,0)'/>\n".format(
                        margin, margin + vstep * i, margin + hstep * cols, vstep * i + margin))
                for j in range(1, cols):
                    # add the vertical lines between the columns
                    outfile.write(
                        "<line x1='{}' y1='{}' x2='{}' y2='{}' style='stroke:rgb(0,0,0)'/>\n".format(
                            margin + hstep * j, margin + vstep, margin + hstep * j, vstep * rows + margin))

            # Add the home / away data
            for i in range(0, rows - 2):
                outfile.write(
                    "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}' style='font-size:12px;font-family:Arial'>{}{}".format(
                        margin + hstep * 1.5, margin + vstep * (2.5 + i),
                        self.schedule[self.name]['schedule'][i]['home-away'],
                        "</text>\n"))

                # Add the opponent logo
                try:
                    opponent = self.schedule[self.name]['schedule'][i]['opponent']
                    outfile.write(
                        "<image x='{}' y='{}' height='{}px' width='{}px' xlink:href='data:image/jpg;base64,{}'>\n<title>{}</title></image>\n".format(
                            2 * hstep + margin + (hstep - logowidth) / 2,
                            vstep * (2 + i) + margin + (vstep - logoheight) / 2, logowidth, logoheight,
                            self.schedule[opponent]['logoURI'], opponent.title()))
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

            outfile.write("</svg>")
        #Utils.convert_to_png(path, method, scale)
