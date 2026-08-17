"""
A simple chess AI: minimax search with alpha-beta pruning, using material
value plus piece-square tables for positional evaluation.
"""

import random

PIECE_VALUES = {"p": 100, "n": 320, "b": 330, "r": 500, "q": 900, "k": 0}

# Piece-square tables (from White's perspective; flipped for Black).
PAWN_TABLE = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [50, 50, 50, 50, 50, 50, 50, 50],
    [10, 10, 20, 30, 30, 20, 10, 10],
    [5, 5, 10, 25, 25, 10, 5, 5],
    [0, 0, 0, 20, 20, 0, 0, 0],
    [5, -5, -10, 0, 0, -10, -5, 5],
    [5, 10, 10, -20, -20, 10, 10, 5],
    [0, 0, 0, 0, 0, 0, 0, 0],
]
KNIGHT_TABLE = [
    [-50, -40, -30, -30, -30, -30, -40, -50],
    [-40, -20, 0, 0, 0, 0, -20, -40],
    [-30, 0, 10, 15, 15, 10, 0, -30],
    [-30, 5, 15, 20, 20, 15, 5, -30],
    [-30, 0, 15, 20, 20, 15, 0, -30],
    [-30, 5, 10, 15, 15, 10, 5, -30],
    [-40, -20, 0, 5, 5, 0, -20, -40],
    [-50, -40, -30, -30, -30, -30, -40, -50],
]
BISHOP_TABLE = [
    [-20, -10, -10, -10, -10, -10, -10, -20],
    [-10, 0, 0, 0, 0, 0, 0, -10],
    [-10, 0, 5, 10, 10, 5, 0, -10],
    [-10, 5, 5, 10, 10, 5, 5, -10],
    [-10, 0, 10, 10, 10, 10, 0, -10],
    [-10, 10, 10, 10, 10, 10, 10, -10],
    [-10, 5, 0, 0, 0, 0, 5, -10],
    [-20, -10, -10, -10, -10, -10, -10, -20],
]
ROOK_TABLE = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [5, 10, 10, 10, 10, 10, 10, 5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [0, 0, 0, 5, 5, 0, 0, 0],
]
QUEEN_TABLE = [
    [-20, -10, -10, -5, -5, -10, -10, -20],
    [-10, 0, 0, 0, 0, 0, 0, -10],
    [-10, 0, 5, 5, 5, 5, 0, -10],
    [-5, 0, 5, 5, 5, 5, 0, -5],
    [0, 0, 5, 5, 5, 5, 0, -5],
    [-10, 5, 5, 5, 5, 5, 0, -10],
    [-10, 0, 5, 0, 0, 0, 0, -10],
    [-20, -10, -10, -5, -5, -10, -10, -20],
]
KING_TABLE = [
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-20, -30, -30, -40, -40, -30, -30, -20],
    [-10, -20, -20, -20, -20, -20, -20, -10],
    [20, 20, 0, 0, 0, 0, 20, 20],
    [20, 30, 10, 0, 0, 10, 30, 20],
]
TABLES = {"p": PAWN_TABLE, "n": KNIGHT_TABLE, "b": BISHOP_TABLE,
          "r": ROOK_TABLE, "q": QUEEN_TABLE, "k": KING_TABLE}


def evaluate(board):
    """Positive = good for White, negative = good for Black."""
    if board.is_checkmate():
        return -100000 if board.turn == "w" else 100000
    if board.is_stalemate() or board.is_threefold_repetition() or board.is_fifty_move_draw():
        return 0

    score = 0
    for r in range(8):
        for c in range(8):
            piece = board.board[r][c]
            if piece == "--":
                continue
            color, kind = piece[0], piece[1]
            value = PIECE_VALUES[kind]
            table_row = r if color == "b" else 7 - r
            positional = TABLES[kind][table_row][c]
            if color == "w":
                score += value + positional
            else:
                score -= value + positional
    return score


# Difficulty presets: search depth plus an optional "blunder chance" that
# occasionally picks a weaker move so lower difficulties feel human-beatable.
DIFFICULTIES = {
    "Easy":   {"depth": 1, "randomness": 0.35},
    "Medium": {"depth": 2, "randomness": 0.15},
    "Hard":   {"depth": 3, "randomness": 0.0},
    "Expert": {"depth": 4, "randomness": 0.0},
}


def search_eval(board, depth):
    """Minimax evaluation of the CURRENT position (White's perspective, cp),
    searching `depth` more plies from the side to move."""
    ai = _SHARED_SEARCH
    maximizing = board.turn == "w"
    return ai._minimax(board, depth, float("-inf"), float("inf"), maximizing)


class ChessAI:
    def __init__(self, difficulty="Hard", depth=None):
        if depth is not None:
            self.depth = depth
            self.randomness = 0.0
        else:
            preset = DIFFICULTIES.get(difficulty, DIFFICULTIES["Hard"])
            self.depth = preset["depth"]
            self.randomness = preset["randomness"]
        self.difficulty = difficulty

    def choose_move(self, board):
        legal_moves = board.get_legal_moves()
        if not legal_moves:
            return None

        random.shuffle(legal_moves)  # add variety among equal-value moves
        maximizing = board.turn == "w"

        scored = []
        alpha, beta = float("-inf"), float("inf")
        for move in legal_moves:
            board.make_move(move)
            score = self._minimax(board, self.depth - 1, alpha, beta, not maximizing)
            board.undo_move()
            scored.append((score, move))
            if maximizing:
                alpha = max(alpha, max(s for s, _ in scored))
            else:
                beta = min(beta, min(s for s, _ in scored))

        scored.sort(key=lambda sm: sm[0], reverse=maximizing)

        # Lower difficulties occasionally play a move from further down the
        # ranked list instead of always the objectively-best one.
        if self.randomness > 0 and random.random() < self.randomness and len(scored) > 1:
            pool_size = max(1, len(scored) // 3)
            pick_from = scored[:min(len(scored), pool_size + 2)]
            return random.choice(pick_from[1:] if len(pick_from) > 1 else pick_from)[1]

        return scored[0][1]

    def _minimax(self, board, depth, alpha, beta, maximizing):
        if depth == 0 or board.is_checkmate() or board.is_stalemate():
            return evaluate(board)

        legal_moves = board.get_legal_moves()
        if not legal_moves:
            return evaluate(board)

        if maximizing:
            value = float("-inf")
            for move in legal_moves:
                board.make_move(move)
                value = max(value, self._minimax(board, depth - 1, alpha, beta, False))
                board.undo_move()
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value
        else:
            value = float("inf")
            for move in legal_moves:
                board.make_move(move)
                value = min(value, self._minimax(board, depth - 1, alpha, beta, True))
                board.undo_move()
                beta = min(beta, value)
                if alpha >= beta:
                    break
            return value


_SHARED_SEARCH = ChessAI(depth=0)  # reusable instance for search_eval()
