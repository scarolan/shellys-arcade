#!/usr/bin/env python3
"""
Terminal Blackjack — Curses UI with color, card art, and a mustachioed dealer.
Features:
- Full curses TUI (no scrolling)
- Colorful felt-green table with red/white card suits
- ASCII card art with box-drawing borders
- Dealer persona: "Lucky Lou" with twisty mustache and quips
- Bankroll tracking, blackjack 3:2 payout
- Keys: h=hit, s=stand, d=deal/new hand, q=quit, +/- adjust bet
"""

import curses
import random
import sys
import time

# ---------------------------------------------------------------------------
# Card data
# ---------------------------------------------------------------------------
SUITS = ("♠", "♥", "♦", "♣")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
RED_SUITS = {"♥", "♦"}
STARTING_BANKROLL = 1000
MIN_BET = 10
MAX_BET = 500

# ---------------------------------------------------------------------------
# Dealer persona — Lucky Lou
# ---------------------------------------------------------------------------
DEALER_NAME = "Lucky Lou"

# Lines of the portrait art. Row 2 has placeholders {EL} / {ER} for eyes.
# Regions: rows 0-1 = hair, row 2 = face+eyes, row 3 = nose/mustache,
#          row 4 = mustache, row 5 = collar/mustache, row 6 = shirt/tie, row 7 = shirt
MUSTACHE_ART = [
    r"⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣶⣶⣶⣶⣦⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",          # 0: hair
    r"⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣽⡟⠈⠙⣯⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀",          # 1: hair
    r"⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠋{EL}--{ER}⠙⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀",  # 2: face (eyes)
    r"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢱⣴⠶⢶⣦⡎⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",          # 3: nose/mustache
    r"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣱⠢⠔⣎⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",          # 4: mustache
    r"⠀⠀⠀⠀⠀⠀⠀⣀⣤⡖⢏⠀⣹⣏⠀⡝⢲⣤⣀⠀⠀⠀⠀⠀⠀⠀",          # 5: collar
    r"⠀⠀⠀⠀⠀⠀⢠⠁⣿⣿⣄⠑⣱⣎⠊⣠⣿⣿⠘⡀⠀⠀⠀⠀⠀⠀",          # 6: shirt
    r"⠀⠀⠀⠀⠀⠀              ⠀⠀⠀⠀⠀⠀",          # 7: shirt bottom
]

# Eye characters for expressions
EYES_NEUTRAL = ("O", "O")
EYES_BLINK = ("-", "-")
EYES_HAPPY = ("^", "^")      # player wins
EYES_SAD = ("Q", "Q")        # player loses / bust
EYES_SURPRISED = ("o", "O")  # deal / blackjack

# Which row regions get which color (indices into MUSTACHE_ART)
LOU_HAIR_ROWS = {0, 1}
LOU_MUSTACHE_ROWS = {3, 4, 5}
LOU_SHIRT_ROWS = {6, 7}

DEALER_QUIPS_DEAL = [
    "Let's see what the cards have in store...",
    "Feeling lucky, friend?",
    "Place your bets, the wheel of fortune spins!",
    "Another round? I like your style!",
    "Cards don't lie... usually.",
]

DEALER_QUIPS_HIT = [
    "Bold move! Let's see...",
    "Living dangerously, I see!",
    "One more card, coming right up!",
    "Fortune favors the brave!",
    "Interesting choice...",
]

DEALER_QUIPS_PLAYER_BUST = [
    "Oh dear... the cards were not kind.",
    "Busted! Better luck next hand.",
    "Too greedy! The house thanks you.",
    "That's a bust! Chin up, friend.",
]

DEALER_QUIPS_PLAYER_WIN = [
    "Well played! You got me this time.",
    "A winner! Don't spend it all in one place.",
    "Impressive! The cards favored you.",
    "You win! My mustache bristles with respect.",
]

DEALER_QUIPS_DEALER_WIN = [
    "The house always has an edge!",
    "Better luck next time, friend.",
    "I'll take that, thank you kindly.",
    "The mustache never loses... well, almost.",
]

