import csv
import json
import re
import time
from datetime import datetime
from random import randint

import requests
from bs4 import BeautifulSoup as bs
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class Poll(object):
    headers = {'User-Agent': 'Mozilla/5.0'}

    def __init__(self, file=None, year=2018, week=1, struct=None):
        if file:
            self.load(file)
            self.year = self.ballots['year']
            self.week = self.ballots['week']
            if self.ballots['date']:
                self.date = self.ballots['date']
            else:
                self.date = None
        elif not struct:
            self.year = year
            self.week = week
            self.date = None
            self.ballots = {'year': self.year, 'week': self.week, 'date': self.date, 'voters': {}}

            if week in range(1, 16):
                self.week = week
            else:
                self.week = 1

    def calculate_ranks(self):
        self.ballots['results'] = {}
        for v in self.ballots['voters']:
            for i in range(len(self.ballots['voters'][v]['rankings'])):
                t = self.ballots['voters'][v]['rankings'][i]
                if t:
                    try:
                        self.ballots['results'][t]['points'] += 25 - i
                    except KeyError:
                        self.ballots['results'][t] = {'points': 25 - i}

        ranks = sorted(self.ballots['results'].items(), key=lambda key: key[1]['points'], reverse=True)
        points = 0
        rank = 1
        for i in range(len(ranks)):
            team = ranks[i][0]
            self.ballots['results'][team]['rank'] = rank
            if points != ranks[i][1]['points']:
                rank += 1
            points = ranks[i][1]['points']

    @staticmethod
    def concatenate_polls(files, out='json'):
        ret = []
        i = 1
        for f in files:
            if out == 'json':
                ret.append(Poll(f).ballots)
            elif out == 'flat':
                header, result = Poll(f).flatten()
                if i == 1:
                    ret.append(header)
                    i += 1
                ret.extend(result)
            else:
                ret.append(Poll(f).ballots)

        return ret

    def flatten(self):
        out = []
        self.calculate_ranks()
        header = ['date', 'year', 'week', 'voter', 'outlet', 'rank', 'team', 'overall rank']

        for v in self.ballots['voters']:
            i = 1  # keep track of ranking position
            o = self.ballots['voters'][v]['outlet']

            for t in self.ballots['voters'][v]['rankings']:
                overall_rank = self.ballots['results'][t]['rank']
                out.append([self.ballots['date'], self.ballots['year'], self.ballots['week'], v, o, i, t, overall_rank])
                i += 1
        return header, out

    def flat_csv(self, file=None):
        header, result = self.flatten()
        with open(file, 'w+', newline='') as outfile:
            csvwriter = csv.writer(outfile)
            csvwriter.writerow(header)
            for row in result:
                csvwriter.writerow(row)

    def json_out(self, file=None):
        with open(file, 'w+') as outfile:
            json.dump(self.ballots, outfile, indent=4, sort_keys=True)

    def load(self, file=None):
        try:
            with open(file, 'r') as file:
                self.ballots = json.load(file)
        except ValueError as e:
            print('Invalid json file: {} at {}'.format(file, e))
            return None

    def scrape(self, url=None, retries=10):
        # Local solution to retrying after timeout or errors
        def requests_retry_session(retries=retries, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None):
            session = session or requests.Session()
            retry = Retry(
                total=retries,
                read=retries,
                connect=retries,
                backoff_factor=backoff_factor,
                status_forcelist=status_forcelist,
            )
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            return session

        return requests_retry_session().get(url)

    def table_csv(self, file=None, transpose=False):
        with open(file, 'w+', newline='') as outfile:
            csvwriter = csv.writer(outfile)
            if not transpose:
                csvwriter.writerow([''] + [x for x in self.ballots['voters']])
                csvwriter.writerow(['Rank'] + [self.ballots['voters'][x]['outlet'] for x in self.ballots['voters']])
                for i in range(0, 25):
                    row = [i + 1]
                    for voter in self.ballots['voters']:
                        row.append(self.ballots['voters'][voter]['rankings'][i])
                    csvwriter.writerow(row)
            else:
                csvwriter.writerow(['Voter', 'Outlet'] + [x + 1 for x in range(0, 25)])
                for voter in self.ballots['voters']:
                    csvwriter.writerow(
                        [voter] + [self.ballots['voters'][voter]['outlet']] + self.ballots['voters'][voter]['rankings'])


