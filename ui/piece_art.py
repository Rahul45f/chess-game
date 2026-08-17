"""
Chess piece artwork drawn entirely with pygame's own drawing primitives —
no cairosvg / cairocffi / native Cairo library required, so it works
identically on Windows, macOS, and Linux with nothing beyond `pip install
pygame`.

Each piece is described as a small "path" mini-language (moveto/lineto/
quadratic/cubic Bezier, evaluated by hand) plus a few circles and lines,
using the same 0-100 design grid as a normal SVG viewBox. Curves are
flattened to polygons and rendered at 4x resolution, then downsampled for
anti-aliased edges.
"""

import pygame

SCALE = 4  # supersampling factor for smooth edges
GRID = 100  # design grid, matches a "viewBox 0 0 100 100" mental model


# ------------------------------------------------------------------ #
# Tiny path flattener: M/L/Q/C/Z commands -> a flat list of points
# ------------------------------------------------------------------ #
def _quad_bezier(p0, p1, p2, steps=10):
    pts = []
    for i in range(1, steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0]
        y = mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]
        pts.append((x, y))
    return pts


def _cubic_bezier(p0, p1, p2, p3, steps=14):
    pts = []
    for i in range(1, steps + 1):
        t = i / steps
        mt = 1 - t
        x = (mt**3) * p0[0] + 3 * (mt**2) * t * p1[0] + 3 * mt * (t**2) * p2[0] + (t**3) * p3[0]
        y = (mt**3) * p0[1] + 3 * (mt**2) * t * p1[1] + 3 * mt * (t**2) * p2[1] + (t**3) * p3[1]
        pts.append((x, y))
    return pts


def flatten_path(commands):
    """commands: list of tuples like ('M',x,y) ('L',x,y) ('Q',cx,cy,x,y)
    ('C',c1x,c1y,c2x,c2y,x,y) ('Z',). Returns a flat list of (x,y) points
    in the 0-100 design grid, ready to draw as a filled polygon."""
    points = []
    current = (0, 0)
    start = (0, 0)
    for cmd in commands:
        kind = cmd[0]
        if kind == "M":
            current = (cmd[1], cmd[2])
            start = current
            points.append(current)
        elif kind == "L":
            current = (cmd[1], cmd[2])
            points.append(current)
        elif kind == "Q":
            ctrl = (cmd[1], cmd[2])
            end = (cmd[3], cmd[4])
            points.extend(_quad_bezier(current, ctrl, end))
            current = end
        elif kind == "C":
            c1 = (cmd[1], cmd[2])
            c2 = (cmd[3], cmd[4])
            end = (cmd[5], cmd[6])
            points.extend(_cubic_bezier(current, c1, c2, end))
            current = end
        elif kind == "Z":
            points.append(start)
            current = start
    return points


# ------------------------------------------------------------------ #
# Piece geometry (0-100 design grid, shared shapes reused across pieces)
# ------------------------------------------------------------------ #
BASE_PATH = [
    ("M", 22, 90), ("Q", 22, 86, 26, 86), ("L", 74, 86), ("Q", 78, 86, 78, 90),
    ("L", 78, 93), ("Q", 78, 96, 74, 96), ("L", 26, 96), ("Q", 22, 96, 22, 93), ("Z",),
]
COLLAR_PATH = [
    ("M", 28, 80), ("Q", 28, 76, 32, 76), ("L", 68, 76), ("Q", 72, 76, 72, 80),
    ("L", 72, 84), ("Q", 72, 87, 68, 87), ("L", 32, 87), ("Q", 28, 87, 28, 84), ("Z",),
]


def _piece_pawn():
    return {
        "polys": [
            BASE_PATH,
            [("M", 35, 86), ("L", 65, 86), ("L", 60, 68), ("L", 40, 68), ("Z",)],
        ],
        "circles": [(50, 60, 6.5), (50, 40, 14)],
        "lines": [],
    }


def _piece_rook():
    return {
        "polys": [
            BASE_PATH,
            [("M", 30, 86), ("L", 30, 50), ("L", 70, 50), ("L", 70, 86), ("Z",)],
            [("M", 26, 50), ("L", 74, 50), ("L", 74, 40), ("L", 62, 40), ("L", 62, 32),
             ("L", 57, 32), ("L", 57, 40), ("L", 43, 40), ("L", 43, 32), ("L", 38, 32),
             ("L", 38, 40), ("L", 26, 40), ("Z",)],
        ],
        "circles": [],
        "lines": [],
    }


