"""
Chess engine core: board representation, legal move generation, and rules.

Board coordinates: (row, col) where row 0 = rank 8 (top), row 7 = rank 1 (bottom),
col 0 = file a, col 7 = file h.  White starts on rows 6-7, Black on rows 0-1.

Pieces are represented as 2-character strings: color + type, e.g. "wp", "bK".
Empty squares are "--".
"""

EMPTY = "--"


class Move:
    """Represents a single move, including special-move metadata."""

    def __init__(self, start, end, board, promotion_choice="Q",
                 is_castle=False, is_en_passant=False):
        self.start = start
        self.end = end
        self.start_row, self.start_col = start
        self.end_row, self.end_col = end

        self.piece_moved = board[self.start_row][self.start_col]
        self.piece_captured = board[self.end_row][self.end_col]

        self.is_en_passant = is_en_passant
        if is_en_passant:
            # captured pawn sits on the same row as the moving pawn, target column
            self.piece_captured = board[self.start_row][self.end_col]

        self.is_castle = is_castle

        self.is_pawn_promotion = (
            self.piece_moved[1] == "p" and self.end_row in (0, 7)
        )
        self.promotion_choice = promotion_choice

        self.is_two_square_pawn_move = (
            self.piece_moved[1] == "p" and abs(self.start_row - self.end_row) == 2
        )

        # unique id for equality comparisons
        self.move_id = (self.start_row, self.start_col, self.end_row, self.end_col,
                         self.promotion_choice)

    def __eq__(self, other):
        return isinstance(other, Move) and self.move_id == other.move_id

    def __hash__(self):
        return hash(self.move_id)

    def get_notation(self):
        files = "abcdefgh"
        start = f"{files[self.start_col]}{8 - self.start_row}"
        end = f"{files[self.end_col]}{8 - self.end_row}"
        promo = f"={self.promotion_choice}" if self.is_pawn_promotion else ""
        return f"{start}{end}{promo}"


