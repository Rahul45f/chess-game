"""
Original SVG chess piece artwork, hand-authored (not traced from any existing
piece set) as smooth Staunton-style silhouettes. Each piece is a 100x100
viewBox path/shape recipe; colour is injected per side when rendered.
"""

# Shared elements, expressed as format strings taking {fill} and {outline}.
BASE = '<path d="M22 90 Q22 86 26 86 L74 86 Q78 86 78 90 L78 93 Q78 96 74 96 L26 96 Q22 96 22 93 Z" fill="{fill}" stroke="{outline}" stroke-width="2.4"/>'
COLLAR = '<path d="M28 80 Q28 76 32 76 L68 76 Q72 76 72 80 L72 84 Q72 87 68 87 L32 87 Q28 87 28 84 Z" fill="{fill}" stroke="{outline}" stroke-width="2.4"/>'


def _piece(inner):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        + inner +
        '</svg>'
    )


def pawn_svg():
    return _piece(
        BASE +
        '<path d="M35 86 L65 86 L60 68 L40 68 Z" fill="{fill}" stroke="{outline}" stroke-width="2.4"/>'
        '<circle cx="50" cy="60" r="6.5" fill="{fill}" stroke="{outline}" stroke-width="2.4"/>'
        '<circle cx="50" cy="40" r="14" fill="{fill}" stroke="{outline}" stroke-width="2.6"/>'
    )


def rook_svg():
    return _piece(
        BASE +
        '<path d="M30 86 L30 50 L70 50 L70 86 Z" fill="{fill}" stroke="{outline}" stroke-width="2.4"/>'
        '<path d="M26 50 L74 50 L74 40 L62 40 L62 32 L57 32 L57 40 L43 40 L43 32 L38 32 L38 40 L26 40 Z" '
        'fill="{fill}" stroke="{outline}" stroke-width="2.4" stroke-linejoin="round"/>'
    )


def bishop_svg():
    return _piece(
        BASE + COLLAR +
        '<path d="M50 32 C40 32 34 42 36 52 C37.5 60 42 63 42 68 L58 68 C58 63 62.5 60 64 52 '
        'C66 42 60 32 50 32 Z" fill="{fill}" stroke="{outline}" stroke-width="2.4" stroke-linejoin="round"/>'
        '<path d="M42 76 L58 76 L56 68 L44 68 Z" fill="{fill}" stroke="{outline}" stroke-width="2.4"/>'
        '<line x1="41" y1="46" x2="57" y2="58" stroke="{outline}" stroke-width="2.6" stroke-linecap="round"/>'
        '<circle cx="50" cy="22" r="6" fill="{fill}" stroke="{outline}" stroke-width="2.4"/>'
    )


def knight_svg():
    return _piece(
        BASE +
        '<path d="M34 86 C32 74 30 68 28 62 C26 56 27 50 32 46 C30 42 30 38 33 35 '
        'C36 32 40 32 42 34 C46 29 53 27 60 29 C68 31 74 38 75 47 C76 54 74 58 70 60 '
        'C71 64 70 68 66 70 C68 76 70 81 71 86 Z" '
        'fill="{fill}" stroke="{outline}" stroke-width="2.4" stroke-linejoin="round"/>'
        '<path d="M37 40 C35.5 38.5 35.5 36.5 37 35.5 C38.5 34.5 40.5 35.5 40.5 37.5 '
        'C40.5 39 39 40.5 37 40 Z" fill="{outline}"/>'
        '<path d="M56 33 L63 30 L60 37 Z" fill="{fill}" stroke="{outline}" stroke-width="1.6" stroke-linejoin="round"/>'
    )


def queen_svg():
    return _piece(
        BASE + COLLAR +
        '<path d="M34 76 L66 76 L62 54 L38 54 Z" fill="{fill}" stroke="{outline}" stroke-width="2.4"/>'
        '<path d="M30 54 L70 54 L67 42 L33 42 Z" fill="{fill}" stroke="{outline}" stroke-width="2.4" '
        'stroke-linejoin="round"/>'
        '<circle cx="30" cy="34" r="5.5" fill="{fill}" stroke="{outline}" stroke-width="2.2"/>'
        '<circle cx="41.5" cy="28" r="5.5" fill="{fill}" stroke="{outline}" stroke-width="2.2"/>'
        '<circle cx="50" cy="25" r="5.5" fill="{fill}" stroke="{outline}" stroke-width="2.2"/>'
        '<circle cx="58.5" cy="28" r="5.5" fill="{fill}" stroke="{outline}" stroke-width="2.2"/>'
        '<circle cx="70" cy="34" r="5.5" fill="{fill}" stroke="{outline}" stroke-width="2.2"/>'
    )


def king_svg():
    return _piece(
        BASE + COLLAR +
        '<path d="M34 76 L66 76 L62 54 L38 54 Z" fill="{fill}" stroke="{outline}" stroke-width="2.4"/>'
        '<path d="M30 54 L70 54 L67 42 L33 42 Z" fill="{fill}" stroke="{outline}" stroke-width="2.4" '
        'stroke-linejoin="round"/>'
        '<rect x="46.5" y="12" width="7" height="20" rx="1.5" fill="{fill}" stroke="{outline}" stroke-width="2.2"/>'
        '<rect x="39" y="18.5" width="22" height="7" rx="1.5" fill="{fill}" stroke="{outline}" stroke-width="2.2"/>'
    )


SVG_BUILDERS = {
    "p": pawn_svg,
    "r": rook_svg,
    "b": bishop_svg,
    "n": knight_svg,
    "q": queen_svg,
    "k": king_svg,
}

WHITE_FILL = "#EEEEE8"
WHITE_OUTLINE = "#23232D"
BLACK_FILL = "#2E303A"
BLACK_OUTLINE = "#D7D7E1"


def get_svg(kind, color):
    """Returns the full SVG markup (string) for a piece kind ('p','n',...) and
    color ('w' or 'b')."""
    template = SVG_BUILDERS[kind]()
    fill, outline = (WHITE_FILL, WHITE_OUTLINE) if color == "w" else (BLACK_FILL, BLACK_OUTLINE)
    return template.format(fill=fill, outline=outline)