def _piece_bishop():
    return {
        "polys": [
            BASE_PATH,
            COLLAR_PATH,
            [("M", 50, 32), ("C", 40, 32, 34, 42, 36, 52), ("C", 37.5, 60, 42, 63, 42, 68),
             ("L", 58, 68), ("C", 58, 63, 62.5, 60, 64, 52), ("C", 66, 42, 60, 32, 50, 32), ("Z",)],
            [("M", 42, 76), ("L", 58, 76), ("L", 56, 68), ("L", 44, 68), ("Z",)],
        ],
        "circles": [(50, 22, 6)],
        "lines": [((41, 46), (57, 58))],
    }


def _piece_knight():
    return {
        "polys": [
            BASE_PATH,
            [("M", 34, 86), ("C", 32, 74, 30, 68, 28, 62), ("C", 26, 56, 27, 50, 32, 46),
             ("C", 30, 42, 30, 38, 33, 35), ("C", 36, 32, 40, 32, 42, 34),
             ("C", 46, 29, 53, 27, 60, 29), ("C", 68, 31, 74, 38, 75, 47),
             ("C", 76, 54, 74, 58, 70, 60), ("C", 71, 64, 70, 68, 66, 70),
             ("C", 68, 76, 70, 81, 71, 86), ("Z",)],
            [("M", 56, 33), ("L", 63, 30), ("L", 60, 37), ("Z",)],
        ],
        "circles": [(37.3, 37.3, 1.8)],
        "lines": [],
    }


def _piece_queen():
    return {
        "polys": [
            BASE_PATH,
            COLLAR_PATH,
            [("M", 34, 76), ("L", 66, 76), ("L", 62, 54), ("L", 38, 54), ("Z",)],
            [("M", 30, 54), ("L", 70, 54), ("L", 67, 42), ("L", 33, 42), ("Z",)],
        ],
        "circles": [(30, 34, 5.5), (41.5, 28, 5.5), (50, 25, 5.5), (58.5, 28, 5.5), (70, 34, 5.5)],
        "lines": [],
    }


def _piece_king():
    return {
        "polys": [
            BASE_PATH,
            COLLAR_PATH,
            [("M", 34, 76), ("L", 66, 76), ("L", 62, 54), ("L", 38, 54), ("Z",)],
            [("M", 30, 54), ("L", 70, 54), ("L", 67, 42), ("L", 33, 42), ("Z",)],
            [("M", 46.5, 12), ("L", 53.5, 12), ("L", 53.5, 32), ("L", 46.5, 32), ("Z",)],
            [("M", 39, 18.5), ("L", 61, 18.5), ("L", 61, 25.5), ("L", 39, 25.5), ("Z",)],
        ],
        "circles": [],
        "lines": [],
    }


PIECE_BUILDERS = {
    "p": _piece_pawn, "r": _piece_rook, "b": _piece_bishop,
    "n": _piece_knight, "q": _piece_queen, "k": _piece_king,
}

WHITE_FILL = (238, 238, 232)
WHITE_OUTLINE = (35, 35, 45)
BLACK_FILL = (46, 48, 58)
BLACK_OUTLINE = (215, 215, 225)


def _draw_piece(size, fill, outline):
    def render(kind):
        big = size * SCALE
        surf = pygame.Surface((big, big), pygame.SRCALPHA)
        geo = PIECE_BUILDERS[kind]()
        px = big / GRID

        for path in geo["polys"]:
            pts = [(x * px, y * px) for x, y in flatten_path(path)]
            if len(pts) >= 3:
                pygame.draw.polygon(surf, fill, pts)
                pygame.draw.polygon(surf, outline, pts, width=max(2, SCALE))

        for cx, cy, r in geo["circles"]:
            center = (cx * px, cy * px)
            radius = r * px
            pygame.draw.circle(surf, fill, center, radius)
            pygame.draw.circle(surf, outline, center, radius, width=max(2, SCALE))

        for (x1, y1), (x2, y2) in geo["lines"]:
            pygame.draw.line(surf, outline, (x1 * px, y1 * px), (x2 * px, y2 * px),
                              width=max(2, SCALE))

        return pygame.transform.smoothscale(surf, (size, size))

    return render


def build_piece_surfaces(size):
    """Returns a dict {"wp": Surface, "bn": Surface, ...} of piece images."""
    surfaces = {}
    white_renderer = _draw_piece(size, WHITE_FILL, WHITE_OUTLINE)
    black_renderer = _draw_piece(size, BLACK_FILL, BLACK_OUTLINE)
    for kind in PIECE_BUILDERS:
        surfaces["w" + kind] = white_renderer(kind)
        surfaces["b" + kind] = black_renderer(kind)
    return surfaces
