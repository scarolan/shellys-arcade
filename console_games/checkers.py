#!/usr/bin/env python3
"""Terminal-based Checkers (Draughts) game with curses, nerd font glyphs, and AI opponent."""

import curses
import random
import sys

# ── Piece symbols (nerd font / Unicode) ─────────────────────────────
GLYPH_RED = "●"        # Red regular piece
GLYPH_RED_KING = "♛"   # Red king
GLYPH_WHITE = "◉"      # White regular piece
GLYPH_WHITE_KING = "♕" # White king
GLYPH_DOT = "·"        # Valid move indicator
GLYPH_DARK_SQ = "░"    # Dark square fill (unused cell)

# Unicode half-block characters for 2-row-tall piece rendering
UPPER_HALF = "▀"
LOWER_HALF = "▄"
FULL_BLOCK = "█"

# ── Box-drawing characters (kept for outer border) ─────────────────
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

# ── Color pair IDs ──────────────────────────────────────────────────
COLOR_DARK_SQ = 1       # Dark board square
COLOR_LIGHT_SQ = 2      # Light board square
COLOR_RED_PIECE = 3     # Red pieces (on dark square)
COLOR_WHITE_PIECE = 4   # White/cream pieces (on dark square)
COLOR_BORDER = 5        # Board border & box-drawing
COLOR_LABEL = 6         # Row/col labels
COLOR_HEADER = 7        # Title / headers
COLOR_STATUS = 8        # Status messages
COLOR_SELECTED = 9      # Selected piece highlight
COLOR_VALID = 10        # Valid move destination highlight
COLOR_MUST_JUMP = 11    # Pieces that must jump highlight
COLOR_AI_MOVE = 12      # AI move flash
COLOR_RED_ON_SEL = 13   # Red piece on selected bg
COLOR_WHITE_ON_SEL = 14 # White piece on selected bg
COLOR_RED_ON_VALID = 15 # Red piece on valid-move bg
COLOR_WHITE_ON_VALID = 16
COLOR_RED_ON_JUMP = 17  # Red piece on must-jump bg
COLOR_WHITE_ON_JUMP = 18
COLOR_RED_ON_CURSOR = 19
COLOR_WHITE_ON_CURSOR = 20
COLOR_RED_SCORE = 21    # Red in score area (default bg)
COLOR_WHITE_SCORE = 22  # White in score area (default bg)


