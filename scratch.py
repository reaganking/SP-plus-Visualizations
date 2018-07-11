from colorsys import hls_to_rgb
import csv


class Team:
    def __init__(self):
        self.win_probabilities = []

    def win_totals_by_week(self):
        # Make a ragged table to store 'games' x 'wins'
        record = [[0 for y in range(0, x + 1)] for x in range(1, len(self.win_probabilities) + 1)]

        record[0][0] = 1 - self.win_probabilities[0]  # first game was a loss
        record[0][1] = self.win_probabilities[0]  # first game was a win

        for i in range(1, len(record)):
            for j in range(0, i + 1):
                record[i][j] += record[i - 1][j] * (1 - self.win_probabilities[i])  # newest game was a loss
                record[i][j + 1] += record[i - 1][j] * (self.win_probabilities[i])  # newest game was a win

        return record

    def set_win_probabilities(self, vector):
        assert isinstance(vector, (list, set, tuple)), "Vector is not a list, set, or tuple!"
        self.win_probabilities = vector

    def write_win_probability_csv(self, file='out'):
        record = self.win_totals_by_week()
        with open("{}.csv".format(file), 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerows(record)

    @staticmethod
    def gradient_color(lower, upper, val):
        # Perform linear interpolation on the hue between 0.33 and 0, then convert back to RGB
        # HLS 0.33, 0.65, 1.0 will give green
        # HLS 0, 0.65, 1.0 will give red
        if upper == lower:
            h = 120
        else:
            h = 120 * (val - lower) / (upper - lower)

        return [255 * x for x in hls_to_rgb(h / 360.0, 0.65, 1)]

    def make_win_probability_graph(self, file='out'):
        record = self.win_totals_by_week()

        with open('{}.svg'.format(file), 'w+') as outfile:
            # The SVG output should generally be divided into 3 leading columns (week, H/A, Opp, Prob) and n = len(self.win_probabilities) + 1 segments
            # and 2 leading rows (Wins and headers) with n = len(self.win_probabilities) vertical segments.
            hstep, vstep = 40, 40
            rows, cols = 2 + len(self.win_probabilities), 4 + len(self.win_probabilities) + 1

            # Write the SVG header; remember to write </svg> to close the file
            outfile.write(
                "<svg version=\"1.1\"\n\tbaseProfile=\"full\"\n\twidth=\"{}\" height=\"{}\"\n\txmlns=\"http://www.w3.org/2000/svg\">\n".format(
                    hstep * cols, vstep * rows))

            # Fill the background with white
            outfile.write("<rect width = \"100%\" height=\"100%\" style=\"fill:rgb(255,255,255)\" />")

            # Add the horizontal header label; it is at the very top of the svg and covers the right 16 columns, with centered text
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:12px;font-family:Arial\">Wins</text>\n".format(
                    hstep * (cols - (cols - 4) / 2), vstep * 0.5))

            # Add column labels for the H/A and Opp
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:12px;font-family:Arial\">Week</text>\n".format(
                    hstep * 0.5, vstep * 1.5))
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:12px;font-family:Arial\">H/A</text>\n".format(
                    hstep * 1.5, vstep * 1.5))
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:12px;font-family:Arial\">Opp</text>\n".format(
                    hstep * 2.5, vstep * 1.5))
            outfile.write(
                "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:12px;font-family:Arial\">WinProb</text>\n".format(
                    hstep * 3.5, vstep * 1.5))

            for i in range(0, rows - 2):
                # Add the row week label
                outfile.write(
                    "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\" style=\"font-size:12px;font-family:Arial\">{}{}".format(
                        hstep * 0.5, vstep * (2.5 + i), i + 1, "</text>\n"))

                # Add the color-coded box in the prob column with its text
                r, g, b = self.gradient_color(0, 1, self.win_probabilities[i])
                outfile.write(
                    "<rect x = \"{}\" y = \"{}\" width = \"{}\" height = \"{}\" style = \"fill:rgb({},{},{})\"/>".format(
                        hstep * 3, vstep * (2 + i), hstep, vstep,
                        r, g, b))
                outfile.write(
                    "<text text-anchor=\"middle\" alignment-baseline=\"central\" x=\"{}\" y=\"{}\" style=\"font-size:11px;font-family:Arial\">{}%{}".format(
                        hstep * 3.5, vstep * (2.5 + i), round(100 * self.win_probabilities[i], 1), "</text>\n"))

                # find the max and min in this week to determine color of cell
                upper, lower = max(record[i]), min(record[i])
                for j in range(0, len(record) + 1):
                    if i == 0:
                        # Add the column label
                        outfile.write(
                            "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\" style=\"font-size:12px;font-family:Arial\">{}{}".format(
                                hstep * (4.5 + j), vstep * 1.5, j, "</text>\n"))

                    if j < len(record[i]):
                        r, g, b = self.gradient_color(lower, upper, record[i][j])
                    else:
                        r, g, b = 150, 150, 150
                    # Draw the color-coded box
                    outfile.write(
                        "<rect x = \"{}\" y = \"{}\" width = \"{}\" height = \"{}\" style = \"fill:rgb({},{},{})\"/>".format(
                            hstep * (4 + j), vstep * (2 + i), hstep, vstep, r, g, b))
                    if j < len(record[i]):
                        # Write the probability in the box
                        outfile.write(
                            "<text text-anchor=\"middle\" alignment-baseline=\"middle\" x=\"{}\" y=\"{}\"  style=\"font-size:11px;font-family:Arial\">{}%{}".format(
                                hstep * (4.5 + j), vstep * (2.5 + i), round(100 * record[i][j], 1), "</text>\n"))

            outfile.write("</svg>")