DEALER_QUIPS_PUSH = [
    "A tie! We live to fight another hand.",
    "Push! Nobody wins, nobody loses.",
    "Even steven! How about another?",
]

DEALER_QUIPS_BLACKJACK = [
    "BLACKJACK! Now THAT'S how you play!",
    "Twenty-one on the nose! Beautiful!",
    "Natural blackjack! Lucky Lou is impressed!",
]


# ---------------------------------------------------------------------------
# Card logic (pure functions, no curses dependency)
# ---------------------------------------------------------------------------
def make_deck():
    """Create and shuffle a standard 52-card deck."""
    deck = [(rank, suit) for suit in SUITS for rank in RANKS]
    random.shuffle(deck)
    return deck


def hand_value(hand):
    """Calculate the best value of a hand, handling aces correctly."""
    value = 0
    aces = 0
    for rank, _ in hand:
        if rank in ("J", "Q", "K"):
            value += 10
        elif rank == "A":
            value += 11
            aces += 1
        else:
            value += int(rank)
    while value > 21 and aces > 0:
        value -= 10
        aces -= 1
    return value


def is_blackjack(hand):
    """Check if a hand is a natural blackjack (21 in exactly two cards)."""
    return len(hand) == 2 and hand_value(hand) == 21


def is_bust(hand):
    """Check if a hand has busted (over 21)."""
    return hand_value(hand) > 21


def deal_card(deck):
    """Deal one card from the deck, reshuffling if empty."""
    if not deck:
        deck.extend(make_deck())
    return deck.pop()


def dealer_should_hit(hand):
    """Dealer hits on 16 or less, stands on 17+."""
    return hand_value(hand) < 17


def resolve(player_hand, dealer_hand, bet):
    """Determine outcome and return (message, payout, quip_list)."""
    pv = hand_value(player_hand)
    dv = hand_value(dealer_hand)
    p_bj = is_blackjack(player_hand)
    d_bj = is_blackjack(dealer_hand)

    if p_bj and d_bj:
        return "Both have Blackjack — Push!", 0, DEALER_QUIPS_PUSH
    if p_bj:
        return "BLACKJACK! 3:2 payout!", int(bet * 1.5), DEALER_QUIPS_BLACKJACK
    if d_bj:
        return "Dealer Blackjack!", -bet, DEALER_QUIPS_DEALER_WIN
    if pv > 21:
        return "BUST! Over 21.", -bet, DEALER_QUIPS_PLAYER_BUST
    if dv > 21:
        return "Dealer busts! You win!", bet, DEALER_QUIPS_PLAYER_WIN
    if pv > dv:
        return "You win!", bet, DEALER_QUIPS_PLAYER_WIN
    if dv > pv:
        return "Dealer wins.", -bet, DEALER_QUIPS_DEALER_WIN
    return "Push!", 0, DEALER_QUIPS_PUSH


# ---------------------------------------------------------------------------
# Card rendering helpers
# ---------------------------------------------------------------------------
CARD_WIDTH = 7
CARD_HEIGHT = 5


def card_lines(rank, suit, hidden=False):
    """Return list of strings for a single card (5 lines tall, 7 wide)."""
    if hidden:
        return [
            "┌─────┐",
            "│░░░░░│",
            "│░░░░░│",
            "│░░░░░│",
            "└─────┘",
        ]
    r = rank.ljust(2)
    rb = rank.rjust(2)
    return [
        "┌─────┐",
        f"│{r}   │",
        f"│  {suit}  │",
        f"│   {rb}│",
        "└─────┘",
    ]


def hand_card_lines(hand, hide_first=False):
    """Combine multiple cards into a row of lines (overlapping slightly)."""
    if not hand:
        return [""] * CARD_HEIGHT
    parts = []
    for i, (rank, suit) in enumerate(hand):
        hidden = (i == 1 and hide_first)
        parts.append(card_lines(rank, suit, hidden))
    # Overlap cards by 2 chars for compactness
    result = [""] * CARD_HEIGHT
    for ci, clines in enumerate(parts):
        for row in range(CARD_HEIGHT):
            if ci == 0:
                result[row] = clines[row]
            else:
                result[row] += clines[row][2:]  # skip first 2 chars for overlap
    return result


