"""Stdlib checks for trusted native V-MAGE evidence; no engine or replay claims."""
import math

GAME = 'tempestrun'


def _number(value, label, minimum=0):
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise ValueError('invalid ' + label)
    return value


def _integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('invalid ' + label)
    return value


def validate_metrics(final, instance):
    m = final['metrics']
    common = {'native_score', 'initial_native_score', 'native_frame_count', 'native_step_calls',
              'native_frames_advanced', 'native_initialization_calls', 'decision_count',
              'native_invalid_action_count', 'native_terminated', 'native_truncated',
              'terminal_cause', 'native_frame_limit', 'visual_wallclock_dependency'}
    extra = {'race': {'native_win', 'native_completion_degree'},
             'flappybird': {'pipe_pair_score', 'counted_live_pipe_halves'},
             'pong': {'score_a', 'score_b'},
             'supermario': {'dashboard_points', 'dashboard_coins', 'dashboard_ticks', 'mario_restart'},
             'tempestrun': {'distance_z', 'player_dead', 'player_mode'}}[GAME]
    if set(m) != common | extra:
        raise ValueError('wrong native metric fields')
    score = _number(m['native_score'], 'native score')
    if type(m['initial_native_score']) not in (int, float) or m['initial_native_score'] != 0:
        raise ValueError('nonzero native initialization score')
    if not math.isclose(final['return'], score - m['initial_native_score'], rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError('score delta does not match public return')
    decisions = _integer(m['decision_count'], 'native decisions')
    if decisions != final['steps']:
        raise ValueError('native/public decision count mismatch')
    calls = _integer(m['native_step_calls'], 'native calls', 1)
    advanced = _integer(m['native_frames_advanced'], 'native advanced frames')
    frames = _integer(m['native_frame_count'], 'native frame ledger', 1)
    if type(m['native_initialization_calls']) is not int or m['native_initialization_calls'] != 1:
        raise ValueError('native initialization must occur exactly once')
    if type(m['native_invalid_action_count']) is not int or m['native_invalid_action_count'] != 0:
        raise ValueError('public rejected actions must not enter native fallback')
    for name, public in [('native_terminated', 'terminated'), ('native_truncated', 'truncated')]:
        if type(m[name]) is not bool or m[name] != final[public]:
            raise ValueError('inconsistent native terminal flags')
    terminated, truncated = m['native_terminated'], m['native_truncated']
    done = terminated or truncated
    sample = instance['frames_per_decision']
    if not decisions:
        if calls != 1 or frames != 1 or advanced != 0 or done or score:
            raise ValueError('native progress without a decision')
    elif done:
        if not (decisions - 1) * sample < calls - 1 <= decisions * sample:
            raise ValueError('inconsistent final native action fragment')
    elif calls != 1 + decisions * sample:
        raise ValueError('nonterminal native action fragment is incomplete')
    passive_terminal = done and (calls - 2) % sample != 0
    if frames != calls - int(passive_terminal):
        raise ValueError('native capture ledger asymmetry mismatch')
    if advanced != calls - 1 - int(GAME == 'race' and truncated):
        raise ValueError('inconsistent native update count')
    limit = instance['native_frame_limit']
    if m['native_frame_limit'] != limit or (truncated and (limit is None or frames < limit)):
        raise ValueError('inconsistent native frame limit')
    if type(m['visual_wallclock_dependency']) is not bool or m['visual_wallclock_dependency'] != (GAME == 'tempestrun'):
        raise ValueError('wrong native visual clock declaration')
    cause = m['terminal_cause']
    if not done:
        if cause != 'running':
            raise ValueError('nonterminal native state has a terminal cause')
    elif truncated:
        expected = 'native_frame_limit+native_death' if terminated else 'native_frame_limit'
        if cause != expected or GAME not in {'race', 'supermario'} or (GAME == 'race' and terminated):
            raise ValueError('wrong native limit terminal cause')
    elif cause != ('native_win' if GAME == 'race' and score == 100 else 'native_collision' if GAME == 'race' else 'native_missed_paddle' if GAME == 'pong' else 'native_death'):
        raise ValueError('wrong native termination cause')
    if GAME == 'race':
        if score not in (0, 100) or type(m['native_win']) is not bool or m['native_win'] != (score == 100):
            raise ValueError('inconsistent native Race win/score')
        if m['native_win'] and not terminated:
            raise ValueError('native Race win without termination')
        if _number(m['native_completion_degree'], 'native completion') > 1:
            raise ValueError('invalid native Race completion degree')
        success = m['native_win']
    else:
        success = score > 0
    if final['success'] != success:
        raise ValueError('inconsistent native or auxiliary success flag')
    if GAME == 'pong':
        a, b = _integer(m['score_a'], 'Pong score A'), _integer(m['score_b'], 'Pong score B')
        if score != a + b:
            raise ValueError('Pong native score must sum both paddles')
    elif GAME == 'flappybird':
        halves = _integer(m['counted_live_pipe_halves'], 'counted live pipe halves')
        if m['pipe_pair_score'] != score or score * 2 != int(score * 2) or halves > score * 2 or halves % 2:
            raise ValueError('inconsistent Flappy pipe score')
    elif GAME == 'supermario':
        points = _integer(m['dashboard_points'], 'Mario points')
        _integer(m['dashboard_coins'], 'Mario coins')
        if points != score or _integer(m['dashboard_ticks'], 'Mario dashboard ticks', 1) != calls:
            raise ValueError('inconsistent Mario dashboard score/ticks')
        if type(m['mario_restart']) is not bool or m['mario_restart'] != terminated:
            raise ValueError('inconsistent native Mario restart')
    elif GAME == 'tempestrun':
        z = _number(m['distance_z'], 'Tempest distance')
        if score != int(z / 10) * 10:
            raise ValueError('Tempest score is quantized native distance')
        if type(m['player_dead']) is not bool or m['player_dead'] != terminated or m['player_mode'] not in {'run', 'jump', 'slide', 'dead'} or m['player_dead'] != (m['player_mode'] == 'dead'):
            raise ValueError('inconsistent Tempest native player mode')