class APPoll(Poll):
    def __init__(self, year=2018, week=1):
        super().__init__(year=year, week=week)

    def flat_csv(self, file=None):
        if not file:
            file = ' '.join(['Flat', str(self.year), 'Week', str(self.week), 'AP Poll.csv'])
        super().flat_csv(file)

    def json_out(self, file=None):
        if not file:
            file = ' '.join([str(self.year), 'Week', str(self.week), 'AP Poll.json'])

        super().json_out(file)

    def scrape(self, url='https://collegefootball.ap.org/poll', status=False, full=True):
        start_time = time.monotonic()

        # the AP records all 2018 seasons as "2019"
        year = self.year
        if year == datetime.now().year:
            year += 1

        url = '/'.join([url, str(year), str(self.week)])

        r = super().scrape(url=url)

        # record the publishing date
        date = bs(r.text, features='html.parser').find('div', {'id': 'poll-released'}).text.split(' ')[-2:]
        self.date = datetime.strptime(' '.join(date), '%b %d')
        if self.date.month < 8:
            self.date = self.date.replace(year=year)
        else:
            self.date = self.date.replace(year=self.year)
        self.ballots['date'] = self.date.strftime('%A %x').replace('/', '-')

        # Find the voter menu
        links = bs(r.text, features='html.parser').find('div', {'class': 'voter-menu filter-menu clearfix'})

        # get the links
        links = links.findAll({'a': 'href'})

        # extract the urls and add the root prefix
        voters = {x.contents[0]: 'https://collegefootball.ap.org/' + x['href'] + '/{}/{}'.format(year, self.week)
                  for x in links}

        self.ballots['voters'] = {}

        for v in voters:
            time.sleep(randint(1, 100) / 100)
            r = super().scrape(voters[v])

            soup = bs(r.text, features='html.parser')
            skip = soup.find('p', {'class': 'no-poll-found'})
            if not skip:
                try:
                    outlet = soup.find('div', {'class': 'voter-pub'}).text

                    # Find the ballot table
                    table = soup.find('table')

                    # get the rows
                    rows = table.findAll('tr', {'class': re.compile('[0-9]*')})

                    # Make a length 25 list
                    self.ballots['voters'][v] = {'outlet': outlet, 'rankings': ['' for x in range(0, 25)]}

                    for row in rows:
                        rank = int(row.contents[0].text)
                        team = row.contents[1].text
                        team = re.sub(r'\([^)]*\)', '', team).strip()
                        self.ballots['voters'][v]['rankings'][rank - 1] = team
                except AttributeError:
                    self.ballots['voters'][v] = {'outlet': None, 'rankings': [None for x in range(0, 25)]}
            else:
                self.ballots['voters'][v] = {'outlet': None, 'rankings': [None for x in range(0, 25)]}

        self.calculate_ranks()
        if status:
            print("{} Week {} Complete!".format(self.year, self.week), end='\n')
            print("Elapsed time: {} seconds".format(round(time.monotonic() - start_time, 3)), end='\n')

    def table_csv(self, file=None, transpose=False):
        if not file:
            if transpose:
                file = ' '.join([str(self.year), 'Week', str(self.week), 'AP Poll Transposed.csv'])
            else:
                file = ' '.join([str(self.year), 'Week', str(self.week), 'AP Poll.csv'])
        super().table_csv(file=file, transpose=transpose)


