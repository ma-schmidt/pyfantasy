
def _check_conditions(player, pos, playing_teams, conds):
    out = True
    for cond in conds:
        inv = cond.get('inverse', False)
        # position condition
        if cond['type'] == 'position':
            if isinstance(cond['position'], list):
                b = (pos in cond['position'])
            elif isinstance(cond['position'], basestring):
                b = (pos == cond['position'])
            else:
                raise ValueError('player attribute is not the correct type: '
                                 '{}'.format(type(cond['position'])))
        # player condition
        elif cond['type'] == 'player':
            if isinstance(getattr(player, cond['attr']), list):
                b = (cond['value'] in getattr(player, cond['attr']))
            elif isinstance(getattr(player, cond['attr']), basestring):
                b = (cond['value'] == getattr(player, cond['attr']))
            else:
                raise ValueError('player attribute is not the correct type: '
                                 '{}'.format(type(getattr(player, cond['attr']))))

        # playing_team condition
        elif cond['type'] == 'not_playing':
            b = (player.nhl_team not in playing_teams)

        else:
            raise ValueError('condition type is not valid: {}'.format(cond['type']))

        b = ~b if inv else b

        out = out & b

    return out


def rule_parser(weight, player, pos, playing_teams, rules):
    for rule in rules:
        if _check_conditions(player, pos, playing_teams, rule['conditions']):
            print 'relative'
            if rule['weight'].get('type', 'absolute') == 'relative':
                weight = weight + rule['weight']['value']
            else:
                weight = rule['weight']['value']
    return weight
