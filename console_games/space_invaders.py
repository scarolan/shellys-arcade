#!/usr/bin/env python3
"""
Terminal Space Invaders — a classic arcade game clone using Python curses.
Defend Earth from waves of descending alien invaders! Move your ship with
arrow keys, shoot with space bar, and survive as long as you can.
"""

import curses
import os
import random
import time

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLAYER_CHAR = "/^^\\"
BULLET_CHAR = "|"
ALIEN_BULLET_CHAR = ":"
UFO_CHAR = "<==>"
SHIELD_CHAR = "\u2588"  # ███ full-block

ALIEN_TYPES = [
    {"chars": ["/oo\\", "\\oo/"], "points": 10},   # Row 1 (top) — frame toggle
    {"chars": ["{@@}", "}@@{"], "points": 20},      # Row 2
    {"chars": ["<**>", ">**<"], "points": 30},      # Row 3
    {"chars": ["|##|", "-##-"], "points": 40},      # Row 4 (bottom)
]

NUM_ALIEN_COLS = 8
NUM_ALIEN_ROWS = 4
ALIEN_SPACING_X = 6
ALIEN_SPACING_Y = 2

SHIELD_COUNT = 4
SHIELD_WIDTH = 5
SHIELD_HEIGHT = 3

STARTING_LIVES = 3
MAX_PLAYER_BULLETS = 3
ALIEN_SHOOT_CHANCE = 0.004  # ~1 bullet/sec across all columns at 30fps
UFO_SPAWN_CHANCE = 0.003

HIGH_SCORE_DIR = os.path.expanduser("~/.shelly-ops")
HIGH_SCORE_FILE = os.path.join(HIGH_SCORE_DIR, "invaders-highscore.txt")

FPS = 30
FRAME_DELAY = 1.0 / FPS

# Color pair IDs
COLOR_PLAYER = 1
COLOR_ALIEN_ROW1 = 2
COLOR_ALIEN_ROW2 = 3
COLOR_ALIEN_ROW3 = 4
COLOR_ALIEN_ROW4 = 5
COLOR_SHIELD = 6
COLOR_UFO = 7
COLOR_BULLET = 8
COLOR_HUD = 9
COLOR_ALIEN_BULLET = 10
COLOR_GAMEOVER = 11


# ---------------------------------------------------------------------------
# High score I/O
# ---------------------------------------------------------------------------

def load_high_score():
    """Load high score from file, return 0 if not found."""
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def save_high_score(score):
    """Save high score to file."""
    try:
        os.makedirs(HIGH_SCORE_DIR, exist_ok=True)
        with open(HIGH_SCORE_FILE, "w") as f:
            f.write(str(score))
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Entity helpers
# ---------------------------------------------------------------------------

def create_aliens(start_x, start_y):
    """Create a fresh alien formation grid."""
    aliens = []
    for row in range(NUM_ALIEN_ROWS):
        alien_type = ALIEN_TYPES[row]
        for col in range(NUM_ALIEN_COLS):
            aliens.append({
                "x": start_x + col * ALIEN_SPACING_X,
                "y": start_y + row * ALIEN_SPACING_Y,
                "alive": True,
                "chars": alien_type["chars"],
                "char": alien_type["chars"][0],
                "frame": 0,
                "points": alien_type["points"],
                "alien_type": row,
                "row": row,
                "col": col,
            })
    return aliens


def create_shields(screen_width, shield_y):
    """Create shield barriers as a list of individual block positions."""
    shields = []
    spacing = screen_width // (SHIELD_COUNT + 1)
    for i in range(SHIELD_COUNT):
        cx = spacing * (i + 1)
        for dy in range(SHIELD_HEIGHT):
            for dx in range(SHIELD_WIDTH):
                shields.append({
                    "x": cx - SHIELD_WIDTH // 2 + dx,
                    "y": shield_y + dy,
                    "alive": True,
                })
    return shields


