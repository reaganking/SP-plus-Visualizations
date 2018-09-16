class Graph(object):
    def __init__(self, path, width, height, background=(255, 255, 255)):
        self.path = path

        self.content = ["<svg version='1.1'\n\t" +
                        "baseProfile='full'\n\t" +
                        "encoding='UTF-8'\n\t" +
                        "width='{}' height='{}'\n\t".format(width, height) +
                        "xmlns='http://www.w3.org/2000/svg'\n\t" +
                        "xmlns:xlink='http://www.w3.org/1999/xlink'\n\t" +
                        "style='shape-rendering:crispEdges;'>\n",
                        "<rect width='100%' height='100%' style='fill:rgb({},{},{})' />\n".format(*background)]

    def add_image(self, x, y, width, height, uri):
        s = "<image x='{}' y='{}'" \
            " width='{}px' height='{}px'" \
            " xlink:href='data:image/jpg;base64,{}'/>\n".format(x, y, width, height, uri)
        self.content.append(s)

    def add_line(self, x1, y1, x2, y2, color=(0, 0, 0), width=1):
        s = "<line x1='{}' y1='{}' x2='{}' y2='{}' style='".format(x1, y1, x2, y2)
        s += "stroke:rgb({},{},{});".format(*color)
        s += "stroke-width:{};".format(width)
        s += "'/>\n"
        self.content.append(s)

    def add_rect(self, x, y, width, height, color=(0, 0, 0), fill='none', stroke_width=1):
        s = "<rect x='{}' y='{}' width='{}' height='{}' style='stroke-width:{};stroke:".format(x, y, width, height,
                                                                                               stroke_width)
        if isinstance(color, tuple):
            s += "rgb({},{},{});".format(*color)
        else:
            s += color + ";"
        s += "fill:"
        if isinstance(fill, tuple):
            s += "rgb({},{},{});".format(*fill)
        else:
            s += fill + ";"
        s += "'/>\n"

        self.content.append(s)

    def add_text(self, x, y, alignment='baseline', anchor='middle', color=(0, 0, 0), font='Arial', size=12, text='',
                 weight='normal'):
        s = "<text text-anchor='{}'" \
            " alignment-baseline='{}'" \
            " x='{}' y='{}' style='".format(anchor, alignment, x, y, text)
        s += "font-family:{};".format(font)
        s += "fill:rgb({},{},{});".format(*color)
        s += "font-size:{}px;".format(size)
        s += "weight:{}".format(weight)
        s += "'>{}</text>\n".format(text)

        self.content.append(s)

    def write_file(self):
        with open(self.path, 'w+', encoding='utf-8') as outfile:
            for x in self.content:
                outfile.write(x)
            outfile.write("</svg>")
