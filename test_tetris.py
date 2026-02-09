#!/usr/bin/env python3
"""
Test suite for tetris.py — Terminal Tetris
Tests the "known good" benchmark: structure, logic, and behavior.
These tests run WITHOUT a terminal (no curses rendering).
"""

import ast
import os
import stat
import sys
import unittest

# Path to the script under test
TETRIS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tetris.py")


def load_tetris_source():
    """Load tetris.py source code as a string."""
    with open(TETRIS_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_tetris_ast():
    """Parse tetris.py into an AST tree."""
    return ast.parse(load_tetris_source())


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


def import_tetris_module():
    """Import tetris.py as a module (without running main).

    Strips the if __name__ == "__main__" block and execs everything else
    into a namespace, avoiding curses initialization.
    """
    source = load_tetris_source()
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

    code = compile(tree, TETRIS_PATH, "exec")
    namespace = {"__file__": TETRIS_PATH, "__name__": "tetris"}
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
    """Tests that tetris.py has the right file-level properties."""

    def test_file_exists(self):
        """tetris.py must exist."""
        self.assertTrue(os.path.isfile(TETRIS_PATH),
                        f"tetris.py not found at {TETRIS_PATH}")

    def test_file_is_executable(self):
        """tetris.py must be executable."""
        mode = os.stat(TETRIS_PATH).st_mode
        self.assertTrue(mode & stat.S_IXUSR,
                        "tetris.py is not executable (missing user +x)")

    def test_has_shebang(self):
        """Must start with a Python shebang."""
        source = load_tetris_source()
        self.assertTrue(source.startswith("#!/"), "Missing shebang line")
        first_line = source.split("\n")[0]
        self.assertIn("python", first_line.lower(),
                      "Shebang doesn't reference python")

    def test_has_docstring(self):
        """Must have a module-level docstring."""
        tree = parse_tetris_ast()
        docstring = ast.get_docstring(tree)
        self.assertIsNotNone(docstring, "Missing module docstring")
        self.assertGreater(len(docstring), 10, "Docstring too short")

    def test_syntax_valid(self):
        """Must parse without syntax errors."""
        try:
            parse_tetris_ast()
        except SyntaxError as e:
            self.fail(f"Syntax error: {e}")

    def test_no_external_dependencies(self):
        """Must only import stdlib modules (no pip packages)."""
        STDLIB = {
            "ast", "curses", "os", "subprocess", "sys", "time",
            "pathlib", "glob", "re", "json", "shutil", "signal",
            "textwrap", "collections", "functools", "itertools",
            "math", "random", "string", "typing", "enum", "copy",
            "dataclasses", "abc",
        }
        tree = parse_tetris_ast()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    self.assertIn(module, STDLIB,
                                  f"Non-stdlib import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split(".")[0]
                    self.assertIn(module, STDLIB,
                                  f"Non-stdlib import: from {node.module}")

    def test_uses_curses(self):
        """Must import curses (it's a TUI)."""
        tree = parse_tetris_ast()
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertIn("curses", imports, "Must import curses")


# =============================================================================
# 2. REQUIRED COMPONENTS TESTS
# =============================================================================

class TestRequiredComponents(unittest.TestCase):
    """Tests that all required functions and data structures exist."""

    @classmethod
    def setUpClass(cls):
        cls.tree = parse_tetris_ast()
        cls.names = get_top_level_names(cls.tree)
        cls.all_funcs = find_all_functions(cls.tree)
        cls.source = load_tetris_source()

    def test_has_main_function(self):
        """Must have a main() function."""
        self.assertIn("main", self.names,
                      "Missing main() function at top level")

    def test_has_tetromino_definitions(self):
        """Must define tetromino/piece shapes as a data structure."""
        # Look for common variable names for piece definitions
        piece_vars = [n for n in self.names
                      if any(kw in n.lower() for kw in
                             ["tetromino", "piece", "shape", "block"])]
        # Also check for class-based definitions
        piece_classes = [n for n in self.names
                         if self.names[n] == "class" and
                         any(kw in n.lower() for kw in
                             ["tetromino", "piece", "shape", "block", "tetris"])]
        self.assertTrue(len(piece_vars) > 0 or len(piece_classes) > 0,
                        "No tetromino/piece definitions found. "
                        f"Top-level names: {list(self.names.keys())}")

    def test_has_board_dimensions(self):
        """Must define board width and height constants."""
        source_upper = self.source.upper()
        has_width = any(kw in source_upper for kw in
                        ["BOARD_WIDTH", "GRID_WIDTH", "COLS", "WIDTH"])
        has_height = any(kw in source_upper for kw in
                         ["BOARD_HEIGHT", "GRID_HEIGHT", "ROWS", "HEIGHT"])
        self.assertTrue(has_width, "No board width constant found")
        self.assertTrue(has_height, "No board height constant found")

    def test_has_scoring(self):
        """Must have scoring values (40/100/300/1200)."""
        numbers = find_all_number_literals(self.tree)
        # Classic NES scoring: 40, 100, 300, 1200
        has_40 = 40 in numbers
        has_100 = 100 in numbers
        has_300 = 300 in numbers
        has_1200 = 1200 in numbers
        self.assertTrue(has_40 and has_100 and has_300 and has_1200,
                        f"Missing scoring constants. Need 40, 100, 300, 1200. "
                        f"Found 40={has_40}, 100={has_100}, 300={has_300}, 1200={has_1200}")

    def test_has_game_loop(self):
        """Must have a game loop (while True or similar)."""
        has_while = False
        for node in ast.walk(self.tree):
            if isinstance(node, ast.While):
                has_while = True
                break
        self.assertTrue(has_while, "No while loop found (game needs a main loop)")

    def test_has_line_clearing(self):
        """Must have line-clearing logic."""
        source_lower = self.source.lower()
        has_clear = any(kw in source_lower for kw in
                        ["clear_line", "clear_row", "remove_line", "remove_row",
                         "clear_complete", "check_lines", "check_rows",
                         "completed_lines", "full_rows", "filled_rows",
                         "line_clear", "clear_filled"])
        self.assertTrue(has_clear,
                        "No line-clearing logic found in source")

    def test_has_collision_detection(self):
        """Must have collision detection."""
        source_lower = self.source.lower()
        has_collision = any(kw in source_lower for kw in
                           ["collision", "collide", "valid_pos", "valid_move",
                            "can_move", "is_valid", "check_pos", "fits",
                            "occupied", "overlap"])
        self.assertTrue(has_collision,
                        "No collision detection logic found in source")

    def test_uses_curses_wrapper(self):
        """Must call curses.wrapper() for proper terminal handling."""
        self.assertIn("curses.wrapper", self.source,
                      "Must use curses.wrapper() for proper terminal handling")


# =============================================================================
# 3. TETROMINO DEFINITIONS TESTS
# =============================================================================

class TestTetrominoDefinitions(unittest.TestCase):
    """Tests that the 7 standard tetrominoes are correctly defined."""

    @classmethod
    def setUpClass(cls):
        cls.mod = import_tetris_module()
        cls.tree = parse_tetris_ast()
        cls.source = load_tetris_source()

        # Find the piece definitions — could be a dict, list, or set of variables
        cls.pieces = None
        cls.piece_key = None

        # Search for common piece container names
        for key in ["TETROMINOES", "TETROMINOS", "PIECES", "SHAPES",
                     "TETROMINOES_DATA", "PIECE_DATA", "BLOCKS",
                     "tetrominoes", "tetrominos", "pieces", "shapes"]:
            if key in cls.mod:
                cls.pieces = cls.mod[key]
                cls.piece_key = key
                break

        # If not found as a single container, look for individual piece defs
        if cls.pieces is None:
            piece_names = ["I", "O", "T", "S", "Z", "J", "L"]
            found = {}
            for name in piece_names:
                for prefix in ["", "PIECE_", "SHAPE_", "TETROMINO_"]:
                    full = prefix + name
                    if full in cls.mod:
                        found[name] = cls.mod[full]
                        break
            if len(found) >= 7:
                cls.pieces = found
                cls.piece_key = "individual"

    def test_pieces_defined(self):
        """Piece definitions must exist."""
        self.assertIsNotNone(self.pieces,
                             f"No piece definitions found. "
                             f"Looked for TETROMINOES, PIECES, SHAPES, etc.")

    def test_exactly_seven_pieces(self):
        """Must define exactly 7 tetrominoes."""
        if isinstance(self.pieces, dict):
            count = len(self.pieces)
        elif isinstance(self.pieces, (list, tuple)):
            count = len(self.pieces)
        else:
            self.fail(f"Unexpected piece container type: {type(self.pieces)}")
        self.assertEqual(count, 7,
                         f"Expected 7 tetrominoes, found {count}")

    def test_pieces_have_rotation_states(self):
        """Each piece must have multiple rotation states (or shape data)."""
        if isinstance(self.pieces, dict):
            items = list(self.pieces.values())
        else:
            items = list(self.pieces)

        for i, piece in enumerate(items):
            # Piece could be: list of rotation states, dict with 'shapes' key,
            # or an object with rotations
            if isinstance(piece, (list, tuple)):
                # Should have at least 1 rotation state
                self.assertGreater(len(piece), 0,
                                   f"Piece {i} has no rotation states")
            elif isinstance(piece, dict):
                # Should have a shape/rotation key
                has_shape = any(k in piece for k in
                                ["shape", "shapes", "rotations", "states"])
                self.assertTrue(has_shape,
                                f"Piece {i} dict has no shape/rotation key: {list(piece.keys())}")
            # else: could be a class instance, we just check it exists

    def test_i_piece_exists(self):
        """I piece must exist (the long straight one)."""
        source = self.source
        # I piece should be identifiable in the source
        self.assertTrue(
            any(kw in source for kw in ['"I"', "'I'", "# I", "I-piece", "I piece"]),
            "I piece not clearly identified in source")

    def test_o_piece_exists(self):
        """O piece must exist (the square)."""
        source = self.source
        self.assertTrue(
            any(kw in source for kw in ['"O"', "'O'", "# O", "O-piece", "O piece"]),
            "O piece not clearly identified in source")

    def test_pieces_have_colors(self):
        """Each piece must have an associated color."""
        source_lower = self.source.lower()
        has_colors = any(kw in source_lower for kw in
                         ["color", "colour", "curses.color_pair",
                          "init_pair", "color_pair"])
        self.assertTrue(has_colors,
                        "No color definitions found for pieces")

    def test_all_seven_piece_names(self):
        """All 7 standard piece names should appear in source."""
        piece_names = ["I", "O", "T", "S", "Z", "J", "L"]
        source = self.source
        found = []
        for name in piece_names:
            # Look for the piece name in quotes or comments
            if (f'"{name}"' in source or f"'{name}'" in source or
                f"# {name}" in source or f"#{name}" in source):
                found.append(name)
        self.assertGreaterEqual(len(found), 7,
                                f"Only found {len(found)}/7 piece names: {found}. "
                                f"Missing: {set(piece_names) - set(found)}")

    def test_no_duplicate_pieces(self):
        """All 7 pieces must be distinct."""
        if isinstance(self.pieces, dict):
            items = list(self.pieces.values())
        else:
            items = list(self.pieces)

        # Convert each piece to a string representation for comparison
        representations = []
        for piece in items:
            representations.append(str(piece))

        unique = set(representations)
        self.assertEqual(len(unique), len(representations),
                         f"Duplicate pieces found: {len(representations)} pieces "
                         f"but only {len(unique)} unique")


# =============================================================================
# 4. BOARD DIMENSIONS TESTS
# =============================================================================

class TestBoardDimensions(unittest.TestCase):
    """Tests that the board has standard Tetris dimensions."""

    @classmethod
    def setUpClass(cls):
        cls.mod = import_tetris_module()

    def _find_dimension(self, keywords):
        """Find a dimension value by searching common variable names."""
        for key in keywords:
            if key in self.mod:
                return self.mod[key]
        return None

    def test_board_width_is_10(self):
        """Board width must be 10 (standard Tetris)."""
        width = self._find_dimension([
            "BOARD_WIDTH", "GRID_WIDTH", "COLS", "WIDTH",
            "FIELD_WIDTH", "PLAY_WIDTH", "NUM_COLS",
            "board_width", "grid_width", "cols", "width",
        ])
        self.assertIsNotNone(width, "No board width constant found")
        self.assertEqual(width, 10, f"Board width is {width}, expected 10")

    def test_board_height_is_20(self):
        """Board height must be 20 (standard Tetris)."""
        height = self._find_dimension([
            "BOARD_HEIGHT", "GRID_HEIGHT", "ROWS", "HEIGHT",
            "FIELD_HEIGHT", "PLAY_HEIGHT", "NUM_ROWS",
            "board_height", "grid_height", "rows", "height",
        ])
        self.assertIsNotNone(height, "No board height constant found")
        self.assertEqual(height, 20, f"Board height is {height}, expected 20")

    def test_board_is_2d_structure(self):
        """Board should be represented as a 2D structure."""
        source_lower = self.source if hasattr(self, 'source') else load_tetris_source().lower()
        # Look for board initialization patterns
        has_2d = any(kw in source_lower for kw in
                     ["[[", "for _ in range", "[0]", "[0] *",
                      "board[", "grid[", "field["])
        self.assertTrue(has_2d,
                        "No 2D board structure found in source")


# =============================================================================
# 5. SCORING SYSTEM TESTS
# =============================================================================

class TestScoringSystem(unittest.TestCase):
    """Tests the classic NES Tetris scoring: 40/100/300/1200."""

    @classmethod
    def setUpClass(cls):
        cls.mod = import_tetris_module()
        cls.tree = parse_tetris_ast()
        cls.numbers = find_all_number_literals(cls.tree)

    def test_single_line_score(self):
        """Single line clear = 40 points."""
        self.assertIn(40, self.numbers,
                      "Score value 40 (single line) not found")

    def test_double_line_score(self):
        """Double line clear = 100 points."""
        self.assertIn(100, self.numbers,
                      "Score value 100 (double line) not found")

    def test_triple_line_score(self):
        """Triple line clear = 300 points."""
        self.assertIn(300, self.numbers,
                      "Score value 300 (triple line) not found")

    def test_tetris_score(self):
        """Tetris (4 lines) = 1200 points."""
        self.assertIn(1200, self.numbers,
                      "Score value 1200 (tetris/quad) not found")


# =============================================================================
# 6. GAME LOGIC TESTS
# =============================================================================

class TestGameLogic(unittest.TestCase):
    """Tests that essential game logic functions exist."""

    @classmethod
    def setUpClass(cls):
        cls.tree = parse_tetris_ast()
        cls.all_funcs = find_all_functions(cls.tree)
        cls.source = load_tetris_source()
        cls.source_lower = cls.source.lower()

    def test_collision_function_exists(self):
        """Must have a collision detection function."""
        collision_funcs = [n for n in self.all_funcs
                           if any(kw in n.lower() for kw in
                                  ["collision", "collide", "valid", "can_move",
                                   "check_pos", "fits", "is_valid"])]
        self.assertGreater(len(collision_funcs), 0,
                           f"No collision function found. Functions: "
                           f"{list(self.all_funcs.keys())}")

    def test_line_clear_function_exists(self):
        """Must have a line clearing function."""
        clear_funcs = [n for n in self.all_funcs
                       if any(kw in n.lower() for kw in
                              ["clear", "remove_line", "remove_row",
                               "check_line", "check_row", "complete",
                               "filled", "full_row"])]
        self.assertGreater(len(clear_funcs), 0,
                           f"No line clearing function found. Functions: "
                           f"{list(self.all_funcs.keys())}")

    def test_rotation_function_exists(self):
        """Must have a piece rotation function."""
        rotate_funcs = [n for n in self.all_funcs
                        if any(kw in n.lower() for kw in
                               ["rotate", "rotation", "spin", "turn"])]
        # Also accept inline rotation in source
        has_rotate_inline = "rotate" in self.source_lower
        self.assertTrue(len(rotate_funcs) > 0 or has_rotate_inline,
                        f"No rotation function found. Functions: "
                        f"{list(self.all_funcs.keys())}")

    def test_game_over_detection(self):
        """Must have game over detection logic."""
        has_gameover = any(kw in self.source_lower for kw in
                          ["game_over", "gameover", "game over",
                           "game_end", "is_over", "lost"])
        self.assertTrue(has_gameover,
                        "No game over detection found in source")

    def test_level_system(self):
        """Must have level progression (every 10 lines)."""
        has_level = "level" in self.source_lower
        self.assertTrue(has_level, "No level system found in source")
        # Check for the "10 lines per level" rule
        self.assertIn(10, find_all_number_literals(self.tree),
                      "Number 10 not found (expected for lines-per-level)")

    def test_drop_function_exists(self):
        """Must have hard drop or drop function."""
        has_drop = any(kw in self.source_lower for kw in
                       ["hard_drop", "drop", "instant_drop", "slam"])
        self.assertTrue(has_drop,
                        "No drop function/logic found in source")


# =============================================================================
# 7. INPUT HANDLING TESTS
# =============================================================================

class TestInputHandling(unittest.TestCase):
    """Tests that the game handles required key inputs."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_tetris_source()

    def test_handles_arrow_keys(self):
        """Must handle arrow key inputs."""
        required_keys = ["KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT"]
        found = [k for k in required_keys if k in self.source]
        self.assertEqual(len(found), 4,
                         f"Missing arrow key handlers. Found: {found}, "
                         f"Missing: {set(required_keys) - set(found)}")

    def test_handles_space_bar(self):
        """Must handle space bar for hard drop."""
        # Space is ord(' ') = 32 or ' ' character
        has_space = any(kw in self.source for kw in
                        ["ord(' ')", 'ord(" ")', "== 32", "== ' '",
                         '== " "', "KEY_SPACE", "' '", '" "'])
        self.assertTrue(has_space,
                        "No space bar handling found (needed for hard drop)")

    def test_handles_quit_key(self):
        """Must handle q/Q to quit the game."""
        has_quit = any(kw in self.source for kw in
                       ["ord('q')", 'ord("q")', "ord('Q')", 'ord("Q")',
                        "'q'", '"q"', "'Q'", '"Q"'])
        self.assertTrue(has_quit,
                        "No quit key (q/Q) handler found")

    def test_handles_pause_key(self):
        """Must handle P key to pause."""
        has_pause = any(kw in self.source for kw in
                        ["ord('p')", 'ord("p")', "ord('P')", 'ord("P")',
                         "'p'", '"p"', "'P'", '"P"', "pause"])
        self.assertTrue(has_pause,
                        "No pause key (P) handler found")

    def test_handles_hold_key(self):
        """Must handle C key for hold piece."""
        has_hold = any(kw in self.source for kw in
                       ["ord('c')", 'ord("c")', "ord('C')", 'ord("C")',
                        "'c'", '"c"', "'C'", '"C"', "hold"])
        self.assertTrue(has_hold,
                        "No hold key (C) handler found")


# =============================================================================
# 8. CURSES INTEGRATION TESTS
# =============================================================================

class TestCursesIntegration(unittest.TestCase):
    """Tests proper curses integration."""

    @classmethod
    def setUpClass(cls):
        cls.tree = parse_tetris_ast()
        cls.functions = find_all_functions(cls.tree)
        cls.source = load_tetris_source()

    def test_main_takes_stdscr(self):
        """main() must accept a stdscr argument (for curses.wrapper)."""
        self.assertIn("main", self.functions,
                      "main() function not found")
        main_func = self.functions["main"]
        args = [a.arg for a in main_func.args.args]
        self.assertGreater(len(args), 0, "main() takes no arguments")
        self.assertIn(args[0], ["stdscr", "screen", "scr", "win"],
                      f"main() first arg is '{args[0]}', "
                      f"expected stdscr/screen/scr/win")

    def test_uses_curses_wrapper(self):
        """Must call curses.wrapper() to properly initialize/cleanup."""
        self.assertIn("curses.wrapper", self.source,
                      "Must use curses.wrapper() for proper terminal handling")


# =============================================================================
# 9. VISUAL FEATURES TESTS
# =============================================================================

class TestVisualFeatures(unittest.TestCase):
    """Tests that required visual features are present."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_tetris_source()
        cls.source_lower = cls.source.lower()

    def test_has_next_piece_display(self):
        """Must show next piece preview."""
        has_next = any(kw in self.source_lower for kw in
                       ["next_piece", "next piece", "preview",
                        "next_tetromino", "upcoming"])
        self.assertTrue(has_next,
                        "No next piece preview found in source")

    def test_has_hold_piece_feature(self):
        """Must have hold piece feature."""
        has_hold = any(kw in self.source_lower for kw in
                       ["hold_piece", "hold piece", "held_piece",
                        "hold_tetromino", "swap_piece"])
        self.assertTrue(has_hold,
                        "No hold piece feature found in source")

    def test_has_ghost_piece(self):
        """Must show ghost piece (where piece will land)."""
        has_ghost = any(kw in self.source_lower for kw in
                        ["ghost", "shadow", "landing_preview",
                         "drop_preview", "projection"])
        self.assertTrue(has_ghost,
                        "No ghost/shadow piece found in source")

    def test_has_score_display(self):
        """Must display score to the player."""
        has_score = "score" in self.source_lower
        self.assertTrue(has_score,
                        "No score display found in source")

    def test_has_level_display(self):
        """Must display current level."""
        has_level = "level" in self.source_lower
        self.assertTrue(has_level,
                        "No level display found in source")

    def test_has_box_drawing_borders(self):
        """Must use box-drawing characters for borders."""
        box_chars = set("╔╗╚╝═║┌┐└┘─│┬┴├┤┼╠╣╦╩╬")
        found = any(c in box_chars for c in self.source)
        self.assertTrue(found,
                        "No box-drawing characters found for borders")


if __name__ == "__main__":
    unittest.main(verbosity=2)