class Board:
    def __init__(self):
        self.board = [
            ["br", "bn", "bb", "bq", "bk", "bb", "bn", "br"],
            ["bp", "bp", "bp", "bp", "bp", "bp", "bp", "bp"],
            [EMPTY] * 8,
            [EMPTY] * 8,
            [EMPTY] * 8,
            [EMPTY] * 8,
            ["wp", "wp", "wp", "wp", "wp", "wp", "wp", "wp"],
            ["wr", "wn", "wb", "wq", "wk", "wb", "wn", "wr"],
        ]
        self.turn = "w"
        self.king_pos = {"w": (7, 4), "b": (0, 4)}

        # castling rights: king-side / queen-side per color
        self.castle_rights = {"wK": True, "wQ": True, "bK": True, "bQ": True}
        self.castle_rights_log = [dict(self.castle_rights)]

        self.en_passant_target = None  # (row, col) or None
        self.en_passant_log = [None]

        self.move_log = []
        self.halfmove_clock = 0  # for 50-move rule
        self.position_counts = {}
        self._record_position()

    # ------------------------------------------------------------------ #
    # Basic helpers
    # ------------------------------------------------------------------ #
    def piece_at(self, r, c):
        return self.board[r][c]

    def in_bounds(self, r, c):
        return 0 <= r < 8 and 0 <= c < 8

    def opponent(self, color):
        return "b" if color == "w" else "w"

    def _record_position(self):
        key = self._position_key()
        self.position_counts[key] = self.position_counts.get(key, 0) + 1

    def _unrecord_position(self):
        key = self._position_key()
        if key in self.position_counts:
            self.position_counts[key] -= 1
            if self.position_counts[key] <= 0:
                del self.position_counts[key]

    def _position_key(self):
        return (
            tuple(tuple(row) for row in self.board),
            self.turn,
            tuple(sorted(self.castle_rights.items())),
            self.en_passant_target,
        )

    def is_threefold_repetition(self):
        return self.position_counts.get(self._position_key(), 0) >= 3

    def is_fifty_move_draw(self):
        return self.halfmove_clock >= 100  # 50 full moves = 100 half-moves

    # ------------------------------------------------------------------ #
    # Make / undo moves
    # ------------------------------------------------------------------ #
    def make_move(self, move):
        self._unrecord_position()

        self.board[move.start_row][move.start_col] = EMPTY
        self.board[move.end_row][move.end_col] = move.piece_moved

        if move.piece_moved[1] == "p" or move.piece_captured != EMPTY:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        # en passant capture: remove the actual captured pawn
        if move.is_en_passant:
            self.board[move.start_row][move.end_col] = EMPTY

        # pawn promotion
        if move.is_pawn_promotion:
            self.board[move.end_row][move.end_col] = move.piece_moved[0] + move.promotion_choice.lower()

        # castling: move the rook too
        if move.is_castle:
            if move.end_col == 6:  # king-side
                rook = self.board[move.end_row][7]
                self.board[move.end_row][7] = EMPTY
                self.board[move.end_row][5] = rook
            else:  # queen-side
                rook = self.board[move.end_row][0]
                self.board[move.end_row][0] = EMPTY
                self.board[move.end_row][3] = rook

        # update king position
        if move.piece_moved[1] == "k":
            self.king_pos[move.piece_moved[0]] = (move.end_row, move.end_col)

        # update castle rights
        self._update_castle_rights(move)
        self.castle_rights_log.append(dict(self.castle_rights))

        # update en passant target
        if move.is_two_square_pawn_move:
            mid_row = (move.start_row + move.end_row) // 2
            self.en_passant_target = (mid_row, move.start_col)
        else:
            self.en_passant_target = None
        self.en_passant_log.append(self.en_passant_target)

        self.move_log.append(move)
        self.turn = self.opponent(self.turn)
        self._record_position()

    def undo_move(self):
        if not self.move_log:
            return
        self._unrecord_position()

        move = self.move_log.pop()
        self.turn = self.opponent(self.turn)

        self.board[move.start_row][move.start_col] = move.piece_moved
        self.board[move.end_row][move.end_col] = move.piece_captured if not move.is_en_passant else EMPTY

        if move.is_en_passant:
            self.board[move.start_row][move.end_col] = move.piece_captured
            self.board[move.end_row][move.end_col] = EMPTY

        if move.is_castle:
            if move.end_col == 6:
                rook = self.board[move.end_row][5]
                self.board[move.end_row][5] = EMPTY
                self.board[move.end_row][7] = rook
            else:
                rook = self.board[move.end_row][3]
                self.board[move.end_row][3] = EMPTY
                self.board[move.end_row][0] = rook

        if move.piece_moved[1] == "k":
            self.king_pos[move.piece_moved[0]] = (move.start_row, move.start_col)

        self.castle_rights_log.pop()
        self.castle_rights = dict(self.castle_rights_log[-1])

        self.en_passant_log.pop()
        self.en_passant_target = self.en_passant_log[-1]

        self._record_position()

    def _update_castle_rights(self, move):
        piece = move.piece_moved
        if piece == "wk":
            self.castle_rights["wK"] = False
            self.castle_rights["wQ"] = False
        elif piece == "bk":
            self.castle_rights["bK"] = False
            self.castle_rights["bQ"] = False

        for (r, c), key in (((7, 7), "wK"), ((7, 0), "wQ"), ((0, 7), "bK"), ((0, 0), "bQ")):
            if (move.start_row, move.start_col) == (r, c) or (move.end_row, move.end_col) == (r, c):
                self.castle_rights[key] = False

    # ------------------------------------------------------------------ #
    # Move generation
    # ------------------------------------------------------------------ #
    def get_legal_moves(self):
        """All fully-legal moves for the side to move (king safety enforced)."""
        moves = self.get_pseudo_legal_moves(self.turn)
        legal = []
        for move in moves:
            self.make_move(move)
            if not self.is_in_check(self.opponent(self.turn)):
                legal.append(move)
            self.undo_move()
        return legal

    def get_pseudo_legal_moves(self, color):
        moves = []
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece == EMPTY or piece[0] != color:
                    continue
                kind = piece[1]
                if kind == "p":
                    self._pawn_moves(r, c, color, moves)
                elif kind == "n":
                    self._knight_moves(r, c, color, moves)
                elif kind == "b":
                    self._sliding_moves(r, c, color, moves, [(-1, -1), (-1, 1), (1, -1), (1, 1)])
                elif kind == "r":
                    self._sliding_moves(r, c, color, moves, [(-1, 0), (1, 0), (0, -1), (0, 1)])
                elif kind == "q":
                    self._sliding_moves(r, c, color, moves,
                                         [(-1, -1), (-1, 1), (1, -1), (1, 1),
                                          (-1, 0), (1, 0), (0, -1), (0, 1)])
                elif kind == "k":
                    self._king_moves(r, c, color, moves)
        return moves

    def _pawn_moves(self, r, c, color, moves):
        direction = -1 if color == "w" else 1
        start_row = 6 if color == "w" else 1
        promo_row = 0 if color == "w" else 7

        # one square forward
        if self.in_bounds(r + direction, c) and self.board[r + direction][c] == EMPTY:
            self._add_pawn_move(r, c, r + direction, c, moves)
            # two squares forward
            if r == start_row and self.board[r + 2 * direction][c] == EMPTY:
                moves.append(Move((r, c), (r + 2 * direction, c), self.board))

        # captures
        for dc in (-1, 1):
            nr, nc = r + direction, c + dc
            if not self.in_bounds(nr, nc):
                continue
            target = self.board[nr][nc]
            if target != EMPTY and target[0] != color:
                self._add_pawn_move(r, c, nr, nc, moves)
            elif self.en_passant_target == (nr, nc):
                moves.append(Move((r, c), (nr, nc), self.board, is_en_passant=True))

    def _add_pawn_move(self, r, c, nr, nc, moves):
        if nr in (0, 7):
            for promo in ("Q", "R", "B", "N"):
                moves.append(Move((r, c), (nr, nc), self.board, promotion_choice=promo))
        else:
            moves.append(Move((r, c), (nr, nc), self.board))

    def _knight_moves(self, r, c, color, moves):
        deltas = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
        for dr, dc in deltas:
            nr, nc = r + dr, c + dc
            if self.in_bounds(nr, nc):
                target = self.board[nr][nc]
                if target == EMPTY or target[0] != color:
                    moves.append(Move((r, c), (nr, nc), self.board))

    def _sliding_moves(self, r, c, color, moves, directions):
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            while self.in_bounds(nr, nc):
                target = self.board[nr][nc]
                if target == EMPTY:
                    moves.append(Move((r, c), (nr, nc), self.board))
                else:
                    if target[0] != color:
                        moves.append(Move((r, c), (nr, nc), self.board))
                    break
                nr += dr
                nc += dc

    def _king_moves(self, r, c, color, moves):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc):
                    target = self.board[nr][nc]
                    if target == EMPTY or target[0] != color:
                        moves.append(Move((r, c), (nr, nc), self.board))

        # castling
        if not self.is_square_attacked(r, c, self.opponent(color)):
            self._try_castle(r, c, color, moves, king_side=True)
            self._try_castle(r, c, color, moves, king_side=False)

    def _try_castle(self, r, c, color, moves, king_side):
        key = f"{color}{'K' if king_side else 'Q'}"
        if not self.castle_rights[key]:
            return
        if king_side:
            path = [(r, 5), (r, 6)]
            rook_sq = (r, 7)
        else:
            path = [(r, 3), (r, 2)]
            empty_only = [(r, 1)]
            rook_sq = (r, 0)
            if self.board[empty_only[0][0]][empty_only[0][1]] != EMPTY:
                return

        if self.board[rook_sq[0]][rook_sq[1]] != color + "r":
            return
        for pr, pc in path:
            if self.board[pr][pc] != EMPTY:
                return
            if self.is_square_attacked(pr, pc, self.opponent(color)):
                return

        end_col = 6 if king_side else 2
        moves.append(Move((r, c), (r, end_col), self.board, is_castle=True))

    # ------------------------------------------------------------------ #
    # Check / attack detection
    # ------------------------------------------------------------------ #
    def is_square_attacked(self, r, c, by_color):
        # pawns
        direction = 1 if by_color == "w" else -1  # attacker's pawn moves opposite
        for dc in (-1, 1):
            pr, pc = r + direction, c + dc
            if self.in_bounds(pr, pc) and self.board[pr][pc] == by_color + "p":
                return True

        # knights
        for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
            nr, nc = r + dr, c + dc
            if self.in_bounds(nr, nc) and self.board[nr][nc] == by_color + "n":
                return True

        # sliding: bishop/queen diagonals
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            nr, nc = r + dr, c + dc
            while self.in_bounds(nr, nc):
                target = self.board[nr][nc]
                if target != EMPTY:
                    if target[0] == by_color and target[1] in ("b", "q"):
                        return True
                    break
                nr += dr
                nc += dc

        # sliding: rook/queen straight
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            while self.in_bounds(nr, nc):
                target = self.board[nr][nc]
                if target != EMPTY:
                    if target[0] == by_color and target[1] in ("r", "q"):
                        return True
                    break
                nr += dr
                nc += dc

        # king
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc) and self.board[nr][nc] == by_color + "k":
                    return True

        return False

    def is_in_check(self, color):
        r, c = self.king_pos[color]
        return self.is_square_attacked(r, c, self.opponent(color))

    def is_checkmate(self):
        return self.is_in_check(self.turn) and not self.get_legal_moves()

    def is_stalemate(self):
        return not self.is_in_check(self.turn) and not self.get_legal_moves()

    def is_game_over(self):
        return (self.is_checkmate() or self.is_stalemate()
                or self.is_threefold_repetition() or self.is_fifty_move_draw()
                or self.is_insufficient_material())

    def is_insufficient_material(self):
        pieces = [p for row in self.board for p in row if p != EMPTY]
        kinds = sorted(p[1] for p in pieces)
        if kinds == ["k", "k"]:
            return True
        if kinds in (["b", "k", "k"], ["k", "k", "n"]):
            return True
        return False

    def result_string(self):
        if self.is_checkmate():
            winner = "Black" if self.turn == "w" else "White"
            return f"Checkmate — {winner} wins"
        if self.is_stalemate():
            return "Stalemate — draw"
        if self.is_threefold_repetition():
            return "Draw — threefold repetition"
        if self.is_fifty_move_draw():
            return "Draw — 50-move rule"
        if self.is_insufficient_material():
            return "Draw — insufficient material"
        return ""
