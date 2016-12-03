"""
Package to facilitate API calls to the Yahoo Fantasy Sports API.
Required packages:
- xmltodict

TODO:
- matching algo: make better assignment of injuries
- comment new separation of team and api
- Make it more robust
- Parameter checking
- Make yahoo_auth part of the package and call it locally
"""
from __future__ import absolute_import

from .yahoo_oauth import OAuth2
from xmltodict import parse
import time
from datetime import datetime, date, timedelta
from collections import Counter, namedtuple, OrderedDict

try:
    from multiprocessing.pool import ThreadPool
    threads = True
except ImportError:
    threads = False


class FantasyAPI:
    """ Instantiation of the API communication and retrieve basic fantasy team info
    Attributes:
    - filepath: path to the json file containing the credentials as outline in the
                yahoo_oauth package.
    - game_key: Yahoo's key for the sport/year (should only use nhl for now).
                For current year teams, can use `nhl'
    """

    def __init__(self, filepath, game_key='nhl'):
        self.oauth = OAuth2(None, None, from_file=filepath)
        self.game_key = game_key
        # self._get_league_info()
        self._get_info()

    def get(self, url):
        """ Retrieves API info and parses it.
        Returns: [dict] parsed data
        TODO: Error handling
        """
        base_url = 'https://fantasysports.yahooapis.com/fantasy/v2/'
        r = self.oauth.session.get(base_url + url)
        r.raise_for_status()
        return parse(r.text)['fantasy_content']

    def raw_get(self, url):
        """ Retrieves API info and parses it.
        Returns: [dict] parsed data
        TODO: Error handling
        """
        return self.oauth.session.get(url)

    def _get_info(self):
        """ Retrieves current user teams' name and team_key.
        Set the attribute team: OrderedDict(name:team_key)

        """
        BasicTeam = namedtuple('BasicTeam', ['league_name', 'league_key',
                                             'team_name', 'team_key'])
        url1 = 'users;use_login=1/games;game_keys={}/teams'.format(self.game_key)
        d_team = self.get(url1)['users']['user']['games']['game']
        url2 = 'users;use_login=1/games;game_keys={}/leagues'.format(self.game_key)
        d_league = self.get(url2)['users']['user']['games']['game']
        self.teams = []
        number_teams = int(d_team['teams']['@count'])
        number_leagues = int(d_league['leagues']['@count'])

        if number_teams != number_leagues:
            raise NotImplemented('Number of teams not equal to the number of leagues')

        if number_teams == 1:
            self.teams = [
                BasicTeam(league_name=d_league['leagues']['league']['name'],
                          league_key=d_league['leagues']['league']['league_key'],
                          team_name=d_team['teams']['team']['name'],
                          team_key=d_team['teams']['team']['team_key'])
            ]
        elif number_teams > 1:
            for league, team in zip(d_league['leagues']['league'],
                                    d_team['teams']['team']):
                self.teams.append(BasicTeam(league_name=league['name'],
                                            league_key=league['league_key'],
                                            team_name=team['name'],
                                            team_key=team['team_key']))
        else:
            raise ValueError('User does not contain any team for the specified game')

    def get_team(self, team_key, get_rank=False):
        return Team(team_key, self, get_rank)

    def get_league(self, league_key, child=None):
        return League(league_key, self, child)


