#!/usr/bin/env python3
"""
Test suite for blackjack.py — Terminal Blackjack Game
Tests the "known good" benchmark: structure, logic, and behavior.
These tests run WITHOUT a terminal (no curses rendering).
"""

import ast
import os
import stat
import sys
import unittest

# Path to the script under test
BLACKJACK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "blackjack.py")


def load_source():
    """Load blackjack.py source code as a string."""
    with open(BLACKJACK_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_ast():
    """Parse blackjack.py into an AST tree."""
    return ast.parse(load_source())


def get_top_level_names(tree):
    """Get all top-level names (functions, classes, assignments) from AST."""
    names = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef):
            names[node.name] = "function"
        elif isinstance(node, ast.ClassDef):
            names[node.name] = "class"
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names[target.id] = "variable"
    return names


def import_module():
    """Import blackjack.py as a module (without running main).

    Strips the if __name__ == "__main__" block and execs everything else
    into a namespace, avoiding curses initialization.
    """
    source = load_source()
    tree = ast.parse(source)

    # Remove the if __name__ == "__main__" block
    new_body = []
    for node in tree.body:
        if isinstance(node, ast.If):
            test = node.test
            if (isinstance(test, ast.Compare) and
                isinstance(test.left, ast.Name) and
                    test.left.id == "__name__"):
                continue
        new_body.append(node)

    tree.body = new_body
    ast.fix_missing_locations(tree)

    code = compile(tree, BLACKJACK_PATH, "exec")
    namespace = {"__file__": BLACKJACK_PATH, "__name__": "blackjack"}
    exec(code, namespace)
    return namespace


def find_all_functions(tree):
    """Find all function definitions in the AST (including nested)."""
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = node
    return functions


def find_all_string_literals(tree):
    """Find all string literals in the AST."""
    strings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append(node.value)
    return strings


# =============================================================================
# 1. FILE STRUCTURE TESTS
# =============================================================================

class TestFileStructure(unittest.TestCase):
    """Tests that blackjack.py has the right file-level properties."""

    def test_file_exists(self):
        """blackjack.py must exist."""
        self.assertTrue(os.path.isfile(BLACKJACK_PATH),
                        "blackjack.py not found")

    def test_file_is_executable(self):
        """blackjack.py must have the executable bit set."""
        mode = os.stat(BLACKJACK_PATH).st_mode
        self.assertTrue(mode & stat.S_IXUSR,
                        "blackjack.py is not executable")

    def test_has_shebang(self):
        """First line must be a Python shebang."""
        source = load_source()
        first_line = source.split("\n")[0]
        self.assertTrue(first_line.startswith("#!"),
                        "Missing shebang line")
        self.assertIn("python", first_line.lower())

    def test_has_docstring(self):
        """Module must have a docstring."""
        tree = parse_ast()
        docstring = ast.get_docstring(tree)
        self.assertIsNotNone(docstring, "Missing module docstring")
        self.assertGreater(len(docstring), 10,
                           "Docstring too short")

    def test_syntax_valid(self):
        """Source must parse without syntax errors."""
        try:
            parse_ast()
        except SyntaxError as e:
            self.fail(f"Syntax error: {e}")

    def test_stdlib_only(self):
        """Must only import standard library modules."""
        tree = parse_ast()
        allowed = {"curses", "random", "os", "sys", "time"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split(".")[0], allowed,
                                  f"Non-stdlib import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.assertIn(node.module.split(".")[0], allowed,
                                  f"Non-stdlib import: {node.module}")

    def test_imports_curses(self):
        """Must import curses."""
        source = load_source()
        self.assertIn("import curses", source)


# =============================================================================
# 2. REQUIRED COMPONENTS
# =============================================================================

