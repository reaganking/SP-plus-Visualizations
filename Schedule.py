import base64
import csv
import json
import os
import re
import urllib.parse
from colorsys import hls_to_rgb
from datetime import datetime
from subprocess import Popen

import requests
from bs4 import BeautifulSoup as bs

class Schedule(object):
    def __init__(self, file):
        with open(file, 'r') as infile:
            self.data = json.load(infile)

    def clean_team_name(self, name):
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

    def swap_teams(team_a, team_b):
    data = dict(self.data)

    for team in self.data:
        if team == team_a:
            data[team_b] = self.data[team]
        elif team == team_b:
            data[team_a] = self.data[team]

    tmp = sp[team_a]['sp+']
    data[team_b]['sp+'] = sp[team_b]['sp+']
    data[team_a]['sp+'] = tmp

    tmp = self.data[team_a]['logoURI']
    data[team_b]['logoURI'] = self.data[team_b]['logoURI']
    data[team_a]['logoURI'] = tmp

    for team in data:
        for game in range(len(data[team]['schedule'])):
            if data[team]['schedule'][game]['opponent'] == team_a:
                data[team]['schedule'][game]['opponent'] = team_b
            elif data[team]['schedule'][game]['opponent'] == team_b:
                data[team]['schedule'][game]['opponent'] = team_a
            try:
                team_a_spplus = sp[team]['sp+']
            except KeyError:
                team_a_spplus = -10
            try:
                team_b_spplus = sp[data[team]['schedule'][game]['opponent']]['sp+']
            except KeyError:
                team_b_spplus = -10
            loc = data[team]['schedule'][game]['home-away']
            if loc == 'home':
                data[team]['schedule'][game]['sp+'] = [
                    Utils.calculate_win_prob_from_spplus(team_a_spplus, team_b_spplus, 'home')]
            else:
                data[team]['schedule'][game]['sp+'] = [
                    Utils.calculate_win_prob_from_spplus(team_a_spplus, team_b_spplus, 'away')]
