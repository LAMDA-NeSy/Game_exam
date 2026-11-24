"""A deterministic opponent that takes wins, blocks threats, then plays a seeded move."""

import hashlib
import json


ROWS, COLUMNS = 6, 7


def winning_move(board, column, player):
    """Check a proposed drop on the native, row-major PettingZoo board."""
    row = next((r for r in range(ROWS - 1, -1, -1) if board[r * COLUMNS + column] == 0), None)
    if row is None:
        return False

    def occupied(r, c):
        return (r, c) == (row, column) or (
            0 <= r < ROWS and 0 <= c < COLUMNS and board[r * COLUMNS + c] == player
        )

    for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
        count = 1
        for sign in (-1, 1):
            r, c = row + sign * dr, column + sign * dc
            while occupied(r, c):
                count += 1
                r += sign * dr
                c += sign * dc
        if count >= 4:
            return True
    return False


def choose(board, legal, seed):
    """Return a legal column; same board and seed always yield the same answer."""
    legal = sorted(int(column) for column in legal)
    if not legal:
        raise ValueError("Cannot choose from a full board")
    for player in (2, 1):
        for column in legal:
            if winning_move(board, column, player):
                return column
    encoded = json.dumps([seed, board], separators=(",", ":")).encode()
    index = int.from_bytes(hashlib.sha256(encoded).digest(), "big") % len(legal)
    return legal[index]