# ---------------------------------------------------------------------------
# Color setup
# ---------------------------------------------------------------------------
# Color pair indices
COLOR_TABLE = 1      # green felt background
COLOR_CARD_WHITE = 2  # white card / black suit
COLOR_CARD_RED = 3   # red suit card
COLOR_GOLD = 4       # bankroll / money
COLOR_HEADER = 5     # title / headers
COLOR_DEALER = 6     # dealer text / face
COLOR_STATUS = 7     # status messages
COLOR_WARN = 8       # warnings / bust
COLOR_HAIR = 9       # Lou's hair
COLOR_SHIRT = 10     # Lou's shirt
COLOR_TIE = 11       # Lou's tie
COLOR_GRAY = 12      # glasses connector


def init_colors():
    """Initialize curses color pairs."""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(COLOR_TABLE, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_CARD_WHITE, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_CARD_RED, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_GOLD, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_HEADER, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_DEALER, curses.COLOR_MAGENTA, -1)
    curses.init_pair(COLOR_STATUS, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_WARN, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_HAIR, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_SHIRT, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_TIE, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_GRAY, 8, -1)  # 8 = bright black (dark gray) on 256-color terms


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def safe_addstr(win, y, x, text, attr=0):
    """addstr that silently ignores curses errors at screen edges."""
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


def draw_card_row(win, y, x, hand, hide_first=False):
    """Draw a hand of cards at position (y, x)."""
    lines = hand_card_lines(hand, hide_first)
    stride = CARD_WIDTH - 2  # each card after the first adds this many chars
    for i, line in enumerate(lines):
        # Color each card character based on which card it belongs to
        for ci, ch in enumerate(line):
            col = x + ci
            # Determine which card index this column belongs to.
            # Card 0 occupies the full CARD_WIDTH columns (0..CARD_WIDTH-1).
            # Each subsequent card adds `stride` columns (its first 2 chars
            # are hidden behind the previous card).
            if len(hand) <= 1:
                card_idx = 0
            elif ci < CARD_WIDTH:
                card_idx = 0
            else:
                card_idx = 1 + (ci - CARD_WIDTH) // stride
            attr = curses.color_pair(COLOR_CARD_WHITE) | curses.A_BOLD
            if card_idx < len(hand):
                _, suit = hand[card_idx]
                if suit in RED_SUITS:
                    attr = curses.color_pair(COLOR_CARD_RED) | curses.A_BOLD
            if hide_first and card_idx == 1:
                attr = curses.color_pair(COLOR_HEADER)
            safe_addstr(win, y + i, col, ch, attr)


def get_eye_chars(game_phase, result_payout, blink_on):
    """Return (left_eye, right_eye) based on game state and blink timer."""
    if game_phase == "result":
        if result_payout > 0:
            return EYES_SAD          # dealer lost → sad Lou
        elif result_payout < 0:
            return EYES_HAPPY        # dealer won → happy Lou
        else:
            return EYES_SURPRISED    # push
    # During play, blink occasionally
    if blink_on:
        return EYES_BLINK
    return EYES_NEUTRAL


