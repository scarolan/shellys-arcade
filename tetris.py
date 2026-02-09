#!/usr/bin/env python3
"""
Terminal Tetris — A fully playable Tetris clone using Python curses.

Features all 7 standard tetrominoes with rotation, wall kicks, soft/hard drop,
hold piece, ghost piece, next piece preview, line clearing with animation,
classic NES scoring (40/100/300/1200), and level progression.
"""

import curses
import random
import time
import copy

# Board dimensions (standard Tetris)
BOARD_WIDTH = 10
BOARD_HEIGHT = 20

# Scoring: classic NES values (multiplied by level + 1)
SCORE_TABLE = {1: 40, 2: 100, 3: 300, 4: 1200}

# Lines per level
LINES_PER_LEVEL = 10

# Tetromino definitions: each piece has a name, color index, and rotation states.
# Each rotation state is a list of (row, col) offsets from the piece origin.
# Colors: 1=cyan, 2=yellow, 3=purple, 4=green, 5=red, 6=blue, 7=orange

TETROMINOES = {
    # I piece — cyan
    "I": {
        "color": 1,
        "rotations": [
            [(0, 0), (0, 1), (0, 2), (0, 3)],
            [(0, 2), (1, 2), (2, 2), (3, 2)],
            [(2, 0), (2, 1), (2, 2), (2, 3)],
            [(0, 1), (1, 1), (2, 1), (3, 1)],
        ],
    },
    # O piece — yellow
    "O": {
        "color": 2,
        "rotations": [
            [(0, 0), (0, 1), (1, 0), (1, 1)],
            [(0, 0), (0, 1), (1, 0), (1, 1)],
            [(0, 0), (0, 1), (1, 0), (1, 1)],
            [(0, 0), (0, 1), (1, 0), (1, 1)],
        ],
    },
    # T piece — purple
    "T": {
        "color": 3,
        "rotations": [
            [(0, 1), (1, 0), (1, 1), (1, 2)],
            [(0, 0), (1, 0), (1, 1), (2, 0)],
            [(0, 0), (0, 1), (0, 2), (1, 1)],
            [(0, 1), (1, 0), (1, 1), (2, 1)],
        ],
    },
    # S piece — green
    "S": {
        "color": 4,
        "rotations": [
            [(0, 1), (0, 2), (1, 0), (1, 1)],
            [(0, 0), (1, 0), (1, 1), (2, 1)],
            [(0, 1), (0, 2), (1, 0), (1, 1)],
            [(0, 0), (1, 0), (1, 1), (2, 1)],
        ],
    },
    # Z piece — red
    "Z": {
        "color": 5,
        "rotations": [
            [(0, 0), (0, 1), (1, 1), (1, 2)],
            [(0, 1), (1, 0), (1, 1), (2, 0)],
            [(0, 0), (0, 1), (1, 1), (1, 2)],
            [(0, 1), (1, 0), (1, 1), (2, 0)],
        ],
    },
    # J piece — blue
    "J": {
        "color": 6,
        "rotations": [
            [(0, 0), (1, 0), (1, 1), (1, 2)],
            [(0, 0), (0, 1), (1, 0), (2, 0)],
            [(0, 0), (0, 1), (0, 2), (1, 2)],
            [(0, 1), (1, 1), (2, 0), (2, 1)],
        ],
    },
    # L piece — orange
    "L": {
        "color": 7,
        "rotations": [
            [(0, 2), (1, 0), (1, 1), (1, 2)],
            [(0, 0), (1, 0), (2, 0), (2, 1)],
            [(0, 0), (0, 1), (0, 2), (1, 0)],
            [(0, 0), (0, 1), (1, 1), (2, 1)],
        ],
    },
}

PIECE_NAMES = ["I", "O", "T", "S", "Z", "J", "L"]


