#!/usr/bin/env python3
"""
2048 Game — Terminal 2048 with curses.
Features:
- Arrow keys / WASD movement for sliding tiles
- Distinct color per tile value (classic 2048 palette)
- Nerd font glyphs and Unicode symbols for tile decorations
- Merge animation with flash/highlight effect
- Box-drawing borders with double-line grid
- Score and best score tracking
- Win detection at 2048 tile
- Game over detection when no moves remain
"""

import curses
import os
import random
import time

BEST_SCORE_FILE = os.path.expanduser("~/shelly-ops/scripts/.game2048-best.txt")

# Board constants
BOARD_SIZE = 4
TILE_WIDTH = 8
TILE_HEIGHT = 3

# Color pair IDs — one per tile value
COLOR_BORDER = 1
COLOR_EMPTY = 2
COLOR_2 = 3
COLOR_4 = 4
COLOR_8 = 5
COLOR_16 = 6
COLOR_32 = 7
COLOR_64 = 8
COLOR_128 = 9
COLOR_256 = 10
COLOR_512 = 11
COLOR_1024 = 12
COLOR_2048 = 13
COLOR_SUPER = 14
COLOR_TITLE = 15
COLOR_SCORE = 16
COLOR_TEXT = 17

# Nerd font / Unicode glyphs
GLYPH_STAR = "★"
GLYPH_DIAMOND = "◆"
GLYPH_CIRCLE = "●"
GLYPH_SPARKLE = "✦"
GLYPH_TROPHY = "🏆"
GLYPH_ARROW_UP = "▲"
GLYPH_ARROW_DN = "▼"
GLYPH_BLOCK = "█"

# Box-drawing characters (double-line)
BOX_TL = "╔"
BOX_TR = "╗"
BOX_BL = "╚"
BOX_BR = "╝"
BOX_H = "═"
BOX_V = "║"
BOX_TM = "╦"
BOX_BM = "╩"
BOX_LM = "╠"
BOX_RM = "╣"
BOX_X = "╬"

# Map tile value -> color pair ID
TILE_COLOR_MAP = {
    0: COLOR_EMPTY,
    2: COLOR_2,
    4: COLOR_4,
    8: COLOR_8,
    16: COLOR_16,
    32: COLOR_32,
    64: COLOR_64,
    128: COLOR_128,
    256: COLOR_256,
    512: COLOR_512,
    1024: COLOR_1024,
    2048: COLOR_2048,
}

# Map tile value -> glyph decoration (for high tiles)
TILE_GLYPH_MAP = {
    128: GLYPH_CIRCLE,
    256: GLYPH_DIAMOND,
    512: GLYPH_STAR,
    1024: GLYPH_SPARKLE,
    2048: GLYPH_STAR,
}


def init_colors():
    """Initialize curses color pairs for all tile values."""
    curses.start_color()
    curses.use_default_colors()

    # Border and UI colors
    curses.init_pair(COLOR_BORDER, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_EMPTY, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_TITLE, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_SCORE, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_TEXT, curses.COLOR_WHITE, -1)

    # Tile colors — distinct per value
    curses.init_pair(COLOR_2, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_4, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_8, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_16, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_32, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_64, curses.COLOR_MAGENTA, -1)
    curses.init_pair(COLOR_128, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_256, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_512, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_1024, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_2048, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_SUPER, curses.COLOR_MAGENTA, -1)


def load_best_score():
    """Load best score from file, return 0 if not found."""
    try:
        with open(BEST_SCORE_FILE) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_best_score(best):
    """Save best score to file."""
    with open(BEST_SCORE_FILE, "w") as f:
        f.write(str(best))


def new_board():
    """Create an empty 4x4 board."""
    return [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]


def new_board_copy(board):
    """Deep copy a board."""
    return [row[:] for row in board]


def empty_cells(board):
    """Return list of (row, col) for all empty cells."""
    return [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE)
            if board[r][c] == 0]