def init_colors():
    """Initialize curses color pairs."""
    curses.start_color()
    curses.use_default_colors()
    # Board squares — brown/tan checkerboard for colorblind friendliness
    curses.init_pair(COLOR_DARK_SQ, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(COLOR_LIGHT_SQ, curses.COLOR_BLACK, curses.COLOR_WHITE)
    # Pieces on dark squares
    curses.init_pair(COLOR_RED_PIECE, curses.COLOR_RED, curses.COLOR_BLUE)
    curses.init_pair(COLOR_WHITE_PIECE, curses.COLOR_WHITE, curses.COLOR_BLUE)
    # Border & chrome
    curses.init_pair(COLOR_BORDER, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_LABEL, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_HEADER, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_STATUS, curses.COLOR_WHITE, -1)
    # Highlights
    curses.init_pair(COLOR_SELECTED, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
    curses.init_pair(COLOR_VALID, curses.COLOR_WHITE, curses.COLOR_CYAN)
    curses.init_pair(COLOR_MUST_JUMP, curses.COLOR_YELLOW, curses.COLOR_BLUE)
    curses.init_pair(COLOR_AI_MOVE, curses.COLOR_BLACK, curses.COLOR_CYAN)
    # Pieces on highlight backgrounds
    curses.init_pair(COLOR_RED_ON_SEL, curses.COLOR_RED, curses.COLOR_MAGENTA)
    curses.init_pair(COLOR_WHITE_ON_SEL, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
    curses.init_pair(COLOR_RED_ON_VALID, curses.COLOR_RED, curses.COLOR_CYAN)
    curses.init_pair(COLOR_WHITE_ON_VALID, curses.COLOR_WHITE, curses.COLOR_CYAN)
    curses.init_pair(COLOR_RED_ON_JUMP, curses.COLOR_RED, curses.COLOR_BLUE)
    curses.init_pair(COLOR_WHITE_ON_JUMP, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(COLOR_RED_ON_CURSOR, curses.COLOR_RED, curses.COLOR_CYAN)
    curses.init_pair(COLOR_WHITE_ON_CURSOR, curses.COLOR_WHITE, curses.COLOR_CYAN)
    # Score area (default terminal bg)
    curses.init_pair(COLOR_RED_SCORE, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_WHITE_SCORE, curses.COLOR_WHITE, -1)


def safe_addstr(win, y, x, text, attr=0):
    """addstr that silently ignores curses errors at screen edges."""
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


# ── Board / Game Logic ──────────────────────────────────────────────

BOARD_SIZE = 8
CELL_W = 3          # Width of each cell in characters
CELL_H = 2          # Height of each cell in rows


def make_board():
    """Create an 8×8 board with initial piece placement.

    Board layout:
        Rows 0-2: red pieces (top, AI)
        Rows 5-7: white pieces (bottom, human)
    Pieces on dark squares only ((r+c) % 2 == 1).
    None = empty, 'r' = red, 'R' = red king, 'w' = white, 'W' = white king.
    """
    board = [[None] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    for r in range(3):
        for c in range(BOARD_SIZE):
            if (r + c) % 2 == 1:
                board[r][c] = "r"
    for r in range(5, BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if (r + c) % 2 == 1:
                board[r][c] = "w"
    return board


def get_directions(piece):
    """Return valid move directions for a piece."""
    if piece == "r":
        return [(1, -1), (1, 1)]
    elif piece == "w":
        return [(-1, -1), (-1, 1)]
    else:  # Kings
        return [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def get_simple_moves(board, row, col):
    """Get non-jump moves for a piece at (row, col)."""
    piece = board[row][col]
    if not piece:
        return []
    moves = []
    for dr, dc in get_directions(piece):
        nr, nc = row + dr, col + dc
        if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] is None:
            moves.append((nr, nc))
    return moves


def get_jumps(board, row, col):
    """Get jump moves for a piece.  Returns list of (land_r, land_c, mid_r, mid_c)."""
    piece = board[row][col]
    if not piece:
        return []
    opponent = "w" if piece.lower() == "r" else "r"
    jumps = []
    for dr, dc in get_directions(piece):
        mr, mc = row + dr, col + dc
        lr, lc = row + 2 * dr, col + 2 * dc
        if (0 <= lr < BOARD_SIZE and 0 <= lc < BOARD_SIZE
                and board[mr][mc] is not None
                and board[mr][mc].lower() == opponent
                and board[lr][lc] is None):
            jumps.append((lr, lc, mr, mc))
    return jumps


def get_all_moves(board, player):
    """Return (jumps, simple_moves) for *player* ('r' or 'w').

    Each jump:  (from_r, from_c, land_r, land_c, mid_r, mid_c)
    Each move:  (from_r, from_c, to_r, to_c)
    """
    jumps = []
    moves = []
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            p = board[r][c]
            if p and p.lower() == player:
                for lr, lc, mr, mc in get_jumps(board, r, c):
                    jumps.append((r, c, lr, lc, mr, mc))
                for nr, nc in get_simple_moves(board, r, c):
                    moves.append((r, c, nr, nc))
    return jumps, moves


def apply_move(board, fr, fc, tr, tc, mid=None):
    """Execute a move on *board* in place.  Returns (promoted, captured_piece)."""
    piece = board[fr][fc]
    board[fr][fc] = None
    board[tr][tc] = piece
    captured = None
    if mid:
        mr, mc = mid
        captured = board[mr][mc]
        board[mr][mc] = None
    # King promotion
    promoted = False
    if piece == "r" and tr == 7:
        board[tr][tc] = "R"
        promoted = True
    elif piece == "w" and tr == 0:
        board[tr][tc] = "W"
        promoted = True
    return promoted, captured


def check_winner(board):
    """Return 'White', 'Red', or None."""
    red = sum(1 for r in board for p in r if p in ("r", "R"))
    white = sum(1 for r in board for p in r if p in ("w", "W"))
    if red == 0:
        return "White"
    if white == 0:
        return "Red"
    rj, rm = get_all_moves(board, "r")
    if not rj and not rm:
        return "White"
    wj, wm = get_all_moves(board, "w")
    if not wj and not wm:
        return "Red"
    return None


def count_pieces(board):
    """Return (red_count, white_count)."""
    red = sum(1 for r in board for p in r if p in ("r", "R"))
    white = sum(1 for r in board for p in r if p in ("w", "W"))
    return red, white


# ── AI Opponent ─────────────────────────────────────────────────────

def ai_choose_move(board, player="r"):
    """Choose a move for the AI (red).  Returns (fr, fc, tr, tc, mid_or_None).

    Strategy (simple heuristic):
      1. If jumps exist they are mandatory — pick the best one.
      2. Prefer multi-jump chains (greedy: pick jump that leads to further captures).
      3. Among simple moves: prefer advancing toward king row,
         avoid moving kings off the back row unnecessarily,
         add small randomness so play isn't fully deterministic.
    """
    jumps, moves = get_all_moves(board, player)

    if jumps:
        return _pick_best_jump(board, jumps, player)

    if not moves:
        return None

    return _pick_best_simple(board, moves, player)


def _copy_board(board):
    """Shallow-copy the 2-D board list."""
    return [row[:] for row in board]


def _pick_best_jump(board, jumps, player):
    """Score each jump (greedy chain length) and return the best."""
    best_score = -1
    best = None
    for fr, fc, lr, lc, mr, mc in jumps:
        score = _chain_depth(board, fr, fc, lr, lc, mr, mc, player)
        # Prefer capturing kings
        if board[mr][mc] and board[mr][mc].isupper():
            score += 2
        # Small random tie-break
        score += random.random() * 0.5
        if score > best_score:
            best_score = score
            best = (fr, fc, lr, lc, (mr, mc))
    return best


def _chain_depth(board, fr, fc, lr, lc, mr, mc, player, depth=1):
    """Recursively count how many captures a chain jump can make."""
    tmp = _copy_board(board)
    apply_move(tmp, fr, fc, lr, lc, mid=(mr, mc))
    further = get_jumps(tmp, lr, lc)
    if not further:
        return depth
    return max(
        _chain_depth(tmp, lr, lc, nlr, nlc, nmr, nmc, player, depth + 1)
        for nlr, nlc, nmr, nmc in further
    )


def _pick_best_simple(board, moves, player):
    """Score simple moves and return the best."""
    scored = []
    for fr, fc, tr, tc in moves:
        score = 0.0
        piece = board[fr][fc]
        # Advance toward king row
        if piece == "r":
            score += tr  # Higher row = closer to king line (row 7)
        elif piece == "w":
            score += (7 - tr)
        # Prefer edges (harder to capture)
        if tc == 0 or tc == 7:
            score += 0.5
        # Kings — slight preference to stay central
        if piece and piece.isupper():
            score += 3 - abs(tc - 3.5)
        score += random.random() * 0.8
        scored.append((score, fr, fc, tr, tc))
    scored.sort(key=lambda x: x[0], reverse=True)
    _, fr, fc, tr, tc = scored[0]
    return (fr, fc, tr, tc, None)


def ai_execute_turn(board):
    """Have the AI execute a full turn (including multi-jump chains).

    Returns a list of (fr, fc, tr, tc, mid) steps, or empty list if no move.
    Also modifies *board* in place.
    """
    steps = []
    choice = ai_choose_move(board, "r")
    if choice is None:
        return steps

    fr, fc, tr, tc, mid = choice
    promoted, captured = apply_move(board, fr, fc, tr, tc, mid=mid)
    steps.append((fr, fc, tr, tc, mid))

    # Chain jumps
    if mid and not promoted:
        while True:
            further = get_jumps(board, tr, tc)
            if not further:
                break
            # Pick best continuation
            best = None
            best_score = -1
            for lr, lc, mr, mc in further:
                sc = 1.0 + random.random() * 0.3
                if board[mr][mc] and board[mr][mc].isupper():
                    sc += 2
                if sc > best_score:
                    best_score = sc
                    best = (lr, lc, mr, mc)
            lr, lc, mr, mc = best
            promoted, _ = apply_move(board, tr, tc, lr, lc, mid=(mr, mc))
            steps.append((tr, tc, lr, lc, (mr, mc)))
            tr, tc = lr, lc
            if promoted:
                break
    return steps


# ── Drawing helpers ─────────────────────────────────────────────────

def _get_cell_colors(r, c, piece, cursor, selected, valid_dests, must_jump):
    """Return (bg_color_pair, piece_color_pair) for a cell.

    bg_color_pair: used for filling the cell background
    piece_color_pair: used for rendering piece glyphs (fg = piece color, bg = cell bg)
    """
    is_dark = (r + c) % 2 == 1

    if selected == (r, c):
        bg = curses.color_pair(COLOR_SELECTED) | curses.A_BOLD
        if piece and piece.lower() == "r":
            fg = curses.color_pair(COLOR_RED_ON_SEL) | curses.A_BOLD
        else:
            fg = curses.color_pair(COLOR_WHITE_ON_SEL) | curses.A_BOLD
    elif (r, c) in valid_dests:
        bg = curses.color_pair(COLOR_VALID) | curses.A_BOLD
        if piece and piece.lower() == "r":
            fg = curses.color_pair(COLOR_RED_ON_VALID) | curses.A_BOLD
        else:
            fg = curses.color_pair(COLOR_WHITE_ON_VALID) | curses.A_BOLD
    elif (r, c) in must_jump:
        bg = curses.color_pair(COLOR_MUST_JUMP) | curses.A_BOLD
        if piece and piece.lower() == "r":
            fg = curses.color_pair(COLOR_RED_ON_JUMP) | curses.A_BOLD
        else:
            fg = curses.color_pair(COLOR_WHITE_ON_JUMP) | curses.A_BOLD
    elif cursor == (r, c):
        bg = curses.color_pair(COLOR_AI_MOVE) | curses.A_BOLD
        if piece and piece.lower() == "r":
            fg = curses.color_pair(COLOR_RED_ON_CURSOR) | curses.A_BOLD
        else:
            fg = curses.color_pair(COLOR_WHITE_ON_CURSOR) | curses.A_BOLD
    elif is_dark:
        bg = curses.color_pair(COLOR_DARK_SQ)
        if piece and piece.lower() == "r":
            fg = curses.color_pair(COLOR_RED_PIECE) | curses.A_BOLD
        else:
            fg = curses.color_pair(COLOR_WHITE_PIECE) | curses.A_BOLD
    else:
        bg = curses.color_pair(COLOR_LIGHT_SQ)
        fg = bg  # Light squares never have pieces

    return bg, fg


def draw_board(stdscr, board, cursor, selected, valid_dests, must_jump, start_y, start_x):
    """Draw the board as solid color blocks, no grid lines, no coordinate labels.

    Each cell is 2 rows tall × 3 chars wide.  Pieces are rendered using
    upper/lower half-block characters to create a rounded checker look.
    """
    border_attr = curses.color_pair(COLOR_BORDER) | curses.A_BOLD
    board_w = BOARD_SIZE * CELL_W  # 24 chars wide

    # Top border: ╔════...════╗
    top = BOX_TL + BOX_H * board_w + BOX_TR
    safe_addstr(stdscr, start_y, start_x, top, border_attr)

    for r in range(BOARD_SIZE):
        row_y = start_y + 1 + r * CELL_H  # top pixel-row of this cell

        # Left border
        safe_addstr(stdscr, row_y, start_x, BOX_V, border_attr)
        safe_addstr(stdscr, row_y + 1, start_x, BOX_V, border_attr)

        for c in range(BOARD_SIZE):
            piece = board[r][c]
            bg, fg = _get_cell_colors(r, c, piece, cursor, selected,
                                      valid_dests, must_jump)
            cx = start_x + 1 + c * CELL_W  # left-most char of this cell

            if piece:
                is_king = piece.isupper()
                # Top row: space + upper-half-block + space
                safe_addstr(stdscr, row_y, cx, " ", bg)
                safe_addstr(stdscr, row_y, cx + 1, LOWER_HALF, fg)
                safe_addstr(stdscr, row_y, cx + 2, " ", bg)
                # Bottom row: space + lower-half-block + space
                # For kings, show a dot/crown indicator on the bottom row
                safe_addstr(stdscr, row_y + 1, cx, " ", bg)
                if is_king:
                    safe_addstr(stdscr, row_y + 1, cx + 1, UPPER_HALF, fg)
                else:
                    safe_addstr(stdscr, row_y + 1, cx + 1, UPPER_HALF, fg)
                safe_addstr(stdscr, row_y + 1, cx + 2, " ", bg)
            elif (r, c) in valid_dests:
                # Valid move dot indicator
                safe_addstr(stdscr, row_y, cx, "   ", bg)
                safe_addstr(stdscr, row_y + 1, cx, " ", bg)
                safe_addstr(stdscr, row_y + 1, cx + 1, GLYPH_DOT, bg)
                safe_addstr(stdscr, row_y + 1, cx + 2, " ", bg)
            else:
                # Empty cell — fill with background
                safe_addstr(stdscr, row_y, cx, "   ", bg)
                safe_addstr(stdscr, row_y + 1, cx, "   ", bg)

        # Right border
        rx = start_x + 1 + BOARD_SIZE * CELL_W
        safe_addstr(stdscr, row_y, rx, BOX_V, border_attr)
        safe_addstr(stdscr, row_y + 1, rx, BOX_V, border_attr)

    # Bottom border: ╚════...════╝
    bot_y = start_y + 1 + BOARD_SIZE * CELL_H
    bot = BOX_BL + BOX_H * board_w + BOX_BR
    safe_addstr(stdscr, bot_y, start_x, bot, border_attr)


def draw_title(stdscr, y, x):
    """Draw the game title."""
    title = "C H E C K E R S"
    safe_addstr(stdscr, y, x, title, curses.color_pair(COLOR_HEADER) | curses.A_BOLD)


def draw_score(stdscr, board, y, x):
    """Draw piece counts."""
    red, white = count_pieces(board)
    safe_addstr(stdscr, y, x, f"  Red  {GLYPH_RED}  : {red} pieces",
                curses.color_pair(COLOR_RED_SCORE) | curses.A_BOLD)
    safe_addstr(stdscr, y + 1, x, f"  White {GLYPH_WHITE} : {white} pieces",
                curses.color_pair(COLOR_WHITE_SCORE) | curses.A_BOLD)


def draw_status(stdscr, msg, y, x):
    """Draw status / instruction message."""
    safe_addstr(stdscr, y, x, msg, curses.color_pair(COLOR_STATUS))


def format_pos(r, c):
    """Internal (r, c) → display string like 'a3'."""
    return f"{chr(ord('a') + c)}{BOARD_SIZE - r}"


# ── Main entry point ────────────────────────────────────────────────

def main(stdscr):
    """Main curses game loop."""
    curses.curs_set(0)
    init_colors()
    stdscr.timeout(100)

    board = make_board()
    current_player = "w"       # White (human) moves first
    cursor = (5, 0)            # Cursor position (row, col)
    selected = None            # Currently selected piece
    valid_dests = []           # Reachable squares from selected piece
    must_jump = []             # Pieces forced to jump
    game_over = False
    winner = None
    status = "Your turn (White). Move cursor with arrows, SPACE to select."
    chain_piece = None         # Non-None when in multi-jump chain

    def refresh_highlights():
        nonlocal must_jump, valid_dests
        must_jump = []
        valid_dests = []
        jumps, moves = get_all_moves(board, current_player)
        if jumps:
            seen = set()
            for fr, fc, lr, lc, mr, mc in jumps:
                if (fr, fc) not in seen:
                    must_jump.append((fr, fc))
                    seen.add((fr, fc))

    refresh_highlights()

    while True:
        # ── Draw ────────────────────────────────────────────────
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        bx, by = 2, 1
        draw_title(stdscr, by, bx + 4)
        draw_board(stdscr, board, cursor, selected, valid_dests, must_jump, by + 1, bx)
        # Board height: 1 (top border) + 8*2 (cells) + 1 (bot border) = 18
        score_y = by + 1 + 1 + BOARD_SIZE * CELL_H + 1
        draw_score(stdscr, board, score_y, bx)
        draw_status(stdscr, status, score_y + 3, bx + 2)

        if game_over:
            msg = f"Game over! {winner} wins!  Press Q to quit."
            safe_addstr(stdscr, score_y + 2, bx + 2, msg,
                        curses.color_pair(COLOR_HEADER) | curses.A_BOLD)

        stdscr.refresh()

        # ── Input ───────────────────────────────────────────────
        key = stdscr.getch()
        if key == -1:
            continue

        if key in (ord("q"), ord("Q")):
            break

        if game_over:
            continue

        # AI turn — triggered after human finishes
        if current_player == "r":
            steps = ai_execute_turn(board)
            if steps:
                last = steps[-1]
                cursor = (last[2], last[3])
            winner = check_winner(board)
            if winner:
                game_over = True
                status = f"Game over! {winner} wins!"
            else:
                current_player = "w"
                selected = None
                chain_piece = None
                refresh_highlights()
                status = "Your turn (White). Move cursor with arrows, SPACE to select."
            continue

        # Human (white) input
        cr, cc = cursor
        if key == curses.KEY_UP and cr > 0:
            cursor = (cr - 1, cc)
        elif key == curses.KEY_DOWN and cr < BOARD_SIZE - 1:
            cursor = (cr + 1, cc)
        elif key == curses.KEY_LEFT and cc > 0:
            cursor = (cr, cc - 1)
        elif key == curses.KEY_RIGHT and cc < BOARD_SIZE - 1:
            cursor = (cr, cc + 1)
        elif key in (ord(" "), ord("\n"), curses.KEY_ENTER):
            # Space / Enter — select or move
            if chain_piece:
                # Must continue jumping with chain_piece
                tr, tc = cursor
                if (tr, tc) in valid_dests:
                    fr, fc = chain_piece
                    jmps = get_jumps(board, fr, fc)
                    mid = None
                    for lr, lc, mr, mc in jmps:
                        if (lr, lc) == (tr, tc):
                            mid = (mr, mc)
                            break
                    if mid:
                        promoted, captured = apply_move(board, fr, fc, tr, tc, mid=mid)
                        further = get_jumps(board, tr, tc) if not promoted else []
                        if further:
                            chain_piece = (tr, tc)
                            selected = (tr, tc)
                            valid_dests = [(lr, lc) for lr, lc, mr, mc in further]
                            must_jump = []
                            status = f"Multi-jump! Continue from {format_pos(tr, tc)}."
                        else:
                            # Turn done
                            chain_piece = None
                            selected = None
                            current_player = "r"
                            winner = check_winner(board)
                            if winner:
                                game_over = True
                                status = f"Game over! {winner} wins!"
                            else:
                                status = "AI is thinking..."
                else:
                    status = "Must continue jump! Select a highlighted destination."
            elif selected is None:
                # Select a piece
                piece = board[cr][cc]
                if piece and piece.lower() == "w":
                    jumps_all, moves_all = get_all_moves(board, "w")
                    if jumps_all:
                        # Must select a piece that can jump
                        pj = get_jumps(board, cr, cc)
                        if pj:
                            selected = (cr, cc)
                            valid_dests = [(lr, lc) for lr, lc, mr, mc in pj]
                            status = f"Selected {format_pos(cr, cc)}. Choose destination."
                        else:
                            status = "That piece can't jump. You must capture!"
                    else:
                        pm = get_simple_moves(board, cr, cc)
                        if pm:
                            selected = (cr, cc)
                            valid_dests = pm
                            status = f"Selected {format_pos(cr, cc)}. Choose destination."
                        else:
                            status = "No moves for that piece."
                else:
                    status = "Select one of your white pieces."
            else:
                # Attempt to move selected piece
                tr, tc = cursor
                if (tr, tc) == selected:
                    # Deselect
                    selected = None
                    valid_dests = []
                    refresh_highlights()
                    status = "Deselected. Pick a piece."
                elif (tr, tc) in valid_dests:
                    fr, fc = selected
                    # Determine if jump or simple
                    mid = None
                    if abs(tr - fr) == 2:
                        jmps = get_jumps(board, fr, fc)
                        for lr, lc, mr, mc in jmps:
                            if (lr, lc) == (tr, tc):
                                mid = (mr, mc)
                                break
                    promoted, captured = apply_move(board, fr, fc, tr, tc, mid=mid)
                    # Check chain jump
                    if mid and not promoted:
                        further = get_jumps(board, tr, tc)
                        if further:
                            chain_piece = (tr, tc)
                            selected = (tr, tc)
                            valid_dests = [(lr, lc) for lr, lc, mr, mc in further]
                            must_jump = []
                            status = f"Multi-jump! Continue from {format_pos(tr, tc)}."
                            continue
                    # Turn done
                    selected = None
                    chain_piece = None
                    current_player = "r"
                    winner = check_winner(board)
                    if winner:
                        game_over = True
                        status = f"Game over! {winner} wins!"
                    else:
                        status = "AI is thinking..."
                else:
                    # Clicked elsewhere — reselect if it's own piece
                    piece = board[tr][tc]
                    if piece and piece.lower() == "w":
                        jumps_all, _ = get_all_moves(board, "w")
                        if jumps_all:
                            pj = get_jumps(board, tr, tc)
                            if pj:
                                selected = (tr, tc)
                                valid_dests = [(lr, lc) for lr, lc, mr, mc in pj]
                                status = f"Selected {format_pos(tr, tc)}. Choose destination."
                            else:
                                status = "That piece can't jump. You must capture!"
                        else:
                            pm = get_simple_moves(board, tr, tc)
                            if pm:
                                selected = (tr, tc)
                                valid_dests = pm
                                status = f"Selected {format_pos(tr, tc)}. Choose destination."
                            else:
                                status = "No moves for that piece."
                    else:
                        status = "Invalid destination. Press SPACE on piece to deselect."


if __name__ == "__main__":
    curses.wrapper(main)
