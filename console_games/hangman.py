#!/usr/bin/env python3
"""
Terminal Hangman — Curses UI with color, box-drawing borders, and ASCII art.
Features:
- Full curses TUI (no scrolling)
- Colorful display: green correct, red wrong, yellow hangman, cyan word blanks
- Box-drawing borders around hangman figure and word display
- Progressive hangman ASCII art (head, body, arms, legs)
- Keys: a-z=guess, n=new game, q=quit
"""

import curses
import random
import sys

# ---------------------------------------------------------------------------
# Word list
# ---------------------------------------------------------------------------
WORDS = [
    "python", "hangman", "developer", "keyboard", "terminal",
    "algorithm", "function", "variable", "compiler", "database",
    "network", "security", "container", "pipeline", "upstream",
    "encoding", "protocol", "abstract", "iterator", "recursion",
]

# ---------------------------------------------------------------------------
# Hangman stages — 7 stages (0 = empty gallows, 6 = full body = dead)
# ---------------------------------------------------------------------------
HANGMAN_STAGES = [
    # 0: empty gallows
    [
        "  ┌──────┐ ",
        "  │      │ ",
        "  │        ",
        "  │        ",
        "  │        ",
        "  │        ",
        "══╧════════",
    ],
    # 1: head
    [
        "  ┌──────┐ ",
        "  │      │ ",
        "  │      O ",
        "  │        ",
        "  │        ",
        "  │        ",
        "══╧════════",
    ],
    # 2: body
    [
        "  ┌──────┐ ",
        "  │      │ ",
        "  │      O ",
        "  │      │ ",
        "  │        ",
        "  │        ",
        "══╧════════",
    ],
    # 3: left arm
    [
        "  ┌──────┐ ",
        "  │      │ ",
        "  │      O ",
        "  │     /│ ",
        "  │        ",
        "  │        ",
        "══╧════════",
    ],
    # 4: both arms
    [
        "  ┌──────┐ ",
        "  │      │ ",
        "  │      O ",
        "  │     /│\\",
        "  │        ",
        "  │        ",
        "══╧════════",
    ],
    # 5: left leg
    [
        "  ┌──────┐ ",
        "  │      │ ",
        "  │      O ",
        "  │     /│\\",
        "  │     /  ",
        "  │        ",
        "══╧════════",
    ],
    # 6: both legs — dead
    [
        "  ┌──────┐ ",
        "  │      │ ",
        "  │      O ",
        "  │     /│\\",
        "  │     / \\",
        "  │        ",
        "══╧════════",
    ],
]

MAX_WRONG = len(HANGMAN_STAGES) - 1

# ---------------------------------------------------------------------------
# Color pair indices
# ---------------------------------------------------------------------------
COLOR_TITLE = 1
COLOR_CORRECT = 2
COLOR_WRONG = 3
COLOR_HANGMAN = 4
COLOR_WORD = 5
COLOR_BORDER = 6
COLOR_STATUS = 7
COLOR_WIN = 8
COLOR_LOSE = 9


def init_colors():
    """Initialize curses color pairs."""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(COLOR_TITLE, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_CORRECT, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_WRONG, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_HANGMAN, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_WORD, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_BORDER, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_STATUS, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_WIN, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_LOSE, curses.COLOR_RED, -1)


# ---------------------------------------------------------------------------
# Pure game logic (no curses dependency)
# ---------------------------------------------------------------------------
def pick_word():
    """Choose a random word from the word list."""
    return random.choice(WORDS)


def get_revealed(word, guessed):
    """Return the word with un-guessed letters replaced by underscores."""
    return "".join(ch if ch in guessed else "_" for ch in word)


def check_win(word, guessed):
    """Return True if all letters in the word have been guessed."""
    return all(ch in guessed for ch in word)


def check_loss(wrong_guesses):
    """Return True if the player has exhausted all wrong guesses."""
    return len(wrong_guesses) >= MAX_WRONG


def process_guess(letter, word, guessed, wrong_guesses):
    """Process a letter guess. Returns (already_guessed, correct).

    Mutates guessed or wrong_guesses in-place.
    """
    if letter in guessed or letter in wrong_guesses:
        return True, False
    if letter in word:
        guessed.add(letter)
        return False, True
    else:
        wrong_guesses.add(letter)
        return False, False


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def safe_addstr(win, y, x, text, attr=0):
    """addstr that silently ignores curses errors at screen edges."""
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


def draw_box(win, y, x, height, width, attr=0):
    """Draw a box using box-drawing characters."""
    safe_addstr(win, y, x, "╔" + "═" * (width - 2) + "╗", attr)
    for row in range(1, height - 1):
        safe_addstr(win, y + row, x, "║", attr)
        safe_addstr(win, y + row, x + width - 1, "║", attr)
    safe_addstr(win, y + height - 1, x, "╚" + "═" * (width - 2) + "╝", attr)


def draw_hangman(win, y, x, wrong_count):
    """Draw the hangman figure inside a box."""
    stage = HANGMAN_STAGES[min(wrong_count, MAX_WRONG)]
    box_w = 16
    box_h = len(stage) + 2
    border_attr = curses.color_pair(COLOR_BORDER) | curses.A_BOLD
    draw_box(win, y, x, box_h, box_w, border_attr)
    for i, line in enumerate(stage):
        safe_addstr(win, y + 1 + i, x + 2, line,
                    curses.color_pair(COLOR_HANGMAN) | curses.A_BOLD)


