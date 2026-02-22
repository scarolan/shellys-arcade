#!/usr/bin/env python3
"""
Neon Drift -- Terminal Racing Game using Python curses.
Race your hoverbike through the neon-lit streets of Neo-Shibuya!
Dodge traffic, collect sats, and activate nitro to survive.
Arrow keys or A/D to steer, Space for nitro, Q to quit.
"""

import curses
import os
import random
import time

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FPS = 30
FRAME_DELAY = 1.0 / FPS

NUM_LANES = 5
ROAD_WIDTH = 30       # characters wide
MIN_WIDTH = 50
MIN_HEIGHT = 30

BASE_SPEED = 1.0
MAX_SPEED = 4.0
SPEED_INCREMENT = 0.002   # per frame
NITRO_SPEED_BONUS = 2.0
NITRO_MAX_FUEL = 100
NITRO_DRAIN_RATE = 2      # per frame while active
NITRO_PICKUP_AMOUNT = 40

STARTING_SHIELD = 3
MAX_SHIELD = 5
INVINCIBLE_FRAMES = 45    # ~1.5 seconds

OBSTACLE_SPAWN_CHANCE = 0.08
PICKUP_SPAWN_CHANCE = 0.025
MIN_OBSTACLE_GAP = 4       # minimum rows between obstacles in same lane
RAIN_SPAWN_CHANCE = 0.3
RAIN_MAX = 60

HIGH_SCORE_DIR = os.path.expanduser("~/.shelly-ops")
HIGH_SCORE_FILE = os.path.join(HIGH_SCORE_DIR, "neondrift-highscore.txt")

# Color pair IDs
COLOR_ROAD = 1
COLOR_PLAYER = 2
COLOR_PLAYER_NITRO = 3
COLOR_OBSTACLE_CAR = 4
COLOR_OBSTACLE_TRUCK = 5
COLOR_OBSTACLE_BARRIER = 6
COLOR_OBSTACLE_DRONE = 7
COLOR_PICKUP_NITRO = 8
COLOR_PICKUP_SATS = 9
COLOR_PICKUP_REPAIR = 10
COLOR_HUD = 11
COLOR_RAIN = 12
COLOR_BUILDING = 13
COLOR_DIVIDER = 14
COLOR_TITLE = 15
COLOR_GAMEOVER = 16

# ---------------------------------------------------------------------------
# Nerd Font Glyphs + ASCII fallback
# ---------------------------------------------------------------------------

GLYPHS_NERD = {
    "bike":       "\uf21c",       # nf-fa-motorcycle
    "car":        "\uf1b9",       # nf-fa-car
    "truck":      "\uf0d1",       # nf-fa-truck
    "barrier":    "\uf071",       # nf-fa-warning
    "drone":      "\uf17b",       # nf-fa-android (drone-like)
    "nitro":      "\uf0e7",       # nf-fa-bolt
    "sats":       "\uf155",       # nf-fa-dollar
    "repair":     "\uf0f9",       # nf-fa-medkit (plus)
    "heart":      "\uf004",       # nf-fa-heart
    "heart_empty": "\uf08a",      # nf-fa-heart_o
    "fuel":       "\uf0e7",       # nf-fa-bolt
    "speed":      "\uf0e4",       # nf-fa-tachometer
    "building":   "\u2588",       # full block
    "rain":       "\u2502",       # light vertical
}

GLYPHS_ASCII = {
    "bike":       "A",
    "car":        "#",
    "truck":      "H",
    "barrier":    "X",
    "drone":      "*",
    "nitro":      "N",
    "sats":       "$",
    "repair":     "+",
    "heart":      "<3",
    "heart_empty": "..",
    "fuel":       "!",
    "speed":      ">",
    "building":   "#",
    "rain":       "|",
}

# Obstacle type definitions: (key, weight_at_low_speed, weight_at_high_speed)
OBSTACLE_TYPES = [
    ("car",     50, 30),
    ("truck",   25, 25),
    ("barrier", 15, 25),
    ("drone",   10, 20),
]