class League:
    """
    League class. Contains methods with actions that are league-specific
    but not team-specific
    """

    def __init__(self, league_key, parent, child=None):
        self.parent = parent
        self.team = child
        self.get = parent.get
        self.league_key = league_key
        self._get_league_settings()

    def _get_league_settings(self):
        settings = self.get('league/{}/settings'.format(self.league_key))
        self.league_type = settings['league']['scoring_type']
        self.name = settings['league']['name']
        roster_list = (settings['league']['settings']['roster_positions']
                               ['roster_position'])
        self.roster_positions = [x['position'] for x in roster_list
                                 for n in range(int(x['count']))]
        self.stats = OrderedDict()
        for s in settings['league']['settings']['stat_categories']['stats']['stat']:
            self.stats[s['stat_id']] = (s['display_name'],
                                        s.get('is_only_display_stat', 0) != '1')

    def get_standings(self):
        """ Get fantasy standing data

        Information returned is:
        - team_name
        - fantasy owner
        - rank
        - total points
        - points change from yesterday

        TODO: Adjust rankings for H2H and Rotisserie
        """
        url = 'league/{}/standings'.format(self.league_key)
        r = self.get(url)
        out = []
        for x in r['league']['standings']['teams']['team']:
            team = OrderedDict()
            team['rank'] = int(x['team_standings']['rank'])
            team['team_name'] = x['name']
            if self.league_type == 'head':
                team['records'] = (int(x['team_standings']['outcome_totals']['wins']),
                                   int(x['team_standings']['outcome_totals']['losses']),
                                   int(x['team_standings']['outcome_totals']['ties']))
            team['totals'] = float(x['team_points']['total'])
            for s in x['team_stats']['stats']['stat']:
                stat_key = self.stats[s['stat_id']]
                if stat_key[1]:
                    try:
                        team[stat_key[0]] = int(s['value'])
                    except ValueError:
                        team[stat_key[0]] = float(s['value'])

            if self.league_type == 'roto':
                team['points_change'] = x['team_standings'].get('points_change', 'N/A')
            team['owner'] = x['managers']['manager']['nickname']

            out.append(team)

        return out

    def get_scoreboard(self):
        """

        :return:
        """
        url = 'league/{}/scoreboard'.format(self.league_key)
        r = self.get(url)
        matchups = []
        for x in r['league']['scoreboard']['matchups']['matchup']:
            own = False
            matchup = []
            for team in x['teams']['team']:
                team_stat = OrderedDict()
                team_stat['team'] = team['name']
                if team['name'] == self.team.name:
                    own = True
                team_stat['total'] = team['team_points']['total']
                for s in team['team_stats']['stats']['stat']:
                    stat_key = self.stats[s['stat_id']]
                    if stat_key[1]:
                        try:
                            team_stat[stat_key[0]] = int(s['value'])
                        except ValueError:
                            team_stat[stat_key[0]] = float(s['value'])
                matchup.append(team_stat)
            if own:
                matchups.insert(0, matchup)
            else:
                matchups.append(matchup)

        return matchups

    def get_transactions(self):
        """ Get transactions that occurred in the past day.
        Maximum number of transactions per call is 30
        Returns a list of dictionary suitable to create a DataFrame. """
        url = 'league/{}/transactions;count=30'.format(self.league_key)
        data = self.get(url)
        res = []
        yesterday = date.today() - timedelta(days=1)
        for tr in data['league']['transactions']['transaction']:
            ts = datetime.fromtimestamp(int(tr['timestamp']))
            if ts.date() >= yesterday:
                player_list = tr.get('players', dict()).get('player', [])
                if int(tr.get('players', dict()).get('@count', 0)) == 1:
                    player_list = [player_list]
                for player in player_list:
                    out = dict()
                    out['transaction_id'] = tr['transaction_id']
                    out['timestamp'] = ts
                    out['type'] = player['transaction_data']['type']
                    out['source_type'] = player['transaction_data']['source_type']
                    out['source_team'] = player['transaction_data'].get(
                        'source_team_name', 'N/A')
                    out['destination_type'] = (player['transaction_data']
                                               ['destination_type'])
                    out['destination_team'] = player['transaction_data'].get(
                        'destination_team_name', 'N/A')
                    out['player_name'] = player['name']['full']
                    res.append(out)
        return res

    def __repr__(self):
        return '<League: {} - {}>'.format(self.name, self.league_type)


