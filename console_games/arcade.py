#!/usr/bin/env python3
"""
Shelly Arcade — Game Launcher TUI
A retro arcade-style terminal menu for launching Python games.
Uses curses for full-screen UI with color themes and ASCII art.
"""

import ast
import curses
import os
import subprocess
import sys
import time

# Scripts to exclude from the game list (not games)
EXCLUDED = {
    "arcade.py",
}

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

ASCII_HEADER_LETTERS = [
    " ███████╗██╗  ██╗███████╗██╗     ██╗  ██╗   ██╗",
    " ██╔════╝██║  ██║██╔════╝██║     ██║  ╚██╗ ██╔╝",
    " ███████╗███████║█████╗  ██║     ██║   ╚████╔╝ ",
    " ╚════██║██╔══██║██╔══╝  ██║     ██║    ╚██╔╝  ",
    " ███████║██║  ██║███████╗███████╗███████╗██║   ",
    " ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝   ",
]

ASCII_HEADER_ARCADE = "🕹️  A R C A D E  🕹️"


def extract_description(filepath):
    """Extract the first docstring from a Python file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        docstring = ast.get_docstring(tree)
        if docstring:
            # Return just the first line of the docstring
            return docstring.strip().split("\n")[0]
    except Exception:
        pass
    # Fallback: look for a # comment on line 2 or 3
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i > 3:
                    break
                line = line.strip()
                if line.startswith("#") and not line.startswith("#!"):
                    return line.lstrip("# ").strip()
    except Exception:
        pass
    return "No description available"


def discover_games():
    """Find all .py game scripts in the scripts directory."""
    games = []
    for fname in os.listdir(SCRIPTS_DIR):
        if fname in EXCLUDED or fname.startswith("test_") or fname.startswith("__"):
            continue
        filepath = os.path.join(SCRIPTS_DIR, fname)
        # Top-level .py files
        if fname.endswith(".py") and os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            description = extract_description(filepath)
            name = fname.replace(".py", "").replace("_", " ").replace("-", " ").title()
            games.append({
                "name": name,
                "file": fname,
                "path": filepath,
                "description": description,
                "size": size,
            })
        # Subdirectories: look for <dirname>/<dirname>.py
        elif os.path.isdir(filepath):
            main_script = os.path.join(filepath, fname + ".py")
            if os.path.isfile(main_script):
                size = os.path.getsize(main_script)
                description = extract_description(main_script)
                name = fname.replace("_", " ").replace("-", " ").title()
                games.append({
                    "name": name,
                    "file": os.path.join(fname, fname + ".py"),
                    "path": main_script,
                    "description": description,
                    "size": size,
                })
    games.sort(key=lambda g: g["name"].lower())
    return games


def format_size(nbytes):
    """Format byte count as a human-readable string."""
    if nbytes < 1024:
        return f"{nbytes} B"
    return f"{nbytes / 1024:.1f} KB"


def init_colors():
    """Initialize the retro arcade color pairs."""
    curses.start_color()
    curses.use_default_colors()
    # Pair 1: Neon green on black (header/border)
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    # Pair 2: Cyan on black (description text)
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
    # Pair 3: Yellow on black (highlighted item)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    # Pair 4: Black on green (selected item bar)
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_GREEN)
    # Pair 5: White on black (normal text)
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
    # Pair 6: Magenta on black (file size)
    curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    # Pair 7: Red on black (footer/quit)
    curses.init_pair(7, curses.COLOR_RED, curses.COLOR_BLACK)


def draw_header(win, max_y, max_x, frame):
    """Draw the animated ASCII art header."""
    # Color cycle for SHELLY letters: green -> cyan -> yellow -> green
    letter_colors = [
        curses.color_pair(1),  # green
        curses.color_pair(2),  # cyan
        curses.color_pair(3),  # yellow
    ]
    letter_color = letter_colors[(frame // 12) % len(letter_colors)] | curses.A_BOLD

    # ARCADE subtitle: alternate bold/dim for pulse effect
    arcade_color = curses.color_pair(3) | curses.A_BOLD  # yellow bold
    if (frame // 6) % 2 == 1:
        arcade_color = curses.color_pair(2) | curses.A_BOLD  # cyan bold

    # Draw top border
    row = 1
    border = "═" * 50
    top = f"╔{border}╗"
    x = max(0, (max_x - len(top)) // 2)
    try:
        win.addnstr(row, x, top, max_x - x, curses.color_pair(1) | curses.A_BOLD)
    except curses.error:
        pass
    row += 1

    # Draw SHELLY block letters
    for line in ASCII_HEADER_LETTERS:
        if row >= max_y:
            break
        padded = f"║{line:^50s}║"
        x = max(0, (max_x - len(padded)) // 2)
        try:
            # Draw the side bars in green, letters in cycling color
            win.addnstr(row, x, "║", 1, curses.color_pair(1) | curses.A_BOLD)
            win.addnstr(row, x + 1, f"{line:^50s}", 50, letter_color)
            win.addnstr(row, x + 51, "║", 1, curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        row += 1

    # Empty separator line
    if row < max_y:
        empty = f"║{' ' * 50}║"
        x = max(0, (max_x - len(empty)) // 2)
        try:
            win.addnstr(row, x, empty, max_x - x, curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        row += 1

    # ARCADE subtitle line
    if row < max_y:
        arcade_text = f"{ASCII_HEADER_ARCADE:^50s}"
        x = max(0, (max_x - 52) // 2)
        try:
            win.addnstr(row, x, "║", 1, curses.color_pair(1) | curses.A_BOLD)
            win.addnstr(row, x + 1, arcade_text, 50, arcade_color)
            win.addnstr(row, x + 51, "║", 1, curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        row += 1

    # Bottom border
    if row < max_y:
        bottom = f"╚{border}╝"
        x = max(0, (max_x - len(bottom)) // 2)
        try:
            win.addnstr(row, x, bottom, max_x - x, curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass


def draw_game_list(win, games, selected, scroll_offset, list_y, max_y, max_x):
    """Draw the scrollable list of games."""
    if not games:
        msg = "No games found in scripts/ directory"
        try:
            win.addnstr(list_y + 2, max(0, (max_x - len(msg)) // 2), msg,
                        max_x, curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass
        return

    # How many items can we display
    available_rows = max_y - list_y - 3  # leave room for footer
    visible_count = max(1, available_rows)  # 1 row per game entry

    # Draw column header
    hdr_y = list_y
    if hdr_y < max_y:
        hdr = "  {:3s}  {:<24s} {:<40s} {:>8s}".format("#", "GAME", "DESCRIPTION", "SIZE")
        x = max(0, (max_x - len(hdr)) // 2)
        try:
            win.addnstr(hdr_y, x, hdr, max_x - x,
                        curses.color_pair(3) | curses.A_BOLD | curses.A_UNDERLINE)
        except curses.error:
            pass

    # Draw separator
    sep_y = list_y + 1
    if sep_y < max_y:
        sep = "─" * min(78, max_x - 4)
        x = max(0, (max_x - len(sep)) // 2)
        try:
            win.addnstr(sep_y, x, sep, max_x - x, curses.color_pair(1))
        except curses.error:
            pass

    # Draw each visible game
    for i in range(visible_count):
        idx = scroll_offset + i
        if idx >= len(games):
            break

        game = games[idx]
        row_y = list_y + 2 + i
        if row_y >= max_y - 2:
            break

        is_selected = (idx == selected)

        # Build the line
        num = f"{idx + 1:3d}"
        name = game["name"][:24]
        desc = game["description"][:40]
        size = format_size(game["size"])

        line = f"  {num}  {name:<24s} {desc:<40s} {size:>8s}"

        x = max(0, (max_x - len(line)) // 2)

        if is_selected:
            # Draw selection indicator and highlighted line
            attr = curses.color_pair(4) | curses.A_BOLD
            # Draw arrow
            try:
                win.addnstr(row_y, x - 2, "▸", max_x,
                            curses.color_pair(3) | curses.A_BOLD)
            except curses.error:
                pass
        else:
            attr = curses.color_pair(5)

        try:
            win.addnstr(row_y, x, line, max_x - x, attr)
        except curses.error:
            pass

    return visible_count


def draw_footer(win, max_y, max_x, game_count):
    """Draw the footer bar with controls."""
    footer_y = max_y - 1
    if footer_y < 1:
        return
    controls = f" ↑↓ Navigate  │  ENTER Launch  │  Q Quit  │  {game_count} games available "
    x = max(0, (max_x - len(controls)) // 2)
    try:
        win.addnstr(footer_y, 0, " " * max_x, max_x,
                    curses.color_pair(4))
        win.addnstr(footer_y, x, controls, max_x - x,
                    curses.color_pair(4) | curses.A_BOLD)
    except curses.error:
        pass


def draw_scroll_indicator(win, games, scroll_offset, visible_count, list_y, max_y, max_x):
    """Draw scroll arrows if there are more items above/below."""
    if not games:
        return
    indicator_x = max(0, (max_x + 80) // 2 + 2)
    if indicator_x >= max_x:
        indicator_x = max_x - 2
    if scroll_offset > 0:
        try:
            win.addnstr(list_y + 2, indicator_x, "▲", 2,
                        curses.color_pair(3) | curses.A_BOLD)
        except curses.error:
            pass
    if scroll_offset + visible_count < len(games):
        bottom_y = min(list_y + 2 + visible_count - 1, max_y - 3)
        try:
            win.addnstr(bottom_y, indicator_x, "▼", 2,
                        curses.color_pair(3) | curses.A_BOLD)
        except curses.error:
            pass


def launch_game(game_path):
    """Launch a game as a subprocess, restoring terminal afterward."""
    curses.endwin()
    try:
        subprocess.run([sys.executable, game_path], cwd=SCRIPTS_DIR)
    except Exception as e:
        print(f"\nError launching game: {e}")
        print("Press Enter to return to the arcade...")
        input()


def main(stdscr):
    """Main arcade loop."""
    # Setup
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(True)  # Non-blocking input for animation
    stdscr.timeout(100)  # 100ms refresh for animation
    init_colors()
    stdscr.bkgd(" ", curses.color_pair(5))

    games = discover_games()
    selected = 0
    scroll_offset = 0
    frame = 0

    while True:
        max_y, max_x = stdscr.getmaxyx()

        # Minimum terminal size check
        if max_y < 15 or max_x < 50:
            stdscr.clear()
            msg = "Terminal too small! (need 50x15)"
            try:
                stdscr.addnstr(max_y // 2, max(0, (max_x - len(msg)) // 2),
                               msg, max_x, curses.color_pair(7) | curses.A_BOLD)
            except curses.error:
                pass
            stdscr.refresh()
            key = stdscr.getch()
            if key == ord("q") or key == ord("Q"):
                break
            frame += 1
            continue

        stdscr.erase()

        # Draw header (ASCII art)
        draw_header(stdscr, max_y, max_x, frame)

        # Game list starts below the header
        list_y = len(ASCII_HEADER_LETTERS) + 5  # letters + borders + arcade + spacing

        # Calculate visible count for scroll
        available_rows = max_y - list_y - 3
        visible_count = max(1, available_rows)

        # Keep selection in view
        if selected < scroll_offset:
            scroll_offset = selected
        elif selected >= scroll_offset + visible_count:
            scroll_offset = selected - visible_count + 1

        # Draw components
        vc = draw_game_list(stdscr, games, selected, scroll_offset,
                            list_y, max_y, max_x)
        if vc:
            draw_scroll_indicator(stdscr, games, scroll_offset, vc,
                                  list_y, max_y, max_x)
        draw_footer(stdscr, max_y, max_x, len(games))

        stdscr.refresh()
        frame += 1

        # Handle input
        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            stdscr.clear()
            continue
        elif key == ord("q") or key == ord("Q"):
            break
        elif key == curses.KEY_UP or key == ord("k"):
            if games:
                selected = (selected - 1) % len(games)
        elif key == curses.KEY_DOWN or key == ord("j"):
            if games:
                selected = (selected + 1) % len(games)
        elif key == curses.KEY_HOME:
            selected = 0
        elif key == curses.KEY_END:
            if games:
                selected = len(games) - 1
        elif key == curses.KEY_PPAGE:  # Page Up
            if games:
                selected = max(0, selected - visible_count)
        elif key == curses.KEY_NPAGE:  # Page Down
            if games:
                selected = min(len(games) - 1, selected + visible_count)
        elif key in (curses.KEY_ENTER, 10, 13):
            if games:
                launch_game(games[selected]["path"])
                # Re-init curses after returning from game
                stdscr = curses.initscr()
                curses.noecho()
                curses.cbreak()
                curses.curs_set(0)
                stdscr.keypad(True)
                stdscr.nodelay(True)
                stdscr.timeout(100)
                init_colors()
                stdscr.bkgd(" ", curses.color_pair(5))
                stdscr.clear()
                # Re-discover in case games were added/removed
                games = discover_games()
                if selected >= len(games):
                    selected = max(0, len(games) - 1)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        # Ensure terminal is restored
        print("\033[?25h", end="")  # Show cursor
        print("\nThanks for playing! 🕹️")
