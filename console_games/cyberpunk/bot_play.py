#!/usr/bin/env python3
"""Cyberpunk Megacity Roguelite — tmux bot player.

Launches the game inside a tmux session, selects Street Samurai,
plays 5-10 turns by parsing the rendered screen, then quits.
Prints a turn-by-turn log of what the bot "sees" and does.
"""

import os
import re
import subprocess
import sys
import time

SESSION = "cyberpunk-bot"
GAME_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyberpunk.py")
COLS, ROWS = 200, 50
TURN_LIMIT = 10


def tmux(*args, capture=False):
    """Run a tmux command."""
    cmd = ["tmux"] + list(args)
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True).stdout
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def send_key(key):
    """Send a key to the tmux pane."""
    tmux("send-keys", "-t", SESSION, key)


def capture_pane():
    """Capture the current tmux pane contents."""
    return tmux("capture-pane", "-t", SESSION, "-p", "-e", capture=True)


def capture_pane_plain():
    """Capture pane without escape sequences."""
    return tmux("capture-pane", "-t", SESSION, "-p", capture=True)


def wait_for(pattern, timeout=15, interval=0.3):
    """Wait until a pattern appears on screen."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        screen = capture_pane_plain()
        if re.search(pattern, screen):
            return screen
        time.sleep(interval)
    return capture_pane_plain()


def cleanup():
    """Kill the tmux session if it exists."""
    subprocess.run(
        ["tmux", "kill-session", "-t", SESSION],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


# ─── Screen parsing helpers ─────────────────────────────────────────────────

# In ASCII mode:
#   Player = @   Enemies = d D S G T N   Items = + $ ) k * ! 0
#   Walls = #    Floor = .   Stairs = >   Terminal = _   Door = +
ENEMY_CHARS = set("dDSGTN")
ITEM_CHARS = set("$)k*")  # skip + (ambiguous with door/medkit) and ! (stim)
WALKABLE_CHARS = set(".>_")

# Characters the player can move onto (floor, corridor, stairs, terminal, open door, shop)
PASSABLE = set(".>_?")


def find_player(lines):
    """Find the @ symbol on the map area (rows 1..40ish, cols 1..~170)."""
    for r, line in enumerate(lines):
        for c, ch in enumerate(line):
            if ch == "@":
                return (r, c)
    return None


def find_chars(lines, charset, map_bounds):
    """Find all characters from charset within the map bounds."""
    rmin, rmax, cmin, cmax = map_bounds
    found = []
    for r in range(rmin, min(rmax, len(lines))):
        for c in range(cmin, min(cmax, len(lines[r]))):
            if lines[r][c] in charset:
                found.append((r, c, lines[r][c]))
    return found


def find_stairs(lines, map_bounds):
    """Find the > (stairs) character."""
    return find_chars(lines, {">"}, map_bounds)


def parse_hp(lines):
    """Extract HP from the status panel (line containing 'HP:')."""
    for line in lines:
        m = re.search(r"HP:\s*(\d+)/(\d+)", line)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None, None


def parse_messages(lines):
    """Extract message log lines (below the map, inside LOG box)."""
    msgs = []
    in_log = False
    for line in lines:
        if "LOG" in line and ("─" in line or "═" in line):
            in_log = True
            continue
        if in_log:
            stripped = line.strip().strip("│║").strip()
            if stripped and not all(c in "─═╔╗╚╝┌┐└┘" for c in stripped):
                msgs.append(stripped)
            if "└" in line or "╚" in line:
                break
    return msgs


def manhattan(a, b):
    """Manhattan distance between two (row, col) points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def direction_toward(pr, pc, tr, tc):
    """Return (key_name, description) to move from player toward target."""
    dr = tr - pr
    dc = tc - pc
    if abs(dr) >= abs(dc):
        if dr < 0:
            return "Up", "up"
        else:
            return "Down", "down"
    else:
        if dc < 0:
            return "Left", "left"
        else:
            return "Right", "right"


