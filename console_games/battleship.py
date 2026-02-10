#!/usr/bin/env python3
"""
Terminal Battleship — Player vs AI naval warfare using Python curses.
Place your fleet, hunt the enemy ships, and sink them all before they
sink yours! Navigate with arrow keys, fire with space bar.
"""

import curses
import random
import sys
import time

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRID_SIZE = 10
COLS = "ABCDEFGHIJ"

# Cell states
WATER = 0
SHIP = 1
HIT = 2
MISS = 3

# Glyphs (Nerd Font / Unicode)
GLYPH_WATER = "≈"
GLYPH_SHIP = "█"
GLYPH_HIT = "X"
GLYPH_MISS = "•"
GLYPH_CURSOR = "◆"
GLYPH_HIDDEN = "≈"  # enemy water (hides ships)

# Ships
SHIPS = {
    "Carrier": 5,
    "Battleship": 4,
    "Cruiser": 3,
    "Submarine": 3,
    "Destroyer": 2,
}

# Color pair IDs
COLOR_WATER = 1
COLOR_SHIP = 2
COLOR_HIT = 3
COLOR_MISS = 4
COLOR_CURSOR = 5
COLOR_HEADER = 6
COLOR_BORDER = 7
COLOR_STATUS = 8
COLOR_SUNK = 9

# Timing
FPS = 30
FRAME_DELAY = 1.0 / FPS


# ---------------------------------------------------------------------------
# Color initialization
# ---------------------------------------------------------------------------

def init_colors():
    """Initialize curses color pairs."""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(COLOR_WATER, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_SHIP, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_HIT, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_MISS, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_CURSOR, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_HEADER, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_BORDER, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_STATUS, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_SUNK, curses.COLOR_MAGENTA, -1)


# ---------------------------------------------------------------------------
# Grid helpers
# ---------------------------------------------------------------------------

def make_grid():
    """Create an empty GRID_SIZE x GRID_SIZE grid."""
    return [[WATER] * GRID_SIZE for _ in range(GRID_SIZE)]


def can_place(grid, row, col, size, horizontal):
    """Check if a ship of given size can be placed at (row, col)."""
    for i in range(size):
        r = row if horizontal else row + i
        c = col + i if horizontal else col
        if r >= GRID_SIZE or c >= GRID_SIZE:
            return False
        if grid[r][c] != WATER:
            return False
    return True


def place_ship(grid, row, col, size, horizontal):
    """Place a ship on the grid. Returns list of coordinates."""
    coords = []
    for i in range(size):
        r = row if horizontal else row + i
        c = col + i if horizontal else col
        grid[r][c] = SHIP
        coords.append((r, c))
    return coords


def ai_place_ships(grid):
    """Randomly place all ships for the AI. Returns dict of ship coords."""
    ship_coords = {}
    for name, size in SHIPS.items():
        while True:
            horizontal = random.choice([True, False])
            row = random.randint(0, GRID_SIZE - 1)
            col = random.randint(0, GRID_SIZE - 1)
            if can_place(grid, row, col, size, horizontal):
                coords = place_ship(grid, row, col, size, horizontal)
                ship_coords[name] = coords
                break
    return ship_coords


def all_sunk(ship_coords, grid):
    """Check if all ships are sunk (all coords are HIT)."""
    for coords in ship_coords.values():
        for r, c in coords:
            if grid[r][c] != HIT:
                return False
    return True


def check_sunk(ship_coords, grid):
    """Return name of any newly sunk ship, or None."""
    for name, coords in ship_coords.items():
        if all(grid[r][c] == HIT for r, c in coords):
            return name
    return None


def get_sunk_ships(ship_coords, grid):
    """Return set of ship names that are fully sunk."""
    sunk = set()
    for name, coords in ship_coords.items():
        if all(grid[r][c] == HIT for r, c in coords):
            sunk.add(name)
    return sunk


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def draw_box(stdscr, y, x, height, width):
    """Draw a box using double-line box-drawing characters."""
    try:
        stdscr.addstr(y, x, "╔" + "═" * (width - 2) + "╗",
                       curses.color_pair(COLOR_BORDER))
        for row in range(1, height - 1):
            stdscr.addstr(y + row, x, "║",
                           curses.color_pair(COLOR_BORDER))
            stdscr.addstr(y + row, x + width - 1, "║",
                           curses.color_pair(COLOR_BORDER))
        stdscr.addstr(y + height - 1, x, "╚" + "═" * (width - 2) + "╝",
                       curses.color_pair(COLOR_BORDER))
    except curses.error:
        pass


