# Chess

A complete, playable chess game built with Python and Pygame — featuring a
selectable-difficulty AI opponent, LAN multiplayer for two people on separate
devices, a dark-themed UI with hand-drawn piece art, and automatic post-game
move analysis.

## Features

- **Full chess rules**: legal move generation for all pieces, castling
  (king-side and queen-side, including "no castling through/out of check"),
  en passant, pawn promotion (Queen/Rook/Bishop/Knight), check, checkmate,
  and stalemate detection, plus draw detection (threefold repetition,
  50-move rule, insufficient material).
- **Selectable AI difficulty**: Easy / Medium / Hard / Expert, chosen from a
  pre-game screen. Difficulty maps to a minimax + alpha-beta search depth
  (1–4 ply); Easy and Medium also add a chance of a deliberately weaker move
  so the AI stays beatable. The AI always runs on a background thread so the
  UI never freezes while it "thinks."
- **Post-game move analysis**: after any game ends (checkmate, stalemate,
  draw, resignation, or disconnect), request an analysis of every move
  played by both sides. Each move is scored against the best available move
  at that position and classified — Best, Excellent, Good, Inaccuracy,
  Mistake, or Blunder — with a per-side summary, a graph of the evaluation
  across the game, and a scrollable move-by-move breakdown.
- **Dark-themed UI with real piece art**: a dark charcoal/navy colour
  scheme throughout, with all twelve piece images (six piece types × two
  colours) drawn as smooth vector shapes (using hand-evaluated Bezier
  curves) directly in pygame — no external image files, and no native
  dependencies beyond pygame itself, so it runs the same on Windows, macOS,
  and Linux with nothing more than `pip install pygame`.
- **LAN multiplayer**: one player hosts (their device listens for a
  connection and plays White); the other joins by entering the host's local
  IP address and plays Black. Moves sync over a simple TCP/JSON protocol.
  Works for two people on two different devices on the same network.
- **Quality-of-life features**: click-to-move with highlighted legal
  destinations, last-move and check highlighting, a live move list, board
  flipping, undo (in AI games), and resign.

## Project structure

```
chess_game/
├── main.py                    # App: menu, difficulty select, LAN host/join,
│                               # gameplay, and analysis screens (entry point)
├── network.py                 # LAN multiplayer transport (TCP host/join)
├── chess_engine/
│   ├── board.py                # Board state, move generation, rules engine
│   ├── ai.py                   # Minimax + alpha-beta AI, difficulty presets
│   └── analysis.py             # Post-game move analysis & classification
├── ui/
│   ├── piece_art.py               # Vector chess piece art (pure pygame, no native deps)
│   └── text_input.py              # Text box widget (used for IP entry)
├── requirements.txt
└── README.md
```

## Setup & running

```bash
pip install -r requirements.txt
python3 main.py
```

Requires Python 3.8+ and Pygame 2.5+.

## How to play

**vs AI**
1. From the main menu choose **Play vs AI**.
2. Pick a difficulty (Easy/Medium/Hard/Expert), then choose to start as
   White or Black.
3. Click a piece to see legal moves highlighted, then click a highlighted
   square to move there. Promotions show a picker for the new piece.

**LAN multiplayer (two devices, same network)**
1. On one device, choose **Host LAN Game**. It will display an IP address
   and port (e.g. `192.168.1.42:5555`) and wait for a connection.
2. On the other device, choose **Join LAN Game**, enter that address, and
   press Connect.
3. The host plays White, the joiner plays Black. Moves you make are sent
   automatically to the other device.

**After the game**
- When the game ends, click **View Move Analysis** to see how each move
  stacked up, or **Back to Menu** to start again.

## Design notes / extending the project

- The rules engine (`chess_engine/board.py`) has no dependency on Pygame or
  any other layer, so it can be reused for unit tests, a CLI version, or a
  different frontend.
- `ChessAI(difficulty=...)` in `chess_engine/ai.py` controls search depth
  and move randomness; see `DIFFICULTIES` for the presets.
- Move legality is enforced by generating pseudo-legal moves per piece, then
  filtering out any move that would leave the mover's own king in check.
- The analysis engine (`chess_engine/analysis.py`) reuses the AI's search
  (`search_eval`) to score each position, so its verdicts are consistent
  with how the AI itself evaluates positions.
- The LAN protocol (`network.py`) sends each move as a small JSON object
  (`{"start": [r, c], "end": [r, c], "promotion": "Q"}`); the receiving side
  matches it against its own legal-move list before applying it, which also
  guards against corrupted or out-of-sync messages.
- Piece art (`ui/piece_art.py`) describes each piece as a tiny path
  "recipe" (moveto/lineto/quadratic/cubic-Bezier commands plus a few
  circles), flattens curves into polygons in pure Python, and renders at 4x
  resolution before downsampling for anti-aliased edges. It depends only on
  pygame — earlier drafts used SVG glyphs (blank on systems without a
  chess-capable font) and later `cairosvg` (which needs a native Cairo
  library that isn't reliably available via pip on Windows); this approach
  avoids both problems.