class TestRequiredComponents(unittest.TestCase):
    """Tests for essential game components."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.tree = parse_ast()
        cls.names = get_top_level_names(cls.tree)
        cls.functions = find_all_functions(cls.tree)

    def test_has_main_function(self):
        """Must have a main() function."""
        self.assertIn("main", self.names)

    def test_main_accepts_stdscr(self):
        """main() must accept stdscr parameter."""
        main_func = self.functions.get("main")
        self.assertIsNotNone(main_func, "main function not found")
        args = [arg.arg for arg in main_func.args.args]
        self.assertIn("stdscr", args,
                       "main() must accept stdscr parameter")

    def test_uses_curses_wrapper(self):
        """Must use curses.wrapper() to launch the game."""
        self.assertIn("curses.wrapper", self.source)


# =============================================================================
# 3. DECK AND CARD LOGIC
# =============================================================================

class TestDeckLogic(unittest.TestCase):
    """Tests for deck creation and card logic."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_make_deck_returns_52_cards(self):
        """make_deck() must return 52 cards."""
        deck = self.ns["make_deck"]()
        self.assertEqual(len(deck), 52)

    def test_deck_has_all_suits(self):
        """Deck must contain all four suits."""
        deck = self.ns["make_deck"]()
        suits = {s for _, s in deck}
        self.assertEqual(suits, {"♠", "♥", "♦", "♣"})

    def test_deck_has_all_ranks(self):
        """Deck must contain all 13 ranks."""
        deck = self.ns["make_deck"]()
        ranks = {r for r, _ in deck}
        expected = {"2", "3", "4", "5", "6", "7", "8", "9", "10",
                    "J", "Q", "K", "A"}
        self.assertEqual(ranks, expected)

    def test_deck_is_shuffled(self):
        """Two fresh decks should differ (shuffled)."""
        d1 = self.ns["make_deck"]()
        d2 = self.ns["make_deck"]()
        # Extremely unlikely both are identical after shuffle
        self.assertNotEqual(d1, d2)


# =============================================================================
# 4. HAND VALUE CALCULATION
# =============================================================================

class TestHandValue(unittest.TestCase):
    """Tests for hand value calculation, especially ace handling."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_number_cards(self):
        """Number cards should have face value."""
        hv = self.ns["hand_value"]
        self.assertEqual(hv([("5", "♠"), ("3", "♥")]), 8)

    def test_face_cards_worth_10(self):
        """J, Q, K should each be worth 10."""
        hv = self.ns["hand_value"]
        self.assertEqual(hv([("J", "♠"), ("Q", "♥")]), 20)
        self.assertEqual(hv([("K", "♦")]), 10)

    def test_ace_as_11(self):
        """Ace should count as 11 when total <= 21."""
        hv = self.ns["hand_value"]
        self.assertEqual(hv([("A", "♠"), ("5", "♥")]), 16)

    def test_ace_as_1_when_bust(self):
        """Ace should count as 1 when 11 would bust."""
        hv = self.ns["hand_value"]
        self.assertEqual(hv([("A", "♠"), ("9", "♥"), ("5", "♦")]), 15)

    def test_two_aces(self):
        """Two aces: one 11 + one 1 = 12."""
        hv = self.ns["hand_value"]
        self.assertEqual(hv([("A", "♠"), ("A", "♥")]), 12)

    def test_blackjack_value(self):
        """Ace + face card = 21."""
        hv = self.ns["hand_value"]
        self.assertEqual(hv([("A", "♠"), ("K", "♥")]), 21)


# =============================================================================
# 5. BLACKJACK / BUST DETECTION
# =============================================================================

class TestBlackjackBust(unittest.TestCase):
    """Tests for blackjack and bust detection."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_is_blackjack_natural(self):
        """Two-card 21 is blackjack."""
        self.assertTrue(self.ns["is_blackjack"]([("A", "♠"), ("K", "♥")]))

    def test_not_blackjack_three_cards(self):
        """Three cards totaling 21 is NOT blackjack."""
        self.assertFalse(self.ns["is_blackjack"]([("7", "♠"), ("7", "♥"), ("7", "♦")]))

    def test_is_bust_over_21(self):
        """Hand over 21 should be bust."""
        self.assertTrue(self.ns["is_bust"]([("K", "♠"), ("Q", "♥"), ("5", "♦")]))

    def test_not_bust_under_21(self):
        """Hand under 21 should not be bust."""
        self.assertFalse(self.ns["is_bust"]([("K", "♠"), ("5", "♥")]))