OBSTACLE_COLOR_MAP = {
    "car":     COLOR_OBSTACLE_CAR,
    "truck":   COLOR_OBSTACLE_TRUCK,
    "barrier": COLOR_OBSTACLE_BARRIER,
    "drone":   COLOR_OBSTACLE_DRONE,
}

PICKUP_TYPES = [
    ("nitro",  40),
    ("sats",   40),
    ("repair", 20),
]

PICKUP_COLOR_MAP = {
    "nitro":  COLOR_PICKUP_NITRO,
    "sats":   COLOR_PICKUP_SATS,
    "repair": COLOR_PICKUP_REPAIR,
}


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
# Glyph helper
# ---------------------------------------------------------------------------

def get_char(key, use_nerd):
    """Return glyph string for key based on current mode."""
    if use_nerd:
        return GLYPHS_NERD.get(key, "?")
    return GLYPHS_ASCII.get(key, "?")


# ---------------------------------------------------------------------------
# Layout calculation
# ---------------------------------------------------------------------------

def calculate_layout(max_y, max_x):
    """Calculate road bounds, lane centers, and margin positions."""
    road_left = (max_x - ROAD_WIDTH) // 2
    road_right = road_left + ROAD_WIDTH - 1
    lane_width = ROAD_WIDTH // NUM_LANES
    lane_centers = []
    for i in range(NUM_LANES):
        center = road_left + i * lane_width + lane_width // 2
        lane_centers.append(center)

    return {
        "road_left": road_left,
        "road_right": road_right,
        "road_width": ROAD_WIDTH,
        "lane_width": lane_width,
        "lane_centers": lane_centers,
        "margin_left": road_left - 1,
        "margin_right": road_right + 1,
        "play_top": 2,          # below HUD
        "play_bottom": max_y - 2,  # above bottom HUD
        "max_y": max_y,
        "max_x": max_x,
    }


# ---------------------------------------------------------------------------
# Entity creation
# ---------------------------------------------------------------------------

