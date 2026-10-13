"""Welcome screen renderables."""

from __future__ import annotations

from rich.align import Align
from rich.text import Text

WELCOME_LOGO_PALETTE = {
    "K": "#0d2b3a",
    "C": "#3f97bd",
    "B": "#7cc7e4",
    "W": "#eefcff",
    "P": "#b8ffdf",
    "Q": "#45e6df",
}

WELCOME_LOGO_PIXELS = (
    "..............KKKBCCBBBKKK",
    "............KKBCCCBBBCCCCBKK",
    "..........KKCCBBWWWWWWWBBCCBKK",
    ".........KBCBWWWWWWWWWWWWWBCCBKKKKKKKK",
    "........KCCBWWWWWWWWWWWWWWWWBBCCCKBBBBKK",
    ".......KCBWWWWWWWWWWWWWWWWWWWWWBBCCCCCCB",
    "......KCBWWWWWWWWWWWWWWWWWWWWWWWWWWWWWBC",
    ".....KCBWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWBC",
    "....KCBWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWBB",
    "...KCBWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWCK",
    "..KCBWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWCKK",
    ".KBCWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWBCBK",
    ".KCWWWWWWWWWWWWWWWWWWWWBBBBWWWWWWBCCBK",
    "KCBWWWWWWWWWWWWWWWWWWBWWBCCCCCCCKKKCK",
    "BCWWWWWWWWWWWWWWWWWWBWWBWWBBBBBBBWWCKK",
    "CBWWWWWWWWWWWWWWWWWBWWWWWWWWWWWWWWWBCK",
    "CBWWWWWWWWWWWWWWWWWWWWWWWBBBBBBBBBWBCK",
    "BBWWWWWWWWWWWWWWWWBBBWWBBWBBBBBBBBWBBK",
    "KCBWWWWWWWWWWWBBWWBBWWBWBCWWBBBBWWBCK",
    "KCBWWWWWWWWWWBWWWBWWWBWWWCCBBWWWBBCK",
    ".KCBWWWWWWWWBWWWBBWBBWWBBWBCCCBBCBK",
    ".KBCWWWWWWWWWWWWBBWBWWBBBBWBBCKBKK",
    "..KCBWWWWWWWWWWWBBWWWBBBBBBBBBCK",
    "...KCBWWWWWWWWWWBBBBBBBBBBBBBBCK",
    "...KKCWWWWWWWWWWBBBBBWBBBBBBWBBK",
    "....KBCWWWWWWWWWBBBBCBWBBBBWBCK",
    ".....KKBWWWWWWWWBBBBBKCBBBWBCKK",
    "......KCBWWWWWWWBBBBWBCCCCCCBK",
    ".......KCCWWWWWWBBBBWBBKKKKKK",
    "........KCCBWWWBBBBBBCK",
    ".........KBCCBBWWBBBCKK",
    "..........KKBCCCBBBCBK",
    "............KKKBCCCKK",
)

WELCOME_PARTICLE_FRAMES = (
    ((6, 3, "P"), (11, 26, "Q"), (25, 29, "P"), (37, 4, "P")),
    ((5, 5, "Q"), (14, 1, "P"), (28, 30, "Q"), (38, 23, "P")),
    ((4, 2, "P"), (10, 24, "P"), (21, 31, "Q"), (35, 28, "P")),
    ((7, 1, "Q"), (16, 29, "P"), (31, 2, "P"), (39, 18, "Q")),
)


def welcome_renderable(*, compact: bool = False, particle_frame: int = 0) -> Align:
    """Render the animated logo, or a small-screen wordmark when space is tight."""
    if compact:
        return Align.center(
            Text.assemble(
                ("first", "#81e8bb bold"),
                ("coder", "#18cfcb bold"),
                ("\nlocal coding agent", "#6e6d72"),
            )
        )
    rows = [list(row) for row in WELCOME_LOGO_PIXELS]
    frame = WELCOME_PARTICLE_FRAMES[particle_frame % len(WELCOME_PARTICLE_FRAMES)]
    for row_index, column_index, pixel in frame:
        if not 0 <= row_index < len(rows):
            continue
        row = rows[row_index]
        if column_index >= len(row):
            row.extend("." for _ in range(column_index - len(row) + 1))
        if row[column_index] == ".":
            row[column_index] = pixel

    text = Text()
    for row_index, row in enumerate(rows):
        if row_index:
            text.append("\n")
        for pixel in row:
            color = WELCOME_LOGO_PALETTE.get(pixel)
            text.append("██" if color else "  ", style=color)
    return Align.center(text)