# ---------------------------------------------------------------------------
# Collision detection
# ---------------------------------------------------------------------------

def check_collision(bx, by, targets, width=1):
    """Check if a bullet at (bx, by) collides with any target.

    Returns the target dict that was hit, or None.
    """
    for t in targets:
        if not t.get("alive", True):
            continue
        tw = len(t.get("char", " "))
        if tw < 1:
            tw = 1
        if by == t["y"] and t["x"] <= bx < t["x"] + tw:
            return t
    return None


def check_hit(bx, by, target_x, target_y, target_width):
    """Check if bullet at (bx, by) intersects a target rectangle.

    Checks both the exact row and one row above to prevent bullets
    skipping past the target between frames.
    """
    return (target_y - 1 <= by <= target_y) and target_x <= bx < target_x + target_width


# ---------------------------------------------------------------------------
# Update functions
# ---------------------------------------------------------------------------

def update_bullets(bullets, direction, max_y, min_y=0):
    """Move bullets in the given direction, removing those off-screen."""
    remaining = []
    for b in bullets:
        b["y"] += direction
        if min_y <= b["y"] <= max_y:
            remaining.append(b)
    return remaining


def move_aliens(aliens, direction, speed, field_width, drop_amount=1):
    """Move alien formation, reverse direction + descend at edges.

    Returns new direction.
    """
    # Find bounding box of living aliens
    live = [a for a in aliens if a["alive"]]
    if not live:
        return direction

    min_x = min(a["x"] for a in live)
    max_x = max(a["x"] + len(a["char"]) - 1 for a in live)

    need_reverse = False
    if direction > 0 and max_x + speed >= field_width - 1:
        need_reverse = True
    elif direction < 0 and min_x + (speed * direction) <= 0:
        need_reverse = True

    if need_reverse:
        for a in live:
            a["y"] += drop_amount
            # Toggle animation frame on each movement tick
            a["frame"] = 1 - a["frame"]
            a["char"] = a["chars"][a["frame"]]
        return -direction
    else:
        for a in live:
            a["x"] += speed * direction
            # Toggle animation frame on each movement tick
            a["frame"] = 1 - a["frame"]
            a["char"] = a["chars"][a["frame"]]
        return direction


def process_alien_shooting(aliens, alien_bullets, field_height):
    """Randomly fire bullets from bottom-most aliens in each column."""
    # Find bottom-most alien per column
    columns = {}
    for a in aliens:
        if not a["alive"]:
            continue
        col = a["col"]
        if col not in columns or a["row"] > columns[col]["row"]:
            columns[col] = a

    for a in columns.values():
        if random.random() < ALIEN_SHOOT_CHANCE:
            alien_bullets.append({
                "x": a["x"] + len(a["char"]) // 2,
                "y": a["y"] + 1,
            })


def update_ufo(ufo, field_width):
    """Move UFO across the screen. Returns None if off-screen."""
    if ufo is None:
        return None
    ufo["x"] += ufo["direction"]
    if ufo["x"] < -len(UFO_CHAR) or ufo["x"] > field_width:
        return None
    return ufo


def spawn_ufo(field_width):
    """Possibly spawn a UFO. Returns a UFO dict or None."""
    if random.random() < UFO_SPAWN_CHANCE:
        going_right = random.choice([True, False])
        return {
            "x": -len(UFO_CHAR) if going_right else field_width,
            "direction": 1 if going_right else -1,
            "points": random.choice([50, 100, 150, 200, 300]),
            "char": UFO_CHAR,
        }
    return None