def add_random_tile(board):
    """Place a 2 (90% chance) or 4 (10% chance) on a random empty cell."""
    cells = empty_cells(board)
    if not cells:
        return
    r, c = random.choice(cells)
    board[r][c] = 2 if random.random() < 0.9 else 4


def slide_row_left(row):
    """Slide and merge a single row to the left. Return (new_row, score, merged_indices)."""
    tiles = [v for v in row if v != 0]
    merged = []
    merged_positions = []
    score = 0
    skip = False
    for i in range(len(tiles)):
        if skip:
            skip = False
            continue
        if i + 1 < len(tiles) and tiles[i] == tiles[i + 1]:
            merged.append(tiles[i] * 2)
            merged_positions.append(len(merged) - 1)
            score += tiles[i] * 2
            skip = True
        else:
            merged.append(tiles[i])
    merged += [0] * (BOARD_SIZE - len(merged))
    return merged, score, merged_positions


def move(board, direction):
    """Apply a move. Returns (new_board, score, changed, merged_cells)."""
    score = 0
    nb = new_board_copy(board)
    changed = False
    merged_cells = []

    if direction == "left":
        for r in range(BOARD_SIZE):
            new_row, s, mp = slide_row_left(nb[r])
            if new_row != nb[r]:
                changed = True
            nb[r] = new_row
            score += s
            for c in mp:
                merged_cells.append((r, c))
    elif direction == "right":
        for r in range(BOARD_SIZE):
            row_rev = nb[r][::-1]
            new_row, s, mp = slide_row_left(row_rev)
            new_row = new_row[::-1]
            if new_row != nb[r]:
                changed = True
            nb[r] = new_row
            score += s
            for c in mp:
                merged_cells.append((r, BOARD_SIZE - 1 - c))
    elif direction == "up":
        for c in range(BOARD_SIZE):
            col = [nb[r][c] for r in range(BOARD_SIZE)]
            new_col, s, mp = slide_row_left(col)
            for r in range(BOARD_SIZE):
                if nb[r][c] != new_col[r]:
                    changed = True
                nb[r][c] = new_col[r]
            score += s
            for r in mp:
                merged_cells.append((r, c))
    elif direction == "down":
        for c in range(BOARD_SIZE):
            col = [nb[r][c] for r in range(BOARD_SIZE)][::-1]
            new_col, s, mp = slide_row_left(col)
            new_col = new_col[::-1]
            for r in range(BOARD_SIZE):
                if nb[r][c] != new_col[r]:
                    changed = True
                nb[r][c] = new_col[r]
            score += s
            for r in mp:
                merged_cells.append((BOARD_SIZE - 1 - r, c))

    return nb, score, changed, merged_cells


def has_moves(board):
    """Check if any moves are possible."""
    if empty_cells(board):
        return True
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            val = board[r][c]
            if c + 1 < BOARD_SIZE and board[r][c + 1] == val:
                return True
            if r + 1 < BOARD_SIZE and board[r + 1][c] == val:
                return True
    return False


def has_won(board):
    """Check if 2048 tile exists."""
    return any(val >= 2048 for row in board for val in row)


def get_tile_color(value):
    """Return the curses color pair for a given tile value."""
    pair_id = TILE_COLOR_MAP.get(value, COLOR_SUPER)
    return curses.color_pair(pair_id)


def get_tile_attr(value):
    """Return curses attribute for a tile (bold for high values)."""
    attr = get_tile_color(value)
    if value >= 64:
        attr |= curses.A_BOLD
    return attr


