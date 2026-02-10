#!/usr/bin/env python3
"""
Test suite for minesweeper.py — Terminal Minesweeper Game
Tests the "known good" benchmark: structure, logic, and behavior.
These tests run WITHOUT a terminal (no curses rendering).
"""

import ast
import os
import stat
import unittest

# Path to the script under test
MINESWEEPER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "minesweeper.py")


def load_source():
    """Load minesweeper.py source code as a string."""
    with open(MINESWEEPER_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_ast():
    """Parse minesweeper.py into an AST tree."""
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
    """Import minesweeper.py as a module (without running main).

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

    code = compile(tree, MINESWEEPER_PATH, "exec")
    namespace = {"__file__": MINESWEEPER_PATH, "__name__": "minesweeper"}
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
    """Tests that minesweeper.py has the right file-level properties."""

    def test_file_exists(self):
        """minesweeper.py must exist."""
        self.assertTrue(os.path.isfile(MINESWEEPER_PATH),
                        "minesweeper.py not found")

    def test_file_is_executable(self):
        """minesweeper.py must have the executable bit set."""
        mode = os.stat(MINESWEEPER_PATH).st_mode
        self.assertTrue(mode & stat.S_IXUSR,
                        "minesweeper.py is not executable")

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
        allowed = {"curses", "random", "os", "sys"}
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

    def test_has_difficulties(self):
        """Must have a DIFFICULTIES dict."""
        self.assertIn("DIFFICULTIES", self.names,
                       "Missing DIFFICULTIES dict")

    def test_has_game_loop(self):
        """Must have a game loop (while True)."""
        tree = parse_ast()
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value:
                    return
        self.fail("No game loop (while True) found")


# =============================================================================
# 3. BOARD INITIALIZATION
# =============================================================================

class TestBoardInit(unittest.TestCase):
    """Tests for board creation and setup."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_create_board_dimensions(self):
        """create_board() returns correct dimensions."""
        create_board = self.ns["create_board"]
        grid = create_board(9, 9)
        self.assertEqual(len(grid), 9)
        self.assertEqual(len(grid[0]), 9)

    def test_create_board_all_zeros(self):
        """create_board() starts with all zeros."""
        create_board = self.ns["create_board"]
        grid = create_board(5, 5)
        for r in range(5):
            for c in range(5):
                self.assertEqual(grid[r][c], 0)

    def test_create_board_large(self):
        """create_board() works for larger boards."""
        create_board = self.ns["create_board"]
        grid = create_board(16, 30)
        self.assertEqual(len(grid), 16)
        self.assertEqual(len(grid[0]), 30)


# =============================================================================
# 4. MINE PLACEMENT
# =============================================================================

class TestMinePlacement(unittest.TestCase):
    """Tests for mine placement logic."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_correct_mine_count(self):
        """place_mines() places exactly the requested number of mines."""
        create_board = self.ns["create_board"]
        place_mines = self.ns["place_mines"]
        grid = create_board(9, 9)
        place_mines(grid, 9, 9, 10)
        mine_count = sum(1 for r in range(9) for c in range(9) if grid[r][c] == -1)
        self.assertEqual(mine_count, 10)

    def test_safe_zone_respected(self):
        """place_mines() avoids the safe cell and its neighbors."""
        create_board = self.ns["create_board"]
        place_mines = self.ns["place_mines"]
        import random
        random.seed(42)
        grid = create_board(9, 9)
        safe_r, safe_c = 4, 4
        place_mines(grid, 9, 9, 10, safe_r, safe_c)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = safe_r + dr, safe_c + dc
                self.assertNotEqual(grid[nr][nc], -1,
                                    f"Mine at safe zone ({nr},{nc})")

    def test_mines_are_negative_one(self):
        """Mines are represented as -1 in the grid."""
        create_board = self.ns["create_board"]
        place_mines = self.ns["place_mines"]
        grid = create_board(5, 5)
        positions = place_mines(grid, 5, 5, 3)
        for r, c in positions:
            self.assertEqual(grid[r][c], -1)


# =============================================================================
# 5. NEIGHBOR COUNT CALCULATION
# =============================================================================

class TestNeighborCounts(unittest.TestCase):
    """Tests for mine neighbor counting."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_counts_adjacent_mines(self):
        """calc_counts() correctly counts neighboring mines."""
        create_board = self.ns["create_board"]
        calc_counts = self.ns["calc_counts"]
        grid = create_board(3, 3)
        grid[0][0] = -1  # mine at top-left
        calc_counts(grid, 3, 3)
        # Cell (1,1) should see 1 mine
        self.assertEqual(grid[1][1], 1)
        # Cell (0,1) should see 1 mine
        self.assertEqual(grid[0][1], 1)
        # Cell (2,2) should see 0 mines
        self.assertEqual(grid[2][2], 0)

    def test_corner_mine_counts(self):
        """Cells in corners count mines correctly."""
        create_board = self.ns["create_board"]
        calc_counts = self.ns["calc_counts"]
        grid = create_board(3, 3)
        grid[0][0] = -1
        grid[0][2] = -1
        grid[2][0] = -1
        grid[2][2] = -1
        calc_counts(grid, 3, 3)
        # Center should see 4 mines
        self.assertEqual(grid[1][1], 4)
        # Edge cells should see 2 mines each
        self.assertEqual(grid[0][1], 2)
        self.assertEqual(grid[1][0], 2)

    def test_mine_cells_stay_negative(self):
        """calc_counts() does not overwrite mine cells."""
        create_board = self.ns["create_board"]
        calc_counts = self.ns["calc_counts"]
        grid = create_board(3, 3)
        grid[1][1] = -1
        calc_counts(grid, 3, 3)
        self.assertEqual(grid[1][1], -1)


# =============================================================================
# 6. CELL REVEAL AND FLOOD FILL
# =============================================================================

class TestRevealAndFloodFill(unittest.TestCase):
    """Tests for cell reveal and flood fill logic."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def _make_simple_board(self):
        """Create a 5x5 board with one mine at (0,0)."""
        create_board = self.ns["create_board"]
        calc_counts = self.ns["calc_counts"]
        grid = create_board(5, 5)
        grid[0][0] = -1
        calc_counts(grid, 5, 5)
        revealed = [[False] * 5 for _ in range(5)]
        flagged = [[False] * 5 for _ in range(5)]
        return grid, revealed, flagged

    def test_reveal_mine_returns_true(self):
        """reveal_cell() returns True when hitting a mine."""
        reveal_cell = self.ns["reveal_cell"]
        grid, revealed, flagged = self._make_simple_board()
        hit = reveal_cell(grid, revealed, flagged, 5, 5, 0, 0)
        self.assertTrue(hit)

    def test_reveal_safe_returns_false(self):
        """reveal_cell() returns False for safe cells."""
        reveal_cell = self.ns["reveal_cell"]
        grid, revealed, flagged = self._make_simple_board()
        hit = reveal_cell(grid, revealed, flagged, 5, 5, 4, 4)
        self.assertFalse(hit)

    def test_flood_fill_reveals_empty_region(self):
        """Flood fill reveals connected empty (0) cells."""
        flood_fill = self.ns["flood_fill"]
        grid, revealed, flagged = self._make_simple_board()
        # (4,4) has count=0, so flood fill should spread
        flood_fill(grid, revealed, flagged, 5, 5, 4, 4)
        # Check that (4,4) is revealed
        self.assertTrue(revealed[4][4])
        # Multiple cells should be revealed by flood fill
        revealed_count = sum(revealed[r][c] for r in range(5) for c in range(5))
        self.assertGreater(revealed_count, 1)

    def test_flood_fill_stops_at_numbers(self):
        """Flood fill stops at numbered cells (reveals them but doesn't continue)."""
        flood_fill = self.ns["flood_fill"]
        grid, revealed, flagged = self._make_simple_board()
        flood_fill(grid, revealed, flagged, 5, 5, 4, 4)
        # Mine cell should NOT be revealed by flood fill
        self.assertFalse(revealed[0][0])

    def test_reveal_flagged_cell_blocked(self):
        """Cannot reveal a flagged cell."""
        reveal_cell = self.ns["reveal_cell"]
        grid, revealed, flagged = self._make_simple_board()
        flagged[2][2] = True
        hit = reveal_cell(grid, revealed, flagged, 5, 5, 2, 2)
        self.assertFalse(hit)
        self.assertFalse(revealed[2][2])

    def test_reveal_already_revealed_noop(self):
        """Revealing an already revealed cell is a no-op."""
        reveal_cell = self.ns["reveal_cell"]
        grid, revealed, flagged = self._make_simple_board()
        reveal_cell(grid, revealed, flagged, 5, 5, 2, 2)
        self.assertTrue(revealed[2][2])
        # Reveal again should not error
        hit = reveal_cell(grid, revealed, flagged, 5, 5, 2, 2)
        self.assertFalse(hit)


# =============================================================================
# 7. FLAG TOGGLING
# =============================================================================

class TestFlagToggling(unittest.TestCase):
    """Tests for flag toggling."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_toggle_flag_on(self):
        """toggle_flag() sets flag on unrevealed cell."""
        toggle_flag = self.ns["toggle_flag"]
        revealed = [[False] * 5 for _ in range(5)]
        flagged = [[False] * 5 for _ in range(5)]
        toggle_flag(revealed, flagged, 2, 2)
        self.assertTrue(flagged[2][2])

    def test_toggle_flag_off(self):
        """toggle_flag() removes flag when toggled again."""
        toggle_flag = self.ns["toggle_flag"]
        revealed = [[False] * 5 for _ in range(5)]
        flagged = [[False] * 5 for _ in range(5)]
        toggle_flag(revealed, flagged, 2, 2)
        toggle_flag(revealed, flagged, 2, 2)
        self.assertFalse(flagged[2][2])

    def test_cannot_flag_revealed_cell(self):
        """toggle_flag() does nothing on a revealed cell."""
        toggle_flag = self.ns["toggle_flag"]
        revealed = [[False] * 5 for _ in range(5)]
        flagged = [[False] * 5 for _ in range(5)]
        revealed[2][2] = True
        toggle_flag(revealed, flagged, 2, 2)
        self.assertFalse(flagged[2][2])

    def test_count_flags(self):
        """count_flags() returns correct flag count."""
        count_flags = self.ns["count_flags"]
        flagged = [[False] * 5 for _ in range(5)]
        flagged[0][0] = True
        flagged[1][1] = True
        flagged[2][2] = True
        self.assertEqual(count_flags(flagged, 5, 5), 3)


# =============================================================================
# 8. WIN AND LOSS DETECTION
# =============================================================================

class TestWinLossDetection(unittest.TestCase):
    """Tests for win and loss detection."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_win_all_safe_revealed(self):
        """check_win() returns True when all non-mine cells are revealed."""
        check_win = self.ns["check_win"]
        create_board = self.ns["create_board"]
        grid = create_board(3, 3)
        grid[0][0] = -1
        revealed = [[True] * 3 for _ in range(3)]
        revealed[0][0] = False  # mine not revealed
        self.assertTrue(check_win(grid, revealed, 3, 3))

    def test_no_win_with_hidden_safe(self):
        """check_win() returns False when safe cells remain hidden."""
        check_win = self.ns["check_win"]
        create_board = self.ns["create_board"]
        grid = create_board(3, 3)
        grid[0][0] = -1
        revealed = [[False] * 3 for _ in range(3)]
        self.assertFalse(check_win(grid, revealed, 3, 3))

    def test_loss_on_mine_reveal(self):
        """Revealing a mine triggers game over (reveal_cell returns True)."""
        reveal_cell = self.ns["reveal_cell"]
        create_board = self.ns["create_board"]
        grid = create_board(3, 3)
        grid[1][1] = -1
        revealed = [[False] * 3 for _ in range(3)]
        flagged = [[False] * 3 for _ in range(3)]
        hit = reveal_cell(grid, revealed, flagged, 3, 3, 1, 1)
        self.assertTrue(hit)

    def test_reveal_all_mines(self):
        """reveal_all_mines() reveals every mine cell."""
        reveal_all_mines = self.ns["reveal_all_mines"]
        create_board = self.ns["create_board"]
        grid = create_board(5, 5)
        grid[0][0] = -1
        grid[2][3] = -1
        grid[4][4] = -1
        revealed = [[False] * 5 for _ in range(5)]
        reveal_all_mines(grid, revealed, 5, 5)
        self.assertTrue(revealed[0][0])
        self.assertTrue(revealed[2][3])
        self.assertTrue(revealed[4][4])
        # Non-mine cells remain unrevealed
        self.assertFalse(revealed[1][1])


# =============================================================================
# 9. CELL DISPLAY
# =============================================================================

class TestCellDisplay(unittest.TestCase):
    """Tests for cell display rendering."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_hidden_cell(self):
        """Unrevealed cell shows hidden glyph."""
        get_cell_display = self.ns["get_cell_display"]
        grid = [[0]]
        revealed = [[False]]
        flagged = [[False]]
        text, color, bold = get_cell_display(grid, revealed, flagged, 0, 0)
        self.assertEqual(text, self.ns["GLYPH_HIDDEN"])

    def test_flagged_cell(self):
        """Flagged cell shows flag glyph."""
        get_cell_display = self.ns["get_cell_display"]
        grid = [[0]]
        revealed = [[False]]
        flagged = [[True]]
        text, color, bold = get_cell_display(grid, revealed, flagged, 0, 0)
        self.assertEqual(text, self.ns["GLYPH_FLAG"])

    def test_mine_cell(self):
        """Revealed mine shows mine glyph."""
        get_cell_display = self.ns["get_cell_display"]
        grid = [[-1]]
        revealed = [[True]]
        flagged = [[False]]
        text, color, bold = get_cell_display(grid, revealed, flagged, 0, 0)
        self.assertEqual(text, self.ns["GLYPH_MINE"])

    def test_empty_cell(self):
        """Revealed empty cell shows empty glyph."""
        get_cell_display = self.ns["get_cell_display"]
        grid = [[0]]
        revealed = [[True]]
        flagged = [[False]]
        text, color, bold = get_cell_display(grid, revealed, flagged, 0, 0)
        self.assertEqual(text, self.ns["GLYPH_EMPTY"])

    def test_numbered_cell(self):
        """Revealed numbered cell shows the number."""
        get_cell_display = self.ns["get_cell_display"]
        grid = [[3]]
        revealed = [[True]]
        flagged = [[False]]
        text, color, bold = get_cell_display(grid, revealed, flagged, 0, 0)
        self.assertEqual(text, "3")


# =============================================================================
# 10. COLOR INITIALIZATION
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

    def test_has_color_pair(self):
        """Must use curses.color_pair() for rendering."""
        self.assertIn("color_pair", self.source)

    def test_has_blue_for_ones(self):
        """Number 1 should use blue."""
        self.assertIn("COLOR_BLUE", self.source)

    def test_has_green_for_twos(self):
        """Number 2 should use green."""
        self.assertIn("COLOR_GREEN", self.source)

    def test_has_red_for_threes(self):
        """Number 3 should use red."""
        self.assertIn("COLOR_RED", self.source)

    def test_has_cyan(self):
        """Must use cyan color."""
        self.assertIn("COLOR_CYAN", self.source)

    def test_has_magenta(self):
        """Must use magenta color."""
        self.assertIn("COLOR_MAGENTA", self.source)

    def test_has_yellow_for_flags(self):
        """Flags should use yellow."""
        self.assertIn("COLOR_YELLOW", self.source)

    def test_has_init_colors_function(self):
        """Must have an init_colors function."""
        functions = find_all_functions(parse_ast())
        self.assertIn("init_colors", functions)

    def test_hides_cursor(self):
        """Must hide the cursor with curs_set(0)."""
        self.assertIn("curs_set", self.source)

    def test_number_specific_colors(self):
        """Must define color pairs for each minesweeper number 1-8."""
        for n in range(1, 9):
            self.assertIn(f"COLOR_NUM{n}", self.source,
                          f"Missing color for number {n}")


# =============================================================================
# 11. BOX-DRAWING AND VISUAL DISPLAY
# =============================================================================

class TestVisualDisplay(unittest.TestCase):
    """Tests for visual elements: box-drawing, glyphs, layout."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.tree = parse_ast()
        cls.strings = find_all_string_literals(cls.tree)

    def test_has_box_drawing_borders(self):
        """Must use box-drawing characters for borders."""
        box_chars = set("╔╗╚╝═║╦╩╠╣╬")
        all_chars = "".join(self.strings)
        found = [ch for ch in box_chars if ch in all_chars]
        self.assertGreaterEqual(len(found), 6,
                                f"Insufficient box-drawing characters: {found}")

    def test_has_flag_glyph(self):
        """Must have a flag glyph symbol."""
        all_chars = "".join(self.strings)
        flag_glyphs = {"⚑", "🚩", "⛳"}
        found = [g for g in flag_glyphs if g in all_chars]
        self.assertGreater(len(found), 0, "No flag glyph found")

    def test_has_mine_glyph(self):
        """Must have a mine glyph symbol."""
        all_chars = "".join(self.strings)
        mine_glyphs = {"✱", "💣", "☀", "✸"}
        found = [g for g in mine_glyphs if g in all_chars]
        self.assertGreater(len(found), 0, "No mine glyph found")

    def test_has_hidden_glyph(self):
        """Must have an unrevealed square glyph."""
        all_chars = "".join(self.strings)
        self.assertIn("■", all_chars, "No hidden square glyph found")

    def test_has_empty_glyph(self):
        """Must have an empty cell glyph."""
        all_chars = "".join(self.strings)
        empty_glyphs = {"·", "∙", "•"}
        found = [g for g in empty_glyphs if g in all_chars]
        self.assertGreater(len(found), 0, "No empty cell glyph found")

    def test_has_star_decoration(self):
        """Must use star glyph for decoration."""
        all_chars = "".join(self.strings)
        self.assertIn("★", all_chars, "No star decoration glyph found")

    def test_has_draw_board_function(self):
        """Must have a draw_board function."""
        functions = find_all_functions(self.tree)
        self.assertIn("draw_board", functions)

    def test_has_draw_title_function(self):
        """Must have a draw_title function."""
        functions = find_all_functions(self.tree)
        self.assertIn("draw_title", functions)

    def test_has_draw_status_function(self):
        """Must have a draw_status function."""
        functions = find_all_functions(self.tree)
        self.assertIn("draw_status", functions)

    def test_consistent_cell_width(self):
        """Must define CELL_W for consistent cell width alignment."""
        self.assertIn("CELL_W", self.source,
                       "Missing CELL_W constant for alignment")

    def test_game_title_contains_minesweeper(self):
        """Must display MINESWEEPER in the title."""
        source_upper = self.source.upper()
        self.assertIn("MINESWEEPER", source_upper)


# =============================================================================
# 12. INPUT HANDLING
# =============================================================================

class TestInputHandling(unittest.TestCase):
    """Tests that the game handles expected keyboard input."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_handles_arrow_keys(self):
        """Must handle arrow key navigation."""
        self.assertIn("KEY_UP", self.source)
        self.assertIn("KEY_DOWN", self.source)
        self.assertIn("KEY_LEFT", self.source)
        self.assertIn("KEY_RIGHT", self.source)

    def test_handles_space_bar(self):
        """Must handle space bar for reveal."""
        self.assertIn("ord(' ')", self.source)

    def test_handles_flag_key(self):
        """Must handle 'f' key for flagging."""
        self.assertIn("ord('f')", self.source)

    def test_handles_quit_key(self):
        """Must handle 'q' key for quit."""
        self.assertIn("ord('q')", self.source)

    def test_handles_new_game_key(self):
        """Must handle 'n' key for new game."""
        self.assertIn("ord('n')", self.source)


if __name__ == "__main__":
    unittest.main()
