#!/usr/bin/env python3
"""
Test suite for battleship.py — Terminal Battleship Game
Tests the "known good" benchmark: structure, logic, and behavior.
These tests run WITHOUT a terminal (no curses rendering).
"""

import ast
import os
import stat
import sys
import unittest

# Path to the script under test
BATTLESHIP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "battleship.py")


def load_source():
    """Load battleship.py source code as a string."""
    with open(BATTLESHIP_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_ast():
    """Parse battleship.py into an AST tree."""
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
    """Import battleship.py as a module (without running main).

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

    code = compile(tree, BATTLESHIP_PATH, "exec")
    namespace = {"__file__": BATTLESHIP_PATH, "__name__": "battleship"}
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


def find_all_number_literals(tree):
    """Find all number literals in the AST."""
    numbers = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            numbers.append(node.value)
    return numbers


# =============================================================================
# 1. FILE STRUCTURE TESTS
# =============================================================================

class TestFileStructure(unittest.TestCase):
    """Tests that battleship.py has the right file-level properties."""

    def test_file_exists(self):
        """battleship.py must exist."""
        self.assertTrue(os.path.isfile(BATTLESHIP_PATH),
                        "battleship.py not found")

    def test_file_is_executable(self):
        """battleship.py must have the executable bit set."""
        mode = os.stat(BATTLESHIP_PATH).st_mode
        self.assertTrue(mode & stat.S_IXUSR,
                        "battleship.py is not executable")

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

    def test_has_grid_creation(self):
        """Must have grid/board creation logic."""
        self.assertIn("make_grid", self.functions,
                       "Missing make_grid function")

    def test_has_ship_placement(self):
        """Must have ship placement logic."""
        placement_funcs = [n for n in self.functions
                           if "place" in n.lower()]
        self.assertGreater(len(placement_funcs), 0,
                           "No ship placement function found")

    def test_has_hit_miss_detection(self):
        """Must have hit/miss detection logic."""
        source_lower = self.source.lower()
        self.assertTrue(
            "hit" in source_lower and "miss" in source_lower,
            "Missing hit/miss detection")

    def test_has_ai_logic(self):
        """Must have AI/computer opponent logic."""
        ai_funcs = [n for n in self.functions
                    if "ai" in n.lower()]
        self.assertGreater(len(ai_funcs), 0,
                           "No AI opponent function found")

    def test_has_game_loop(self):
        """Must have a game loop (while True)."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value:
                    return
        self.fail("No game loop (while True) found")


# =============================================================================
# 3. BOARD AND GRID LOGIC
# =============================================================================

class TestBoardLogic(unittest.TestCase):
    """Tests for board/grid data structures and logic."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_grid_size_is_10(self):
        """Grid must be 10x10."""
        self.assertEqual(self.ns.get("GRID_SIZE", None), 10)

    def test_make_grid_returns_2d(self):
        """make_grid() must return a 2D list."""
        make_grid = self.ns.get("make_grid")
        self.assertIsNotNone(make_grid)
        grid = make_grid()
        self.assertEqual(len(grid), 10)
        self.assertEqual(len(grid[0]), 10)

    def test_column_labels(self):
        """Must have column labels A-J."""
        cols = self.ns.get("COLS", "")
        self.assertEqual(cols, "ABCDEFGHIJ")

    def test_cell_states_defined(self):
        """Must define cell states for WATER, SHIP, HIT, MISS."""
        for state in ("WATER", "SHIP", "HIT", "MISS"):
            self.assertIn(state, self.ns,
                          f"Missing cell state: {state}")


# =============================================================================
# 4. SHIP PLACEMENT
# =============================================================================

class TestShipPlacement(unittest.TestCase):
    """Tests for ship placement mechanics."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_five_ships_defined(self):
        """Must define 5 ships."""
        ships = self.ns.get("SHIPS")
        self.assertIsNotNone(ships)
        self.assertEqual(len(ships), 5)

    def test_ship_sizes(self):
        """Ships must have correct sizes: 5, 4, 3, 3, 2."""
        ships = self.ns.get("SHIPS")
        sizes = sorted(ships.values(), reverse=True)
        self.assertEqual(sizes, [5, 4, 3, 3, 2])

    def test_can_place_validates_bounds(self):
        """can_place() must reject out-of-bounds placements."""
        can_place = self.ns["can_place"]
        make_grid = self.ns["make_grid"]
        grid = make_grid()
        # Ship of size 5 starting at col 8 horizontally should fail
        self.assertFalse(can_place(grid, 0, 8, 5, True))
        # Ship of size 5 starting at row 8 vertically should fail
        self.assertFalse(can_place(grid, 8, 0, 5, False))

    def test_can_place_rejects_overlap(self):
        """can_place() must reject overlapping ships."""
        can_place = self.ns["can_place"]
        place_ship = self.ns["place_ship"]
        make_grid = self.ns["make_grid"]
        grid = make_grid()
        place_ship(grid, 0, 0, 3, True)  # place horizontal at (0,0)
        # Trying to place vertically at (0,1) should overlap
        self.assertFalse(can_place(grid, 0, 1, 3, False))

    def test_ai_place_ships_fills_all(self):
        """ai_place_ships() must place all 5 ships."""
        ai_place = self.ns["ai_place_ships"]
        make_grid = self.ns["make_grid"]
        grid = make_grid()
        coords = ai_place(grid)
        self.assertEqual(len(coords), 5)
        # Total cells = 5+4+3+3+2 = 17
        total = sum(len(c) for c in coords.values())
        self.assertEqual(total, 17)


# =============================================================================
# 5. HIT / MISS / SUNK DETECTION
# =============================================================================

class TestHitMissDetection(unittest.TestCase):
    """Tests for hit, miss, and sunk detection."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_all_sunk_detects_victory(self):
        """all_sunk() must return True when all ship cells are HIT."""
        all_sunk = self.ns["all_sunk"]
        HIT = self.ns["HIT"]
        grid = [[HIT] * 10 for _ in range(10)]
        coords = {"TestShip": [(0, 0), (0, 1), (0, 2)]}
        self.assertTrue(all_sunk(coords, grid))

    def test_all_sunk_false_when_alive(self):
        """all_sunk() must return False when ships still afloat."""
        all_sunk = self.ns["all_sunk"]
        SHIP = self.ns["SHIP"]
        WATER = self.ns["WATER"]
        grid = [[WATER] * 10 for _ in range(10)]
        grid[0][0] = SHIP
        coords = {"TestShip": [(0, 0), (0, 1)]}
        self.assertFalse(all_sunk(coords, grid))

    def test_check_sunk_identifies_ship(self):
        """check_sunk() must return ship name when all coords are HIT."""
        check_sunk = self.ns["check_sunk"]
        HIT = self.ns["HIT"]
        grid = [[HIT] * 10 for _ in range(10)]
        coords = {"Destroyer": [(0, 0), (0, 1)]}
        result = check_sunk(coords, grid)
        self.assertEqual(result, "Destroyer")


# =============================================================================
# 6. AI OPPONENT
# =============================================================================

class TestAIOpponent(unittest.TestCase):
    """Tests for AI targeting logic."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_ai_fire_exists(self):
        """Must have an AI fire function."""
        funcs = find_all_functions(parse_ast())
        ai_funcs = [n for n in funcs if "ai" in n.lower() and "fire" in n.lower()]
        self.assertGreater(len(ai_funcs), 0,
                           "No AI fire function found")

    def test_ai_uses_hunt_target(self):
        """AI must use hunt/target strategy (maintains target queue)."""
        source = load_source()
        self.assertIn("targets", source.lower(),
                       "AI should use a target queue")

    def test_ai_fire_returns_result(self):
        """ai_fire() must mark cells as HIT or MISS."""
        ai_fire = self.ns["ai_fire"]
        make_grid = self.ns["make_grid"]
        SHIP = self.ns["SHIP"]
        HIT = self.ns["HIT"]
        MISS = self.ns["MISS"]

        grid = make_grid()
        grid[0][0] = SHIP
        coords = {"TestShip": [(0, 0)]}
        state = {"targets": [(0, 0)]}

        row, col, hit = ai_fire(grid, coords, state)
        self.assertEqual(row, 0)
        self.assertEqual(col, 0)
        self.assertTrue(hit)
        self.assertEqual(grid[0][0], HIT)


# =============================================================================
# 7. INPUT HANDLING
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

    def test_handles_space_bar(self):
        """Must handle space bar for firing."""
        self.assertIn("ord(' ')", self.source)

    def test_handles_quit(self):
        """Must handle Q key to quit."""
        self.assertIn("ord('q')", self.source.lower())


# =============================================================================
# 8. CURSES INTEGRATION
# =============================================================================

class TestCursesIntegration(unittest.TestCase):
    """Tests for proper curses integration."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.tree = parse_ast()

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


# =============================================================================
# 9. VISUAL DISPLAY
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
        box_chars = set("╔╗╚╝═║┌┐└┘─│┬┴├┤┼╠╣╦╩╬")
        all_chars = "".join(self.strings)
        found = [ch for ch in box_chars if ch in all_chars]
        self.assertGreater(len(found), 3,
                           "Insufficient box-drawing characters found")

    def test_has_nerd_font_glyphs(self):
        """Must use Unicode/nerd font glyphs (not plain ASCII)."""
        all_chars = "".join(self.strings)
        # Check for Unicode symbols beyond basic ASCII
        unicode_glyphs = {"≈", "█", "✖", "•", "◆", "●"}
        found = [g for g in unicode_glyphs if g in all_chars]
        self.assertGreater(len(found), 2,
                           "Insufficient Unicode/nerd font glyphs")

    def test_has_game_title(self):
        """Must display a game title."""
        source_lower = self.source.lower()
        self.assertTrue(
            "battleship" in source_lower or "b a t t l e" in source_lower,
            "No game title found")

    def test_has_game_over_screen(self):
        """Must have a game over display."""
        source_lower = self.source.lower()
        self.assertTrue(
            "game_over" in source_lower or "victory" in source_lower
            or "defeat" in source_lower,
            "No game over screen found")

    def test_has_ship_status_display(self):
        """Must show ship sunk/alive status."""
        funcs = find_all_functions(self.tree)
        status_funcs = [n for n in funcs
                        if "status" in n.lower() or "sunk" in n.lower()]
        self.assertGreater(len(status_funcs), 0,
                           "No ship status display function found")

    def test_color_constants_defined(self):
        """Must define named color constants."""
        source = self.source
        color_consts = [line for line in source.split("\n")
                        if line.strip().startswith("COLOR_")]
        self.assertGreater(len(color_consts), 4,
                           "Too few color constants defined")


# =============================================================================
# 10. GAME LOGIC FUNCTIONS
# =============================================================================

class TestGameLogicFunctions(unittest.TestCase):
    """Tests for core game logic functions."""

    @classmethod
    def setUpClass(cls):
        cls.tree = parse_ast()
        cls.source = load_source()
        cls.functions = find_all_functions(cls.tree)

    def test_has_draw_board_function(self):
        """Must have a board drawing function."""
        draw_funcs = [n for n in self.functions if "draw" in n.lower()
                      and "board" in n.lower()]
        self.assertGreater(len(draw_funcs), 0,
                           "No draw_board function found")

    def test_has_placement_phase(self):
        """Must have interactive ship placement phase."""
        placement_funcs = [n for n in self.functions
                           if "placement" in n.lower() or "place_ship" in n.lower()]
        self.assertGreater(len(placement_funcs), 0,
                           "No placement phase function found")

    def test_uses_random(self):
        """Must use random module for AI."""
        self.assertIn("import random", self.source)

    def test_has_init_colors(self):
        """Must have a color initialization function."""
        self.assertIn("init_colors", self.functions,
                       "No init_colors function found")


if __name__ == "__main__":
    unittest.main()