def draw_grid(stdscr, y, x):
    """Draw the box-drawing border grid for the 4x4 board."""
    w = TILE_WIDTH
    h = TILE_HEIGHT
    total_w = BOARD_SIZE * w + BOARD_SIZE + 1
    border_attr = curses.color_pair(COLOR_BORDER)

    try:
        # Top border
        top = BOX_TL + (BOX_H * w + BOX_TM) * (BOARD_SIZE - 1) + BOX_H * w + BOX_TR
        stdscr.addstr(y, x, top, border_attr)

        for row in range(BOARD_SIZE):
            # Tile rows
            for dy in range(h):
                ry = y + 1 + row * (h + 1) + dy
                stdscr.addstr(ry, x, BOX_V, border_attr)
                for col in range(BOARD_SIZE):
                    cx = x + 1 + col * (w + 1)
                    stdscr.addstr(ry, cx + w, BOX_V, border_attr)

            # Row separator or bottom border
            if row < BOARD_SIZE - 1:
                sep = BOX_LM + (BOX_H * w + BOX_X) * (BOARD_SIZE - 1) + BOX_H * w + BOX_RM
                sy = y + 1 + (row + 1) * (h + 1) - 1
                stdscr.addstr(sy, x, sep, border_attr)

        # Bottom border
        bot = BOX_BL + (BOX_H * w + BOX_BM) * (BOARD_SIZE - 1) + BOX_H * w + BOX_BR
        by = y + 1 + BOARD_SIZE * (h + 1) - 1
        stdscr.addstr(by, x, bot, border_attr)
    except curses.error:
        pass


def draw_tile(stdscr, y, x, value, highlight=False):
    """Draw a single tile at position (y, x) inside the grid."""
    w = TILE_WIDTH
    h = TILE_HEIGHT
    attr = get_tile_attr(value)

    if highlight:
        attr |= curses.A_REVERSE

    try:
        for dy in range(h):
            if value == 0:
                text = " " * w
                stdscr.addstr(y + dy, x, text, curses.color_pair(COLOR_EMPTY))
            else:
                if dy == h // 2:
                    # Middle row: show value and optional glyph
                    glyph = TILE_GLYPH_MAP.get(value, "")
                    if glyph:
                        label = f"{glyph}{value}{glyph}"
                    else:
                        label = str(value)
                    text = label.center(w)
                    stdscr.addstr(y + dy, x, text, attr)
                else:
                    text = " " * w
                    stdscr.addstr(y + dy, x, text, attr)
    except curses.error:
        pass


def draw_board(stdscr, board, start_y, start_x, merged_cells=None):
    """Draw the full board with grid and tiles."""
    draw_grid(stdscr, start_y, start_x)

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            ty = start_y + 1 + r * (TILE_HEIGHT + 1)
            tx = start_x + 1 + c * (TILE_WIDTH + 1)
            highlight = merged_cells is not None and (r, c) in merged_cells
            draw_tile(stdscr, ty, tx, board[r][c], highlight=highlight)


def draw_score(stdscr, y, x, score, best_score):
    """Draw score and best score line."""
    try:
        stdscr.addstr(y, x, f"Score: {score}", curses.color_pair(COLOR_SCORE) | curses.A_BOLD)
        stdscr.addstr(y, x + 20, f"Best: {best_score}", curses.color_pair(COLOR_SCORE))
    except curses.error:
        pass


def animate_merge(stdscr, board, start_y, start_x, merged_cells):
    """Flash merged tiles briefly to show animation."""
    if not merged_cells:
        return
    # Frame 1: highlight (reverse)
    draw_board(stdscr, board, start_y, start_x, merged_cells=merged_cells)
    stdscr.refresh()
    time.sleep(0.06)
    # Frame 2: normal
    draw_board(stdscr, board, start_y, start_x, merged_cells=None)
    stdscr.refresh()
    time.sleep(0.03)
    # Frame 3: highlight again (quick flash)
    draw_board(stdscr, board, start_y, start_x, merged_cells=merged_cells)
    stdscr.refresh()
    time.sleep(0.04)
    # Final: normal
    draw_board(stdscr, board, start_y, start_x, merged_cells=None)
    stdscr.refresh()


