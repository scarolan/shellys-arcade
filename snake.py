#!/usr/bin/env python3
"""
Snake Game — Terminal snake with curses.
Features:
- Arrow keys / WASD movement with wall/self collision
- Food spawning, eating, and snake growth
- Score tracking with speed increase every 5 food
- High score tracking per session
- Start screen with instructions
- Pause with 'p' key
"""

import curses
import time
import random

# Directions: (dy, dx)
UP = (-1, 0)
DOWN = (1, 0)
LEFT = (0, -1)
RIGHT = (0, 1)

OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}


def main(stdscr):
    stdscr.clear()

    # Initialize colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)   # Snake
    curses.init_pair(2, curses.COLOR_RED, -1)     # Food
    curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Border/Text
    curses.init_pair(4, curses.COLOR_WHITE, -1)   # UI text
    curses.curs_set(0)

    # Get screen dimensions
    height, width = stdscr.getmaxyx()

    # Check if terminal is large enough
    if height < 24 or width < 44:
        stdscr.addstr(0, 0, "Terminal too small!", curses.color_pair(3))
        stdscr.addstr(1, 0, f"Need at least 24x44, got {height}x{width}", curses.color_pair(3))
        stdscr.addstr(2, 0, "Press 'q' to quit", curses.color_pair(3))
        while True:
            ch = stdscr.getch()
            if ch == ord('q'):
                return
        return

    # Calculate centered position for 40x20 game window
    win_h, win_w = 20, 40
    start_y = (height - win_h) // 2 - 1
    start_x = (width - win_w) // 2

    # Create game window
    gamewin = curses.newwin(win_h, win_w, start_y, start_x)
    gamewin.keypad(True)

    # --- Start screen ---
    gamewin.erase()
    gamewin.box()
    title = " S N A K E "
    gamewin.addstr(0, (win_w - len(title)) // 2, title, curses.color_pair(3) | curses.A_BOLD)
    gamewin.addstr(4, (win_w - 18) // 2, "Arrow keys / WASD", curses.color_pair(4))
    gamewin.addstr(5, (win_w - 14) // 2, "to move snake", curses.color_pair(4))
    gamewin.addstr(7, (win_w - 16) // 2, "P  -  Pause game", curses.color_pair(4))
    gamewin.addstr(8, (win_w - 16) // 2, "Q  -  Quit game", curses.color_pair(4))
    gamewin.addstr(10, (win_w - 22) // 2, "Eat food to grow!", curses.color_pair(1) | curses.A_BOLD)
    gamewin.addstr(11, (win_w - 28) // 2, "Speed increases every 5 food", curses.color_pair(2))
    prompt = "Press any key to start..."
    gamewin.addstr(win_h - 3, (win_w - len(prompt)) // 2, prompt, curses.color_pair(3) | curses.A_BOLD)
    gamewin.refresh()
    gamewin.nodelay(False)
    gamewin.getch()

    high_score = 0

    # Key mappings
    key_map = {
        curses.KEY_UP: UP, ord('w'): UP, ord('W'): UP,
        curses.KEY_DOWN: DOWN, ord('s'): DOWN, ord('S'): DOWN,
        curses.KEY_LEFT: LEFT, ord('a'): LEFT, ord('A'): LEFT,
        curses.KEY_RIGHT: RIGHT, ord('d'): RIGHT, ord('D'): RIGHT,
    }

    while True:  # Restart loop
        # --- Game setup ---
        gamewin.nodelay(True)
        gamewin.timeout(100)

        # Snake starts as 3 segments in the center, moving right
        center_y = win_h // 2
        center_x = win_w // 2
        snake = [
            (center_y, center_x - 2),
            (center_y, center_x - 1),
            (center_y, center_x),
        ]
        direction = RIGHT

        # Score and speed
        score = 0
        base_timeout = 100
        timeout = base_timeout

        def spawn_food():
            while True:
                fy = random.randint(1, win_h - 2)
                fx = random.randint(1, win_w - 2)
                if (fy, fx) not in snake:
                    return (fy, fx)

        food = spawn_food()

        while True:
            # Process input
            new_dir = None
            while True:
                ch = gamewin.getch()
                if ch == -1:
                    break
                if ch == ord('q') or ch == ord('Q'):
                    return
                # Pause
                if ch == ord('p') or ch == ord('P'):
                    pause_msg = " PAUSED "
                    gamewin.addstr(win_h // 2, (win_w - len(pause_msg)) // 2, pause_msg, curses.color_pair(3) | curses.A_BOLD)
                    resume_msg = "Press P to resume"
                    gamewin.addstr(win_h // 2 + 1, (win_w - len(resume_msg)) // 2, resume_msg, curses.color_pair(4))
                    gamewin.refresh()
                    gamewin.nodelay(False)
                    while True:
                        pch = gamewin.getch()
                        if pch == ord('p') or pch == ord('P'):
                            break
                        if pch == ord('q') or pch == ord('Q'):
                            return
                    gamewin.nodelay(True)
                    gamewin.timeout(timeout)
                    continue
                if ch in key_map:
                    candidate = key_map[ch]
                    if candidate != OPPOSITE[direction]:
                        new_dir = candidate

            if new_dir:
                direction = new_dir

            # Move snake
            head_y, head_x = snake[-1]
            new_head = (head_y + direction[0], head_x + direction[1])

            # Check for wall collision (game over)
            if new_head[0] <= 0 or new_head[0] >= win_h - 1 or new_head[1] <= 0 or new_head[1] >= win_w - 1:
                break

            # Check for self collision (game over)
            if new_head in snake:
                break

            # Check for food
            if new_head == food:
                # Grow snake - don't pop tail
                score += 1
                if score > high_score:
                    high_score = score
                # Speed increase every 5 food (min timeout 40ms)
                timeout = max(40, base_timeout - (score // 5) * 10)
                gamewin.timeout(timeout)
                food = spawn_food()
            else:
                # Move normally - pop tail
                snake.pop(0)

            snake.append(new_head)

            # Redraw
            gamewin.erase()
            gamewin.box()

            title = " SNAKE "
            gamewin.addstr(0, (win_w - len(title)) // 2, title, curses.color_pair(3))

            # Draw score on top border
            score_str = f" Score: {score} "
            gamewin.addstr(0, 1, score_str, curses.color_pair(4) | curses.A_BOLD)

            # Draw food
            fy, fx = food
            try:
                gamewin.addstr(fy, fx, '●', curses.color_pair(2) | curses.A_BOLD)
            except curses.error:
                gamewin.addch(fy, fx, ord('@'), curses.color_pair(2) | curses.A_BOLD)

            # Draw snake
            for i, (sy, sx) in enumerate(snake):
                if 1 <= sy < win_h - 1 and 1 <= sx < win_w - 1:
                    if i == len(snake) - 1:
                        gamewin.addch(sy, sx, ord('O'), curses.color_pair(1) | curses.A_BOLD)
                    else:
                        gamewin.addch(sy, sx, ord('*'), curses.color_pair(1))

            gamewin.refresh()

        # Game over screen
        if score > high_score:
            high_score = score
        gamewin.nodelay(False)
        gamewin.erase()
        gamewin.box()
        go_msg = " GAME OVER "
        gamewin.addstr(0, (win_w - len(go_msg)) // 2, go_msg, curses.color_pair(3) | curses.A_BOLD)
        score_msg = f"Score: {score}"
        gamewin.addstr(win_h // 2 - 1, (win_w - len(score_msg)) // 2, score_msg, curses.color_pair(4) | curses.A_BOLD)
        hs_msg = f"High Score: {high_score}"
        gamewin.addstr(win_h // 2, (win_w - len(hs_msg)) // 2, hs_msg, curses.color_pair(3) | curses.A_BOLD)
        size_msg = f"Snake Length: {len(snake)}"
        gamewin.addstr(win_h // 2 + 1, (win_w - len(size_msg)) // 2, size_msg, curses.color_pair(4))
        restart_msg = "R - Restart  |  Q - Quit"
        gamewin.addstr(win_h // 2 + 3, (win_w - len(restart_msg)) // 2, restart_msg, curses.color_pair(3) | curses.A_BOLD)
        gamewin.refresh()
        while True:
            ch = gamewin.getch()
            if ch == ord('r') or ch == ord('R'):
                break  # Break to restart loop
            if ch == ord('q') or ch == ord('Q'):
                return


if __name__ == "__main__":
    curses.wrapper(main)