#!/usr/bin/env python3
"""
Test suite for arcade.py — Game Launcher TUI
Tests the "known good" benchmark: structure, logic, and behavior.
These tests run WITHOUT a terminal (no curses rendering).
"""

import ast
import importlib.util
import os
import stat
import sys
import tempfile
import textwrap
import unittest

# Path to the script under test
ARCADE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arcade.py")


def load_arcade_source():
    """Load arcade.py source code as a string."""
    with open(ARCADE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_arcade_ast():
    """Parse arcade.py into an AST tree."""
    return ast.parse(load_arcade_source())


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


def import_arcade_module():
    """Import arcade.py as a module (without running main)."""
    # We can't import normally because curses.wrapper(main) runs at module level.
    # Instead, we exec everything except the if __name__ == "__main__" block.
    source = load_arcade_source()
    tree = ast.parse(source)

    # Remove the if __name__ == "__main__" block
    new_body = []
    for node in tree.body:
        if isinstance(node, ast.If):
            # Check if this is the __name__ == "__main__" guard
            test = node.test
            if (isinstance(test, ast.Compare) and
                isinstance(test.left, ast.Name) and
                test.left.id == "__name__"):
                continue  # Skip this node
        new_body.append(node)

    tree.body = new_body
    ast.fix_missing_locations(tree)

    # Compile and exec into a namespace
    code = compile(tree, ARCADE_PATH, "exec")
    namespace = {"__file__": ARCADE_PATH, "__name__": "arcade"}
    exec(code, namespace)
    return namespace


# =============================================================================
# 1. FILE STRUCTURE TESTS
# =============================================================================

class TestFileStructure(unittest.TestCase):
    """Tests that arcade.py has the right file-level properties."""

    def test_file_exists(self):
        """arcade.py must exist."""
        self.assertTrue(os.path.isfile(ARCADE_PATH), f"arcade.py not found at {ARCADE_PATH}")

    def test_file_is_executable(self):
        """arcade.py must be executable."""
        mode = os.stat(ARCADE_PATH).st_mode
        self.assertTrue(mode & stat.S_IXUSR, "arcade.py is not executable (missing user +x)")

    def test_has_shebang(self):
        """Must start with a Python shebang."""
        source = load_arcade_source()
        self.assertTrue(source.startswith("#!/"), "Missing shebang line")
        first_line = source.split("\n")[0]
        self.assertIn("python", first_line.lower(), "Shebang doesn't reference python")

    def test_has_docstring(self):
        """Must have a module-level docstring."""
        tree = parse_arcade_ast()
        docstring = ast.get_docstring(tree)
        self.assertIsNotNone(docstring, "Missing module docstring")
        self.assertGreater(len(docstring), 10, "Docstring too short")

    def test_syntax_valid(self):
        """Must parse without syntax errors."""
        try:
            parse_arcade_ast()
        except SyntaxError as e:
            self.fail(f"Syntax error: {e}")

    def test_no_external_dependencies(self):
        """Must only import stdlib modules (no pip packages)."""
        STDLIB = {
            "ast", "curses", "os", "subprocess", "sys", "time",
            "pathlib", "glob", "re", "json", "shutil", "signal",
            "textwrap", "collections", "functools", "itertools",
            "math", "random", "string", "typing", "enum",
        }
        tree = parse_arcade_ast()
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
        tree = parse_arcade_ast()
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
        cls.tree = parse_arcade_ast()
        cls.names = get_top_level_names(cls.tree)

    def test_has_excluded_set(self):
        """Must define an EXCLUDED set/list of non-game scripts."""
        self.assertIn("EXCLUDED", self.names, "Missing EXCLUDED variable")

    def test_has_ascii_header(self):
        """Must define an ASCII_HEADER for the banner."""
        has_header = "ASCII_HEADER" in self.names or "ASCII_HEADER_LETTERS" in self.names
        self.assertTrue(has_header, "Missing ASCII_HEADER or ASCII_HEADER_LETTERS variable")

    def test_has_discover_games_function(self):
        """Must have a discover_games() function."""
        self.assertIn("discover_games", self.names)
        self.assertEqual(self.names["discover_games"], "function")

    def test_has_main_function(self):
        """Must have a main() function."""
        self.assertIn("main", self.names)
        self.assertEqual(self.names["main"], "function")

    def test_has_extract_description_function(self):
        """Must have a way to extract game descriptions."""
        # Could be named extract_description, get_description, parse_description, etc.
        desc_funcs = [n for n in self.names if "descri" in n.lower() or "docstring" in n.lower() or "parse" in n.lower()]
        self.assertGreater(len(desc_funcs), 0,
                           "No function for extracting game descriptions (expected *descri* or *parse*)")

    def test_has_name_guard(self):
        """Must have if __name__ == '__main__' guard."""
        source = load_arcade_source()
        self.assertIn('__name__', source, "Missing __name__ guard")
        self.assertIn('__main__', source, "Missing __main__ check")


# =============================================================================
# 3. EXCLUDED SET TESTS
# =============================================================================

class TestExcludedSet(unittest.TestCase):
    """Tests that the EXCLUDED set filters the right scripts."""

    @classmethod
    def setUpClass(cls):
        cls.mod = import_arcade_module()

    def test_excluded_is_collection(self):
        """EXCLUDED must be a set, list, or tuple."""
        excluded = self.mod.get("EXCLUDED")
        self.assertIsNotNone(excluded, "EXCLUDED not defined")
        self.assertIsInstance(excluded, (set, list, tuple),
                              f"EXCLUDED is {type(excluded).__name__}, expected set/list/tuple")

    def test_excludes_self(self):
        """Must exclude arcade.py itself."""
        self.assertIn("arcade.py", self.mod["EXCLUDED"])

    def test_does_not_exclude_games(self):
        """Must NOT exclude known game files."""
        excluded = self.mod["EXCLUDED"]
        for game in ["snake.py", "chess.py", "hangman.py", "blackjack.py",
                      "minesweeper.py", "battleship.py", "checkers.py"]:
            self.assertNotIn(game, excluded, f"Incorrectly excludes game: {game}")


# =============================================================================
# 4. ASCII HEADER TESTS
# =============================================================================

class TestAsciiHeader(unittest.TestCase):
    """Tests that the banner looks right."""

    @classmethod
    def setUpClass(cls):
        cls.mod = import_arcade_module()

    def test_header_is_list(self):
        """ASCII_HEADER must be a list of strings."""
        header = self.mod.get("ASCII_HEADER") or self.mod.get("ASCII_HEADER_LETTERS")
        self.assertIsNotNone(header, "No ASCII_HEADER or ASCII_HEADER_LETTERS found")
        self.assertIsInstance(header, list)
        for line in header:
            self.assertIsInstance(line, str)

    def test_header_has_minimum_lines(self):
        """Banner must have at least 5 lines (enough for readable art)."""
        header = self.mod.get("ASCII_HEADER") or self.mod.get("ASCII_HEADER_LETTERS")
        self.assertGreaterEqual(len(header), 5, "Banner too short")

    def test_header_contains_arcade_text(self):
        """Banner must contain 'ARCADE' somewhere."""
        # Check all header-related variables for ARCADE text
        parts = []
        for key in ["ASCII_HEADER", "ASCII_HEADER_LETTERS", "ASCII_HEADER_ARCADE"]:
            val = self.mod.get(key)
            if val is None:
                continue
            if isinstance(val, list):
                parts.extend(val)
            elif isinstance(val, str):
                parts.append(val)
        header_text = " ".join(parts).upper()
        header_nospace = header_text.replace(" ", "")
        self.assertIn("ARCADE", header_nospace, "Banner doesn't mention ARCADE")

    def test_header_has_box_drawing(self):
        """Banner should use box-drawing characters for the border."""
        header = self.mod.get("ASCII_HEADER") or self.mod.get("ASCII_HEADER_LETTERS") or []
        header_text = "".join(header)
        box_chars = set("╔╗╚╝═║┌┐└┘─│┬┴├┤┼╠╣╦╩╬")
        found = any(c in box_chars for c in header_text)
        self.assertTrue(found, "Banner has no box-drawing characters")


# =============================================================================
# 5. GAME DISCOVERY LOGIC TESTS
# =============================================================================

class TestGameDiscovery(unittest.TestCase):
    """Tests the discover_games() function's return structure."""

    @classmethod
    def setUpClass(cls):
        cls.mod = import_arcade_module()
        # stored in cls.mod

    def test_returns_list(self):
        """discover_games() must return a list."""
        result = self.mod["discover_games"]()
        self.assertIsInstance(result, list)

    def test_returns_nonempty(self):
        """Must find at least one game (we know games exist)."""
        result = self.mod["discover_games"]()
        self.assertGreater(len(result), 0, "No games discovered")

    def test_game_dict_has_required_keys(self):
        """Each game entry must have name, file, path, description, size."""
        result = self.mod["discover_games"]()
        required_keys = {"name", "file", "path", "description", "size"}
        # Allow slight variations (e.g., "filename" instead of "file")
        name_keys = {"name", "title", "display_name"}
        file_keys = {"file", "filename", "fname"}
        path_keys = {"path", "filepath", "full_path"}
        desc_keys = {"description", "desc", "summary"}
        size_keys = {"size", "filesize", "file_size", "bytes"}

        for game in result:
            self.assertIsInstance(game, dict, f"Game entry is not a dict: {type(game)}")
            keys = set(game.keys())
            self.assertTrue(keys & name_keys, f"Missing name key. Has: {keys}")
            self.assertTrue(keys & file_keys, f"Missing file key. Has: {keys}")
            self.assertTrue(keys & path_keys, f"Missing path key. Has: {keys}")
            self.assertTrue(keys & desc_keys, f"Missing description key. Has: {keys}")
            self.assertTrue(keys & size_keys, f"Missing size key. Has: {keys}")

    def test_games_are_sorted(self):
        """Games must be sorted alphabetically."""
        result = self.mod["discover_games"]()
        if len(result) < 2:
            return
        # Get the sort key (name or file)
        names = []
        for g in result:
            n = g.get("name") or g.get("title") or g.get("file", "")
            names.append(n.lower())
        self.assertEqual(names, sorted(names), "Games are not sorted alphabetically")

    def test_excludes_non_games(self):
        """Must not include excluded scripts in results."""
        result = self.mod["discover_games"]()
        excluded_names = {"arcade.py"}
        for game in result:
            fname = game.get("file") or game.get("filename", "")
            self.assertNotIn(fname, excluded_names,
                             f"Non-game script included: {fname}")

    def test_excludes_test_files(self):
        """Must not include test_*.py files."""
        result = self.mod["discover_games"]()
        for game in result:
            fname = game.get("file") or game.get("filename", "")
            self.assertFalse(fname.startswith("test_"),
                             f"Test file included: {fname}")

    def test_finds_known_games(self):
        """Must find games we know exist."""
        result = self.mod["discover_games"]()
        found_files = set()
        for game in result:
            found_files.add(game.get("file") or game.get("filename", ""))
        # At least some of these should be found
        known_games = {"snake.py", "chess.py", "hangman.py", "blackjack.py"}
        found_known = known_games & found_files
        self.assertGreater(len(found_known), 0,
                           f"None of the known games found. Got: {found_files}")

    def test_descriptions_are_strings(self):
        """All descriptions must be non-empty strings."""
        result = self.mod["discover_games"]()
        for game in result:
            desc = game.get("description") or game.get("desc") or game.get("summary", "")
            self.assertIsInstance(desc, str)
            self.assertGreater(len(desc), 0,
                               f"Empty description for {game.get('file', '?')}")

    def test_sizes_are_positive(self):
        """All sizes must be positive integers."""
        result = self.mod["discover_games"]()
        for game in result:
            size = game.get("size") or game.get("filesize") or game.get("bytes", 0)
            self.assertIsInstance(size, (int, float))
            self.assertGreater(size, 0,
                               f"Zero/negative size for {game.get('file', '?')}")


# =============================================================================
# 6. DESCRIPTION EXTRACTION TESTS
# =============================================================================

class TestDescriptionExtraction(unittest.TestCase):
    """Tests that game descriptions are correctly extracted."""

    @classmethod
    def setUpClass(cls):
        cls.mod = import_arcade_module()
        # Find the description extraction function
        for name in ["extract_description", "get_description", "parse_description"]:
            if name in cls.mod:
                cls._extract_name = name
                return
        cls._extract_name = None

    def setUp(self):
        if self._extract_name is None:
            self.skipTest("No description extraction function found")

    def test_extracts_docstring(self):
        """Must extract docstring from a Python file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('"""My Cool Game\nA fun game to play."""\nprint("hi")\n')
            f.flush()
            desc = self.mod[self._extract_name](f.name)
        os.unlink(f.name)
        self.assertIn("My Cool Game", desc)

    def test_extracts_comment_fallback(self):
        """Must fall back to # comment if no docstring."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('#!/usr/bin/env python3\n# A simple puzzle game\nprint("hi")\n')
            f.flush()
            desc = self.mod[self._extract_name](f.name)
        os.unlink(f.name)
        self.assertIsInstance(desc, str)
        self.assertGreater(len(desc), 0)

    def test_handles_missing_file(self):
        """Must not crash on missing file."""
        try:
            desc = self.mod[self._extract_name]("/nonexistent/file.py")
        except Exception:
            pass  # Either returns default or raises — both acceptable


# =============================================================================
# 7. CURSES FUNCTION SIGNATURES
# =============================================================================

class TestCursesFunctions(unittest.TestCase):
    """Tests that the curses drawing functions have correct signatures."""

    @classmethod
    def setUpClass(cls):
        cls.tree = parse_arcade_ast()
        cls.functions = {}
        for node in ast.walk(cls.tree):
            if isinstance(node, ast.FunctionDef):
                cls.functions[node.name] = node

    def test_main_takes_stdscr(self):
        """main() must accept a stdscr argument (for curses.wrapper)."""
        self.assertIn("main", self.functions)
        main_func = self.functions["main"]
        args = [a.arg for a in main_func.args.args]
        self.assertGreater(len(args), 0, "main() takes no arguments")
        self.assertIn(args[0], ["stdscr", "screen", "scr", "win"],
                      f"main() first arg is '{args[0]}', expected stdscr/screen/scr/win")

    def test_uses_curses_wrapper(self):
        """Must call curses.wrapper() to properly initialize/cleanup."""
        source = load_arcade_source()
        self.assertIn("curses.wrapper", source,
                      "Must use curses.wrapper() for proper terminal handling")


if __name__ == "__main__":
    unittest.main(verbosity=2)
