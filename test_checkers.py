#!/usr/bin/env python3
"""Test suite for the Checkers game (scripts/games/checkers.py)."""

import ast
import os
import stat
import sys
import unittest

# ── Path setup ──────────────────────────────────────────────────────
CHECKERS_PATH = os.path.join(os.path.dirname(__file__), "checkers.py")


def load_source():
    """Load checkers.py source as a string."""
    with open(CHECKERS_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_ast():
    """Parse checkers.py into an AST tree."""
    return ast.parse(load_source())


def get_top_level_names(tree):
    """Extract top-level function, class, and variable names from AST."""
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


def find_all_functions(tree):
    """Walk AST and find all function definitions (including nested)."""
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = node
    return functions


def find_all_string_literals(tree):
    """Extract all string constants from AST."""
    strings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append(node.value)
    return strings


def import_module():
    """Import checkers module by stripping __main__ guard and exec'ing."""
    source = load_source()
    tree = ast.parse(source)
    new_body = []
    for node in tree.body:
        if isinstance(node, ast.If):
            test = node.test
            if (isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name)
                    and test.left.id == "__name__"):
                continue
        new_body.append(node)
    tree.body = new_body
    ast.fix_missing_locations(tree)
    code = compile(tree, CHECKERS_PATH, "exec")
    namespace = {"__file__": CHECKERS_PATH, "__name__": "checkers"}
    exec(code, namespace)
    return namespace


# ════════════════════════════════════════════════════════════════════
#  Test classes
# ════════════════════════════════════════════════════════════════════

class TestFileStructure(unittest.TestCase):
    """Validate file existence, shebang, docstring, and imports."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.tree = parse_ast()

    def test_file_exists(self):
        """checkers.py must exist."""
        self.assertTrue(os.path.isfile(CHECKERS_PATH))

    def test_file_is_executable(self):
        """checkers.py should have executable permission."""
        mode = os.stat(CHECKERS_PATH).st_mode
        self.assertTrue(mode & stat.S_IXUSR, "File should be executable")

    def test_has_shebang(self):
        """First line should be a Python shebang."""
        self.assertTrue(self.source.startswith("#!/usr/bin/env python3"))

    def test_has_docstring(self):
        """Module-level docstring should be present."""
        module = self.tree
        self.assertIsInstance(module.body[0], ast.Expr)
        self.assertIsInstance(module.body[0].value, ast.Constant)
        self.assertIsInstance(module.body[0].value.value, str)

    def test_syntax_valid(self):
        """Source must parse without syntax errors."""
        try:
            ast.parse(self.source)
        except SyntaxError:
            self.fail("checkers.py has syntax errors")

    def test_stdlib_only(self):
        """Only standard library modules should be imported."""
        allowed = {"curses", "random", "sys", "os", "copy"}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split(".")[0], allowed,
                                  f"Non-stdlib import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.assertIn(node.module.split(".")[0], allowed,
                                  f"Non-stdlib import: {node.module}")

    def test_imports_curses(self):
        """Must import the curses module."""
        self.assertIn("curses", self.source)


class TestRequiredComponents(unittest.TestCase):
    """Validate essential game structure."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.tree = parse_ast()
        cls.names = get_top_level_names(cls.tree)
        cls.functions = find_all_functions(cls.tree)

    def test_has_main_function(self):
        """Must have a main() function."""
        self.assertIn("main", self.functions)

    def test_main_accepts_stdscr(self):
        """main() must accept an stdscr parameter."""
        node = self.functions["main"]
        params = [a.arg for a in node.args.args]
        self.assertIn("stdscr", params)

    def test_has_curses_wrapper(self):
        """Must call curses.wrapper(main)."""
        self.assertIn("curses.wrapper", self.source)


