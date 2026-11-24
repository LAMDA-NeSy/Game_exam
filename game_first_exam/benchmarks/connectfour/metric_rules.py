"""Independently replay public Connect Four moves and check the native verdict."""

from opponent import choose, winning_move


def validate_metrics(final, instance):
    metrics = final["metrics"]
    board = [0] * 42
    moves = metrics["moves"]
    if not isinstance(moves, list) or len(moves) > 42:
        raise ValueError("Invalid Connect Four move count")

    outcome = "playing"
    for index, move in enumerate(moves):
        actor = "player_0" if index % 2 == 0 else "player_1"
        player = 1 if index % 2 == 0 else 2
        column = move["column"]
        legal = [c for c in range(7) if board[c] == 0]
        if (outcome != "playing" or move["actor"] != actor or type(column) is not int
                or not 0 <= column < 7 or move["board_before"] != board):
            raise ValueError("Connect Four move order or board is inconsistent")
        if actor == "player_1" and column != choose(board, legal, instance["opponent_seed"]):
            raise ValueError("Connect Four opponent did not follow its frozen policy")

        if column not in legal:
            outcome = "illegal"
            rewards = [-1, 0]
        else:
            won = winning_move(board, column, player)
            row = next(r for r in range(5, -1, -1) if board[r * 7 + column] == 0)
            board[row * 7 + column] = player
            if won:
                outcome = "win" if player == 1 else "loss"
            elif all(board[:7]):
                outcome = "draw"
            rewards = ([1, -1] if outcome == "win" else
                       [-1, 1] if outcome == "loss" else [0, 0])
        if move["board_after"] != board or move["rewards"] != rewards:
            raise ValueError("Connect Four board or native reward disagrees with replay")

    decisions = (len(moves) + 1) // 2
    if (type(metrics["agent_decisions"]) is not int or metrics["agent_decisions"] != decisions
            or decisions != final["steps"] or metrics["total_plies"] != len(moves)
            or metrics["final_board"] != board or metrics["outcome"] != outcome
            or metrics["native_rewards"] != (rewards if moves else [0, 0])):
        raise ValueError("Connect Four final metrics disagree with move replay")
    success = outcome == "win"
    if (metrics["success"] != int(success) or final["success"] != success
            or final["terminated"] != (outcome != "playing")
            or final["truncated"] != (outcome == "illegal")
            or final["return"] != (rewards if moves else [0, 0])[0]):
        raise ValueError("Connect Four terminal result disagrees with replay")