def create_player(layout):
    """Create the player hoverbike dict."""
    return {
        "lane": NUM_LANES // 2,
        "x": layout["lane_centers"][NUM_LANES // 2],
        "y": layout["play_bottom"] - 2,
        "shield": STARTING_SHIELD,
        "speed": BASE_SPEED,
        "nitro_fuel": 0,
        "nitro_active": False,
        "invincible": 0,
        "distance": 0.0,
        "sats": 0,
        "score": 0,
    }


def pick_obstacle_type(speed):
    """Choose a weighted-random obstacle type based on current speed."""
    ratio = min(1.0, (speed - BASE_SPEED) / (MAX_SPEED - BASE_SPEED))
    weights = []
    for _, low_w, high_w in OBSTACLE_TYPES:
        w = low_w + (high_w - low_w) * ratio
        weights.append(w)
    total = sum(weights)
    r = random.random() * total
    cumulative = 0
    for i, w in enumerate(weights):
        cumulative += w
        if r <= cumulative:
            return OBSTACLE_TYPES[i][0]
    return OBSTACLE_TYPES[0][0]


def spawn_obstacle(layout, obstacles, speed):
    """Try to spawn a new obstacle at the top of the play area."""
    if random.random() > OBSTACLE_SPAWN_CHANCE:
        return None
    lane = random.randint(0, NUM_LANES - 1)
    y = layout["play_top"]
    # Gap enforcement: don't spawn too close to existing obstacles in same lane
    for obs in obstacles:
        if obs["lane"] == lane and abs(obs["y"] - y) < MIN_OBSTACLE_GAP:
            return None
    obs_type = pick_obstacle_type(speed)
    return {
        "lane": lane,
        "x": layout["lane_centers"][lane],
        "y": y,
        "type": obs_type,
    }


def pick_pickup_type():
    """Choose a weighted-random pickup type."""
    total = sum(w for _, w in PICKUP_TYPES)
    r = random.random() * total
    cumulative = 0
    for ptype, w in PICKUP_TYPES:
        cumulative += w
        if r <= cumulative:
            return ptype
    return PICKUP_TYPES[0][0]


def spawn_pickup(layout, pickups):
    """Try to spawn a pickup at the top of the play area."""
    if random.random() > PICKUP_SPAWN_CHANCE:
        return None
    lane = random.randint(0, NUM_LANES - 1)
    y = layout["play_top"]
    # Don't stack pickups
    for p in pickups:
        if p["lane"] == lane and abs(p["y"] - y) < MIN_OBSTACLE_GAP:
            return None
    ptype = pick_pickup_type()
    return {
        "lane": lane,
        "x": layout["lane_centers"][lane],
        "y": y,
        "type": ptype,
    }


# ---------------------------------------------------------------------------
# Update functions
# ---------------------------------------------------------------------------

def update_scroll(obstacles, pickups, layout, scroll_acc, speed):
    """Scroll obstacles and pickups downward based on speed.

    Uses a fractional accumulator so sub-pixel speeds work.
    Returns (obstacles, pickups, new_accumulator).
    """
    scroll_acc += speed
    steps = int(scroll_acc)
    scroll_acc -= steps

    bottom = layout["play_bottom"]

    for _ in range(steps):
        for obs in obstacles:
            obs["y"] += 1
        for p in pickups:
            p["y"] += 1

    obstacles = [o for o in obstacles if o["y"] <= bottom + 1]
    pickups = [p for p in pickups if p["y"] <= bottom + 1]

    return obstacles, pickups, scroll_acc


def update_rain(rain_particles, layout):
    """Move rain particles down, remove off-screen, spawn new ones."""
    for r in rain_particles:
        r["y"] += 1

    rain_particles = [r for r in rain_particles if r["y"] <= layout["play_bottom"]]

    while len(rain_particles) < RAIN_MAX and random.random() < RAIN_SPAWN_CHANCE:
        rain_particles.append({
            "x": random.randint(0, layout["max_x"] - 2),
            "y": random.randint(layout["play_top"], layout["play_top"] + 3),
        })

    return rain_particles


def update_buildings(building_offsets, frame_count):
    """Update building parallax offsets (scroll at 30% main speed)."""
    if frame_count % 3 == 0:
        for b in building_offsets:
            b["y"] += 1
            if b["y"] > b["max_y"]:
                b["y"] = b["start_y"]
    return building_offsets


def create_building_offsets(layout):
    """Create initial building segment positions for both margins."""
    offsets = []
    for side in ("left", "right"):
        x = layout["margin_left"] - 3 if side == "left" else layout["margin_right"] + 1
        for row in range(layout["play_top"], layout["play_bottom"], 4):
            offsets.append({
                "x": x,
                "y": row,
                "start_y": layout["play_top"],
                "max_y": layout["play_bottom"],
                "width": 3,
                "side": side,
            })
    return offsets


def update_nitro(player):
    """Tick nitro fuel, deactivate when empty."""
    if player["nitro_active"]:
        player["nitro_fuel"] -= NITRO_DRAIN_RATE
        if player["nitro_fuel"] <= 0:
            player["nitro_fuel"] = 0
            player["nitro_active"] = False


# ---------------------------------------------------------------------------
# Collision detection
# ---------------------------------------------------------------------------

def check_player_obstacle_collision(player, obstacles):
    """Check if player collides with any obstacle. Returns hit obstacle or None."""
    for obs in obstacles:
        if obs["lane"] == player["lane"]:
            if abs(obs["y"] - player["y"]) <= 1:
                return obs
    return None


def check_player_pickup_collision(player, pickups):
    """Check if player collides with any pickup. Returns hit pickup or None."""
    for p in pickups:
        if p["lane"] == player["lane"]:
            if abs(p["y"] - player["y"]) <= 1:
                return p
    return None


# ---------------------------------------------------------------------------
# Safe draw helper
# ---------------------------------------------------------------------------

def safe_addstr(stdscr, y, x, text, attr=0):
    """Write text to screen, silently ignoring out-of-bounds errors."""
    try:
        max_y, max_x = stdscr.getmaxyx()
        if 0 <= y < max_y and 0 <= x < max_x:
            # Truncate text if it would go off-screen
            available = max_x - x - 1
            if available > 0:
                stdscr.addstr(y, x, text[:available], attr)
    except curses.error:
        pass


# ---------------------------------------------------------------------------
# Draw functions
# ---------------------------------------------------------------------------

def draw_road(stdscr, layout, frame_count):
    """Draw road edges and dashed lane dividers."""
    left = layout["road_left"]
    right = layout["road_right"]
    lane_w = layout["lane_width"]
    color_road = curses.color_pair(COLOR_ROAD)
    color_div = curses.color_pair(COLOR_DIVIDER)

    for row in range(layout["play_top"], layout["play_bottom"] + 1):
        # Road edges
        safe_addstr(stdscr, row, left - 1, "\u2551", color_road | curses.A_BOLD)
        safe_addstr(stdscr, row, right + 1, "\u2551", color_road | curses.A_BOLD)

        # Lane dividers (dashed, scroll with frame)
        for lane_i in range(1, NUM_LANES):
            div_x = left + lane_i * lane_w
            if (row + frame_count // 2) % 3 != 0:
                safe_addstr(stdscr, row, div_x, "\u2506", color_div | curses.A_DIM)


def draw_buildings(stdscr, building_offsets, layout, use_nerd):
    """Draw parallax building margins."""
    glyph = get_char("building", use_nerd)
    color = curses.color_pair(COLOR_BUILDING) | curses.A_DIM

    for b in building_offsets:
        for dx in range(b["width"]):
            bx = b["x"] + dx
            if 0 <= bx < layout["max_x"] - 1:
                safe_addstr(stdscr, b["y"], bx, glyph, color)
                if b["y"] + 1 <= layout["play_bottom"]:
                    safe_addstr(stdscr, b["y"] + 1, bx, glyph, color)


def draw_rain(stdscr, rain_particles, layout, use_nerd):
    """Draw falling rain particles."""
    glyph = get_char("rain", use_nerd)
    color = curses.color_pair(COLOR_RAIN) | curses.A_DIM

    for r in rain_particles:
        if layout["play_top"] <= r["y"] <= layout["play_bottom"]:
            safe_addstr(stdscr, r["y"], r["x"], glyph, color)


def draw_obstacles(stdscr, obstacles, layout, use_nerd):
    """Draw all obstacles on screen."""
    for obs in obstacles:
        if layout["play_top"] <= obs["y"] <= layout["play_bottom"]:
            glyph = get_char(obs["type"], use_nerd)
            color_id = OBSTACLE_COLOR_MAP.get(obs["type"], COLOR_OBSTACLE_CAR)
            color = curses.color_pair(color_id) | curses.A_BOLD
            safe_addstr(stdscr, obs["y"], obs["x"], glyph, color)


def draw_pickups(stdscr, pickups, layout, use_nerd):
    """Draw all pickups on screen."""
    for p in pickups:
        if layout["play_top"] <= p["y"] <= layout["play_bottom"]:
            glyph = get_char(p["type"], use_nerd)
            color_id = PICKUP_COLOR_MAP.get(p["type"], COLOR_PICKUP_SATS)
            color = curses.color_pair(color_id) | curses.A_BOLD
            safe_addstr(stdscr, p["y"], p["x"], glyph, color)


def draw_player(stdscr, player, layout, frame_count, use_nerd):
    """Draw the player hoverbike."""
    if player["invincible"] > 0 and frame_count % 4 < 2:
        return  # Blink during invincibility

    glyph = get_char("bike", use_nerd)
    if player["nitro_active"]:
        color = curses.color_pair(COLOR_PLAYER_NITRO) | curses.A_BOLD
    else:
        color = curses.color_pair(COLOR_PLAYER) | curses.A_BOLD

    safe_addstr(stdscr, player["y"], player["x"], glyph, color)

    # Draw exhaust trail below bike
    if player["y"] + 1 <= layout["play_bottom"]:
        exhaust = "\u2503" if not use_nerd else "\u2503"
        exhaust_color = curses.color_pair(COLOR_PLAYER_NITRO if player["nitro_active"]
                                          else COLOR_PLAYER) | curses.A_DIM
        safe_addstr(stdscr, player["y"] + 1, player["x"], exhaust, exhaust_color)


def draw_hud(stdscr, player, high_score, layout, use_nerd):
    """Draw the heads-up display — speed, distance, sats, shield, nitro."""
    color = curses.color_pair(COLOR_HUD) | curses.A_BOLD
    max_x = layout["max_x"]

    # Top row: speed + distance
    speed_display = f" SPD: {player['speed']:.1f}  DIST: {int(player['distance'])} "
    safe_addstr(stdscr, 0, 0, speed_display, color)

    # Top row right: sats + score
    score_display = f" SATS: {player['sats']}  SCORE: {player['score']}  HI: {high_score} "
    right_x = max(0, max_x - len(score_display) - 1)
    safe_addstr(stdscr, 0, right_x, score_display, color)

    # Bottom row: shield hearts + nitro gauge
    bottom_y = layout["max_y"] - 1
    hearts = ""
    heart_full = get_char("heart", use_nerd)
    heart_empty = get_char("heart_empty", use_nerd)
    for i in range(MAX_SHIELD):
        if i < player["shield"]:
            hearts += heart_full + " "
        else:
            hearts += heart_empty + " "
    shield_str = f" SHIELD: {hearts}"
    safe_addstr(stdscr, bottom_y, 0, shield_str,
                curses.color_pair(COLOR_PICKUP_REPAIR) | curses.A_BOLD)

    # Nitro gauge
    fuel_pct = player["nitro_fuel"] / NITRO_MAX_FUEL if NITRO_MAX_FUEL > 0 else 0
    bar_len = 10
    filled = int(fuel_pct * bar_len)
    bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
    nitro_label = "NITRO" if not player["nitro_active"] else "NITRO!"
    nitro_str = f" {nitro_label}: [{bar}] "
    nitro_x = max(0, max_x - len(nitro_str) - 1)
    nitro_color = (curses.color_pair(COLOR_PLAYER_NITRO) | curses.A_BOLD
                   if player["nitro_active"]
                   else curses.color_pair(COLOR_PICKUP_NITRO))
    safe_addstr(stdscr, bottom_y, nitro_x, nitro_str, nitro_color)


# ---------------------------------------------------------------------------
# Game screens
# ---------------------------------------------------------------------------

def draw_title_screen(stdscr, high_score, max_y, max_x, use_nerd):
    """Draw the title screen with ASCII art and controls."""
    color_title = curses.color_pair(COLOR_TITLE) | curses.A_BOLD
    color_text = curses.color_pair(COLOR_HUD)
    color_neon = curses.color_pair(COLOR_PLAYER_NITRO) | curses.A_BOLD

    title_art = [
        " _   _                    ____       _  __ _   ",
        "| \\ | | ___  ___  _ __   |  _ \\ _ __(_)/ _| |_ ",
        "|  \\| |/ _ \\/ _ \\| '_ \\  | | | | '__| | |_| __|",
        "| |\\  |  __/ (_) | | | | | |_| | |  | |  _| |_ ",
        "|_| \\_|\\___|\\___/|_| |_| |____/|_|  |_|_|  \\__|",
    ]

    start_y = max_y // 2 - 10
    for i, line in enumerate(title_art):
        x = max_x // 2 - len(line) // 2
        if 0 <= start_y + i < max_y - 1 and x >= 0:
            safe_addstr(stdscr, start_y + i, x, line, color_title)

    subtitle = "~ Neo-Shibuya Hoverbike Racing ~"
    sx = max_x // 2 - len(subtitle) // 2
    safe_addstr(stdscr, start_y + 6, sx, subtitle, color_neon)

    controls = [
        "",
        "CONTROLS:",
        "  Arrow Keys / A,D  -  Steer left/right",
        "  Space             -  Activate Nitro",
        "  T                 -  Toggle NerdFont/ASCII",
        "  Q                 -  Quit",
        "",
        f"  High Score: {high_score}",
        "",
        "  Press any key to start...",
    ]

    for i, line in enumerate(controls):
        cy = start_y + 8 + i
        cx = max_x // 2 - len(line) // 2
        if 0 <= cy < max_y - 1 and cx >= 0:
            safe_addstr(stdscr, cy, cx, line, color_text)


def draw_game_over(stdscr, player, high_score, max_y, max_x):
    """Draw the game over stats box."""
    color = curses.color_pair(COLOR_GAMEOVER) | curses.A_BOLD

    lines = [
        "\u2554" + "\u2550" * 30 + "\u2557",
        "\u2551" + "        GAME OVER             " + "\u2551",
        "\u2551" + f"  Distance: {int(player['distance']):<18}" + "\u2551",
        "\u2551" + f"  Sats:     {player['sats']:<18}" + "\u2551",
        "\u2551" + f"  Score:    {player['score']:<18}" + "\u2551",
        "\u2551" + f"  High:     {high_score:<18}" + "\u2551",
        "\u2551" + "                              " + "\u2551",
        "\u2551" + "  Press 'r' to restart        " + "\u2551",
        "\u2551" + "  Press 'q' to quit           " + "\u2551",
        "\u255a" + "\u2550" * 30 + "\u255d",
    ]

    start_y = max_y // 2 - len(lines) // 2
    for i, line in enumerate(lines):
        x = max_x // 2 - len(line) // 2
        if 0 <= start_y + i < max_y - 1 and x >= 0:
            safe_addstr(stdscr, start_y + i, x, line, color)


# ---------------------------------------------------------------------------
# Main game
# ---------------------------------------------------------------------------

def main(stdscr):
    """Main game loop -- called by curses.wrapper()."""
    # Curses setup
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(0)
    curses.start_color()
    curses.use_default_colors()

    # Initialize color pairs
    curses.init_pair(COLOR_ROAD, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_PLAYER, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_PLAYER_NITRO, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_OBSTACLE_CAR, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_OBSTACLE_TRUCK, curses.COLOR_MAGENTA, -1)
    curses.init_pair(COLOR_OBSTACLE_BARRIER, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_OBSTACLE_DRONE, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_PICKUP_NITRO, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_PICKUP_SATS, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_PICKUP_REPAIR, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_HUD, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_RAIN, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_BUILDING, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_DIVIDER, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_TITLE, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_GAMEOVER, curses.COLOR_RED, -1)

    max_y, max_x = stdscr.getmaxyx()

    # Terminal size check
    if max_y < MIN_HEIGHT or max_x < MIN_WIDTH:
        stdscr.addstr(0, 0, "Terminal too small!",
                      curses.color_pair(COLOR_GAMEOVER))
        stdscr.addstr(1, 0, f"Need {MIN_HEIGHT}x{MIN_WIDTH}, got {max_y}x{max_x}")
        stdscr.addstr(2, 0, "Press 'q' to quit.")
        stdscr.nodelay(False)
        while stdscr.getch() != ord('q'):
            pass
        return

    # Game mode flags
    use_nerd = True
    high_score = load_high_score()

    # ---- Title screen ----
    stdscr.erase()
    draw_title_screen(stdscr, high_score, max_y, max_x, use_nerd)
    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()  # Wait for any key
    stdscr.nodelay(True)
    stdscr.timeout(0)

    # ---- Game init ----
    def reset_game():
        layout = calculate_layout(max_y, max_x)
        player = create_player(layout)
        return {
            "layout": layout,
            "player": player,
            "obstacles": [],
            "pickups": [],
            "rain": [],
            "buildings": create_building_offsets(layout),
            "scroll_acc": 0.0,
            "frame_count": 0,
            "game_over": False,
        }

    state = reset_game()

    while True:
        frame_start = time.time()

        layout = state["layout"]
        player = state["player"]

        # --- Input ---
        key = stdscr.getch()

        if state["game_over"]:
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('r') or key == ord('R'):
                high_score = load_high_score()
                state = reset_game()
            elif key == ord('t') or key == ord('T'):
                use_nerd = not use_nerd

            stdscr.erase()
            draw_game_over(stdscr, player, high_score, max_y, max_x)
            stdscr.refresh()
            elapsed = time.time() - frame_start
            time.sleep(max(0, FRAME_DELAY - elapsed))
            continue

        # Steering
        if key in (curses.KEY_LEFT, ord('a'), ord('A')):
            if player["lane"] > 0:
                player["lane"] -= 1
                player["x"] = layout["lane_centers"][player["lane"]]
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            if player["lane"] < NUM_LANES - 1:
                player["lane"] += 1
                player["x"] = layout["lane_centers"][player["lane"]]
        elif key == ord(' '):
            # Activate nitro
            if player["nitro_fuel"] > 0 and not player["nitro_active"]:
                player["nitro_active"] = True
        elif key == ord('t') or key == ord('T'):
            use_nerd = not use_nerd
        elif key == ord('q') or key == ord('Q'):
            break

        # --- Update ---

        # Speed increases over time
        if player["speed"] < MAX_SPEED:
            player["speed"] += SPEED_INCREMENT
            if player["speed"] > MAX_SPEED:
                player["speed"] = MAX_SPEED

        effective_speed = player["speed"]
        if player["nitro_active"]:
            effective_speed += NITRO_SPEED_BONUS

        # Scroll entities
        state["obstacles"], state["pickups"], state["scroll_acc"] = update_scroll(
            state["obstacles"], state["pickups"], layout,
            state["scroll_acc"], effective_speed
        )

        # Spawn obstacles and pickups
        new_obs = spawn_obstacle(layout, state["obstacles"], player["speed"])
        if new_obs:
            state["obstacles"].append(new_obs)

        new_pickup = spawn_pickup(layout, state["pickups"])
        if new_pickup:
            state["pickups"].append(new_pickup)

        # Rain
        state["rain"] = update_rain(state["rain"], layout)

        # Buildings parallax
        state["buildings"] = update_buildings(state["buildings"], state["frame_count"])

        # Nitro fuel
        update_nitro(player)

        # Distance / score
        player["distance"] += effective_speed * 0.1
        speed_bonus = int(player["speed"])
        player["score"] = int(player["distance"]) + player["sats"] * 10 + speed_bonus

        # Invincibility countdown
        if player["invincible"] > 0:
            player["invincible"] -= 1

        # --- Collision Detection ---

        # Player vs obstacles
        if player["invincible"] <= 0:
            hit_obs = check_player_obstacle_collision(player, state["obstacles"])
            if hit_obs and not player["nitro_active"]:
                player["shield"] -= 1
                player["invincible"] = INVINCIBLE_FRAMES
                state["obstacles"].remove(hit_obs)
                if player["shield"] <= 0:
                    state["game_over"] = True
                    if player["score"] > high_score:
                        high_score = player["score"]
                        save_high_score(high_score)
            elif hit_obs and player["nitro_active"]:
                # Nitro destroys obstacles
                state["obstacles"].remove(hit_obs)
                player["sats"] += 5  # bonus for nitro smash

        # Player vs pickups
        hit_pickup = check_player_pickup_collision(player, state["pickups"])
        if hit_pickup:
            state["pickups"].remove(hit_pickup)
            if hit_pickup["type"] == "nitro":
                player["nitro_fuel"] = min(NITRO_MAX_FUEL,
                                           player["nitro_fuel"] + NITRO_PICKUP_AMOUNT)
            elif hit_pickup["type"] == "sats":
                player["sats"] += 10
            elif hit_pickup["type"] == "repair":
                if player["shield"] < MAX_SHIELD:
                    player["shield"] += 1

        state["frame_count"] += 1

        # --- Draw ---
        stdscr.erase()

        draw_buildings(stdscr, state["buildings"], layout, use_nerd)
        draw_rain(stdscr, state["rain"], layout, use_nerd)
        draw_road(stdscr, layout, state["frame_count"])
        draw_obstacles(stdscr, state["obstacles"], layout, use_nerd)
        draw_pickups(stdscr, state["pickups"], layout, use_nerd)
        draw_player(stdscr, player, layout, state["frame_count"], use_nerd)
        draw_hud(stdscr, player, high_score, layout, use_nerd)

        stdscr.refresh()

        # Frame rate limiter
        elapsed = time.time() - frame_start
        time.sleep(max(0, FRAME_DELAY - elapsed))


if __name__ == "__main__":
    curses.wrapper(main)