def draw_dealer_portrait(win, y, x, eyes=None):
    """Draw the dealer's portrait with per-character coloring and dynamic eyes."""
    if eyes is None:
        eyes = EYES_NEUTRAL
    for i, raw_line in enumerate(MUSTACHE_ART):
        # Substitute eye placeholders
        line = raw_line.replace("{EL}", eyes[0]).replace("{ER}", eyes[1])
        # Pick base color for this row region
        if i in LOU_HAIR_ROWS:
            attr = curses.color_pair(COLOR_HAIR) | curses.A_BOLD
        elif i in LOU_SHIRT_ROWS:
            attr = curses.color_pair(COLOR_SHIRT) | curses.A_BOLD
        else:
            attr = curses.color_pair(COLOR_DEALER) | curses.A_BOLD
        safe_addstr(win, y + i, x, line, attr)

    # --- Per-character color overrides ---

    # Row 2 (face): eyes white, glasses connector dark gray
    line2 = MUSTACHE_ART[2].replace("{EL}", eyes[0]).replace("{ER}", eyes[1])
    # Eyes at positions 11 and 14
    safe_addstr(win, y + 2, x + 11, line2[11],
                curses.color_pair(COLOR_CARD_WHITE) | curses.A_BOLD)
    safe_addstr(win, y + 2, x + 14, line2[14],
                curses.color_pair(COLOR_CARD_WHITE) | curses.A_BOLD)
    # Glasses connector (--) at positions 12-13
    safe_addstr(win, y + 2, x + 12, line2[12:14],
                curses.color_pair(COLOR_GRAY))

    # Row 3 (mustache upper): positions 11-14 yellow like hair
    line3 = MUSTACHE_ART[3]
    safe_addstr(win, y + 3, x + 11, line3[11:15],
                curses.color_pair(COLOR_HAIR) | curses.A_BOLD)

    # Row 5 (collar): positions 7-10 and 15-18 blue/aqua like shirt
    line5 = MUSTACHE_ART[5]
    safe_addstr(win, y + 5, x + 7, line5[7:11],
                curses.color_pair(COLOR_SHIRT) | curses.A_BOLD)
    safe_addstr(win, y + 5, x + 15, line5[15:19],
                curses.color_pair(COLOR_SHIRT) | curses.A_BOLD)
    # Tie accent on row 5 center (positions 11-14)
    mid = len(line5) // 2
    tie_start = max(0, mid - 2)
    tie_end = min(len(line5), mid + 2)
    safe_addstr(win, y + 5, x + tie_start, line5[tie_start:tie_end],
                curses.color_pair(COLOR_TIE) | curses.A_BOLD)

    # Row 6 (shirt): positions 11-14 blue/aqua like shirt (no tie overlay)
    line6 = MUSTACHE_ART[6]
    safe_addstr(win, y + 6, x + 11, line6[11:15],
                curses.color_pair(COLOR_SHIRT) | curses.A_BOLD)


