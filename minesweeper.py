#!/usr/bin/env python3
"""Terminal-based Minesweeper game with curses UI, nerd font glyphs, and color."""

import curses
import random
import sys

# ── Nerd font / Unicode glyphs ────────────────────────────────────────
GLYPH_FLAG = "⚑"
GLYPH_MINE = "✱"
GLYPH_HIDDEN = "■"
GLYPH_EMPTY = "·"
GLYPH_STAR = "★"

# ── Box-drawing characters ────────────────────────────────────────────
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

# ── Color pair IDs ────────────────────────────────────────────────────
COLOR_BORDER = 1
COLOR_NUM1 = 2        # 1 = blue
COLOR_NUM2 = 3        # 2 = green
COLOR_NUM3 = 4        # 3 = red
COLOR_NUM4 = 5        # 4 = dark blue (cyan)
COLOR_NUM5 = 6        # 5 = dark red (magenta)
COLOR_NUM6 = 7        # 6 = teal (cyan bold)
COLOR_NUM7 = 8        # 7 = black (white on default)
COLOR_NUM8 = 9        # 8 = gray
COLOR_HIDDEN = 10
COLOR_FLAG = 11
COLOR_MINE = 12
COLOR_CURSOR = 13
COLOR_TITLE = 14
COLOR_STATUS = 15
COLOR_EMPTY = 16

# Map number values to their color pair IDs
NUM_COLORS = {
    1: COLOR_NUM1,
    2: COLOR_NUM2,
    3: COLOR_NUM3,
    4: COLOR_NUM4,
    5: COLOR_NUM5,
    6: COLOR_NUM6,
    7: COLOR_NUM7,
    8: COLOR_NUM8,
}

# ── Cell rendering ────────────────────────────────────────────────────
CELL_W = 4  # Characters per cell (includes padding)