def create_board():
    """Create an empty board (2D list of zeros)."""
    return [[0 for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]


def is_valid_position(board, piece_name, rotation, row, col):
    """Check if a piece at (row, col) with given rotation fits on the board."""
    cells = TETROMINOES[piece_name]["rotations"][rotation]
    for dr, dc in cells:
        r, c = row + dr, col + dc
        if r < 0 or r >= BOARD_HEIGHT or c < 0 or c >= BOARD_WIDTH:
            return False
        if board[r][c] != 0:
            return False
    return True


def lock_piece(board, piece_name, rotation, row, col):
    """Lock a piece onto the board."""
    color = TETROMINOES[piece_name]["color"]
    cells = TETROMINOES[piece_name]["rotations"][rotation]
    for dr, dc in cells:
        r, c = row + dr, col + dc
        if 0 <= r < BOARD_HEIGHT and 0 <= c < BOARD_WIDTH:
            board[r][c] = color


def clear_filled_rows(board):
    """Clear completed lines and return the number cleared."""
    cleared = 0
    new_board = []
    for row in board:
        if all(cell != 0 for cell in row):
            cleared += 1
        else:
            new_board.append(row)
    # Add empty rows at the top
    while len(new_board) < BOARD_HEIGHT:
        new_board.insert(0, [0 for _ in range(BOARD_WIDTH)])
    # Copy back
    for i in range(BOARD_HEIGHT):
        board[i] = new_board[i]
    return cleared


def rotate_piece(piece_name, rotation, direction=1):
    """Rotate a piece clockwise (direction=1) or counterclockwise (direction=-1)."""
    num_rotations = len(TETROMINOES[piece_name]["rotations"])
    return (rotation + direction) % num_rotations


def try_rotate(board, piece_name, rotation, row, col):
    """Try to rotate a piece with wall kicks."""
    new_rotation = rotate_piece(piece_name, rotation)
    # Try normal rotation
    if is_valid_position(board, piece_name, new_rotation, row, col):
        return new_rotation, row, col
    # Wall kick: try shifting left, right, up
    for kick_col in [col - 1, col + 1, col - 2, col + 2]:
        if is_valid_position(board, piece_name, new_rotation, row, kick_col):
            return new_rotation, row, kick_col
    # Try shifting up (for I piece near bottom)
    for kick_row in [row - 1, row - 2]:
        if is_valid_position(board, piece_name, new_rotation, kick_row, col):
            return new_rotation, kick_row, col
    # Rotation failed
    return rotation, row, col


def get_ghost_position(board, piece_name, rotation, row, col):
    """Get the row where the ghost piece would land."""
    ghost_row = row
    while is_valid_position(board, piece_name, rotation, ghost_row + 1, col):
        ghost_row += 1
    return ghost_row


def hard_drop(board, piece_name, rotation, row, col):
    """Hard drop: instantly move piece to lowest valid position."""
    drop_row = get_ghost_position(board, piece_name, rotation, row, col)
    return drop_row


def get_drop_interval(level):
    """Get the drop interval in seconds based on level."""
    # Starts at ~1 second, gets faster each level
    return max(0.05, 1.0 - (level * 0.08))


def generate_bag():
    """Generate a shuffled bag of all 7 pieces (7-bag randomizer)."""
    bag = list(PIECE_NAMES)
    random.shuffle(bag)
    return bag


def init_colors():
    """Initialize curses color pairs for each piece."""
    curses.start_color()
    curses.use_default_colors()
    # Color pairs: 1=cyan(I), 2=yellow(O), 3=magenta(T), 4=green(S),
    #              5=red(Z), 6=blue(J), 7=white/orange(L), 8=ghost
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_BLACK)  # ghost


def draw_board(stdscr, board, offset_y, offset_x):
    """Draw the game board with borders using box-drawing characters."""
    # Top border
    stdscr.addstr(offset_y, offset_x, "┌" + "──" * BOARD_WIDTH + "┐")
    # Board rows
    for r in range(BOARD_HEIGHT):
        stdscr.addstr(offset_y + 1 + r, offset_x, "│")
        for c in range(BOARD_WIDTH):
            cell = board[r][c]
            if cell != 0:
                stdscr.addstr("██", curses.color_pair(cell) | curses.A_BOLD)
            else:
                stdscr.addstr("  ")
        stdscr.addstr("│")
    # Bottom border
    stdscr.addstr(offset_y + BOARD_HEIGHT + 1, offset_x, "└" + "──" * BOARD_WIDTH + "┘")


def draw_piece(stdscr, piece_name, rotation, row, col, offset_y, offset_x, attr=None):
    """Draw a piece on the screen."""
    color = TETROMINOES[piece_name]["color"]
    cells = TETROMINOES[piece_name]["rotations"][rotation]
    pair = curses.color_pair(color) | curses.A_BOLD
    if attr is not None:
        pair = attr
    for dr, dc in cells:
        screen_r = offset_y + 1 + row + dr
        screen_c = offset_x + 1 + (col + dc) * 2
        try:
            stdscr.addstr(screen_r, screen_c, "██", pair)
        except curses.error:
            pass