def draw_title_bar(win, width):
    """Draw the title bar at top."""
    title = " ♠ ♥  BLACKJACK  ♦ ♣ "
    bar = "═" * width
    safe_addstr(win, 0, 0, bar, curses.color_pair(COLOR_TABLE))
    tx = max(0, (width - len(title)) // 2)
    safe_addstr(win, 0, tx, title, curses.color_pair(COLOR_HEADER) | curses.A_BOLD)


def draw_status_bar(win, y, width, bankroll, bet):
    """Draw the bottom status bar."""
    bar = "═" * width
    safe_addstr(win, y, 0, bar, curses.color_pair(COLOR_TABLE))
    info = f" 💰 ${bankroll}  │  Bet: ${bet}  │  h=Hit  s=Stand  d=Deal  q=Quit  +/-=Bet "
    safe_addstr(win, y + 1, 0, info, curses.color_pair(COLOR_GOLD) | curses.A_BOLD)


# ---------------------------------------------------------------------------
# Main game
# ---------------------------------------------------------------------------
def main(stdscr):
    """Main curses game loop."""
    stdscr.clear()
    init_colors()
    curses.curs_set(0)

    height, width = stdscr.getmaxyx()
    if height < 24 or width < 60:
        safe_addstr(stdscr, 0, 0, "Terminal too small! Need 60x24 minimum.",
                    curses.color_pair(COLOR_WARN))
        safe_addstr(stdscr, 1, 0, f"Current: {width}x{height}",
                    curses.color_pair(COLOR_WARN))
        safe_addstr(stdscr, 2, 0, "Press 'q' to quit.",
                    curses.color_pair(COLOR_STATUS))
        stdscr.refresh()
        while stdscr.getch() != ord('q'):
            pass
        return

    # Game state
    bankroll = STARTING_BANKROLL
    bet = MIN_BET
    deck = make_deck()
    player_hand = []
    dealer_hand = []
    message = "Welcome! Press 'd' to deal."
    quip = random.choice(DEALER_QUIPS_DEAL)
    game_phase = "betting"  # betting, player_turn, dealer_turn, result
    result_shown = False
    result_payout = 0  # tracks last payout for Lou's expression
    last_blink = time.time()
    blink_on = False
    BLINK_INTERVAL = 3.0   # seconds between blinks
    BLINK_DURATION = 0.3   # how long a blink lasts

    def redraw():
        """Redraw the entire screen."""
        stdscr.erase()
        draw_title_bar(stdscr, width)

        # Determine Lou's eyes
        eyes = get_eye_chars(game_phase, result_payout, blink_on)

        # Dealer portrait — top left
        draw_dealer_portrait(stdscr, 2, 2, eyes=eyes)

        # Dealer quip
        safe_addstr(stdscr, 2, 28, f'"{quip}"',
                    curses.color_pair(COLOR_DEALER))

        # Dealer hand label — moved down 1 row for taller portrait
        label_y = 10
        safe_addstr(stdscr, label_y, 4, "Dealer's Hand:",
                    curses.color_pair(COLOR_TABLE) | curses.A_BOLD)
        if dealer_hand:
            hide = game_phase == "player_turn"
            draw_card_row(stdscr, label_y + 1, 4, dealer_hand, hide_first=hide)
            if not hide:
                val = hand_value(dealer_hand)
                safe_addstr(stdscr, label_y + 1, 4 + len(dealer_hand) * (CARD_WIDTH - 2) + 4,
                            f"= {val}",
                            curses.color_pair(COLOR_GOLD) | curses.A_BOLD)

        # Player hand label
        player_y = label_y + 7
        safe_addstr(stdscr, player_y, 4, "Your Hand:",
                    curses.color_pair(COLOR_TABLE) | curses.A_BOLD)
        if player_hand:
            draw_card_row(stdscr, player_y + 1, 4, player_hand)
            val = hand_value(player_hand)
            safe_addstr(stdscr, player_y + 1, 4 + len(player_hand) * (CARD_WIDTH - 2) + 4,
                        f"= {val}",
                        curses.color_pair(COLOR_GOLD) | curses.A_BOLD)

        # Message
        msg_y = player_y + 7
        attr = curses.color_pair(COLOR_STATUS) | curses.A_BOLD
        if "BUST" in message or "lose" in message.lower():
            attr = curses.color_pair(COLOR_WARN) | curses.A_BOLD
        elif "win" in message.lower() or "BLACKJACK" in message:
            attr = curses.color_pair(COLOR_GOLD) | curses.A_BOLD
        safe_addstr(stdscr, msg_y, 4, message, attr)

        # Status bar
        draw_status_bar(stdscr, height - 3, width, bankroll, bet)

        stdscr.refresh()

    # Use non-blocking input with a short timeout for blink animation
    stdscr.timeout(100)

    # Main loop
    while True:
        # Update blink state
        now = time.time()
        elapsed = now - last_blink
        if blink_on:
            if elapsed >= BLINK_DURATION:
                blink_on = False
                last_blink = now
        else:
            if elapsed >= BLINK_INTERVAL:
                blink_on = True
                last_blink = now

        redraw()
        ch = stdscr.getch()
        if ch == -1:
            continue  # timeout, just re-render for animation

        if ch == ord('q') or ch == ord('Q'):
            break

        if game_phase == "betting":
            if ch == ord('d') or ch == ord('D'):
                if bankroll < bet:
                    bet = bankroll
                if bankroll <= 0:
                    message = "You're broke! Game over. Press 'q' to quit."
                    quip = "No more chips? The table remembers..."
                    continue
                # Deal new hand
                player_hand = [deal_card(deck), deal_card(deck)]
                dealer_hand = [deal_card(deck), deal_card(deck)]

                # Check for immediate blackjacks
                if is_blackjack(player_hand) or is_blackjack(dealer_hand):
                    msg, payout, quip_list = resolve(player_hand, dealer_hand, bet)
                    bankroll += payout
                    message = f"{msg}  (${'+' if payout >= 0 else ''}{payout})"
                    quip = random.choice(quip_list)
                    game_phase = "result"
                    result_shown = True
                    result_payout = payout
                else:
                    message = "Your turn: (h)it or (s)tand"
                    quip = random.choice(DEALER_QUIPS_DEAL)
                    game_phase = "player_turn"
                    result_payout = 0
            elif ch == ord('+') or ch == ord('='):
                bet = min(bet + 10, MAX_BET, bankroll)
                message = f"Bet raised to ${bet}. Press 'd' to deal."
                quip = "Raising the stakes! I like it."
            elif ch == ord('-') or ch == ord('_'):
                bet = max(bet - 10, MIN_BET)
                message = f"Bet lowered to ${bet}. Press 'd' to deal."
                quip = "Playing it safe, eh?"

        elif game_phase == "player_turn":
            if ch == ord('h') or ch == ord('H'):
                player_hand.append(deal_card(deck))
                quip = random.choice(DEALER_QUIPS_HIT)
                if is_bust(player_hand):
                    msg, payout, quip_list = resolve(player_hand, dealer_hand, bet)
                    bankroll += payout
                    message = f"{msg}  (${'+' if payout >= 0 else ''}{payout})"
                    quip = random.choice(quip_list)
                    game_phase = "result"
                    result_shown = True
                    result_payout = payout
                elif hand_value(player_hand) == 21:
                    message = "21! Standing automatically."
                    # Dealer turn
                    while dealer_should_hit(dealer_hand):
                        dealer_hand.append(deal_card(deck))
                    msg, payout, quip_list = resolve(player_hand, dealer_hand, bet)
                    bankroll += payout
                    message = f"{msg}  (${'+' if payout >= 0 else ''}{payout})"
                    quip = random.choice(quip_list)
                    game_phase = "result"
                    result_shown = True
                    result_payout = payout
                else:
                    message = f"Value: {hand_value(player_hand)}. (h)it or (s)tand?"
            elif ch == ord('s') or ch == ord('S'):
                # Dealer turn
                while dealer_should_hit(dealer_hand):
                    dealer_hand.append(deal_card(deck))
                msg, payout, quip_list = resolve(player_hand, dealer_hand, bet)
                bankroll += payout
                message = f"{msg}  (${'+' if payout >= 0 else ''}{payout})"
                quip = random.choice(quip_list)
                game_phase = "result"
                result_shown = True
                result_payout = payout

        elif game_phase == "result":
            if ch == ord('d') or ch == ord('D'):
                if bankroll <= 0:
                    message = "You're broke! Game over. Press 'q' to quit."
                    quip = "The table has spoken. Come back anytime!"
                    continue
                # New hand
                player_hand = [deal_card(deck), deal_card(deck)]
                dealer_hand = [deal_card(deck), deal_card(deck)]
                if is_blackjack(player_hand) or is_blackjack(dealer_hand):
                    msg, payout, quip_list = resolve(player_hand, dealer_hand, bet)
                    bankroll += payout
                    message = f"{msg}  (${'+' if payout >= 0 else ''}{payout})"
                    quip = random.choice(quip_list)
                    game_phase = "result"
                    result_payout = payout
                else:
                    message = "Your turn: (h)it or (s)tand"
                    quip = random.choice(DEALER_QUIPS_DEAL)
                    game_phase = "player_turn"
                    result_payout = 0
            elif ch == ord('+') or ch == ord('='):
                bet = min(bet + 10, MAX_BET, bankroll)
                message = f"Bet adjusted to ${bet}. Press 'd' to deal."
            elif ch == ord('-') or ch == ord('_'):
                bet = max(bet - 10, MIN_BET)
                message = f"Bet adjusted to ${bet}. Press 'd' to deal."


if __name__ == "__main__":
    curses.wrapper(main)
