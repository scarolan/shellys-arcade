#!/usr/bin/env python3
"""
Test suite for game2048.py — Terminal 2048 Game
Tests the "known good" benchmark: structure, logic, and behavior.
These tests run WITHOUT a terminal (no curses rendering).
"""

import ast
import os
import stat
import unittest

# Path to the script under test
GAME_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "game2048.py")


def load_source():
    """Load game2048.py source code as a string."""
    with open(GAME_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_ast():
    """Parse game2048.py into an AST tree."""
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
    """Import game2048.py as a module (without running main).

    Strips the if __name__ == "__main__" block and execs everything else
    into a namespace, avoiding curses initialization.
    """
    source = load_source()
    tree = ast.parse(source)

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

    code = compile(tree, GAME_PATH, "exec")
    namespace = {"__file__": GAME_PATH, "__name__": "game2048"}
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
    """Tests that game2048.py has the right file-level properties."""

    def test_file_exists(self):
        """game2048.py must exist."""
        self.assertTrue(os.path.isfile(GAME_PATH),
                        "game2048.py not found")

    def test_file_is_executable(self):
        """game2048.py must have the executable bit set."""
        mode = os.stat(GAME_PATH).st_mode
        self.assertTrue(mode & stat.S_IXUSR,
                        "game2048.py is not executable")

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
        source = load_source()
        try:
            ast.parse(source)
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

    def test_has_board_creation(self):
        """Must have board creation logic."""
        self.assertIn("new_board", self.functions,
                       "Missing new_board function")

    def test_has_tile_spawning(self):
        """Must have tile spawning logic."""
        self.assertIn("add_random_tile", self.functions,
                       "Missing add_random_tile function")

    def test_has_slide_merge(self):
        """Must have slide/merge logic."""
        self.assertIn("slide_row_left", self.functions,
                       "Missing slide_row_left function")

    def test_has_move_function(self):
        """Must have a move function for all 4 directions."""
        self.assertIn("move", self.functions,
                       "Missing move function")
        source = self.source
        for d in ("left", "right", "up", "down"):
            self.assertIn(f'"{d}"', source,
                          f"move() missing direction: {d}")

    def test_has_game_loop(self):
        """Must have a game loop (while True)."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value:
                    return
        self.fail("No game loop (while True) found")


# =============================================================================
# 3. BOARD AND TILE LOGIC
# =============================================================================

class TestBoardLogic(unittest.TestCase):
    """Tests for board data structures and core logic."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_board_is_4x4(self):
        """new_board() must return a 4x4 grid."""
        new_board = self.ns["new_board"]
        board = new_board()
        self.assertEqual(len(board), 4)
        for row in board:
            self.assertEqual(len(row), 4)
            for cell in row:
                self.assertEqual(cell, 0)

    def test_add_random_tile_places_2_or_4(self):
        """add_random_tile() must place a 2 or 4 on an empty cell."""
        new_board = self.ns["new_board"]
        add_tile = self.ns["add_random_tile"]
        board = new_board()
        add_tile(board)
        non_zero = [v for row in board for v in row if v != 0]
        self.assertEqual(len(non_zero), 1)
        self.assertIn(non_zero[0], (2, 4))

    def test_empty_cells_returns_all_on_empty_board(self):
        """empty_cells() must return 16 cells for an empty board."""
        empty_cells = self.ns["empty_cells"]
        new_board = self.ns["new_board"]
        board = new_board()
        cells = empty_cells(board)
        self.assertEqual(len(cells), 16)

    def test_empty_cells_excludes_filled(self):
        """empty_cells() must exclude non-zero cells."""
        empty_cells = self.ns["empty_cells"]
        new_board = self.ns["new_board"]
        board = new_board()
        board[0][0] = 2
        board[1][1] = 4
        cells = empty_cells(board)
        self.assertEqual(len(cells), 14)
        self.assertNotIn((0, 0), cells)
        self.assertNotIn((1, 1), cells)


# =============================================================================
# 4. SLIDE AND MERGE LOGIC
# =============================================================================

class TestSlideMerge(unittest.TestCase):
    """Tests for the slide and merge mechanics."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_slide_left_basic(self):
        """Sliding [2, 0, 0, 2] left produces [4, 0, 0, 0] with score 4."""
        slide = self.ns["slide_row_left"]
        row, score, _ = slide([2, 0, 0, 2])
        self.assertEqual(row, [4, 0, 0, 0])
        self.assertEqual(score, 4)

    def test_slide_left_no_merge(self):
        """Sliding [2, 4, 0, 0] left produces [2, 4, 0, 0] with score 0."""
        slide = self.ns["slide_row_left"]
        row, score, _ = slide([2, 4, 0, 0])
        self.assertEqual(row, [2, 4, 0, 0])
        self.assertEqual(score, 0)

    def test_slide_left_double_merge(self):
        """Sliding [2, 2, 4, 4] left produces [4, 8, 0, 0]."""
        slide = self.ns["slide_row_left"]
        row, score, _ = slide([2, 2, 4, 4])
        self.assertEqual(row, [4, 8, 0, 0])
        self.assertEqual(score, 12)

    def test_slide_left_returns_merged_positions(self):
        """slide_row_left must return positions of merged tiles."""
        slide = self.ns["slide_row_left"]
        _, _, merged = slide([2, 2, 0, 0])
        self.assertIn(0, merged)

    def test_move_right(self):
        """Move right merges tiles toward the right edge."""
        move_fn = self.ns["move"]
        board = [[0, 0, 2, 2],
                 [0, 0, 0, 0],
                 [0, 0, 0, 0],
                 [0, 0, 0, 0]]
        new_b, score, changed, _ = move_fn(board, "right")
        self.assertTrue(changed)
        self.assertEqual(new_b[0][3], 4)
        self.assertEqual(score, 4)

    def test_move_up(self):
        """Move up merges tiles upward."""
        move_fn = self.ns["move"]
        board = [[2, 0, 0, 0],
                 [2, 0, 0, 0],
                 [0, 0, 0, 0],
                 [0, 0, 0, 0]]
        new_b, score, changed, _ = move_fn(board, "up")
        self.assertTrue(changed)
        self.assertEqual(new_b[0][0], 4)
        self.assertEqual(score, 4)

    def test_move_down(self):
        """Move down merges tiles downward."""
        move_fn = self.ns["move"]
        board = [[0, 0, 0, 0],
                 [0, 0, 0, 0],
                 [2, 0, 0, 0],
                 [2, 0, 0, 0]]
        new_b, score, changed, _ = move_fn(board, "down")
        self.assertTrue(changed)
        self.assertEqual(new_b[3][0], 4)
        self.assertEqual(score, 4)

    def test_move_no_change(self):
        """Move returns changed=False when nothing can slide."""
        move_fn = self.ns["move"]
        board = [[2, 0, 0, 0],
                 [0, 0, 0, 0],
                 [0, 0, 0, 0],
                 [0, 0, 0, 0]]
        _, _, changed, _ = move_fn(board, "left")
        self.assertFalse(changed)


# =============================================================================
# 5. WIN AND GAME OVER DETECTION
# =============================================================================

class TestWinGameOver(unittest.TestCase):
    """Tests for win detection and game over detection."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_has_won_detects_2048(self):
        """has_won() must return True when 2048 tile exists."""
        has_won = self.ns["has_won"]
        board = [[0] * 4 for _ in range(4)]
        board[0][0] = 2048
        self.assertTrue(has_won(board))

    def test_has_won_false_below_2048(self):
        """has_won() must return False when no tile >= 2048."""
        has_won = self.ns["has_won"]
        board = [[0] * 4 for _ in range(4)]
        board[0][0] = 1024
        self.assertFalse(has_won(board))

    def test_has_moves_true_with_empty(self):
        """has_moves() must return True when empty cells exist."""
        has_moves = self.ns["has_moves"]
        board = [[0] * 4 for _ in range(4)]
        self.assertTrue(has_moves(board))

    def test_has_moves_true_with_adjacent_match(self):
        """has_moves() must return True when adjacent tiles can merge."""
        has_moves = self.ns["has_moves"]
        board = [[2, 4, 2, 4],
                 [4, 2, 4, 2],
                 [2, 4, 2, 4],
                 [4, 2, 4, 2]]
        # No adjacent match and no empty => False
        self.assertFalse(has_moves(board))
        # Set adjacent match
        board[0][0] = 4  # now board[0][0]==4 == board[0][1]==4
        self.assertTrue(has_moves(board))

    def test_game_over_no_moves(self):
        """has_moves() must return False when board is full with no merges."""
        has_moves = self.ns["has_moves"]
        board = [[2, 4, 2, 4],
                 [4, 2, 4, 2],
                 [2, 4, 2, 4],
                 [4, 2, 4, 2]]
        self.assertFalse(has_moves(board))


# =============================================================================
# 6. SCORE TRACKING
# =============================================================================

class TestScoreTracking(unittest.TestCase):
    """Tests for score tracking functionality."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.ns = import_module()

    def test_has_score_tracking(self):
        """Must track score during gameplay."""
        self.assertIn("score", self.source.lower())

    def test_has_best_score(self):
        """Must track best/high score."""
        self.assertIn("best_score", self.source)

    def test_load_best_score_function(self):
        """Must have load_best_score function."""
        self.assertIn("load_best_score", self.ns)

    def test_save_best_score_function(self):
        """Must have save_best_score function."""
        self.assertIn("save_best_score", self.ns)


# =============================================================================
# 7. CURSES INTEGRATION
# =============================================================================

class TestCursesIntegration(unittest.TestCase):
    """Tests for proper curses integration."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_uses_init_pair(self):
        """Must use curses.init_pair() for color setup."""
        self.assertIn("init_pair", self.source)

    def test_uses_color_pair(self):
        """Must use curses.color_pair() for rendering."""
        self.assertIn("color_pair", self.source)

    def test_uses_start_color(self):
        """Must call curses.start_color()."""
        self.assertIn("start_color", self.source)

    def test_hides_cursor(self):
        """Must hide the cursor with curs_set(0)."""
        self.assertIn("curs_set", self.source)

    def test_has_multiple_color_pairs(self):
        """Must define multiple color pairs for distinct tile values."""
        count = self.source.count("init_pair")
        self.assertGreaterEqual(count, 10,
                                "Fewer than 10 color pairs defined")


# =============================================================================
# 8. VISUAL DISPLAY
# =============================================================================

class TestVisualDisplay(unittest.TestCase):
    """Tests for visual elements: glyphs, box-drawing, color."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.tree = parse_ast()
        cls.strings = find_all_string_literals(cls.tree)

    def test_has_box_drawing_borders(self):
        """Must use box-drawing characters for board borders."""
        box_chars = set("╔╗╚╝═║╦╩╠╣╬")
        all_chars = "".join(self.strings)
        found = [ch for ch in box_chars if ch in all_chars]
        self.assertGreater(len(found), 5,
                           "Insufficient box-drawing characters found")

    def test_has_nerd_font_glyphs(self):
        """Must use Unicode/nerd font glyphs (not plain ASCII)."""
        all_chars = "".join(self.strings)
        unicode_glyphs = {"★", "◆", "●", "✦", "▲", "▼", "█"}
        found = [g for g in unicode_glyphs if g in all_chars]
        self.assertGreater(len(found), 3,
                           "Insufficient Unicode/nerd font glyphs")

    def test_has_game_title(self):
        """Must display a game title."""
        source_lower = self.source.lower()
        self.assertTrue(
            "2048" in source_lower or "2 0 4 8" in source_lower,
            "No game title found")

    def test_has_game_over_message(self):
        """Must have a game over display."""
        source_lower = self.source.lower()
        self.assertTrue(
            "game over" in source_lower or "no moves" in source_lower,
            "No game over message found")

    def test_color_constants_defined(self):
        """Must define named color constants."""
        source = self.source
        color_consts = [line for line in source.split("\n")
                        if line.strip().startswith("COLOR_")]
        self.assertGreater(len(color_consts), 8,
                           "Too few color constants defined")


# =============================================================================
# 9. INPUT HANDLING
# =============================================================================

class TestInputHandling(unittest.TestCase):
    """Tests that the game handles expected keyboard input."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_handles_arrow_keys(self):
        """Must handle arrow key input."""
        self.assertIn("KEY_UP", self.source)
        self.assertIn("KEY_DOWN", self.source)
        self.assertIn("KEY_LEFT", self.source)
        self.assertIn("KEY_RIGHT", self.source)

    def test_handles_wasd(self):
        """Must handle WASD keys."""
        self.assertIn("ord('w')", self.source)
        self.assertIn("ord('a')", self.source)
        self.assertIn("ord('s')", self.source)
        self.assertIn("ord('d')", self.source)

    def test_handles_quit(self):
        """Must handle Q key to quit."""
        self.assertIn("ord('q')", self.source)


# =============================================================================
# 10. ANIMATION
# =============================================================================

class TestAnimation(unittest.TestCase):
    """Tests for merge animation support."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.functions = find_all_functions(parse_ast())

    def test_has_animate_merge_function(self):
        """Must have an animate_merge function."""
        self.assertIn("animate_merge", self.functions,
                       "No animate_merge function found")

    def test_uses_reverse_or_bold_for_animation(self):
        """Animation must use A_REVERSE or A_BOLD for highlight effect."""
        self.assertTrue(
            "A_REVERSE" in self.source or "A_BOLD" in self.source,
            "No highlight attribute used for merge animation")

    def test_uses_time_sleep_for_frames(self):
        """Animation must use time.sleep() for frame timing."""
        self.assertIn("time.sleep", self.source)


if __name__ == "__main__":
    unittest.main()
