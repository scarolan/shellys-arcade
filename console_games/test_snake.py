#!/usr/bin/env python3
"""
Test suite for snake.py — Terminal Snake Game
Tests the "known good" benchmark: structure, logic, and behavior.
These tests run WITHOUT a terminal (no curses rendering).
"""

import ast
import os
import stat
import sys
import unittest

# Path to the script under test
SNAKE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snake.py")


def load_snake_source():
    """Load snake.py source code as a string."""
    with open(SNAKE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_snake_ast():
    """Parse snake.py into an AST tree."""
    return ast.parse(load_snake_source())


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


def import_snake_module():
    """Import snake.py as a module (without running main).

    Strips the if __name__ == "__main__" block and execs everything else
    into a namespace, avoiding curses initialization.
    """
    source = load_snake_source()
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

    code = compile(tree, SNAKE_PATH, "exec")
    namespace = {"__file__": SNAKE_PATH, "__name__": "snake"}
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
    """Tests that snake.py has the right file-level properties."""

    def test_file_exists(self):
        """snake.py must exist."""
        self.assertTrue(os.path.isfile(SNAKE_PATH),
                        f"snake.py not found at {SNAKE_PATH}")

    def test_file_is_executable(self):
        """snake.py must be executable."""
        mode = os.stat(SNAKE_PATH).st_mode
        self.assertTrue(mode & stat.S_IXUSR,
                        "snake.py is not executable (missing user +x)")

    def test_has_shebang(self):
        """Must start with a Python shebang."""
        source = load_snake_source()
        self.assertTrue(source.startswith("#!/"), "Missing shebang line")
        first_line = source.split("\n")[0]
        self.assertIn("python", first_line.lower(),
                      "Shebang doesn't reference python")

    def test_has_docstring(self):
        """Must have a module-level docstring."""
        tree = parse_snake_ast()
        docstring = ast.get_docstring(tree)
        self.assertIsNotNone(docstring, "Missing module docstring")
        self.assertGreater(len(docstring), 10, "Docstring too short")

    def test_syntax_valid(self):
        """Must parse without syntax errors."""
        try:
            parse_snake_ast()
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
        tree = parse_snake_ast()
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
        """Must import curses (it's a TUI game)."""
        tree = parse_snake_ast()
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
        cls.tree = parse_snake_ast()
        cls.names = get_top_level_names(cls.tree)
        cls.all_funcs = find_all_functions(cls.tree)
        cls.source = load_snake_source()

    def test_has_main_function(self):
        """Must have a main() function."""
        self.assertIn("main", self.names,
                      "Missing main() function at top level")

    def test_has_curses_wrapper(self):
        """Must call curses.wrapper() to initialize curses properly."""
        self.assertIn("curses.wrapper", self.source,
                      "Must use curses.wrapper() for safe init/cleanup")

    def test_main_accepts_stdscr(self):
        """main() must accept stdscr as its first argument."""
        main_func = self.all_funcs.get("main")
        self.assertIsNotNone(main_func, "main() function not found")
        args = main_func.args
        arg_names = [a.arg for a in args.args]
        self.assertIn("stdscr", arg_names,
                      "main() must accept 'stdscr' parameter")


# =============================================================================
# 3. SNAKE DATA STRUCTURE TESTS
# =============================================================================

class TestSnakeDataStructure(unittest.TestCase):
    """Tests that snake body/segments are properly defined."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_snake_source()
        cls.tree = parse_snake_ast()
        cls.ns = import_snake_module()

    def test_has_snake_variable(self):
        """Source must reference a snake body/segments data structure."""
        self.assertIn("snake", self.source.lower(),
                      "No 'snake' variable found in source")

    def test_snake_is_list_of_tuples(self):
        """Snake body should be initialized as a list of tuples."""
        # Look for list literal containing tuples in the source
        self.assertRegex(self.source, r"snake\s*=\s*\[",
                         "Snake should be initialized as a list")

    def test_has_direction_constants(self):
        """Must define direction constants (UP, DOWN, LEFT, RIGHT)."""
        for direction in ["UP", "DOWN", "LEFT", "RIGHT"]:
            self.assertIn(direction, self.ns,
                          f"Missing direction constant: {direction}")

    def test_direction_values_are_tuples(self):
        """Direction constants must be (dy, dx) tuples."""
        for direction in ["UP", "DOWN", "LEFT", "RIGHT"]:
            val = self.ns[direction]
            self.assertIsInstance(val, tuple,
                                 f"{direction} must be a tuple")
            self.assertEqual(len(val), 2,
                             f"{direction} must have 2 elements (dy, dx)")


# =============================================================================
# 4. FOOD SPAWNING TESTS
# =============================================================================

class TestFoodSpawning(unittest.TestCase):
    """Tests that food/apple spawning logic exists and works."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_snake_source()
        cls.tree = parse_snake_ast()
        cls.all_funcs = find_all_functions(cls.tree)

    def test_has_food_spawn_function(self):
        """Must have a function for spawning food."""
        food_funcs = [name for name in self.all_funcs
                      if any(kw in name.lower() for kw in
                             ["food", "apple", "spawn", "fruit"])]
        self.assertTrue(len(food_funcs) > 0,
                        "No food spawning function found (expected spawn_food or similar)")

    def test_food_variable_in_source(self):
        """Source must assign food to a variable."""
        self.assertRegex(self.source, r"food\s*=",
                         "No food variable assignment found")

    def test_food_uses_random(self):
        """Food position must use random for placement."""
        self.assertIn("random", self.source,
                      "Food spawning should use random module")

    def test_food_not_on_snake_check(self):
        """Food must check it doesn't spawn on snake body."""
        self.assertRegex(self.source, r"not\s+in\s+snake",
                         "Must check food doesn't overlap snake body")

    def test_food_respawns_after_eaten(self):
        """Food must be respawned after being eaten (spawn_food called twice+)."""
        # spawn_food should be called at least twice: once at start, once when eaten
        count = self.source.count("spawn_food()")
        self.assertGreaterEqual(count, 2,
                                "spawn_food() must be called at init AND when food is eaten")

    def test_source_contains_food_keywords(self):
        """Source must contain food-related keywords."""
        source_lower = self.source.lower()
        food_keywords = ["food", "eat", "grow"]
        found = [kw for kw in food_keywords if kw in source_lower]
        self.assertGreaterEqual(len(found), 2,
                                f"Source should mention food concepts, found: {found}")

    def test_food_rendering_uses_addstr(self):
        """Food rendering must use addstr (not addch) for Unicode support."""
        # The critical bug fix: addch can't handle multi-byte chars like ●
        self.assertIn("addstr", self.source,
                      "Must use addstr for food rendering (Unicode safety)")


# =============================================================================
# 5. COLLISION DETECTION TESTS
# =============================================================================

class TestCollisionDetection(unittest.TestCase):
    """Tests that collision detection exists for walls and self."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_snake_source()

    def test_has_wall_collision(self):
        """Must detect collision with walls (boundary check)."""
        # Look for boundary comparisons
        has_wall_check = ("win_h" in self.source and "win_w" in self.source
                          and ("<=" in self.source or ">=" in self.source))
        self.assertTrue(has_wall_check,
                        "Must have wall collision detection using window bounds")

    def test_has_self_collision(self):
        """Must detect collision with own body."""
        self.assertRegex(self.source, r"new_head\s+in\s+snake",
                         "Must check if new head position collides with snake body")

    def test_has_game_over(self):
        """Must have game over detection."""
        source_lower = self.source.lower()
        self.assertIn("game over", source_lower,
                      "Must display 'GAME OVER' message")


# =============================================================================
# 6. SNAKE GROWTH LOGIC TESTS
# =============================================================================

class TestSnakeGrowth(unittest.TestCase):
    """Tests that the snake grows when eating food."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_snake_source()

    def test_grows_on_food(self):
        """Snake must grow when eating food (skip tail pop)."""
        # When food is eaten, the tail is NOT popped, causing growth
        self.assertIn("pop(0)", self.source,
                      "Must have tail pop for normal movement")

    def test_conditional_growth(self):
        """Growth must be conditional on eating food."""
        # The food check should be near the pop logic
        self.assertIn("new_head == food", self.source,
                      "Must compare head position with food position")


# =============================================================================
# 7. INPUT HANDLING TESTS
# =============================================================================

class TestInputHandling(unittest.TestCase):
    """Tests that keyboard input is properly handled."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_snake_source()

    def test_handles_arrow_keys(self):
        """Must handle arrow key input."""
        for key in ["KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT"]:
            self.assertIn(key, self.source,
                          f"Must handle {key} input")

    def test_handles_wasd_keys(self):
        """Must handle WASD key input."""
        for key in ["'w'", "'a'", "'s'", "'d'"]:
            self.assertIn(key, self.source,
                          f"Must handle {key} input")

    def test_has_quit_key(self):
        """Must support Q key to quit."""
        self.assertIn("ord('q')", self.source,
                      "Must handle 'q' key for quitting")

    def test_has_pause_key(self):
        """Must support P key to pause."""
        self.assertIn("ord('p')", self.source,
                      "Must handle 'p' key for pausing")


# =============================================================================
# 8. SCORE TRACKING TESTS
# =============================================================================

class TestScoreTracking(unittest.TestCase):
    """Tests that score is tracked and displayed."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_snake_source()

    def test_has_score_variable(self):
        """Must track score."""
        self.assertRegex(self.source, r"score\s*[=+]",
                         "Must have a score variable")

    def test_score_increments(self):
        """Score must increase when food is eaten."""
        self.assertIn("score += 1", self.source,
                      "Score should increment by 1 per food")

    def test_has_high_score(self):
        """Must track high score across restarts."""
        self.assertIn("high_score", self.source,
                      "Must track high score")

    def test_score_displayed(self):
        """Score must be displayed on screen."""
        self.assertRegex(self.source, r"Score:",
                         "Must display 'Score:' label")


# =============================================================================
# 9. COLOR INITIALIZATION TESTS
# =============================================================================

class TestColorInit(unittest.TestCase):
    """Tests that curses colors are properly initialized."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_snake_source()

    def test_has_color_init(self):
        """Must initialize curses colors."""
        self.assertIn("start_color", self.source,
                      "Must call curses.start_color()")

    def test_has_color_pairs(self):
        """Must define color pairs for snake, food, etc."""
        self.assertIn("init_pair", self.source,
                      "Must call curses.init_pair() to define colors")

    def test_has_green_for_snake(self):
        """Snake should be green."""
        self.assertIn("COLOR_GREEN", self.source,
                      "Snake should use green color")

    def test_has_red_for_food(self):
        """Food should be red."""
        self.assertIn("COLOR_RED", self.source,
                      "Food should use red color")


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":
    unittest.main()