# Conference Win Probabilities

# Teams are alphabetical:

bigten = [  # Week 1
    [
        [.24, .31, .37, .24, .17, .7, .32, .34, .5],    # Illinois
        [.44, .64, .14, .22, .47, .06, .19, .53, .56],  # Indiana
        [.76, .56, .75, .59, .67, .57, .19, .54, .32],  # Iowa
        [.69, .36, .25, .1, .16, .5, .06, .08, .59],    # Maryland
        [.86, .90, .45, .86, .71, .26, .51, .86, .57],  # Michigan
        [.78, .84, .55, .78, .79, .35, .39, .84, .91],  # Michigan St
        [.63, .53, .41, .5, .42, .43, .05, .5, .13],    # Minnesota
        [.76, .33, .14, .22, .58, .34, .06, .53, .14],  # Nebraska
        [.83, .43, .29, .21, .57, .66, .52, .66, .31],  # Northwestern
        [.94, .94, .74, .65, .95, .94, .60, .89, .97],  # Ohio St
        [.93, .81, .81, .92, .49, .61, .40, .89, .61],  # Penn St
        [.68, .47, .46, .16, .50, .47, .48, .11, .24],  # Purdue
        [.66, .44, .41, .14, .9, .34, .03, .11, .91],   # Rutgers
        [.95, .68, .43, .87, .86, .69, .39, .76, .09]   # Wisconsin
    ]
]
# Teams are alphabetical; dimensions are week, team, win total
acc = [  # Week 1
    [
        [],  # Boston College
        [],  # Clemson
        [],  # Duke
        [],  # Florida State
        [],  # Georgia Tech
        [],  # Louisville
        [],  # Miami
        [0.54, 0.18, 0.38, 0.54, 0.55, 0.56, 0.40, 0.48],  # North Carolina
        [],  # North Carolina St
        [],  # Pitt
        [0.27, 0.05, 0.33, 0.46, 0.38, 0.27, 0.34, 0.34],  # Syracuse
        [],  # Virginia
        [],  # Virginia Tech
        []  # Wake Forest
    ]
]

wins = [.52, .99, .27, .83, .05, .33, .46, .38, .27, .34, .10, .34]
foo = Team()
foo.set_win_probabilities(wins)
foo.make_win_probability_graph()
foo.write_win_probability_csv()