# =============================================================================
# 6. DEALER AI
# =============================================================================

class TestDealerAI(unittest.TestCase):
    """Tests for dealer hit/stand logic."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_dealer_hits_under_17(self):
        """Dealer should hit on 16."""
        self.assertTrue(self.ns["dealer_should_hit"]([("10", "♠"), ("6", "♥")]))

    def test_dealer_stands_on_17(self):
        """Dealer should stand on 17."""
        self.assertFalse(self.ns["dealer_should_hit"]([("10", "♠"), ("7", "♥")]))

    def test_dealer_stands_on_soft_17(self):
        """Dealer should stand on soft 17 (A+6)."""
        self.assertFalse(self.ns["dealer_should_hit"]([("A", "♠"), ("6", "♥")]))


# =============================================================================
# 7. RESOLVE (WIN/LOSS/PUSH)
# =============================================================================

class TestResolve(unittest.TestCase):
    """Tests for game outcome resolution."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_player_blackjack_pays_3_to_2(self):
        """Player blackjack pays 1.5x bet."""
        msg, payout, _ = self.ns["resolve"](
            [("A", "♠"), ("K", "♥")],  # player BJ
            [("10", "♦"), ("7", "♣")],  # dealer 17
            100
        )
        self.assertEqual(payout, 150)
        self.assertIn("BLACKJACK", msg.upper())

    def test_player_bust_loses_bet(self):
        """Player bust loses the bet."""
        msg, payout, _ = self.ns["resolve"](
            [("K", "♠"), ("Q", "♥"), ("5", "♦")],  # 25, bust
            [("10", "♣"), ("7", "♣")],
            100
        )
        self.assertEqual(payout, -100)

    def test_dealer_bust_wins(self):
        """Dealer bust means player wins."""
        msg, payout, _ = self.ns["resolve"](
            [("10", "♠"), ("8", "♥")],  # 18
            [("K", "♦"), ("Q", "♣"), ("5", "♣")],  # 25, bust
            100
        )
        self.assertEqual(payout, 100)

    def test_push_returns_zero(self):
        """Equal hands result in push (0 payout)."""
        msg, payout, _ = self.ns["resolve"](
            [("10", "♠"), ("7", "♥")],
            [("10", "♦"), ("7", "♣")],
            100
        )
        self.assertEqual(payout, 0)

    def test_player_higher_wins(self):
        """Player with higher value wins."""
        msg, payout, _ = self.ns["resolve"](
            [("10", "♠"), ("9", "♥")],  # 19
            [("10", "♦"), ("8", "♣")],  # 18
            100
        )
        self.assertEqual(payout, 100)


# =============================================================================
# 8. COLOR INITIALIZATION
# =============================================================================