class TestBoardInit(unittest.TestCase):
    """Board initialization and piece placement."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_make_board_returns_8x8(self):
        """make_board() must return an 8×8 grid."""
        board = self.ns["make_board"]()
        self.assertEqual(len(board), 8)
        for row in board:
            self.assertEqual(len(row), 8)

    def test_red_has_12_pieces(self):
        """Initial board should have 12 red pieces."""
        board = self.ns["make_board"]()
        red = sum(1 for r in board for p in r if p in ("r", "R"))
        self.assertEqual(red, 12)

    def test_white_has_12_pieces(self):
        """Initial board should have 12 white pieces."""
        board = self.ns["make_board"]()
        white = sum(1 for r in board for p in r if p in ("w", "W"))
        self.assertEqual(white, 12)

    def test_pieces_on_dark_squares_only(self):
        """All pieces must be on dark squares ((r+c) % 2 == 1)."""
        board = self.ns["make_board"]()
        for r in range(8):
            for c in range(8):
                if board[r][c] is not None:
                    self.assertEqual((r + c) % 2, 1,
                                     f"Piece on light square at ({r},{c})")


class TestMoveValidation(unittest.TestCase):
    """Move and jump validation logic."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_get_simple_moves_exists(self):
        """get_simple_moves function must exist."""
        self.assertIn("get_simple_moves", self.ns)

    def test_simple_moves_from_start(self):
        """White pieces in row 5 should have forward moves at start."""
        board = self.ns["make_board"]()
        # White piece at (5, 0) should be able to move to (4, 1)
        moves = self.ns["get_simple_moves"](board, 5, 0)
        self.assertIn((4, 1), moves)

    def test_no_backward_moves_for_regular(self):
        """Regular white piece should not move backward (increasing row)."""
        board = self.ns["make_board"]()
        moves = self.ns["get_simple_moves"](board, 5, 0)
        for mr, mc in moves:
            self.assertLess(mr, 5, "Regular white piece moved backward")


class TestJumpCapture(unittest.TestCase):
    """Jump and capture detection."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_get_jumps_exists(self):
        """get_jumps function must exist."""
        self.assertIn("get_jumps", self.ns)

    def test_jump_captures_opponent(self):
        """A piece should be able to jump over an adjacent opponent."""
        board = [[None] * 8 for _ in range(8)]
        board[4][3] = "w"
        board[3][2] = "r"
        jumps = self.ns["get_jumps"](board, 4, 3)
        # Should land at (2, 1) jumping over (3, 2)
        lands = [(lr, lc) for lr, lc, mr, mc in jumps]
        self.assertIn((2, 1), lands)

    def test_no_jump_over_own_piece(self):
        """Cannot jump over your own piece."""
        board = [[None] * 8 for _ in range(8)]
        board[4][3] = "w"
        board[3][2] = "w"  # Own piece
        jumps = self.ns["get_jumps"](board, 4, 3)
        self.assertEqual(len(jumps), 0)

    def test_mandatory_jumps_enforced(self):
        """get_all_moves should return jumps when available."""
        board = [[None] * 8 for _ in range(8)]
        board[4][3] = "w"
        board[3][2] = "r"
        jumps, moves = self.ns["get_all_moves"](board, "w")
        self.assertGreater(len(jumps), 0, "Jumps should be detected")


class TestKingPromotion(unittest.TestCase):
    """King promotion logic."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_white_promotes_at_row_0(self):
        """White piece reaching row 0 should become king 'W'."""
        board = [[None] * 8 for _ in range(8)]
        board[1][0] = "w"
        self.ns["apply_move"](board, 1, 0, 0, 1)
        self.assertEqual(board[0][1], "W")

    def test_red_promotes_at_row_7(self):
        """Red piece reaching row 7 should become king 'R'."""
        board = [[None] * 8 for _ in range(8)]
        board[6][1] = "r"
        self.ns["apply_move"](board, 6, 1, 7, 0)
        self.assertEqual(board[7][0], "R")

    def test_king_moves_all_directions(self):
        """A king should be able to move in all four diagonal directions."""
        board = [[None] * 8 for _ in range(8)]
        board[4][3] = "W"  # White king in center
        moves = self.ns["get_simple_moves"](board, 4, 3)
        # Should be able to go to all four diagonals
        self.assertIn((3, 2), moves)
        self.assertIn((3, 4), moves)
        self.assertIn((5, 2), moves)
        self.assertIn((5, 4), moves)