def draw_ghost(stdscr, piece_name, rotation, ghost_row, col, offset_y, offset_x):
    """Draw the ghost piece (dim outline showing where piece will land)."""
    cells = TETROMINOES[piece_name]["rotations"][rotation]
    ghost_attr = curses.color_pair(8) | curses.A_DIM
    for dr, dc in cells:
        screen_r = offset_y + 1 + ghost_row + dr
        screen_c = offset_x + 1 + (col + dc) * 2
        try:
            stdscr.addstr(screen_r, screen_c, "░░", ghost_attr)
        except curses.error:
            pass


def draw_sidebar_box(stdscr, title, piece_name, rotation, y, x):
    """Draw a sidebar box (NEXT or HOLD) with a piece preview."""
    stdscr.addstr(y, x, "┌────────┐")
    stdscr.addstr(y + 1, x, "│ {:<6s} │".format(title))
    for i in range(2, 5):
        stdscr.addstr(y + i, x, "│        │")
    stdscr.addstr(y + 5, x, "└────────┘")
    if piece_name is not None:
        cells = TETROMINOES[piece_name]["rotations"][rotation]
        color = TETROMINOES[piece_name]["color"]
        pair = curses.color_pair(color) | curses.A_BOLD
        for dr, dc in cells:
            try:
                stdscr.addstr(y + 2 + dr, x + 2 + dc * 2, "██", pair)
            except curses.error:
                pass


def draw_stats(stdscr, score, level, lines, y, x):
    """Draw score, level, and lines cleared."""
    stdscr.addstr(y, x, f"Score: {score}")
    stdscr.addstr(y + 1, x, f"Level: {level}")
    stdscr.addstr(y + 2, x, f"Lines: {lines}")


def flash_clear_lines(stdscr, board, filled_rows, offset_y, offset_x):
    """Simple line clear animation — flash filled rows."""
    for _ in range(3):
        for r in filled_rows:
            stdscr.addstr(offset_y + 1 + r, offset_x + 1, "▓▓" * BOARD_WIDTH,
                          curses.color_pair(7) | curses.A_BOLD)
        stdscr.refresh()
        curses.napms(60)
        for r in filled_rows:
            stdscr.addstr(offset_y + 1 + r, offset_x + 1, "  " * BOARD_WIDTH)
        stdscr.refresh()
        curses.napms(60)


def check_game_over(board):
    """Check if the game is over (top row has blocks)."""
    return any(cell != 0 for cell in board[0])