class TestColorInit(unittest.TestCase):
    """Tests that curses colors are properly set up."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_has_start_color(self):
        """Must call curses.start_color()."""
        self.assertIn("start_color", self.source)

    def test_has_init_pair(self):
        """Must call curses.init_pair() to define colors."""
        self.assertIn("init_pair", self.source)

    def test_has_green_for_table(self):
        """Table should use green (felt)."""
        self.assertIn("COLOR_GREEN", self.source)

    def test_has_red_for_suits(self):
        """Red suits should use red color."""
        self.assertIn("COLOR_RED", self.source)

    def test_has_yellow_for_gold(self):
        """Bankroll/money should use yellow."""
        self.assertIn("COLOR_YELLOW", self.source)

    def test_has_cyan_for_headers(self):
        """Headers should use cyan."""
        self.assertIn("COLOR_CYAN", self.source)

    def test_has_init_colors_function(self):
        """Must have an init_colors function."""
        functions = find_all_functions(parse_ast())
        self.assertIn("init_colors", functions)


# =============================================================================
# 9. CARD SUIT SYMBOLS
# =============================================================================

class TestCardSuitSymbols(unittest.TestCase):
    """Tests that card suit Unicode symbols are used."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.strings = find_all_string_literals(parse_ast())
        cls.all_text = "".join(cls.strings)

    def test_has_spade(self):
        """Must use ♠ symbol."""
        self.assertIn("♠", self.all_text)

    def test_has_heart(self):
        """Must use ♥ symbol."""
        self.assertIn("♥", self.all_text)

    def test_has_diamond(self):
        """Must use ♦ symbol."""
        self.assertIn("♦", self.all_text)

    def test_has_club(self):
        """Must use ♣ symbol."""
        self.assertIn("♣", self.all_text)

    def test_has_box_drawing_chars(self):
        """Must use box-drawing characters for card borders."""
        box_chars = set("┌┐└┘─│╭╰╮╯═╔╗╚╝║")
        found = [ch for ch in box_chars if ch in self.all_text]
        self.assertGreater(len(found), 3,
                           f"Too few box-drawing chars found: {found}")


# =============================================================================
# 10. DEALER PERSONA
# =============================================================================

class TestDealerPersona(unittest.TestCase):
    """Tests for the dealer character and personality."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.ns = import_module()

    def test_has_dealer_name(self):
        """Must have a dealer name defined."""
        self.assertIn("DEALER_NAME", self.ns)

    def test_has_mustache_art(self):
        """Must have ASCII mustache art."""
        self.assertIn("MUSTACHE_ART", self.ns)
        art = self.ns["MUSTACHE_ART"]
        self.assertIsInstance(art, list)
        self.assertGreater(len(art), 2)

    def test_mustache_has_twisty_chars(self):
        """Mustache art must contain wavy/twisty characters."""
        art = "\n".join(self.ns["MUSTACHE_ART"])
        twisty = {"~", "}", "{", "─", "╭", "╰"}
        found = [ch for ch in twisty if ch in art]
        self.assertGreater(len(found), 1,
                           "Mustache art needs twisty characters")

    def test_has_dealer_quips(self):
        """Must have dealer dialogue/quip lists."""
        quip_lists = [k for k in self.ns if k.startswith("DEALER_QUIPS")]
        self.assertGreaterEqual(len(quip_lists), 4,
                                "Need at least 4 quip categories")

    def test_quips_are_nonempty_lists(self):
        """Each quip list must contain at least one string."""
        for key in self.ns:
            if key.startswith("DEALER_QUIPS"):
                val = self.ns[key]
                self.assertIsInstance(val, list)
                self.assertGreater(len(val), 0,
                                   f"{key} is empty")
                self.assertIsInstance(val[0], str)

    def test_draw_dealer_portrait_exists(self):
        """Must have a draw_dealer_portrait function."""
        functions = find_all_functions(parse_ast())
        self.assertIn("draw_dealer_portrait", functions)


# =============================================================================
# 11. INPUT HANDLING
# =============================================================================

class TestInputHandling(unittest.TestCase):
    """Tests that the game handles expected keyboard input."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_handles_hit_key(self):
        """Must handle 'h' key for hit."""
        self.assertIn("ord('h')", self.source)

    def test_handles_stand_key(self):
        """Must handle 's' key for stand."""
        self.assertIn("ord('s')", self.source)

    def test_handles_quit_key(self):
        """Must handle 'q' key for quit."""
        self.assertIn("ord('q')", self.source)

    def test_handles_deal_key(self):
        """Must handle 'd' key for deal/new hand."""
        self.assertIn("ord('d')", self.source)


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":
    unittest.main()