class TestAIOpponent(unittest.TestCase):
    """AI / computer opponent."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()
        cls.source = load_source()

    def test_ai_choose_move_exists(self):
        """ai_choose_move function must exist."""
        self.assertIn("ai_choose_move", self.ns)

    def test_ai_execute_turn_exists(self):
        """ai_execute_turn function must exist."""
        self.assertIn("ai_execute_turn", self.ns)

    def test_ai_returns_valid_move(self):
        """AI should return a move from the starting position."""
        board = self.ns["make_board"]()
        result = self.ns["ai_choose_move"](board, "r")
        self.assertIsNotNone(result, "AI should find a move from starting position")
        fr, fc, tr, tc, mid = result
        # Must be a red piece
        self.assertIn(board[fr][fc], ("r", "R"))

    def test_ai_executes_full_turn(self):
        """ai_execute_turn should modify board and return steps."""
        board = self.ns["make_board"]()
        steps = self.ns["ai_execute_turn"](board)
        self.assertGreater(len(steps), 0, "AI should make at least one step")


class TestColorInit(unittest.TestCase):
    """Curses color initialization."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.functions = find_all_functions(parse_ast())

    def test_has_init_colors_function(self):
        """init_colors() function must exist."""
        self.assertIn("init_colors", self.functions)

    def test_uses_start_color(self):
        """Must call curses.start_color()."""
        self.assertIn("curses.start_color()", self.source)

    def test_uses_init_pair(self):
        """Must call curses.init_pair() for color pairs."""
        self.assertIn("curses.init_pair(", self.source)

    def test_uses_color_pair(self):
        """Must call curses.color_pair() for rendering."""
        self.assertIn("curses.color_pair(", self.source)

    def test_hides_cursor(self):
        """Must call curses.curs_set(0) to hide cursor."""
        self.assertIn("curses.curs_set(0)", self.source)


class TestUnicodePieceSymbols(unittest.TestCase):
    """Unicode / nerd font glyphs for pieces."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_has_circle_glyph(self):
        """Must use circle-style glyphs for pieces (● or ◉)."""
        has = "●" in self.source or "◉" in self.source or "◎" in self.source
        self.assertTrue(has, "Should use Unicode circle glyphs for pieces")

    def test_has_king_glyph(self):
        """Must use crown/queen glyph for kings (♛ or ♕)."""
        has = "♛" in self.source or "♕" in self.source or "♚" in self.source
        self.assertTrue(has, "Should use Unicode crown glyphs for kings")

    def test_has_dot_indicator(self):
        """Must use a dot indicator for valid moves (· or •)."""
        has = "·" in self.source or "•" in self.source
        self.assertTrue(has, "Should use dot glyph for valid-move indicator")


class TestBoxDrawingBorders(unittest.TestCase):
    """Box-drawing characters for the board border."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_has_box_drawing_corners(self):
        """Must use box-drawing corner characters (╔ ╗ ╚ ╝)."""
        for ch in "╔╗╚╝":
            self.assertIn(ch, self.source, f"Missing box-drawing corner '{ch}'")

    def test_has_box_drawing_lines(self):
        """Must use box-drawing line characters (═ ║)."""
        self.assertIn("═", self.source)
        self.assertIn("║", self.source)


class TestInputHandling(unittest.TestCase):
    """Arrow-key and selection input handling."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_handles_arrow_keys(self):
        """Must handle curses arrow key constants."""
        for key in ("KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT"):
            self.assertIn(key, self.source, f"Missing input handler for {key}")

    def test_handles_space_select(self):
        """Must handle space bar for piece selection."""
        self.assertIn("ord(\" \")", self.source)

    def test_handles_quit(self):
        """Must handle Q key to quit."""
        has_quit = 'ord("q")' in self.source or "ord('q')" in self.source
        self.assertTrue(has_quit, "Must handle Q key to quit")


class TestWinDetection(unittest.TestCase):
    """Win / loss / game-over detection."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_check_winner_exists(self):
        """check_winner function must exist."""
        self.assertIn("check_winner", self.ns)

    def test_white_wins_when_no_red(self):
        """White should win if all red pieces are removed."""
        board = [[None] * 8 for _ in range(8)]
        board[7][0] = "w"
        result = self.ns["check_winner"](board)
        self.assertEqual(result, "White")

    def test_red_wins_when_no_white(self):
        """Red should win if all white pieces are removed."""
        board = [[None] * 8 for _ in range(8)]
        board[0][1] = "r"
        result = self.ns["check_winner"](board)
        self.assertEqual(result, "Red")

    def test_no_winner_at_start(self):
        """No winner at start of game."""
        board = self.ns["make_board"]()
        result = self.ns["check_winner"](board)
        self.assertIsNone(result)


# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    unittest.main()
