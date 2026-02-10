#!/usr/bin/env python3
"""
Terminal Wordle — Curses UI with color feedback and on-screen keyboard.
Features:
- Classic Wordle rules: 6 guesses to find a 5-letter word
- Colored tile feedback: green (correct), yellow (wrong position), gray (not in word)
- On-screen keyboard showing letter states
- Box-drawing borders and Unicode decorations
- Keys: a-z=type, backspace=delete, enter=submit, n=new game, q=quit
"""

import curses
import random
import os

# ---------------------------------------------------------------------------
# Word list — valid 5-letter words (all lowercase)
# ---------------------------------------------------------------------------
WORDS = [
    "about", "above", "abuse", "actor", "acute", "admit", "adopt", "adult",
    "after", "again", "agent", "agree", "ahead", "alarm", "album", "alert",
    "alike", "alive", "allow", "alone", "along", "alter", "among", "angel",
    "anger", "angle", "angry", "anime", "ankle", "apart", "apple", "apply",
    "arena", "argue", "arise", "armor", "array", "aside", "asset", "audio",
    "avoid", "award", "aware", "badly", "baker", "bases", "basic", "basis",
    "beach", "began", "begin", "being", "below", "bench", "berry", "birth",
    "black", "blade", "blame", "bland", "blank", "blast", "blaze", "bleed",
    "blend", "bless", "blind", "block", "blood", "bloom", "blown", "board",
    "bonus", "boost", "bound", "brain", "brand", "brave", "bread", "break",
    "breed", "brick", "bride", "brief", "bring", "broad", "broke", "brown",
    "brush", "build", "bunch", "burst", "buyer", "cabin", "candy", "carry",
    "catch", "cause", "chain", "chair", "chaos", "charm", "chart", "chase",
    "cheap", "check", "cheek", "chess", "chest", "chief", "child", "china",
    "chunk", "claim", "clash", "class", "clean", "clear", "click", "cliff",
    "climb", "cling", "clock", "clone", "close", "cloth", "cloud", "coach",
    "coast", "color", "comet", "comic", "coral", "couch", "could", "count",
    "court", "cover", "crack", "craft", "crane", "crash", "crazy", "cream",
    "crime", "cross", "crowd", "crown", "cruel", "crush", "curve", "cycle",
    "daily", "dance", "dealt", "debug", "decay", "delay", "delta", "dense",
    "depth", "derby", "devil", "dirty", "donor", "doubt", "draft", "drain",
    "drama", "drank", "drawn", "dream", "dress", "dried", "drift", "drink",
    "drive", "drove", "drunk", "dying", "eager", "early", "earth", "eight",
    "elect", "elite", "email", "empty", "enemy", "enjoy", "enter", "equal",
    "error", "essay", "event", "every", "exact", "exile", "exist", "extra",
    "faint", "fairy", "faith", "false", "fancy", "fatal", "fault", "feast",
    "fiber", "field", "fifth", "fifty", "fight", "final", "first", "fixed",
    "flame", "flash", "flask", "flesh", "float", "flood", "floor", "flour",
    "fluid", "flush", "flute", "focus", "force", "forge", "forth", "forum",
    "found", "frame", "frank", "fraud", "fresh", "front", "frost", "fruit",
    "fully", "funny", "ghost", "giant", "given", "gland", "glass", "globe",
    "gloom", "glory", "glove", "going", "grace", "grade", "grain", "grand",
    "grant", "grape", "graph", "grasp", "grass", "grave", "great", "green",
    "greet", "grief", "grill", "grind", "groan", "gross", "group", "grove",
    "grown", "guard", "guess", "guest", "guide", "guild", "guilt", "habit",
    "happy", "harsh", "haste", "haven", "heart", "heavy", "hence", "herbs",
    "honey", "honor", "horse", "hotel", "house", "human", "humor", "hurry",
    "ideal", "image", "imply", "index", "inner", "input", "irony", "issue",
    "ivory", "joint", "joker", "judge", "juice", "knack", "kneel", "knife",
    "knock", "known", "label", "large", "laser", "later", "laugh", "layer",
    "learn", "lease", "least", "leave", "legal", "lemon", "level", "light",
    "limit", "linen", "liver", "local", "lodge", "logic", "login", "loose",
    "lover", "lower", "loyal", "lunar", "lunch", "lying", "magic", "major",
    "maker", "manor", "maple", "march", "match", "maybe", "mayor", "meant",
    "media", "mercy", "merit", "metal", "meter", "midst", "might", "minor",
    "minus", "mixed", "model", "money", "month", "moral", "motor", "mount",
    "mouse", "mouth", "moved", "movie", "muddy", "music", "naval", "nerve",
    "never", "newly", "night", "noble", "noise", "north", "noted", "novel",
    "nurse", "nylon", "occur", "ocean", "offer", "often", "olive", "onset",
    "opera", "orbit", "order", "organ", "other", "ought", "outer", "owner",
    "oxide", "ozone", "paint", "panel", "panic", "paper", "patch", "pause",
    "peace", "pearl", "penny", "phase", "phone", "photo", "piano", "piece",
    "pilot", "pinch", "pitch", "pixel", "place", "plain", "plane", "plant",
    "plate", "plaza", "plead", "pluck", "plumb", "plume", "point", "porch",
    "poser", "posit", "pound", "power", "press", "price", "pride", "prime",
    "print", "prior", "prize", "prone", "proof", "prose", "proud", "prove",
    "psalm", "pulse", "punch", "pupil", "purse", "queen", "query", "quest",
    "queue", "quick", "quiet", "quote", "radar", "radio", "raise", "rally",
    "range", "rapid", "ratio", "reach", "react", "ready", "realm", "rebel",
    "reign", "relax", "reply", "rider", "ridge", "rifle", "right", "rigid",
    "rival", "river", "robin", "robot", "rocky", "roger", "roman", "rouge",
    "rough", "round", "route", "royal", "rural", "sadly", "saint", "salad",
    "scale", "scene", "scope", "score", "sense", "serve", "setup", "seven",
    "shade", "shaft", "shake", "shall", "shame", "shape", "share", "sharp",
    "shear", "sheep", "sheer", "sheet", "shelf", "shell", "shift", "shine",
    "shirt", "shock", "shore", "short", "shout", "sight", "sigma", "since",
    "sixth", "sixty", "sized", "skill", "skull", "slave", "sleep", "slide",
    "slope", "small", "smart", "smell", "smile", "smoke", "snake", "solar",
    "solid", "solve", "sorry", "sound", "south", "space", "spare", "spark",
    "speak", "speed", "spend", "spent", "spice", "spine", "spite", "split",
    "spoke", "spoon", "sport", "spray", "squad", "stack", "staff", "stage",
    "stain", "stake", "stale", "stall", "stamp", "stand", "stare", "stark",
    "start", "state", "stays", "steam", "steel", "steep", "steer", "stern",
    "stick", "stiff", "still", "stock", "stone", "stood", "store", "storm",
    "story", "stout", "stove", "strap", "straw", "strip", "stuck", "study",
    "stuff", "style", "sugar", "suite", "sunny", "super", "surge", "swamp",
    "swear", "sweet", "swept", "swift", "swing", "sword", "swore", "sworn",
    "syrup", "table", "taste", "teach", "tease", "tempo", "tenor", "tense",
    "terms", "theft", "theme", "there", "thick", "thing", "think", "third",
    "those", "three", "threw", "throw", "thumb", "tiger", "tight", "timer",
    "tired", "title", "today", "token", "topic", "total", "touch", "tough",
    "towel", "tower", "toxic", "trace", "track", "trade", "trail", "train",
    "trait", "trash", "treat", "trend", "trial", "tribe", "trick", "tried",
    "troop", "truck", "truly", "trump", "trunk", "trust", "truth", "tulip",
    "tumor", "tweed", "twice", "twist", "tying", "ultra", "uncle", "under",
    "union", "unity", "until", "upper", "upset", "urban", "usage", "usual",
    "utter", "valid", "value", "vapor", "vault", "verse", "video", "vigor",
    "vinyl", "viral", "virus", "visit", "vista", "vital", "vivid", "vocal",
    "vodka", "voice", "voter", "wagon", "waste", "watch", "water", "weary",
    "weave", "wedge", "weird", "wheat", "wheel", "where", "which", "while",
    "white", "whole", "whose", "width", "witch", "woman", "women", "world",
    "worry", "worse", "worst", "worth", "would", "wound", "wrath", "write",
    "wrong", "wrote", "yacht", "yield", "young", "youth", "zebra",
]