def adjacent_passable(lines, pr, pc, map_bounds):
    """Return list of (r, c, direction_key) for passable adjacent cells."""
    rmin, rmax, cmin, cmax = map_bounds
    dirs = [(-1, 0, "Up"), (1, 0, "Down"), (0, -1, "Left"), (0, 1, "Right")]
    result = []
    for dr, dc, key in dirs:
        nr, nc = pr + dr, pc + dc
        if rmin <= nr < rmax and cmin <= nc < cmax and nr < len(lines) and nc < len(lines[nr]):
            ch = lines[nr][nc]
            if ch in PASSABLE or ch in ENEMY_CHARS or ch == "@":
                result.append((nr, nc, key))
    return result


# ─── Bot AI ──────────────────────────────────────────────────────────────────

def decide_action(lines, player_pos, map_bounds, hp, max_hp, has_medkit):
    """Decide what to do this turn. Returns (key_to_send, reason)."""
    pr, pc = player_pos

    # Find entities
    enemies = find_chars(lines, ENEMY_CHARS, map_bounds)
    items = find_chars(lines, ITEM_CHARS, map_bounds)
    stairs = find_stairs(lines, map_bounds)

    # Adjacent enemies → bump attack (move toward)
    adj_enemies = [e for e in enemies if manhattan(player_pos, (e[0], e[1])) == 1]
    if adj_enemies:
        er, ec, ech = adj_enemies[0]
        key, desc = direction_toward(pr, pc, er, ec)
        return key, f"attack adjacent enemy '{ech}' ({desc})"

    # Low HP and has medkit → use it
    if hp is not None and max_hp is not None:
        if hp < max_hp * 0.35 and has_medkit:
            return "m", "use medkit (HP low)"

    # Nearby items (within 5 tiles) → move toward closest
    close_items = [(manhattan(player_pos, (i[0], i[1])), i) for i in items]
    close_items.sort()
    if close_items and close_items[0][0] <= 5:
        _, (ir, ic, ich) = close_items[0]
        key, desc = direction_toward(pr, pc, ir, ic)
        return key, f"move toward item '{ich}' ({desc})"

    # Enemies within 8 tiles → move toward closest
    close_enemies = [(manhattan(player_pos, (e[0], e[1])), e) for e in enemies]
    close_enemies.sort()
    if close_enemies and close_enemies[0][0] <= 8:
        _, (er, ec, ech) = close_enemies[0]
        key, desc = direction_toward(pr, pc, er, ec)
        return key, f"approach enemy '{ech}' ({desc})"

    # Stairs visible → move toward them
    if stairs:
        sr, sc, _ = stairs[0]
        key, desc = direction_toward(pr, pc, sr, sc)
        return key, f"move toward stairs ({desc})"

    # Explore: try each direction, prefer directions with more open space
    passable = adjacent_passable(lines, pr, pc, map_bounds)
    if passable:
        # Pick a random passable direction to explore
        import random
        nr, nc, key = random.choice(passable)
        return key, f"explore ({key.lower()})"

    # Fallback: wait
    return " ", "wait (nowhere to go)"


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  CYBERPUNK MEGACITY ROGUELITE — Bot Player")
    print("=" * 60)
    print()

    # Ensure clean state
    cleanup()

    # Force ASCII tile mode for easier parsing
    settings_file = os.path.expanduser("~/.cyberpunk_settings")
    old_settings = None
    if os.path.exists(settings_file):
        with open(settings_file) as f:
            old_settings = f.read()
    with open(settings_file, "w") as f:
        import json
        json.dump({"tile_mode": "ascii"}, f)

    try:
        # Start tmux session
        print(f"[setup] Starting tmux session '{SESSION}' ({COLS}x{ROWS})...")
        tmux("new-session", "-d", "-s", SESSION, "-x", str(COLS), "-y", str(ROWS))
        time.sleep(0.5)

        # Launch the game
        print(f"[setup] Launching cyberpunk.py...")
        send_key(f"python3 {GAME_SCRIPT}\n")

        # Wait for class selection screen
        print("[setup] Waiting for class selection screen...")
        screen = wait_for(r"Choose your class", timeout=10)
        if "Choose your class" not in screen:
            print("[ERROR] Class selection screen did not appear!")
            print("Screen contents:")
            print(screen[:500])
            return 1

        print("[setup] Class selection screen detected.")
        time.sleep(0.3)

        # Select Street Samurai (first option, already highlighted) → press Enter
        print("[setup] Selecting Street Samurai (Enter)...")
        send_key("Enter")

        # Wait for jack-in sequence, then press any key
        print("[setup] Waiting for jack-in sequence...")
        screen = wait_for(r"Press any key", timeout=15)
        time.sleep(0.5)
        send_key("Enter")

        # Wait for the game map to appear
        print("[setup] Waiting for game to start...")
        screen = wait_for(r"LEVEL 1", timeout=10)
        if "LEVEL 1" not in screen:
            print("[ERROR] Game map did not appear!")
            print(screen[:500])
            return 1

        time.sleep(0.5)
        print("[setup] Game started! Beginning bot play.\n")

        # ── Turn loop ──
        medkit_count = 0
        for turn in range(1, TURN_LIMIT + 1):
            time.sleep(0.4)

            screen = capture_pane_plain()
            lines = screen.split("\n")

            player_pos = find_player(lines)
            if player_pos is None:
                print(f"[turn {turn}] Cannot find player (@) on screen!")
                # Check for game over
                if "GAME OVER" in screen or "SIGNAL LOST" in screen:
                    print(f"[turn {turn}] GAME OVER detected!")
                    break
                if "MISSION COMPLETE" in screen or "JACKED OUT" in screen:
                    print(f"[turn {turn}] VICTORY detected!")
                    break
                # Might be on a sub-screen, press escape/enter
                send_key("Enter")
                continue

            pr, pc = player_pos
            # Estimate map bounds: map starts at row 1, col 1, extends to status panel
            # Status panel is typically at col ~view_w+3; we scan until we see STATUS box
            map_rmin, map_cmin = 1, 1
            map_rmax = min(40, len(lines))
            map_cmax = 170
            # Refine: find STATUS panel column
            for line in lines[:5]:
                idx = line.find("STATUS")
                if idx > 0:
                    map_cmax = idx - 3
                    break
            map_bounds = (map_rmin, map_rmax, map_cmin, map_cmax)

            hp, max_hp = parse_hp(lines)
            messages = parse_messages(lines)

            # Check if we picked up medkits (from messages)
            for msg in messages:
                if "medkit" in msg.lower() and "picked" in msg.lower():
                    medkit_count += 1
                if "used medkit" in msg.lower():
                    medkit_count = max(0, medkit_count - 1)

            # Count visible entities
            enemies = find_chars(lines, ENEMY_CHARS, map_bounds)
            items = find_chars(lines, ITEM_CHARS, map_bounds)
            stairs = find_stairs(lines, map_bounds)

            # Decide action
            key, reason = decide_action(
                lines, player_pos, map_bounds,
                hp, max_hp, medkit_count > 0,
            )

            # Print turn summary
            hp_str = f"{hp}/{max_hp}" if hp is not None else "?/?"
            print(f"[turn {turn:2d}] pos=({pr},{pc})  HP={hp_str}  "
                  f"enemies={len(enemies)}  items={len(items)}  "
                  f"stairs={'yes' if stairs else 'no'}")
            print(f"          action: {reason}")
            if messages:
                for msg in messages[-2:]:
                    print(f"          log: {msg}")
            print()

            # Send the key
            send_key(key)

            # If we stepped on stairs, the game asks "Descend? (y/n)" — say yes
            time.sleep(0.3)
            check = capture_pane_plain()
            if "Descend to the next level" in check:
                print(f"          → Stairs prompt detected, descending!")
                send_key("y")
                time.sleep(0.5)

        # Final state
        time.sleep(0.5)
        final_screen = capture_pane_plain()
        final_hp, final_max = parse_hp(final_screen.split("\n"))
        print("=" * 60)
        print("  Bot session complete!")
        if final_hp is not None:
            print(f"  Final HP: {final_hp}/{final_max}")
        if "GAME OVER" in final_screen or "SIGNAL LOST" in final_screen:
            print("  Result: DIED")
        elif "MISSION COMPLETE" in final_screen:
            print("  Result: VICTORY")
        else:
            print("  Result: ALIVE (quit after turn limit)")
        print("=" * 60)

        # Quit the game cleanly
        send_key("q")
        time.sleep(0.5)

    finally:
        # Restore settings
        if old_settings is not None:
            with open(settings_file, "w") as f:
                f.write(old_settings)
        elif os.path.exists(settings_file):
            os.remove(settings_file)

        # Cleanup tmux
        cleanup()
        print("\n[cleanup] tmux session killed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