def draw_board(stdscr, grid, y, x, title, show_ships=True,
               cursor_pos=None, ship_coords=None):
    """Draw a single game board with box-drawing border and title."""
    # Board is 2 chars per cell + col headers + row numbers + border
    board_inner_w = GRID_SIZE * 2 + 1  # "A B C D E F G H I J "
    box_w = board_inner_w + 5  # border + row number + spaces
    box_h = GRID_SIZE + 4  # border + header row + grid rows + border

    # Title
    try:
        title_x = x + (box_w - len(title)) // 2
        stdscr.addstr(y, title_x, title,
                       curses.color_pair(COLOR_HEADER) | curses.A_BOLD)
    except curses.error:
        pass

    # Box border
    draw_box(stdscr, y + 1, x, box_h, box_w)

    # Column headers
    col_header = "  " + " ".join(COLS)
    try:
        stdscr.addstr(y + 2, x + 2, col_header,
                       curses.color_pair(COLOR_HEADER))
    except curses.error:
        pass

    sunk = get_sunk_ships(ship_coords, grid) if ship_coords else set()

    # Grid cells
    for r in range(GRID_SIZE):
        row_label = f"{r + 1:>2}"
        try:
            stdscr.addstr(y + 3 + r, x + 1, row_label,
                           curses.color_pair(COLOR_HEADER))
        except curses.error:
            pass

        for c in range(GRID_SIZE):
            cell = grid[r][c]
            cx = x + 4 + c * 2

            # Determine glyph and color
            if cursor_pos and (r, c) == cursor_pos:
                glyph = GLYPH_CURSOR
                color = curses.color_pair(COLOR_CURSOR) | curses.A_BOLD
            elif cell == HIT:
                glyph = GLYPH_HIT
                color = curses.color_pair(COLOR_HIT) | curses.A_BOLD
            elif cell == MISS:
                glyph = GLYPH_MISS
                color = curses.color_pair(COLOR_MISS)
            elif cell == SHIP and show_ships:
                glyph = GLYPH_SHIP
                color = curses.color_pair(COLOR_SHIP) | curses.A_BOLD
            else:
                glyph = GLYPH_WATER
                color = curses.color_pair(COLOR_WATER)

            try:
                stdscr.addstr(y + 3 + r, cx, glyph, color)
            except curses.error:
                pass


def draw_ship_status(stdscr, y, x, title, ship_coords, grid):
    """Draw ship status list showing which ships are sunk."""
    try:
        stdscr.addstr(y, x, title,
                       curses.color_pair(COLOR_HEADER) | curses.A_BOLD)
    except curses.error:
        pass

    sunk = get_sunk_ships(ship_coords, grid)
    row = y + 1
    for name, size in SHIPS.items():
        if name in sunk:
            label = f"  X {name} ({size})"
            color = curses.color_pair(COLOR_SUNK) | curses.A_BOLD
        else:
            label = f"  ● {name} ({size})"
            color = curses.color_pair(COLOR_SHIP)
        try:
            stdscr.addstr(row, x, label, color)
        except curses.error:
            pass
        row += 1


def draw_status_message(stdscr, y, x, message):
    """Draw a status message."""
    try:
        stdscr.addstr(y, x, message,
                       curses.color_pair(COLOR_STATUS) | curses.A_BOLD)
    except curses.error:
        pass