class CoachesPoll(Poll):
    def flat_csv(self, file=None):
        if not file:
            file = ' '.join(['Flat', str(self.year), 'Week', str(self.week), 'Coaches Poll.csv'])

        super().flat_csv(file)

    def json_out(self, file=None):
        if not file:
            file = ' '.join([str(self.year), 'Week', str(self.week), 'Coaches Poll.json'])

        super().json_out(file)

    def scrape(self, url='https://www.usatoday.com/sports/ncaaf/ballots/', status=False):
        start_time = time.monotonic()

        r = super().scrape(url='/'.join([url, 'coaches', self.year.__str__(), '%02d'.format(self.week.__str__())]))

        page = bs(r.text, features='html.parser')

        # Get the published date
        date = page.find('span', {'class': 'ncaaf-ballots'}).text.split()[-1][:-1]
        self.date = datetime.strptime(date, '%Y-%m-%d')
        self.ballots['date'] = self.date.strftime('%A %x').replace('/', '-')

        # Get the list of coaches
        for x in page.findAll('tr', {'class': 'ballot-key'}):
            self.ballots['voters'][x.contents[0].text.strip()] = {
                'outlet': x.find('td', {'class': 'team_name'}).contents[0].strip(), 'rankings': []}

        # Find the team names
        names = page.findAll('span', {'class': 'first_name'})
        teams = {
            x.text: '/'.join(
                [url, 'schools', self.year.__str__(), self.week.__str__(), '-'.join(x.text.split()).lower()]) for x in
            names}

        for team in teams:
            r = super().scrape(teams[team])

            # Find the ballot table
            rows = bs(r.text, features='html.parser').findAll('tr',
                                                              {'class': re.compile(r'ballot-ranking-row*')})

            # The structure of these data are to give us the team, then who voted for them. We'll work backwards.
            for row in rows:
                coach = row.contents[1].text.strip()
                rank = int(row.contents[5].text.strip())
                self.ballots['voters'][coach]['rankings'].append([team, rank])

        for v in self.ballots['voters']:
            l = ['' for x in range(0, 25)]
            for x in sorted(self.ballots['voters'][v]['rankings'], key=lambda x: x[1]):
                l[x[1] - 1] = x[0]
            self.ballots['voters'][v]['rankings'] = l

        if status:
            print("{} Week {} Complete!".format(self.year, self.week), end='\n')
            print("Elapsed time: {} seconds".format(round(time.monotonic() - start_time, 3)), end='\n')

    def table_csv(self, file=None, transpose=False):
        if not file:
            if transpose:
                file = ' '.join([str(self.year), 'Week', str(self.week), 'Coaches Poll Transposed.csv'])
            else:
                file = ' '.join([str(self.year), 'Week', str(self.week), 'Coaches Poll.csv'])
        super().table_csv(file=file, transpose=transpose)


class RCFBPoll(Poll):
    def __init__(self, file, year=2018, week=1, date=None):
        with open(file, 'r') as infile:
            reader = csv.reader(infile)
            i = 0
            self.year = year
            self.week = week
            self.date = None
            if week in range(1, 16):
                self.week = week
            else:
                self.week = 1
            self.ballots = {'year': self.year, 'week': self.week, 'date': date, 'voters': {}}
            ranks = []
            for row in reader:
                if i == 0:
                    for v in row[1:]:
                        ranks.append([v])
                elif i == 1:
                    pass
                else:
                    j = 0
                    for t in row[1:]:
                        ranks[j].append(t)
                        j += 1
                i += 1
            for i in range(len(ranks)):
                self.ballots['voters'][ranks[i][0]] = {'outlet': None, 'rankings': ranks[i][1:]}

        super().__init__(struct=True)

    def flat_csv(self, file=None):
        if not file:
            file = ' '.join(['Flat', str(self.year), 'Week', str(self.week), 'r-cfb Poll.csv'])
        super().flat_csv(file)

    def json_out(self, file=None):
        if not file:
            file = ' '.join([str(self.year), 'Week', str(self.week), 'AP Poll.json'])

        super().json_out(file)

    def table_csv(self, file=None, transpose=False):
        if not file:
            if transpose:
                file = ' '.join([str(self.year), 'Week', str(self.week), 'AP Poll Transposed.csv'])
            else:
                file = ' '.join([str(self.year), 'Week', str(self.week), 'AP Poll.csv'])
        super().table_csv(file=file, transpose=transpose)