def init_colors():
    """Initialize curses color pairs."""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(COLOR_BORDER, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_NUM1, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_NUM2, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_NUM3, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_NUM4, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_NUM5, curses.COLOR_MAGENTA, -1)
    curses.init_pair(COLOR_NUM6, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_NUM7, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_NUM8, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_HIDDEN, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_FLAG, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_MINE, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_CURSOR, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(COLOR_TITLE, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_STATUS, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_EMPTY, curses.COLOR_WHITE, -1)


def safe_addstr(win, y, x, text, attr=0):
    """addstr that silently ignores curses errors at screen edges."""
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


# ── Game Logic ────────────────────────────────────────────────────────

DIFFICULTIES = {
    "easy": (9, 9, 10),
    "medium": (16, 16, 40),
    "hard": (16, 30, 99),
}


def create_board(rows, cols):
    """Create an empty board grid."""
    return [[0] * cols for _ in range(rows)]


def place_mines(grid, rows, cols, num_mines, safe_r=-1, safe_c=-1):
    """Place mines randomly, avoiding the safe cell and its neighbors."""
    safe_zone = set()
    if safe_r >= 0 and safe_c >= 0:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = safe_r + dr, safe_c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    safe_zone.add((nr, nc))

    positions = [(r, c) for r in range(rows) for c in range(cols)
                 if (r, c) not in safe_zone]
    mine_positions = random.sample(positions, min(num_mines, len(positions)))
    for r, c in mine_positions:
        grid[r][c] = -1
    return mine_positions


def calc_counts(grid, rows, cols):
    """Calculate neighbor mine counts for each non-mine cell."""
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == -1:
                continue
            count = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == -1:
                        count += 1
            grid[r][c] = count


def flood_fill(grid, revealed, flagged, rows, cols, r, c):
    """Reveal cells recursively for empty (0-count) cells."""
    if not (0 <= r < rows and 0 <= c < cols):
        return
    if revealed[r][c] or flagged[r][c]:
        return
    if grid[r][c] == -1:
        return

    revealed[r][c] = True

    if grid[r][c] == 0:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                flood_fill(grid, revealed, flagged, rows, cols, r + dr, c + dc)


def reveal_cell(grid, revealed, flagged, rows, cols, r, c):
    """Reveal a cell. Returns True if a mine was hit."""
    if flagged[r][c] or revealed[r][c]:
        return False
    if grid[r][c] == -1:
        revealed[r][c] = True
        return True
    flood_fill(grid, revealed, flagged, rows, cols, r, c)
    return False


def toggle_flag(revealed, flagged, r, c):
    """Toggle flag on an unrevealed cell."""
    if revealed[r][c]:
        return
    flagged[r][c] = not flagged[r][c]


def check_win(grid, revealed, rows, cols):
    """Check if all non-mine cells are revealed."""
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != -1 and not revealed[r][c]:
                return False
    return True


def count_flags(flagged, rows, cols):
    """Count the number of flagged cells."""
    return sum(flagged[r][c] for r in range(rows) for c in range(cols))


def reveal_all_mines(grid, revealed, rows, cols):
    """Reveal all mine cells (called on game over)."""
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == -1:
                revealed[r][c] = True


def get_cell_display(grid, revealed, flagged, r, c):
    """Return (text, color_pair_id, bold) for a cell."""
    if flagged[r][c] and not revealed[r][c]:
        return GLYPH_FLAG, COLOR_FLAG, True
    if not revealed[r][c]:
        return GLYPH_HIDDEN, COLOR_HIDDEN, False
    if grid[r][c] == -1:
        return GLYPH_MINE, COLOR_MINE, True
    if grid[r][c] == 0:
        return GLYPH_EMPTY, COLOR_EMPTY, False
    num = grid[r][c]
    return str(num), NUM_COLORS.get(num, COLOR_STATUS), True


# ── Drawing ───────────────────────────────────────────────────────────

def build_hline(cols, left, mid, right, fill):
    """Build a horizontal border line: left + (fill * w + mid) * (n-1) + fill * w + right."""
    w = CELL_W - 1
    line = left
    for c in range(cols):
        line += fill * w
        line += mid if c < cols - 1 else right
    return line


def draw_board(win, grid, revealed, flagged, rows, cols, cursor_r, cursor_c,
               by, bx):
    """Draw the minefield with box-drawing borders."""
    border_attr = curses.color_pair(COLOR_BORDER) | curses.A_BOLD
    cw = CELL_W - 1  # inner cell width (characters of content per cell)

    # Column numbers — center each number over its cell
    for c in range(cols):
        cx = bx + 1 + c * CELL_W + cw // 2
        label = str(c)
        safe_addstr(win, by - 1, cx - len(label) // 2, label, border_attr)

    # Top border
    safe_addstr(win, by, bx, build_hline(cols, BOX_TL, BOX_TM, BOX_TR, BOX_H),
                border_attr)

    # Rows
    for r in range(rows):
        y = by + 1 + r * 2

        # Row label
        safe_addstr(win, y, bx - 3, f"{r:>2} ", border_attr)

        # Build cell row character by character
        safe_addstr(win, y, bx, BOX_V, border_attr)
        for c in range(cols):
            text, color_id, bold = get_cell_display(grid, revealed, flagged, r, c)
            attr = curses.color_pair(color_id)
            if bold:
                attr |= curses.A_BOLD
            if r == cursor_r and c == cursor_c:
                attr = curses.color_pair(COLOR_CURSOR) | curses.A_BOLD

            cell_x = bx + 1 + c * CELL_W
            cell_content = text.center(cw)
            safe_addstr(win, y, cell_x, cell_content, attr)
            # Column separator or right border
            safe_addstr(win, y, cell_x + cw, BOX_V, border_attr)

        # Horizontal separator between rows
        if r < rows - 1:
            sep_y = by + 2 + r * 2
            safe_addstr(win, sep_y, bx,
                        build_hline(cols, BOX_LM, BOX_X, BOX_RM, BOX_H),
                        border_attr)

    # Bottom border
    bot_y = by + rows * 2
    safe_addstr(win, bot_y, bx,
                build_hline(cols, BOX_BL, BOX_BM, BOX_BR, BOX_H),
                border_attr)


def draw_title(win, y, x):
    """Draw the game title."""
    title = f"          {GLYPH_STAR} MINESWEEPER {GLYPH_STAR} "
    safe_addstr(win, y, x, title,
                curses.color_pair(COLOR_TITLE) | curses.A_BOLD)


def difficulty_menu(stdscr):
    """Show a difficulty selection screen. Returns the chosen difficulty key."""
    options = list(DIFFICULTIES.keys())
    descriptions = {
        "easy": "9x9 board, 10 mines",
        "medium": "16x16 board, 40 mines",
        "hard": "16x30 board, 99 mines",
    }
    selected = 0

    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        # Title
        title = f"{GLYPH_STAR} MINESWEEPER {GLYPH_STAR}"
        tx = max(0, (max_x - len(title)) // 2)
        safe_addstr(stdscr, 2, tx, title,
                    curses.color_pair(COLOR_TITLE) | curses.A_BOLD)

        # Subtitle
        sub = "Select Difficulty"
        sx = max(0, (max_x - len(sub)) // 2)
        safe_addstr(stdscr, 4, sx, sub, curses.color_pair(COLOR_STATUS))

        # Options
        for i, opt in enumerate(options):
            label = f"  {opt.upper():8s} - {descriptions[opt]}"
            if i == selected:
                attr = curses.color_pair(COLOR_CURSOR) | curses.A_BOLD
                label = "> " + label[2:]
            else:
                attr = curses.color_pair(COLOR_STATUS)
            ox = max(0, (max_x - 36) // 2)
            safe_addstr(stdscr, 7 + i * 2, ox, label, attr)

        # Terminal size warning
        warn = "NOTE: Medium and Hard require a larger terminal window."
        wx = max(0, (max_x - len(warn)) // 2)
        safe_addstr(stdscr, 14, wx, warn,
                    curses.color_pair(COLOR_FLAG) | curses.A_BOLD)

        # Instructions
        hint = "Arrow keys: select   Enter: confirm   Q: quit"
        hx = max(0, (max_x - len(hint)) // 2)
        safe_addstr(stdscr, 16, hx, hint, curses.color_pair(COLOR_STATUS))

        stdscr.refresh()

        ch = stdscr.getch()
        if ch == curses.KEY_UP:
            selected = (selected - 1) % len(options)
        elif ch == curses.KEY_DOWN:
            selected = (selected + 1) % len(options)
        elif ch in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            return options[selected]
        elif ch in (ord('q'), ord('Q')):
            return None


def draw_status(win, y, x, mines_remaining, game_over, won):
    """Draw status line with mine count and game state."""
    status = f"Mines: {mines_remaining}"
    safe_addstr(win, y, x, status,
                curses.color_pair(COLOR_FLAG) | curses.A_BOLD)

    if game_over:
        msg = " BOOM! Game Over! "
        safe_addstr(win, y + 1, x, msg,
                    curses.color_pair(COLOR_MINE) | curses.A_BOLD)
        safe_addstr(win, y + 2, x, "Press 'n' for new game, 'q' to quit",
                    curses.color_pair(COLOR_STATUS))
    elif won:
        msg = " YOU WIN! "
        safe_addstr(win, y + 1, x, msg,
                    curses.color_pair(COLOR_NUM2) | curses.A_BOLD)
        safe_addstr(win, y + 2, x, "Press 'n' for new game, 'q' to quit",
                    curses.color_pair(COLOR_STATUS))
    else:
        controls = "Arrow keys: move  Space: reveal  F: flag  Q: quit"
        safe_addstr(win, y + 1, x, controls,
                    curses.color_pair(COLOR_STATUS))


# ── Main ──────────────────────────────────────────────────────────────

def main(stdscr):
    """Main game loop with curses UI."""
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    init_colors()

    difficulty = difficulty_menu(stdscr)
    if difficulty is None:
        return
    rows, cols, num_mines = DIFFICULTIES[difficulty]

    def new_game():
        grid = create_board(rows, cols)
        revealed = [[False] * cols for _ in range(rows)]
        flagged = [[False] * cols for _ in range(rows)]
        return grid, revealed, flagged, False, False, True

    grid, revealed, flagged, game_over, won, first_move = new_game()
    cursor_r, cursor_c = 0, 0

    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        # Board dimensions
        board_w = cols * CELL_W + 1  # cols cells + (cols+1) separators = cols*(cw+1)+1
        board_h = rows * 2 + 1      # top border + rows*2 (cell + sep) - last sep + bot

        # Position board centered, with room for title and status
        bx = max(4, (max_x - board_w) // 2)
        by = 4  # Leave room for title

        # Draw UI
        draw_title(stdscr, 1, bx)
        draw_board(stdscr, grid, revealed, flagged, rows, cols,
                   cursor_r, cursor_c, by, bx)

        mines_remaining = num_mines - count_flags(flagged, rows, cols)
        status_y = by + rows * 2 + 2
        draw_status(stdscr, status_y, bx, mines_remaining, game_over, won)

        stdscr.refresh()

        ch = stdscr.getch()

        # Quit
        if ch in (ord('q'), ord('Q')):
            break

        # New game
        if ch in (ord('n'), ord('N')):
            grid, revealed, flagged, game_over, won, first_move = new_game()
            cursor_r, cursor_c = 0, 0
            continue

        # Return to difficulty menu
        if ch in (ord('d'), ord('D')) and (game_over or won or first_move):
            difficulty = difficulty_menu(stdscr)
            if difficulty is None:
                break
            rows, cols, num_mines = DIFFICULTIES[difficulty]
            grid, revealed, flagged, game_over, won, first_move = new_game()
            cursor_r, cursor_c = 0, 0
            continue

        if game_over or won:
            continue

        # Arrow key navigation
        if ch == curses.KEY_UP:
            cursor_r = max(0, cursor_r - 1)
        elif ch == curses.KEY_DOWN:
            cursor_r = min(rows - 1, cursor_r + 1)
        elif ch == curses.KEY_LEFT:
            cursor_c = max(0, cursor_c - 1)
        elif ch == curses.KEY_RIGHT:
            cursor_c = min(cols - 1, cursor_c + 1)

        # Space bar to reveal
        elif ch == ord(' '):
            if first_move:
                place_mines(grid, rows, cols, num_mines, cursor_r, cursor_c)
                calc_counts(grid, rows, cols)
                first_move = False
            hit = reveal_cell(grid, revealed, flagged, rows, cols,
                              cursor_r, cursor_c)
            if hit:
                game_over = True
                reveal_all_mines(grid, revealed, rows, cols)
            elif check_win(grid, revealed, rows, cols):
                won = True

        # F to flag
        elif ch in (ord('f'), ord('F')):
            if not first_move:
                toggle_flag(revealed, flagged, cursor_r, cursor_c)


if __name__ == "__main__":
    curses.wrapper(main)
