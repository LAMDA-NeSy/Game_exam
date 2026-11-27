"""Offline smoke reference; excluded from the agent image."""
def choose(observation):
    frame = observation['frame_data']
    if frame['empty_flag']:
        return 'noop'
    player = observation['player']
    me, other = frame['character_data'][player], frame['character_data'][1-player]
    forward = 'R' if me['x'] < other['x'] else 'L'
    return forward if abs(me['x']-other['x']) > 260 else 'BD' + forward


if __name__ == '__main__':
    from game_client import GameClient
    client = GameClient()
    reply = client.observe()
    while not reply['done']:
        reply = client.step(choose(reply['observation']), reply['step'])
    print('Match completed:', reply['step'], 'input frames')