def draw_game_over(stdscr, max_y, max_x, won, turns):
    """Draw game over overlay with box-drawing border."""
    if won:
        msg1 = "VICTORY!"
        msg2 = f"All enemy ships sunk in {turns} turns!"
    else:
        msg1 = "DEFEAT!"
        msg2 = f"Your fleet was sunk on turn {turns}."
    msg3 = "Press R to replay  •  Q to quit"

    box_w = max(len(msg1), len(msg2), len(msg3)) + 6
    box_h = 7
    bx = (max_x - box_w) // 2
    by = (max_y - box_h) // 2

    draw_box(stdscr, by, bx, box_h, box_w)

    # Fill interior
    for row in range(1, box_h - 1):
        try:
            stdscr.addstr(by + row, bx + 1, " " * (box_w - 2))
        except curses.error:
            pass

    color1 = curses.color_pair(COLOR_HIT if not won else COLOR_SHIP) | curses.A_BOLD
    try:
        stdscr.addstr(by + 2, bx + (box_w - len(msg1)) // 2, msg1, color1)
        stdscr.addstr(by + 3, bx + (box_w - len(msg2)) // 2, msg2,
                       curses.color_pair(COLOR_STATUS))
        stdscr.addstr(by + 5, bx + (box_w - len(msg3)) // 2, msg3,
                       curses.color_pair(COLOR_HEADER))
    except curses.error:
        pass


# ---------------------------------------------------------------------------
# Ship placement phase
# ---------------------------------------------------------------------------

def placement_phase(stdscr, player_grid, max_y, max_x):
    """Interactive ship placement using arrow keys and space bar."""
    ship_coords = {}
    ship_list = list(SHIPS.items())
    ship_idx = 0
    cursor_r, cursor_c = 0, 0
    horizontal = True

    while ship_idx < len(ship_list):
        name, size = ship_list[ship_idx]
        key = -1

        while True:
            stdscr.erase()

            # Title
            title = "B A T T L E S H I P"
            try:
                stdscr.addstr(0, (max_x - len(title)) // 2, title,
                               curses.color_pair(COLOR_HEADER) | curses.A_BOLD)
            except curses.error:
                pass

            # Draw player board
            draw_board(stdscr, player_grid, 2, 2, "YOUR FLEET",
                       show_ships=True, cursor_pos=(cursor_r, cursor_c))

            # Placement instructions
            info_x = 32
            try:
                stdscr.addstr(3, info_x, f"Place: {name} (size {size})",
                               curses.color_pair(COLOR_STATUS) | curses.A_BOLD)
                direction = "Horizontal →" if horizontal else "Vertical ↓"
                stdscr.addstr(5, info_x, f"Direction: {direction}",
                               curses.color_pair(COLOR_SHIP))
                stdscr.addstr(7, info_x, "Arrow keys : move",
                               curses.color_pair(COLOR_MISS))
                stdscr.addstr(8, info_x, "R          : rotate",
                               curses.color_pair(COLOR_MISS))
                stdscr.addstr(9, info_x, "Space      : place ship",
                               curses.color_pair(COLOR_MISS))
                stdscr.addstr(10, info_x, "Q          : quit",
                               curses.color_pair(COLOR_MISS))
            except curses.error:
                pass

            # Preview ship placement
            valid = can_place(player_grid, cursor_r, cursor_c, size, horizontal)
            for i in range(size):
                pr = cursor_r if horizontal else cursor_r + i
                pc = cursor_c + i if horizontal else cursor_c
                if 0 <= pr < GRID_SIZE and 0 <= pc < GRID_SIZE:
                    cx = 6 + pc * 2
                    cy = 5 + pr
                    color = (curses.color_pair(COLOR_SHIP) if valid
                             else curses.color_pair(COLOR_HIT))
                    try:
                        stdscr.addstr(cy, cx, GLYPH_SHIP, color | curses.A_BOLD)
                    except curses.error:
                        pass

            stdscr.refresh()

            key = stdscr.getch()
            if key == curses.KEY_UP and cursor_r > 0:
                cursor_r -= 1
            elif key == curses.KEY_DOWN and cursor_r < GRID_SIZE - 1:
                cursor_r += 1
            elif key == curses.KEY_LEFT and cursor_c > 0:
                cursor_c -= 1
            elif key == curses.KEY_RIGHT and cursor_c < GRID_SIZE - 1:
                cursor_c += 1
            elif key in (ord('r'), ord('R')):
                horizontal = not horizontal
            elif key in (ord('q'), ord('Q')):
                return None  # signal quit
            elif key == ord(' '):
                if valid:
                    coords = place_ship(player_grid, cursor_r, cursor_c,
                                        size, horizontal)
                    ship_coords[name] = coords
                    break

        ship_idx += 1
        cursor_r, cursor_c = 0, 0
        horizontal = True

    return ship_coords


# ---------------------------------------------------------------------------
# AI logic
# ---------------------------------------------------------------------------

def ai_fire(player_grid, player_ship_coords, ai_state):
    """AI fires a shot using hunt/target strategy. Returns (row, col, hit)."""
    target_queue = ai_state["targets"]

    while True:
        if target_queue:
            row, col = target_queue.pop(0)
            if player_grid[row][col] in (HIT, MISS):
                continue
            break
        else:
            row = random.randint(0, GRID_SIZE - 1)
            col = random.randint(0, GRID_SIZE - 1)
            if player_grid[row][col] in (HIT, MISS):
                continue
            break

    hit = player_grid[row][col] == SHIP
    if hit:
        player_grid[row][col] = HIT
        sunk = check_sunk(player_ship_coords, player_grid)
        if sunk:
            ai_state["targets"].clear()
        else:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                    if player_grid[nr][nc] not in (HIT, MISS):
                        target_queue.append((nr, nc))
    else:
        player_grid[row][col] = MISS

    return row, col, hit


# ---------------------------------------------------------------------------
# Main game
# ---------------------------------------------------------------------------

def main(stdscr):
    """Main game loop."""
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(100)
    init_colors()

    max_y, max_x = stdscr.getmaxyx()

    # --- Ship placement phase ---
    stdscr.nodelay(False)
    player_grid = make_grid()
    player_ship_coords = placement_phase(stdscr, player_grid, max_y, max_x)
    if player_ship_coords is None:
        return  # user quit

    # --- AI setup ---
    enemy_grid = make_grid()
    tracking_grid = make_grid()
    enemy_ship_coords = ai_place_ships(enemy_grid)
    ai_state = {"targets": []}

    # --- Battle phase ---
    stdscr.nodelay(False)
    cursor_r, cursor_c = 0, 0
    turn = 0
    game_over = False
    player_won = False
    status_msg = "Your turn — arrow keys to aim, SPACE to fire"

    while True:
        stdscr.erase()

        title = "B A T T L E S H I P"
        try:
            stdscr.addstr(0, (max_x - len(title)) // 2, title,
                           curses.color_pair(COLOR_HEADER) | curses.A_BOLD)
        except curses.error:
            pass

        # Draw boards side by side
        board_gap = 4
        left_x = 2
        right_x = 32 + board_gap

        draw_board(stdscr, player_grid, 2, left_x, "YOUR FLEET",
                   show_ships=True, ship_coords=player_ship_coords)
        draw_board(stdscr, tracking_grid, 2, right_x, "ENEMY WATERS",
                   show_ships=False, cursor_pos=(cursor_r, cursor_c)
                   if not game_over else None,
                   ship_coords=enemy_ship_coords)

        # Ship status panels
        status_y = 17
        draw_ship_status(stdscr, status_y, left_x,
                         "Your Ships:", player_ship_coords, player_grid)
        draw_ship_status(stdscr, status_y, right_x,
                         "Enemy Ships:", enemy_ship_coords, tracking_grid)

        # Turn counter and status
        try:
            stdscr.addstr(status_y + 7, left_x,
                           f"Turn: {turn}",
                           curses.color_pair(COLOR_HEADER))
        except curses.error:
            pass
        draw_status_message(stdscr, status_y + 8, left_x, status_msg)

        # Game over overlay
        if game_over:
            draw_game_over(stdscr, max_y, max_x, player_won, turn)

        stdscr.refresh()

        # --- Input ---
        key = stdscr.getch()

        if game_over:
            if key in (ord('r'), ord('R')):
                main(stdscr)
                return
            elif key in (ord('q'), ord('Q')):
                return
            continue

        if key in (ord('q'), ord('Q')):
            return
        elif key == curses.KEY_UP and cursor_r > 0:
            cursor_r -= 1
        elif key == curses.KEY_DOWN and cursor_r < GRID_SIZE - 1:
            cursor_r += 1
        elif key == curses.KEY_LEFT and cursor_c > 0:
            cursor_c -= 1
        elif key == curses.KEY_RIGHT and cursor_c < GRID_SIZE - 1:
            cursor_c += 1
        elif key == ord(' '):
            # Fire!
            if tracking_grid[cursor_r][cursor_c] != WATER:
                status_msg = "Already fired there! Pick another target."
                continue

            turn += 1
            coord_str = f"{COLS[cursor_c]}{cursor_r + 1}"

            # Player fires
            if enemy_grid[cursor_r][cursor_c] == SHIP:
                enemy_grid[cursor_r][cursor_c] = HIT
                tracking_grid[cursor_r][cursor_c] = HIT
                sunk = check_sunk(enemy_ship_coords, enemy_grid)
                if sunk:
                    status_msg = f"BOOM! {coord_str} — You sunk the {sunk}!"
                else:
                    status_msg = f"HIT at {coord_str}!"
            else:
                tracking_grid[cursor_r][cursor_c] = MISS
                status_msg = f"Miss at {coord_str}."

            # Check win
            if all_sunk(enemy_ship_coords, enemy_grid):
                game_over = True
                player_won = True
                continue

            # AI fires
            ar, ac, a_hit = ai_fire(player_grid, player_ship_coords,
                                     ai_state)
            ai_coord = f"{COLS[ac]}{ar + 1}"
            if a_hit:
                ai_sunk = check_sunk(player_ship_coords, player_grid)
                if ai_sunk:
                    status_msg += f"  |  Enemy: {ai_coord} sunk your {ai_sunk}!"
                else:
                    status_msg += f"  |  Enemy: HIT at {ai_coord}!"
            else:
                status_msg += f"  |  Enemy: miss at {ai_coord}."

            # Check loss
            if all_sunk(player_ship_coords, player_grid):
                game_over = True
                player_won = False


if __name__ == "__main__":
    curses.wrapper(main)
