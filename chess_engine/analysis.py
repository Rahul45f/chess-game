"""
Post-game analysis: replays a finished game move by move, scoring each
position with a minimax search to see how much each move lost compared to
the best available move, then classifies the move quality.
"""

from chess_engine.board import Board
from chess_engine.ai import evaluate, search_eval

CLASSIFICATIONS = [
    ("Best", 15, (95, 200, 120)),
    ("Excellent", 35, (140, 205, 110)),
    ("Good", 75, (150, 190, 220)),
    ("Inaccuracy", 150, (235, 200, 90)),
    ("Mistake", 350, (235, 150, 70)),
    ("Blunder", float("inf"), (225, 90, 90)),
]


def classify(loss_cp):
    for label, threshold, color in CLASSIFICATIONS:
        if loss_cp <= threshold:
            return label, color
    return "Blunder", CLASSIFICATIONS[-1][2]


def analyze_game(move_log, depth=2, progress_callback=None):
    """
    Replays move_log from the start and, for every move, computes:
      - eval_before: best achievable evaluation (mover's perspective, cp)
      - eval_after: evaluation actually reached (mover's perspective, cp)
      - loss_cp: how many centipawns worse than best (>= 0)
      - label / color: quality classification

    Returns a list of dicts, one per move, plus the running eval (White's
    perspective) after each move so a graph can be drawn.
    """
    board = Board()
    records = []
    total = len(move_log)

    for i, played_move in enumerate(move_log):
        mover = board.turn
        sign = 1 if mover == "w" else -1

        legal_moves = board.get_legal_moves()
        best_cp = float("-inf")
        for candidate in legal_moves:
            board.make_move(candidate)
            score = search_eval(board, depth - 1) * sign
            board.undo_move()
            if score > best_cp:
                best_cp = score

        # score actually achieved by the played move
        match = next((m for m in legal_moves if m.move_id == played_move.move_id), played_move)
        board.make_move(match)
        actual_cp = search_eval(board, depth - 1) * sign
        eval_after_white = evaluate(board) if depth <= 1 else search_eval(board, depth - 1)

        loss_cp = max(0, round(best_cp - actual_cp))
        label, color = classify(loss_cp)
        display_loss = min(loss_cp, 900)  # cap display; mate-level swings are already "Blunder"

        records.append({
            "index": i,
            "mover": mover,
            "notation": match.get_notation(),
            "loss_cp": display_loss,
            "label": label,
            "color": color,
            "eval_after_white": eval_after_white,
        })

        if progress_callback:
            progress_callback(i + 1, total)

    return records


def summarize(records):
    """Counts of each classification per color, for a post-game summary."""
    summary = {"w": {}, "b": {}}
    for rec in records:
        side = summary[rec["mover"]]
        side[rec["label"]] = side.get(rec["label"], 0) + 1
    return summary