def main(stdscr):
    """Main game loop."""
    curses.curs_set(0)
    init_colors()
    stdscr.nodelay(True)
    stdscr.timeout(16)  # ~60fps refresh

    # Board position on screen
    offset_y = 1
    offset_x = 2

    # Sidebar position
    sidebar_x = offset_x + BOARD_WIDTH * 2 + 4

    # Game state
    board = create_board()
    score = 0
    level = 0
    lines_cleared = 0
    game_over = False
    paused = False

    # Piece bag
    bag = generate_bag()
    next_bag = generate_bag()

    def next_piece_from_bag():
        nonlocal bag, next_bag
        if not bag:
            bag = next_bag
            next_bag = generate_bag()
        return bag.pop(0)

    # Current piece
    current_piece = next_piece_from_bag()
    current_rotation = 0
    current_row = 0
    current_col = BOARD_WIDTH // 2 - 1

    # Next piece
    next_piece = next_piece_from_bag()

    # Hold piece
    hold_piece = None
    can_hold = True

    # Timing
    last_drop_time = time.time()
    drop_interval = get_drop_interval(level)

    while True:
        now = time.time()

        # Handle input
        key = stdscr.getch()

        if key == ord('q') or key == ord('Q'):
            break

        if key == ord('p') or key == ord('P'):
            paused = not paused
            if paused:
                stdscr.addstr(offset_y + BOARD_HEIGHT // 2, offset_x + 4, "  PAUSED  ",
                              curses.A_REVERSE | curses.A_BOLD)
                stdscr.refresh()
            continue

        if paused:
            continue

        if game_over:
            stdscr.addstr(offset_y + BOARD_HEIGHT // 2, offset_x + 2, "  GAME OVER  ",
                          curses.A_REVERSE | curses.A_BOLD)
            stdscr.addstr(offset_y + BOARD_HEIGHT // 2 + 2, offset_x + 2, " Press Q to quit ",
                          curses.A_DIM)
            stdscr.refresh()
            continue

        moved = False

        if key == curses.KEY_LEFT:
            if is_valid_position(board, current_piece, current_rotation,
                                 current_row, current_col - 1):
                current_col -= 1
                moved = True

        elif key == curses.KEY_RIGHT:
            if is_valid_position(board, current_piece, current_rotation,
                                 current_row, current_col + 1):
                current_col += 1
                moved = True

        elif key == curses.KEY_DOWN:
            # Soft drop
            if is_valid_position(board, current_piece, current_rotation,
                                 current_row + 1, current_col):
                current_row += 1
                score += 1
                moved = True

        elif key == curses.KEY_UP:
            # Rotate clockwise
            new_rot, new_row, new_col = try_rotate(
                board, current_piece, current_rotation, current_row, current_col)
            current_rotation = new_rot
            current_row = new_row
            current_col = new_col
            moved = True

        elif key == ord(' '):
            # Hard drop
            drop_row = hard_drop(board, current_piece, current_rotation,
                                 current_row, current_col)
            score += (drop_row - current_row) * 2
            current_row = drop_row
            # Lock immediately
            lock_piece(board, current_piece, current_rotation,
                       current_row, current_col)

            # Check for filled rows
            filled_rows = [r for r in range(BOARD_HEIGHT)
                           if all(board[r][c] != 0 for c in range(BOARD_WIDTH))]
            if filled_rows:
                flash_clear_lines(stdscr, board, filled_rows, offset_y, offset_x)
                num_cleared = clear_filled_rows(board)
                lines_cleared += num_cleared
                score += SCORE_TABLE.get(num_cleared, 0) * (level + 1)
                level = lines_cleared // LINES_PER_LEVEL
                drop_interval = get_drop_interval(level)

            # Spawn next piece
            current_piece = next_piece
            next_piece = next_piece_from_bag()
            current_rotation = 0
            current_row = 0
            current_col = BOARD_WIDTH // 2 - 1
            can_hold = True
            last_drop_time = now

            if not is_valid_position(board, current_piece, current_rotation,
                                     current_row, current_col):
                game_over = True
            continue

        elif key == ord('c') or key == ord('C'):
            # Hold piece
            if can_hold:
                can_hold = False
                if hold_piece is None:
                    hold_piece = current_piece
                    current_piece = next_piece
                    next_piece = next_piece_from_bag()
                else:
                    hold_piece, current_piece = current_piece, hold_piece
                current_rotation = 0
                current_row = 0
                current_col = BOARD_WIDTH // 2 - 1
                last_drop_time = now

        # Gravity: auto drop
        if now - last_drop_time >= drop_interval:
            if is_valid_position(board, current_piece, current_rotation,
                                 current_row + 1, current_col):
                current_row += 1
            else:
                # Lock piece
                lock_piece(board, current_piece, current_rotation,
                           current_row, current_col)

                # Check for filled rows
                filled_rows = [r for r in range(BOARD_HEIGHT)
                               if all(board[r][c] != 0 for c in range(BOARD_WIDTH))]
                if filled_rows:
                    flash_clear_lines(stdscr, board, filled_rows, offset_y, offset_x)
                    num_cleared = clear_filled_rows(board)
                    lines_cleared += num_cleared
                    score += SCORE_TABLE.get(num_cleared, 0) * (level + 1)
                    level = lines_cleared // LINES_PER_LEVEL
                    drop_interval = get_drop_interval(level)

                # Spawn next piece
                current_piece = next_piece
                next_piece = next_piece_from_bag()
                current_rotation = 0
                current_row = 0
                current_col = BOARD_WIDTH // 2 - 1
                can_hold = True

                if not is_valid_position(board, current_piece, current_rotation,
                                         current_row, current_col):
                    game_over = True

            last_drop_time = now

        # Draw everything
        stdscr.erase()

        # Draw board
        draw_board(stdscr, board, offset_y, offset_x)

        # Draw ghost piece
        ghost_row = get_ghost_position(board, current_piece, current_rotation,
                                        current_row, current_col)
        if ghost_row != current_row:
            draw_ghost(stdscr, current_piece, current_rotation,
                       ghost_row, current_col, offset_y, offset_x)

        # Draw current piece
        draw_piece(stdscr, current_piece, current_rotation,
                   current_row, current_col, offset_y, offset_x)

        # Draw sidebar: next piece
        draw_sidebar_box(stdscr, "NEXT", next_piece, 0, offset_y, sidebar_x)

        # Draw sidebar: hold piece
        draw_sidebar_box(stdscr, "HOLD", hold_piece, 0,
                         offset_y + 7, sidebar_x)

        # Draw stats
        draw_stats(stdscr, score, level, lines_cleared,
                   offset_y + 15, sidebar_x)

        # Title
        stdscr.addstr(0, offset_x, "TETRIS", curses.A_BOLD)

        stdscr.refresh()


if __name__ == "__main__":
    curses.wrapper(main)
