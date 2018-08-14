import os

from team import Team
from utils import Utils


class Cluster:
    # A cluster is just a group of teams, not necessarily any particular conference or division
    def __init__(self, schedule, teams):
        self.teams = {Team(name=x, schedule=schedule) for x in schedule if x in teams}

    def make_standings_projection_graph(self, file='out', week=None, hstep=40, vstep=40, margin=5, logowidth=30,
                                        method='s&p+', logoheight=30, absolute=False, scale='red-green'):
        # get the records for the final week for each team
        record = []

        # make sure the week is valid
        if (not week) or (week < 1) or (week > max([len(x.win_probabilities) for x in self.teams])):
            week = -1

        # sort teams by their weighted average number of wins and division

        record.extend(
            sorted([(x, x.win_totals_by_week(method=method)[1][week]) for x in self.teams],
                   key=lambda y: sum([y[1][z] * z for z in range(len(y[1]))]), reverse=True))

        if not os.path.exists(".\svg output\{} - {}".format(method, scale)):
            os.makedirs(".\svg output\{} - {}".format(method, scale))
        path = os.path.join(".\svg output\{} - {}".format(method, scale),
                            '{} - {} - {}.svg'.format(file, method, scale))

        with open(path, 'w+') as outfile:
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
                "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}'  style='font-size:12px;font-family:Arial'>Total Wins as projected by {}</text>\n".format(
                    margin + hstep * (cols - (cols - 1) / 2), margin + vstep * 0.5, method.upper()))

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
                        record[i][0].logo_URI))

                # Add the rank in the upper left of the logo box
                outfile.write(
                    "<text text-anchor='left' alignment-baseline='top' x='{}' y='{}' style='font-size:8px;font-family:Arial'>{}</text>".format(
                        1.5 * margin, vstep * (3 + i) + margin / 2, i + 1))

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
                        # Draw the color-coded box
                    outfile.write(
                        "<rect id='{}_{}' x='{}' y='{}' width='{}' height='{}' style='".format(
                            i, j, margin + hstep * (1 + j), margin + vstep * (2 + i), hstep, vstep, ))

                    if j < len(record[i][1]):
                        # We need to fill the absolute color code in the box initially and store the relative and absolute color codes
                        # so that we can use them later to animate the chart
                        ra, ga, ba = Utils.gradient_color(lower, upper, record[i][1][j], scale=scale,
                                                          primaryColor=record[i][0].primary_color,
                                                          secondaryColor=record[i][0].secondary_color)
                        r, g, b = Utils.gradient_color(0, 1, record[i][1][j], scale=scale,
                                                       primaryColor=record[i][0].primary_color,
                                                       secondaryColor=record[i][0].secondary_color)

                        if absolute:
                            ra, ga, ba, r, g, b = r, g, b, ra, ga, ba

                        # Assign the color code.
                        outfile.write("fill:rgb({},{},{})'>\n".format(ra, ga, ba))

                        # The first two animate the colors to change when the user mouses over / off the game box
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
                                margin + hstep * (1.5 + j), margin + vstep * (2.5 + i), *text_color,
                                round(100 * record[i][1][j], 1)))

                        # These next two animate the colors to change when the user mouses over / off the week label
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='{}_{}.mouseover'/>\n".format(
                                *alt_color, *text_color, i, j))
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='{}_{}.mouseout'/></text>\n".format(
                                *text_color, *alt_color, i, j))

                        # Add the cumulative probability text
                        # Should the text be white or black?
                        text_color = Utils.get_text_contrast_color(ra, ga, ba)

                        # set the alt color to the opposite of the text color
                        alt_color = Utils.get_text_contrast_color(r, g, b)

                        # Write the probability in the box
                        outfile.write(
                            "<text text-anchor='left' alignment-baseline='bottom' x='{}' y='{}' style='font-size:8px;fill:rgb({},{},{});font-family:Arial;pointer-events: none'>{}%".format(
                                margin * 1.5 + hstep * (1 + j), margin * 0.5 + vstep * (3 + i), *text_color,
                                round(abs(100 * (1 - sum(record[i][1][x] for x in range(0, j)))), 1)))

                        # These next two animate the colors to change when the user mouses over / off the week label
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='{}_{}.mouseover'/>\n".format(
                                *alt_color, *text_color, i, j))
                        outfile.write(
                            "<animate fill='freeze' dur='0.1s' to='rgb({},{},{})' from='rgb({},{},{})' attributeName='fill' begin='{}_{}.mouseout'/></text>\n".format(
                                *text_color, *alt_color, i, j))
                    else:
                        # Assign the color code.
                        outfile.write(
                            "fill:rgb({},{},{})'/>\n".format(150, 150, 150))

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
            # Draw the outline box for the table
            outfile.write(
                "<rect x='{}' y='{}' width='{}' height='{}' style='stroke:rgb(0,0,0);stroke-width:2;fill:none'/>\n".format(
                    margin, margin + vstep, hstep * cols, vstep * (rows - 1)))

            # Draw the outline box for the win total sub-table
            outfile.write(
                "<rect x='{}' y='{}' width='{}' height='{}' style='stroke:rgb(0,0,0);stroke-width:2;fill:none'/>\n".format(
                    margin + hstep, margin + vstep, hstep * (cols - 1), vstep * (rows - 1)))

            # Draw the outline box for the column headers
            outfile.write(
                "<rect x='{}' y='{}' width='{}' height='{}' style='stroke:rgb(0,0,0);stroke-width:2;fill:none'/>".format(
                    margin, margin + vstep, hstep * cols, vstep))

            # Draw the outline box for the win total header label
            outfile.write(
                "<rect x='{}' y='{}' width='{}' height='{}' style='stroke:rgb(0,0,0);stroke-width:2;fill:none'/>".format(
                    margin + hstep, margin, hstep * (cols - 1), vstep))

            outfile.write("</svg>")
        # Utils.convert_to_png(path, method, scale)