# Maximum guesses allowed
MAX_GUESSES = 6

# Word length
WORD_LENGTH = 5

# ---------------------------------------------------------------------------
# Color pair indices
# ---------------------------------------------------------------------------
COLOR_TITLE = 1
COLOR_CORRECT = 2
COLOR_PRESENT = 3
COLOR_ABSENT = 4
COLOR_BORDER = 5
COLOR_STATUS = 6
COLOR_WIN = 7
COLOR_LOSE = 8
COLOR_INPUT = 9
COLOR_EMPTY_TILE = 10


def init_colors():
    """Initialize curses color pairs."""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(COLOR_TITLE, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_CORRECT, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(COLOR_PRESENT, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(COLOR_ABSENT, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(COLOR_BORDER, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_STATUS, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_WIN, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_LOSE, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_INPUT, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_EMPTY_TILE, curses.COLOR_WHITE, -1)


# ---------------------------------------------------------------------------
# Pure game logic (no curses dependency)
# ---------------------------------------------------------------------------
def pick_word():
    """Choose a random word from the word list."""
    return random.choice(WORDS)


def evaluate_guess(guess, target):
    """Evaluate a guess against the target word.

    Returns a list of 5 states: 'correct', 'present', or 'absent'.
    Handles duplicate letters correctly per standard Wordle rules.
    """
    result = ['absent'] * WORD_LENGTH
    target_chars = list(target)

    # First pass: mark correct letters (green)
    for i in range(WORD_LENGTH):
        if guess[i] == target_chars[i]:
            result[i] = 'correct'
            target_chars[i] = None

    # Second pass: mark present letters (yellow)
    for i in range(WORD_LENGTH):
        if result[i] == 'correct':
            continue
        if guess[i] in target_chars:
            result[i] = 'present'
            target_chars[target_chars.index(guess[i])] = None

    return result


def is_valid_guess(guess, word_list):
    """Check if a guess is valid (5 letters and in the word list)."""
    return len(guess) == WORD_LENGTH and guess in word_list


def check_win(result):
    """Return True if all letters are correct."""
    return all(r == 'correct' for r in result)


def update_keyboard(keyboard, guess, result):
    """Update the keyboard state based on guess results.

    Priority: correct > present > absent (never downgrade).
    """
    priority = {'absent': 0, 'present': 1, 'correct': 2}
    for i, letter in enumerate(guess):
        current = keyboard.get(letter)
        new_state = result[i]
        if current is None or priority[new_state] > priority[current]:
            keyboard[letter] = new_state


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def safe_addstr(win, y, x, text, attr=0):
    """addstr that silently ignores curses errors at screen edges."""
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


def get_state_attr(state):
    """Return the curses attribute for a letter state."""
    if state == 'correct':
        return curses.color_pair(COLOR_CORRECT) | curses.A_BOLD
    elif state == 'present':
        return curses.color_pair(COLOR_PRESENT) | curses.A_BOLD
    elif state == 'absent':
        return curses.color_pair(COLOR_ABSENT)
    return curses.color_pair(COLOR_EMPTY_TILE)


def draw_title(win, width):
    """Draw the title bar."""
    title = " ★ WORDLE ★ "
    bar = "═" * width
    safe_addstr(win, 0, 0, bar, curses.color_pair(COLOR_BORDER))
    tx = max(0, (width - len(title)) // 2)
    safe_addstr(win, 0, tx, title,
                curses.color_pair(COLOR_TITLE) | curses.A_BOLD)


def draw_grid(win, y, x, guesses, results, current_input, current_row):
    """Draw the 6x5 guess grid with colored feedback."""
    tile_w = 4
    for row in range(MAX_GUESSES):
        for col in range(WORD_LENGTH):
            cx = x + col * (tile_w + 1)
            if row < len(guesses):
                # Completed guess row
                letter = guesses[row][col].upper()
                state = results[row][col]
                attr = get_state_attr(state)
                cell = f" {letter} "
                safe_addstr(win, y + row * 2, cx, cell, attr)
            elif row == current_row:
                # Current input row
                if col < len(current_input):
                    letter = current_input[col].upper()
                    cell = f" {letter} "
                    safe_addstr(win, y + row * 2, cx, cell,
                                curses.color_pair(COLOR_INPUT) | curses.A_BOLD)
                else:
                    cell = " _ "
                    safe_addstr(win, y + row * 2, cx, cell,
                                curses.color_pair(COLOR_EMPTY_TILE))
            else:
                # Empty future row
                cell = " · "
                safe_addstr(win, y + row * 2, cx, cell,
                            curses.color_pair(COLOR_EMPTY_TILE))


def draw_keyboard(win, y, x, keyboard):
    """Draw the on-screen keyboard showing letter states."""
    rows = [
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm",
    ]
    for ri, row in enumerate(rows):
        offset = ri * 2  # indent each row a bit
        for ci, letter in enumerate(row):
            cx = x + offset + ci * 4
            state = keyboard.get(letter)
            if state is not None:
                attr = get_state_attr(state)
            else:
                attr = curses.color_pair(COLOR_BORDER) | curses.A_BOLD
            safe_addstr(win, y + ri * 2, cx, f" {letter.upper()} ", attr)


def draw_status_bar(win, y, width, wins, games, message, msg_attr=0):
    """Draw the bottom status bar."""
    bar = "═" * width
    safe_addstr(win, y, 0, bar, curses.color_pair(COLOR_BORDER))
    info = " a-z=Type  Enter=Submit  Bksp=Delete  n=New  q=Quit "
    safe_addstr(win, y + 1, 0, info,
                curses.color_pair(COLOR_STATUS) | curses.A_BOLD)
    score_str = f" Score: {wins}/{games} "
    safe_addstr(win, y + 1, width - len(score_str) - 1, score_str,
                curses.color_pair(COLOR_STATUS) | curses.A_BOLD)
    if message:
        mx = max(0, (width - len(message)) // 2)
        safe_addstr(win, y - 1, mx, message, msg_attr)


# ---------------------------------------------------------------------------
# Main game
# ---------------------------------------------------------------------------
def main(stdscr):
    """Main curses game loop."""
    stdscr.clear()
    init_colors()
    curses.curs_set(0)

    height, width = stdscr.getmaxyx()
    if height < 24 or width < 50:
        safe_addstr(stdscr, 0, 0, "Terminal too small! Need 50x24 minimum.",
                    curses.color_pair(COLOR_LOSE))
        safe_addstr(stdscr, 1, 0, f"Current: {width}x{height}",
                    curses.color_pair(COLOR_LOSE))
        safe_addstr(stdscr, 2, 0, "Press 'q' to quit.",
                    curses.color_pair(COLOR_STATUS))
        stdscr.refresh()
        while stdscr.getch() != ord('q'):
            pass
        return

    word_set = set(WORDS)

    # Game state
    wins = 0
    games = 0
    target = pick_word()
    guesses = []
    results = []
    current_input = ""
    keyboard = {}
    message = "Guess a 5-letter word!"
    msg_attr = curses.color_pair(COLOR_STATUS) | curses.A_BOLD
    game_over = False

    def redraw():
        """Redraw the entire screen."""
        stdscr.erase()
        draw_title(stdscr, width)

        # Grid
        grid_x = max(0, (width - WORD_LENGTH * 5) // 2)
        grid_y = 3
        current_row = len(guesses) if not game_over else MAX_GUESSES
        draw_grid(stdscr, grid_y, grid_x, guesses, results,
                  current_input, current_row)

        # Keyboard
        kb_y = grid_y + MAX_GUESSES * 2 + 1
        kb_x = max(0, (width - 42) // 2)
        draw_keyboard(stdscr, kb_y, kb_x, keyboard)

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
                target = pick_word()
                guesses = []
                results = []
                current_input = ""
                keyboard = {}
                message = "Guess a 5-letter word!"
                msg_attr = curses.color_pair(COLOR_STATUS) | curses.A_BOLD
                game_over = False
            continue

        # Backspace
        if ch in (curses.KEY_BACKSPACE, 127, 8):
            if current_input:
                current_input = current_input[:-1]
                message = ""
            continue

        # Enter — submit guess
        if ch in (curses.KEY_ENTER, 10, 13):
            if len(current_input) != WORD_LENGTH:
                message = "Not enough letters!"
                msg_attr = curses.color_pair(COLOR_LOSE) | curses.A_BOLD
                continue

            if not is_valid_guess(current_input, word_set):
                message = "Not in word list!"
                msg_attr = curses.color_pair(COLOR_LOSE) | curses.A_BOLD
                continue

            result = evaluate_guess(current_input, target)
            guesses.append(current_input)
            results.append(result)
            update_keyboard(keyboard, current_input, result)

            if check_win(result):
                wins += 1
                games += 1
                message = f"Brilliant! You got it in {len(guesses)}! Press 'n' for new game."
                msg_attr = curses.color_pair(COLOR_WIN) | curses.A_BOLD
                game_over = True
            elif len(guesses) >= MAX_GUESSES:
                games += 1
                message = f"The word was \"{target.upper()}\". Press 'n' for new game."
                msg_attr = curses.color_pair(COLOR_LOSE) | curses.A_BOLD
                game_over = True
            else:
                remaining = MAX_GUESSES - len(guesses)
                message = f"{remaining} guess{'es' if remaining != 1 else ''} remaining."
                msg_attr = curses.color_pair(COLOR_STATUS) | curses.A_BOLD

            current_input = ""
            continue

        # Letter keys a-z
        if 97 <= ch <= 122:
            if len(current_input) < WORD_LENGTH:
                current_input += chr(ch)
                message = ""


if __name__ == "__main__":
    curses.wrapper(main)