class Team:
    """ Team class with many methods to get league or team information change the roster
    - get_rank: bool to know whether to retrieve players' rank information
    - team_key: Yahoo's key for the fantasy team
    - league_key: Yahoo's key for the fantasy league
    - num_players: number of players on the fantasy team
    - players: list of Player objects
    - data: player raw data in dict form
    """

    def __init__(self, team_key, parent=None, get_rank=False):
        self.team_key = team_key
        self.league_key = team_key[:team_key.rfind('.') - 2]
        self.parent = parent
        self.get = self.parent.get
        self._get_rank = get_rank
        self._get_roster(team_key)
        self.league = parent.get_league(self.league_key, self)

    def _get_player(self, data):
        """ Creates and returns a Player object. Allows for threads. """
        return Player(data, self, rank=self._get_rank)

    def _get_roster(self, team_key):
        """ Get fantasy team information and list of players.
        This function gets called at initialization. """
        url = 'team/{}/roster'.format(team_key)
        response = self.get(url)
        self.name = response['team']['name']
        data = response['team']['roster']['players']['player']
        self.num_players = len(data)
        if threads:
            pool = ThreadPool(20)
            func = pool.map
        else:
            func = map
        self.players = func(self._get_player, data)
        self.data = data

    def update_roster(self, data):
        """ Updates the roster with the new alignment.

        Data should be a list of tuples of the form:
            (Player, old position, new position)

        See: https://developer.yahoo.com/fantasysports/guide/roster-resource.html
        """
        header = ('<?xml version="1.0"?> <fantasy_content> <roster>'
                  '<coverage_type>date</coverage_type>')
        footer = '</roster> </fantasy_content>'
        date_str = '<date>{}</date>'.format(time.strftime("%Y-%m-%d"))
        players_str = '<players>'
        for player, old_pos, new_pos in data:
            players_str += ('<player> <player_key>{}</player_key> <position>{}'
                            '</position> </player>'.format(player.player_key, new_pos))
        players_str += '</players>'
        msg = '{} {} {} {}'.format(header, date_str, players_str, footer)
        url = ('https://fantasysports.yahooapis.com/fantasy/v2/team/'
               '{}/roster'.format(self.team_key))
        r = self.parent.oauth.session.put(url,
                                          msg,
                                          headers={'content-type': 'application/xml'})
        if r.status_code != 200:
            print(r.text)
        r.raise_for_status()
        return r

    def start_active(self, playing_teams):
        """ Create an optimal assignment between players and positions.

        Takes the list of player and creates a weighted bipartite graph.
        The weights are inversely proportional to the player's rank except if:
        (a) the player is injured (weight=1) or (b) the player is not playing
        (weight=2). Then, using the networkx package, the graph is analyzed with
        a maximum weighted matching algorithm. Finally, calls the update_roster
        method to update the alignment.

        returns: [list] list of changes to the roster

        TODO: Add IR spots, and add message to email saying that there is a free
            spot in the team.
        """
        try:
            import networkx as nx
        except ImportError:
            raise ImportError('Could not import package networkx. This package is '
                              'necessary to compute the optimal allocation.'  )

        # rank is necessary
        if not self._get_rank:
            self._get_rank = True
            self._get_roster(self.team_key)

        # Creating the list of position. Final form should be
        # [('C', 1), ('C', 2), ('LW', 1), etc.]
        # This is required because the matching algorithm needs unique nodes
        pos_list = []
        c = Counter()
        for p in self.league.roster_positions:
            c[p] += 1
            pos_list.append((p, c[p]))
        pos_list.append(('BN', 99))
        pos_list.append(('BN', 98))
        pos_list.append(('BN', 97))
        pos_list.append(('BN', 96))

        # Creating the graph
        G = nx.Graph()

        for player in self.players:
            for pos_u in pos_list:
                for pos in player.eligible_positions + ['BN']:
                    weight = 1000 - player.rank
                    # If player is injured
                    if player.status != 'OK':
                        weight = 4
                    # If player does not play tonight
                    if player.nhl_team not in playing_teams:
                        weight = 3
                    # If edge is for the bench
                    if pos == 'BN':
                        weight = 2
                    # If edge is for IR or IR+
                    if pos in ['IR', 'IR+']:
                        weight = 1

                    if pos_u[0] == pos:
                        G.add_edge(pos_u, player.name['full'], weight=weight)

                # If player is on IR or IR+ spot, keep it there
                # Works even if the player is not injured anymore
                if ((player.selected_position in ['IR', 'IR+']) and
                        (player.selected_position == pos_u[0])):
                    G.add_edge(pos_u, player.name['full'], weight=1001)

        best = nx.max_weight_matching(G)

        # Create a roster change list.
        # Elements are tuples of (Player, old position, new position)
        update_data = []
        for player in self.players:
            new = best[player.name['full']][0]
            if player.selected_position != new:
                update_data.append((player, player.selected_position, new))

        if len(update_data) > 0:
            self.update_roster(update_data)

        return update_data

    def __repr__(self):
        return u'<Team: {} - {}>'.format(self.name, self.league.name)


class Player:
    """ Player data with multiple attributes from data.
    Can also get the fantasy rank of the player if rank=True
    """

    def __init__(self, player_data, parent, rank=False):
        self.parent = parent
        self.data = player_data
        self.player_key = player_data['player_key']
        self.name = player_data['name']
        self.selected_position = player_data['selected_position']['position']
        self.position = player_data['display_position']
        eligible_positions = player_data['eligible_positions']['position']
        if isinstance(eligible_positions, basestring):
            self.eligible_positions = [eligible_positions]
        else:
            self.eligible_positions = eligible_positions

        self.nhl_team = player_data['editorial_team_abbr']
        self.status = player_data.get('status', 'OK')
        if rank:
            self.rank = self.get_rank()

    def get_rank(self):
        url = 'player/{}/draft_analysis'.format(self.player_key)
        data = self.parent.get(url)
        try:
            return int(float(data['player']['draft_analysis']
                             ['average_pick']))
        except ValueError:
            return 700

    def __repr__(self):
        return '<Player: {:<4} - {} ({})>'.format(self.selected_position,
                                                  self.name['full'],
                                                  self.position)