def draw_word_display(win, y, x, word, guessed):
    """Draw the word with blanks in a box."""
    revealed = get_revealed(word, guessed)
    spaced = " ".join(revealed)
    box_w = max(len(spaced) + 4, len(word) * 2 + 4)
    box_h = 3
    border_attr = curses.color_pair(COLOR_BORDER) | curses.A_BOLD
    draw_box(win, y, x, box_h, box_w, border_attr)
    for i, ch in enumerate(spaced):
        cx = x + 2 + i
        if ch == "_":
            safe_addstr(win, y + 1, cx, ch,
                        curses.color_pair(COLOR_WORD) | curses.A_BOLD)
        elif ch == " ":
            safe_addstr(win, y + 1, cx, ch)
        else:
            safe_addstr(win, y + 1, cx, ch,
                        curses.color_pair(COLOR_CORRECT) | curses.A_BOLD)


def draw_used_letters(win, y, x, guessed, wrong_guesses):
    """Draw the used letters section."""
    safe_addstr(win, y, x, "Guessed Letters:",
                curses.color_pair(COLOR_STATUS) | curses.A_BOLD)
    all_letters = sorted(guessed | wrong_guesses)
    lx = x
    for i, ch in enumerate(all_letters):
        if ch in guessed:
            attr = curses.color_pair(COLOR_CORRECT) | curses.A_BOLD
        else:
            attr = curses.color_pair(COLOR_WRONG) | curses.A_BOLD
        safe_addstr(win, y + 1, lx + i * 2, ch.upper(), attr)


def draw_title(win, width):
    """Draw the title bar."""
    title = " ★ HANGMAN ★ "
    bar = "═" * width
    safe_addstr(win, 0, 0, bar, curses.color_pair(COLOR_BORDER))
    tx = max(0, (width - len(title)) // 2)
    safe_addstr(win, 0, tx, title,
                curses.color_pair(COLOR_TITLE) | curses.A_BOLD)


def draw_status_bar(win, y, width, wins, games, message, msg_attr=0):
    """Draw the bottom status bar."""
    bar = "═" * width
    safe_addstr(win, y, 0, bar, curses.color_pair(COLOR_BORDER))
    info = f" Score: {wins}/{games}  │  a-z=Guess  n=New Game  q=Quit "
    safe_addstr(win, y + 1, 0, info,
                curses.color_pair(COLOR_STATUS) | curses.A_BOLD)
    if message:
        safe_addstr(win, y - 1, 4, message, msg_attr)


# ---------------------------------------------------------------------------
# Main game
# ---------------------------------------------------------------------------
def main(stdscr):
    """Main curses game loop."""
    stdscr.clear()
    init_colors()
    curses.curs_set(0)

    height, width = stdscr.getmaxyx()
    if height < 20 or width < 50:
        safe_addstr(stdscr, 0, 0, "Terminal too small! Need 50x20 minimum.",
                    curses.color_pair(COLOR_LOSE))
        safe_addstr(stdscr, 1, 0, f"Current: {width}x{height}",
                    curses.color_pair(COLOR_LOSE))
        safe_addstr(stdscr, 2, 0, "Press 'q' to quit.",
                    curses.color_pair(COLOR_STATUS))
        stdscr.refresh()
        while stdscr.getch() != ord('q'):
            pass
        return

    # Game state
    wins = 0
    games = 0
    word = pick_word()
    guessed = set()
    wrong_guesses = set()
    message = "Guess a letter to begin!"
    msg_attr = curses.color_pair(COLOR_STATUS) | curses.A_BOLD
    game_over = False

    def redraw():
        """Redraw the entire screen."""
        stdscr.erase()
        draw_title(stdscr, width)

        # Hangman figure
        draw_hangman(stdscr, 2, 4, len(wrong_guesses))

        # Wrong guesses count
        remaining = MAX_WRONG - len(wrong_guesses)
        safe_addstr(stdscr, 2, 24, f"Guesses left: {remaining}",
                    curses.color_pair(COLOR_HANGMAN) | curses.A_BOLD)

        # Word display
        draw_word_display(stdscr, 12, 4, word, guessed)

        # Used letters
        draw_used_letters(stdscr, 16, 4, guessed, wrong_guesses)

        # Status bar
        draw_status_bar(stdscr, height - 3, width, wins, games,
                        message, msg_attr)

        stdscr.refresh()

    # Main loop
    while True:
        redraw()
        ch = stdscr.getch()

        if ch == ord('q') or ch == ord('Q'):
            break

        if game_over:
            if ch == ord('n') or ch == ord('N'):
                word = pick_word()
                guessed = set()
                wrong_guesses = set()
                message = "New game! Guess a letter."
                msg_attr = curses.color_pair(COLOR_STATUS) | curses.A_BOLD
                game_over = False
            continue

        # Process letter guess
        if 97 <= ch <= 122:  # a-z
            letter = chr(ch)
            already, correct = process_guess(letter, word, guessed,
                                             wrong_guesses)
            if already:
                message = f"Already guessed '{letter.upper()}'!"
                msg_attr = curses.color_pair(COLOR_WRONG) | curses.A_BOLD
            elif correct:
                message = f"'{letter.upper()}' is correct!"
                msg_attr = curses.color_pair(COLOR_CORRECT) | curses.A_BOLD
            else:
                message = f"'{letter.upper()}' is not in the word."
                msg_attr = curses.color_pair(COLOR_WRONG) | curses.A_BOLD

            # Check win/loss
            if check_win(word, guessed):
                wins += 1
                games += 1
                message = f"You win! The word was \"{word}\". Press 'n' for new game."
                msg_attr = curses.color_pair(COLOR_WIN) | curses.A_BOLD
                game_over = True
            elif check_loss(wrong_guesses):
                games += 1
                message = f"Game over! The word was \"{word}\". Press 'n' for new game."
                msg_attr = curses.color_pair(COLOR_LOSE) | curses.A_BOLD
                game_over = True


if __name__ == "__main__":
    curses.wrapper(main)