def tick_speed(alive_count, total_count, base_interval):
    """Calculate movement interval — aliens speed up as fewer remain.

    Returns the number of frames between alien movement steps.
    Fewer aliens → shorter interval → faster movement.
    """
    if total_count == 0:
        return base_interval
    ratio = alive_count / total_count
    # Speed increases as ratio decreases
    min_interval = max(1, base_interval // 6)
    interval = max(min_interval, int(base_interval * ratio))
    return interval


# ---------------------------------------------------------------------------
# Draw functions
# ---------------------------------------------------------------------------

def draw_aliens(stdscr, aliens, max_y, max_x):
    """Render all living aliens."""
    color_map = {
        0: curses.color_pair(COLOR_ALIEN_ROW1),
        1: curses.color_pair(COLOR_ALIEN_ROW2),
        2: curses.color_pair(COLOR_ALIEN_ROW3),
        3: curses.color_pair(COLOR_ALIEN_ROW4),
    }
    for a in aliens:
        if not a["alive"]:
            continue
        if 0 <= a["y"] < max_y - 1 and 0 <= a["x"] < max_x - len(a["char"]):
            try:
                stdscr.addstr(a["y"], a["x"], a["char"],
                              color_map.get(a["alien_type"],
                                            curses.color_pair(0)))
            except curses.error:
                pass


def draw_shields(stdscr, shields, max_y, max_x):
    """Render all surviving shield blocks."""
    color = curses.color_pair(COLOR_SHIELD)
    for s in shields:
        if not s["alive"]:
            continue
        if 0 <= s["y"] < max_y - 1 and 0 <= s["x"] < max_x - 1:
            try:
                stdscr.addstr(s["y"], s["x"], SHIELD_CHAR, color)
            except curses.error:
                pass


def draw_player(stdscr, player_x, player_y, max_y, max_x):
    """Render the player ship."""
    if 0 <= player_y < max_y - 1 and 0 <= player_x < max_x - len(PLAYER_CHAR):
        try:
            stdscr.addstr(player_y, player_x, PLAYER_CHAR,
                          curses.color_pair(COLOR_PLAYER))
        except curses.error:
            pass


def draw_bullets(stdscr, bullets, char, color_pair, max_y, max_x):
    """Render a list of bullets."""
    color = curses.color_pair(color_pair)
    for b in bullets:
        if 0 <= b["y"] < max_y - 1 and 0 <= b["x"] < max_x - 1:
            try:
                stdscr.addstr(b["y"], b["x"], char, color)
            except curses.error:
                pass


def draw_ufo(stdscr, ufo, max_y, max_x):
    """Render UFO if present."""
    if ufo is None:
        return
    color = curses.color_pair(COLOR_UFO)
    if 0 <= ufo["y"] < max_y - 1 and 0 <= ufo["x"] < max_x - len(ufo["char"]):
        try:
            stdscr.addstr(ufo["y"], ufo["x"], ufo["char"], color)
        except curses.error:
            pass


def draw_hud(stdscr, score, high_score, lives, wave, max_x):
    """Render the heads-up display (score, lives, wave)."""
    color = curses.color_pair(COLOR_HUD)
    hud_left = f" Score: {score}  High Score: {high_score} "
    hud_right = f" Lives: {lives}  Wave: {wave} "
    try:
        stdscr.addstr(0, 0, hud_left, color | curses.A_BOLD)
        right_x = max(0, max_x - len(hud_right) - 1)
        stdscr.addstr(0, right_x, hud_right, color | curses.A_BOLD)
    except curses.error:
        pass


def draw_game_over(stdscr, score, high_score, max_y, max_x):
    """Render the game over screen."""
    color = curses.color_pair(COLOR_GAMEOVER) | curses.A_BOLD
    lines = [
        "╔══════════════════════════╗",
        "║       GAME OVER          ║",
        f"║  Score: {score:<17}║",
        f"║  High Score: {high_score:<12}║",
        "║                          ║",
        "║  Press 'r' to restart    ║",
        "║  Press 'q' to quit       ║",
        "╚══════════════════════════╝",
    ]
    start_y = max_y // 2 - len(lines) // 2
    for i, line in enumerate(lines):
        x = max_x // 2 - len(line) // 2
        if 0 <= start_y + i < max_y - 1 and x >= 0:
            try:
                stdscr.addstr(start_y + i, x, line, color)
            except curses.error:
                pass


# ---------------------------------------------------------------------------
# Wave setup
# ---------------------------------------------------------------------------

def init_wave(wave_num, field_width, field_height):
    """Initialize a new wave of aliens.

    Returns (aliens, shields, base_move_interval).
    """
    start_x = max(2, (field_width - NUM_ALIEN_COLS * ALIEN_SPACING_X) // 2)
    start_y = 3
    aliens = create_aliens(start_x, start_y)

    shield_y = field_height - 8
    shields = create_shields(field_width, shield_y)

    # Each wave gets faster — reduce base interval
    base_interval = max(4, 20 - wave_num * 2)

    return aliens, shields, base_interval


# ---------------------------------------------------------------------------
# Main game
# ---------------------------------------------------------------------------

def main(stdscr):
    """Main game loop — called by curses.wrapper()."""
    # Curses setup
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(0)
    curses.start_color()
    curses.use_default_colors()

    # Initialize color pairs
    curses.init_pair(COLOR_PLAYER, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_ALIEN_ROW1, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_ALIEN_ROW2, curses.COLOR_MAGENTA, -1)
    curses.init_pair(COLOR_ALIEN_ROW3, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_ALIEN_ROW4, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_SHIELD, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_UFO, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_BULLET, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_HUD, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_ALIEN_BULLET, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_GAMEOVER, curses.COLOR_RED, -1)

    max_y, max_x = stdscr.getmaxyx()

    # Game state
    score = 0
    high_score = load_high_score()
    lives = STARTING_LIVES
    wave = 1
    game_over = False

    # Player
    player_x = max_x // 2 - len(PLAYER_CHAR) // 2
    player_y = max_y - 3

    # Bullets
    player_bullets = []
    alien_bullets = []

    # UFO
    ufo = None

    # Wave setup
    aliens, shields, base_move_interval = init_wave(wave, max_x, max_y)
    total_aliens = sum(1 for a in aliens if a["alive"])
    alien_direction = 1
    move_counter = 0

    # Invincibility frames after being hit
    invincible_timer = 0

    while True:
        frame_start = time.time()

        # --- Input ---
        key = stdscr.getch()

        if game_over:
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('r') or key == ord('R'):
                # Restart game
                score = 0
                lives = STARTING_LIVES
                wave = 1
                game_over = False
                player_x = max_x // 2 - len(PLAYER_CHAR) // 2
                player_bullets = []
                alien_bullets = []
                ufo = None
                aliens, shields, base_move_interval = init_wave(wave, max_x, max_y)
                total_aliens = sum(1 for a in aliens if a["alive"])
                alien_direction = 1
                move_counter = 0
                invincible_timer = 0
            # Draw game over screen
            stdscr.erase()
            draw_game_over(stdscr, score, high_score, max_y, max_x)
            stdscr.refresh()
            elapsed = time.time() - frame_start
            time.sleep(max(0, FRAME_DELAY - elapsed))
            continue

        # Player movement
        if key == curses.KEY_LEFT:
            player_x = max(0, player_x - 2)
        elif key == curses.KEY_RIGHT:
            player_x = min(max_x - len(PLAYER_CHAR) - 1, player_x + 2)
        elif key == ord(' '):
            # Shoot — limit active bullets
            if len(player_bullets) < MAX_PLAYER_BULLETS:
                player_bullets.append({
                    "x": player_x + len(PLAYER_CHAR) // 2,
                    "y": player_y - 1,
                })
        elif key == ord('q') or key == ord('Q'):
            break

        # --- Update ---

        # Move player bullets up
        player_bullets = update_bullets(player_bullets, -1, max_y)

        # Move alien bullets down
        alien_bullets = update_bullets(alien_bullets, 1, max_y)

        # Alien formation movement (tick-based speed)
        alive_count = sum(1 for a in aliens if a["alive"])
        current_interval = tick_speed(alive_count, total_aliens, base_move_interval)
        move_counter += 1
        if move_counter >= current_interval:
            move_counter = 0
            alien_direction = move_aliens(aliens, alien_direction, 1, max_x)

        # Alien shooting
        process_alien_shooting(aliens, alien_bullets, max_y)

        # UFO
        if ufo is None:
            ufo = spawn_ufo(max_x)
            if ufo is not None:
                ufo["y"] = 1
        else:
            ufo = update_ufo(ufo, max_x)

        # --- Collision Detection ---

        # Player bullets vs aliens
        for b in player_bullets[:]:
            hit = check_collision(b["x"], b["y"], aliens)
            if hit:
                hit["alive"] = False
                score += hit["points"]
                if b in player_bullets:
                    player_bullets.remove(b)

        # Player bullets vs UFO
        if ufo is not None:
            for b in player_bullets[:]:
                if check_hit(b["x"], b["y"], ufo["x"], ufo["y"],
                             len(ufo["char"])):
                    score += ufo["points"]
                    ufo = None
                    if b in player_bullets:
                        player_bullets.remove(b)
                    break

        # Player bullets vs shields (erode from top)
        for b in player_bullets[:]:
            hit_shield = check_collision(b["x"], b["y"],
                                         [s for s in shields if s["alive"]])
            if hit_shield:
                hit_shield["alive"] = False
                if b in player_bullets:
                    player_bullets.remove(b)

        # Alien bullets vs shields (erode from bottom)
        for b in alien_bullets[:]:
            hit_shield = check_collision(b["x"], b["y"],
                                         [s for s in shields if s["alive"]])
            if hit_shield:
                hit_shield["alive"] = False
                if b in alien_bullets:
                    alien_bullets.remove(b)

        # Alien bullets vs player
        if invincible_timer <= 0:
            for b in alien_bullets[:]:
                if check_hit(b["x"], b["y"], player_x, player_y,
                             len(PLAYER_CHAR)):
                    lives -= 1
                    if b in alien_bullets:
                        alien_bullets.remove(b)
                    invincible_timer = FPS  # ~1 second of invincibility
                    if lives <= 0:
                        game_over = True
                        if score > high_score:
                            high_score = score
                            save_high_score(high_score)
                    break

        if invincible_timer > 0:
            invincible_timer -= 1

        # Check if aliens reached bottom — game over
        for a in aliens:
            if a["alive"] and a["y"] >= player_y - 1:
                game_over = True
                if score > high_score:
                    high_score = score
                    save_high_score(high_score)
                break

        # Check wave complete
        if alive_count == 0 and not game_over:
            wave += 1
            aliens, shields, base_move_interval = init_wave(wave, max_x, max_y)
            total_aliens = sum(1 for a in aliens if a["alive"])
            alien_direction = 1
            move_counter = 0
            player_bullets = []
            alien_bullets = []
            ufo = None

        # --- Draw ---
        stdscr.erase()

        draw_hud(stdscr, score, high_score, lives, wave, max_x)
        draw_shields(stdscr, shields, max_y, max_x)
        draw_aliens(stdscr, aliens, max_y, max_x)
        draw_player(stdscr, player_x, player_y, max_y, max_x)
        draw_bullets(stdscr, player_bullets, BULLET_CHAR, COLOR_BULLET,
                     max_y, max_x)
        draw_bullets(stdscr, alien_bullets, ALIEN_BULLET_CHAR, COLOR_ALIEN_BULLET,
                     max_y, max_x)
        draw_ufo(stdscr, ufo, max_y, max_x)

        stdscr.refresh()

        # Frame rate limiter
        elapsed = time.time() - frame_start
        time.sleep(max(0, FRAME_DELAY - elapsed))


if __name__ == "__main__":
    curses.wrapper(main)
