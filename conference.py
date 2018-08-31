import os

from team import Team
from utils import Utils


class Conference:
    def __init__(self, name, schedule):
        self.name = name
        self.teams = {Team(name=x, schedule=schedule) for x in schedule if schedule[x]['conference'] == name}
        self.divisions = {}
        for team in self.teams:
            if team.division not in self.divisions:
                self.divisions[team.division] = []
            self.divisions[team.division].append(team)

        if len(self.divisions) == 0:
            self.divisions['all'] = self.teams

    def get_record_array(self, week=None):
        # get the records for the final week for each team
        record = []

        # make sure the week is valid
        if (not week) or (week < 1) or (week > max([len(x.win_probabilities[week]) for x in self.teams])):
            week = -1
            prior_week = week
        else:
            prior_week = week - 1

        for t in self.teams:
            record.append([t, t.project_win_totals(week=week)[-1], t.project_win_totals(week=prior_week)[-1]])

        # sort teams by their weighted average number of wins and division
        record.sort(key=lambda x: (x[0].division, sum([x[1][z] * z for z in range(len(x[1]))])), reverse=True)

        return record

    def make_standings_projection_graph(self, file='out', week=None, hstep=50, vstep=50, margin=5, logowidth=40,
                                        method='sp+', logoheight=40, absolute=False,
                                        scale='red-green', old=None):

        # get the records for the final week for each team
        record = self.get_record_array(week=week)
        if not os.path.exists(".\svg output\{} - {}".format(method, scale)):
            os.makedirs(".\svg output\{} - {}".format(method, scale))
        path = os.path.join(".\svg output\{} - {}".format(method, scale),
                            '{} - {} - {}.svg'.format(file, method, scale))
        with open(path, 'w+', encoding='utf-8') as outfile:
            if not old:
                rows, cols = len(record) + 2, max([len(x[1]) for x in record]) + 1
            else:
                rows, cols = len(record) + 2, max([len(x[1]) for x in record]) + 2

            # Write the SVG header; remember to write </svg> to close the file
            outfile.write(
                "<svg version='1.1'\n\tbaseProfile='full'\n\tencoding='UTF-8'\n\twidth='{}' height='{}'\n\txmlns='http://www.w3.org/2000/svg'\n\txmlns:xlink='http://www.w3.org/1999/xlink'\n\tstyle='shape-rendering:crispEdges;'>\n".format(
                    hstep * cols + 2 * margin, vstep * rows + 2 * margin))

            # Fill the background with white
            outfile.write("<rect width='100%' height='100%' style='fill:rgb(255,255,255)' />")

            # Add the horizontal header label; it is at the very top of the svg and covers all but the first column, with centered text
            outfile.write(
                "<text text-anchor='middle' alignment-baseline='baseline' x='{}' y='{}'  style='font-size:13px;font-family:Arial'>Total Wins as projected by {}</text>\n".format(
                    margin + hstep * (cols - (cols - 1) / 2), margin + vstep * 0.5 - 3, method.upper()))
            if not week or week == 0:
                first_week, second_week = 0, 0
            else:
                first_week = week - 1
                second_week = week

            outfile.write(
                "<text text-anchor='middle' alignment-baseline='hanging' x='{}' y='{}'  style='font-size:13px;font-family:Arial'>(change from week {} to week {})</text>\n".format(
                    margin + hstep * (cols - (cols - 1) / 2), margin + vstep * 0.5 + 3, first_week, second_week))

            # Add column labels for the Team Name
            outfile.write(
                "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}'  style='font-size:13px;font-family:Arial'>Team</text>\n".format(
                    margin + hstep * 0.5, margin + vstep * 1.5))

            # This set of loops fills in the body of the table
            for i in range(0, rows - 2):
                # Add the team logo
                outfile.write(
                    "<image x='{}' y='{}' height='{}px' width='{}px' xlink:href='data:image/jpg;base64,{}'/>".format(
                        margin + (hstep - logowidth) / 2,
                        vstep * (2 + i) + margin + (vstep - logoheight) / 2, logowidth, logoheight,
                        record[i][0].logo_URI))

                # find the max and min in this week to determine color of cell
                if absolute:
                    upper, lower = 1, 0
                else:
                    upper, lower = max(record[i][1]), min(record[i][1])

                for j in range(0, cols - 1):
                    if i == 0:
                        if not old:
                            if j != 1:
                                txt = 'Wins'
                            else:
                                txt = 'Win'
                            # Add the column label
                            outfile.write(
                                "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}' style='font-size:13px;font-family:Arial'>{} {}</text>\n".format(
                                    margin + hstep * (1.5 + j), margin + vstep * 1.5, j, txt))
                        else:
                            if j == cols - 2:
                                if old:
                                    # Add the column label
                                    outfile.write(
                                        "<text text-anchor='middle' alignment-baseline='baseline' x='{}' y='{}' style='font-size:10px;font-family:Arial'>Expected</text>\n".format(
                                            margin + hstep * (1.5 + j), margin + vstep * 1.5 - 8))
                                    outfile.write(
                                        "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}' style='font-size:10px;font-family:Arial'>Wins</text>\n".format(
                                            margin + hstep * (1.5 + j), margin + vstep * 1.5))
                                    outfile.write(
                                        "<text text-anchor='middle' alignment-baseline='hanging' x='{}' y='{}' style='font-size:10px;font-family:Arial'>(Change)</text>\n".format(
                                            margin + hstep * (1.5 + j), margin + vstep * 1.5 + 6))
                            else:
                                if j != 1:
                                    txt = 'Wins'
                                else:
                                    txt = 'Win'
                                # Add the column label
                                outfile.write(
                                    "<text text-anchor='middle' alignment-baseline='middle' x='{}' y='{}' style='font-size:13px;font-family:Arial'>{} {}</text>\n".format(
                                        margin + hstep * (1.5 + j), margin + vstep * 1.5, j, txt))
                    if j < len(record[i][1]):
                        if absolute:
                            r, g, b = Utils.gradient_color(0, 1, record[i][1][j], scale=scale,
                                                           primaryColor=record[i][0].primary_color,
                                                           secondaryColor=record[i][0].secondary_color)
                        else:
                            r, g, b = Utils.gradient_color(lower, upper, record[i][1][j], scale=scale,
                                                           primaryColor=record[i][0].primary_color,
                                                           secondaryColor=record[i][0].secondary_color)

                        # Draw the color-coded box
                        outfile.write(
                            "<rect id='{}_{}' x='{}' y='{}' width='{}' height='{}' style='fill:rgb({},{},{})'/>\n".format(
                                i, j, margin + hstep * (1 + j), margin + vstep * (2 + i), hstep, vstep, r, g, b))

                        # Should the text be white or black?
                        text_color = Utils.get_text_contrast_color(r, g, b)

                        # Write the probability in the box
                        outfile.write(
                            "<text text-anchor='middle' alignment-baseline='baseline' x='{}' y='{}' style='font-size:12px;fill:rgb({},{},{});font-family:Arial;pointer-events: none'>{}%</text>".format(
                                margin + hstep * (1.5 + j), margin + vstep * (2.5 + i) - 2, *text_color,
                                round(100 * record[i][1][j], 1)))

                        # Add the cumulative probability text
                        outfile.write(
                            "<text text-anchor='end' alignment-baseline='baseline' x='{}' y='{}' style='font-size:8px;fill:rgb({},{},{});font-family:Arial;pointer-events: none'>{}%</text>".format(
                                margin * 0.8 + hstep * (2 + j), margin * 0.5 + vstep * (3 + i), *text_color,
                                round(abs(100 * (1 - sum(record[i][1][x] for x in range(0, j)))), 1)))
                        if old:
                            diff = round(100 * (record[i][2][j] - record[i][1][j]), 1)
                            if diff > 0:
                                txt = '+{}'.format(diff)
                            elif diff == 0:
                                txt = '+0.0'
                            else:
                                txt = str(diff)

                            # Write the probability change in the box
                            outfile.write(
                                "<text text-anchor='middle' alignment-baseline='hanging' x='{}' y='{}' style='font-size:12px;fill:rgb({},{},{});font-family:Arial;pointer-events: none'>({}%)</text>\n".format(
                                    margin + hstep * (1.5 + j), margin + vstep * (2.5 + i) + 2, *text_color,
                                    txt))
                    elif old:
                        old_xw = sum(x * record[i][2][x] for x in range(len(record[i][2])))
                        new_xw = sum(x * record[i][1][x] for x in range(len(record[i][1])))
                        diff = round(new_xw - old_xw, 1)
                        if diff > 0:
                            txt = '+{}'.format(diff)
                            r, g, b = 0, 205, 0
                            weight = 'bolder'
                        elif diff == 0:
                            txt = '+0.0'
                            r, g, b = 0, 0, 0
                            weight = 'normal'
                        else:
                            txt = str(diff)
                            r, g, b = 255, 77, 77
                            weight = 'bolder'

                        outfile.write(
                            "<text text-anchor='middle' alignment-baseline='baseline ' x='{}' y='{}' style='font-size:13px;fill:rgb(0,0,0);font-family:Arial;pointer-events: none'>{}</text>".format(
                                margin + hstep * (1.5 + j), margin + vstep * (2.5 + i) - 3, round(new_xw, 1)))

                        # How did the win expectation change?
                        outfile.write(
                            "<text text-anchor='middle' alignment-baseline='hanging ' x='{}' y='{}' style='font-weight:{};font-size:13px;fill:rgb({},{},{});font-family:Arial;pointer-events: none'>({})</text>".format(
                                margin + hstep * (1.5 + j), margin + vstep * (2.5 + i) + 3, weight, r, g, b, txt))

                    else:
                        # Draw a gray box
                        outfile.write(
                            "<rect id='{}_{}' x='{}' y='{}' width='{}' height='{}' style='fill:rgb({},{},{})'/>\n".format(
                                i, j, margin + hstep * (1 + j), margin + vstep * (2 + i), hstep, vstep, 150, 150, 150))

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