def main(stdscr):
    """Main game loop."""
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    init_colors()

    max_y, max_x = stdscr.getmaxyx()
    grid_h = BOARD_SIZE * (TILE_HEIGHT + 1) + 1
    grid_w = BOARD_SIZE * (TILE_WIDTH + 1) + 1

    min_h = grid_h + 8
    min_w = grid_w + 4

    if max_y < min_h or max_x < min_w:
        stdscr.addstr(0, 0, "Terminal too small!", curses.color_pair(COLOR_TITLE))
        stdscr.addstr(1, 0, f"Need at least {min_h}x{min_w}, got {max_y}x{max_x}",
                       curses.color_pair(COLOR_TEXT))
        stdscr.addstr(2, 0, "Press 'q' to quit", curses.color_pair(COLOR_TEXT))
        while True:
            ch = stdscr.getch()
            if ch == ord('q') or ch == ord('Q'):
                return

    start_y = max(0, (max_y - grid_h) // 2 - 2)
    start_x = max(0, (max_x - grid_w) // 2)

    board = new_board()
    add_random_tile(board)
    add_random_tile(board)
    score = 0
    best_score = load_best_score()
    won = False

    key_map = {
        curses.KEY_UP: "up",
        curses.KEY_DOWN: "down",
        curses.KEY_LEFT: "left",
        curses.KEY_RIGHT: "right",
        ord('w'): "up",
        ord('s'): "down",
        ord('a'): "left",
        ord('d'): "right",
    }

    while True:
        stdscr.erase()

        # Title
        title = f" {GLYPH_STAR} 2 0 4 8 {GLYPH_STAR} "
        title_x = start_x + (grid_w - len(title)) // 2
        try:
            stdscr.addstr(start_y, max(0, title_x), title,
                          curses.color_pair(COLOR_TITLE) | curses.A_BOLD)
        except curses.error:
            pass

        # Controls
        controls = f"{GLYPH_ARROW_UP}{GLYPH_ARROW_DN} Arrow keys / WASD to move  Q to quit"
        ctrl_x = start_x + (grid_w - len(controls)) // 2
        try:
            stdscr.addstr(start_y + 1, max(0, ctrl_x), controls,
                          curses.color_pair(COLOR_TEXT))
        except curses.error:
            pass

        board_y = start_y + 3
        draw_board(stdscr, board, board_y, start_x)

        score_y = board_y + grid_h + 1
        draw_score(stdscr, score_y, start_x, score, best_score)

        if won:
            try:
                msg = f"{GLYPH_SPARKLE} You reached 2048! Keep playing! {GLYPH_SPARKLE}"
                stdscr.addstr(score_y + 1, start_x, msg,
                              curses.color_pair(COLOR_2048) | curses.A_BOLD)
            except curses.error:
                pass

        stdscr.refresh()

        ch = stdscr.getch()
        if ch == ord('q') or ch == ord('Q'):
            break

        direction = key_map.get(ch)
        if direction is None:
            continue

        new_b, gained, changed, merged_cells = move(board, direction)
        if not changed:
            continue

        board = new_b
        score += gained
        if score > best_score:
            best_score = score
            save_best_score(best_score)

        # Animate merges
        if merged_cells:
            animate_merge(stdscr, board, board_y, start_x, merged_cells)

        add_random_tile(board)

        if not won and has_won(board):
            won = True

        if not has_moves(board):
            stdscr.erase()
            # Draw final state
            try:
                stdscr.addstr(start_y, start_x, f" {GLYPH_STAR} 2 0 4 8 {GLYPH_STAR} ",
                              curses.color_pair(COLOR_TITLE) | curses.A_BOLD)
            except curses.error:
                pass
            draw_board(stdscr, board, board_y, start_x)
            draw_score(stdscr, score_y, start_x, score, best_score)
            try:
                msg = "Game Over! No moves left."
                stdscr.addstr(score_y + 1, start_x, msg,
                              curses.color_pair(COLOR_32) | curses.A_BOLD)
                stdscr.addstr(score_y + 2, start_x, "Press any key to exit...",
                              curses.color_pair(COLOR_TEXT))
            except curses.error:
                pass
            stdscr.refresh()
            stdscr.nodelay(False)
            stdscr.getch()
            break


if __name__ == "__main__":
    curses.wrapper(main)
