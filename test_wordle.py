#!/usr/bin/env python3
"""
Test suite for wordle.py — Terminal Wordle Game
Tests the "known good" benchmark: structure, logic, and behavior.
These tests run WITHOUT a terminal (no curses rendering).
"""

import ast
import os
import stat
import unittest

# Path to the script under test
WORDLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "wordle.py")


def load_source():
    """Load wordle.py source code as a string."""
    with open(WORDLE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_ast():
    """Parse wordle.py into an AST tree."""
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
    """Import wordle.py as a module (without running main).

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

    code = compile(tree, WORDLE_PATH, "exec")
    namespace = {"__file__": WORDLE_PATH, "__name__": "wordle"}
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
    """Tests that wordle.py has the right file-level properties."""

    def test_file_exists(self):
        """wordle.py must exist."""
        self.assertTrue(os.path.isfile(WORDLE_PATH),
                        "wordle.py not found")

    def test_file_is_executable(self):
        """wordle.py must have the executable bit set."""
        mode = os.stat(WORDLE_PATH).st_mode
        self.assertTrue(mode & stat.S_IXUSR,
                        "wordle.py is not executable")

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

    def test_has_word_list(self):
        """Must have a WORDS list."""
        self.assertIn("WORDS", self.names,
                       "Missing WORDS list")

    def test_word_list_has_words(self):
        """WORDS must contain at least 50 words."""
        ns = import_module()
        words = ns["WORDS"]
        self.assertIsInstance(words, list)
        self.assertGreaterEqual(len(words), 50,
                                "WORDS list too small")

    def test_all_words_are_five_letters(self):
        """All words in WORDS must be exactly 5 letters."""
        ns = import_module()
        words = ns["WORDS"]
        for word in words:
            self.assertEqual(len(word), 5,
                             f"Word '{word}' is not 5 letters")

    def test_all_words_are_lowercase(self):
        """All words in WORDS must be lowercase."""
        ns = import_module()
        words = ns["WORDS"]
        for word in words:
            self.assertEqual(word, word.lower(),
                             f"Word '{word}' is not lowercase")

    def test_has_max_guesses(self):
        """Must define MAX_GUESSES constant."""
        self.assertIn("MAX_GUESSES", self.names)

    def test_max_guesses_is_six(self):
        """MAX_GUESSES must be 6."""
        ns = import_module()
        self.assertEqual(ns["MAX_GUESSES"], 6)

    def test_has_word_length(self):
        """Must define WORD_LENGTH constant."""
        self.assertIn("WORD_LENGTH", self.names)

    def test_word_length_is_five(self):
        """WORD_LENGTH must be 5."""
        ns = import_module()
        self.assertEqual(ns["WORD_LENGTH"], 5)

    def test_has_game_loop(self):
        """Must have a game loop (while True)."""
        tree = parse_ast()
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value:
                    return
        self.fail("No game loop (while True) found")


# =============================================================================
# 3. GAME LOGIC — EVALUATE GUESS
# =============================================================================

class TestEvaluateGuess(unittest.TestCase):
    """Tests for the evaluate_guess() function."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_all_correct(self):
        """All letters correct returns all 'correct'."""
        evaluate = self.ns["evaluate_guess"]
        result = evaluate("hello", "hello")
        self.assertEqual(result, ['correct'] * 5)

    def test_all_absent(self):
        """No matching letters returns all 'absent'."""
        evaluate = self.ns["evaluate_guess"]
        result = evaluate("xxxxx", "hello")
        self.assertEqual(result, ['absent'] * 5)

    def test_correct_position(self):
        """Letters in correct position are marked 'correct'."""
        evaluate = self.ns["evaluate_guess"]
        result = evaluate("heart", "hello")
        self.assertEqual(result[0], 'correct')  # h
        self.assertEqual(result[1], 'correct')  # e

    def test_wrong_position(self):
        """Letters in wrong position are marked 'present'."""
        evaluate = self.ns["evaluate_guess"]
        result = evaluate("ohelx", "hello")
        # o is in hello but not at position 0 -> present
        self.assertEqual(result[0], 'present')

    def test_absent_letters(self):
        """Letters not in word are marked 'absent'."""
        evaluate = self.ns["evaluate_guess"]
        result = evaluate("hexyz", "hello")
        self.assertEqual(result[2], 'absent')  # x
        self.assertEqual(result[3], 'absent')  # y
        self.assertEqual(result[4], 'absent')  # z

    def test_duplicate_handling(self):
        """Duplicate letters handled correctly per Wordle rules."""
        evaluate = self.ns["evaluate_guess"]
        # Target "aabbc" — guess "aaxxa"
        # a at 0: correct (matches target[0])
        # a at 1: correct (matches target[1])
        # x at 2: absent
        # x at 3: absent
        # a at 4: absent (no more a's available)
        result = evaluate("aaxxa", "aabbc")
        self.assertEqual(result[0], 'correct')
        self.assertEqual(result[1], 'correct')
        self.assertEqual(result[4], 'absent')

    def test_duplicate_present_limited(self):
        """Only as many 'present' as remaining unmatched target letters."""
        evaluate = self.ns["evaluate_guess"]
        # Target "abcde", guess "aaxxx"
        # a at 0: correct
        # a at 1: absent (only one 'a' in target, already matched)
        result = evaluate("aaxxx", "abcde")
        self.assertEqual(result[0], 'correct')
        self.assertEqual(result[1], 'absent')

    def test_returns_list_of_five(self):
        """Result must be a list of exactly 5 elements."""
        evaluate = self.ns["evaluate_guess"]
        result = evaluate("crane", "stale")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 5)

    def test_result_values_valid(self):
        """All result values must be 'correct', 'present', or 'absent'."""
        evaluate = self.ns["evaluate_guess"]
        result = evaluate("crane", "stale")
        valid = {'correct', 'present', 'absent'}
        for r in result:
            self.assertIn(r, valid)


# =============================================================================
# 4. GUESS VALIDATION
# =============================================================================

class TestGuessValidation(unittest.TestCase):
    """Tests for is_valid_guess() function."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_valid_guess(self):
        """A word in the list is valid."""
        is_valid = self.ns["is_valid_guess"]
        words = set(self.ns["WORDS"])
        word = self.ns["WORDS"][0]
        self.assertTrue(is_valid(word, words))

    def test_invalid_not_in_list(self):
        """A word not in the list is invalid."""
        is_valid = self.ns["is_valid_guess"]
        words = set(self.ns["WORDS"])
        self.assertFalse(is_valid("zzzzz", words))

    def test_invalid_wrong_length(self):
        """A word of wrong length is invalid."""
        is_valid = self.ns["is_valid_guess"]
        words = set(self.ns["WORDS"])
        self.assertFalse(is_valid("hi", words))

    def test_invalid_too_long(self):
        """A word that's too long is invalid."""
        is_valid = self.ns["is_valid_guess"]
        words = set(self.ns["WORDS"])
        self.assertFalse(is_valid("toolong", words))


# =============================================================================
# 5. WIN DETECTION
# =============================================================================

class TestWinDetection(unittest.TestCase):
    """Tests for check_win() function."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_win_all_correct(self):
        """All correct letters means win."""
        check_win = self.ns["check_win"]
        self.assertTrue(check_win(['correct'] * 5))

    def test_no_win_with_present(self):
        """Having 'present' letters is not a win."""
        check_win = self.ns["check_win"]
        result = ['correct', 'correct', 'present', 'correct', 'correct']
        self.assertFalse(check_win(result))

    def test_no_win_with_absent(self):
        """Having 'absent' letters is not a win."""
        check_win = self.ns["check_win"]
        result = ['correct', 'absent', 'correct', 'correct', 'correct']
        self.assertFalse(check_win(result))

    def test_no_win_all_absent(self):
        """All absent is not a win."""
        check_win = self.ns["check_win"]
        self.assertFalse(check_win(['absent'] * 5))


# =============================================================================
# 6. KEYBOARD TRACKING
# =============================================================================

class TestKeyboardTracking(unittest.TestCase):
    """Tests for update_keyboard() function."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_updates_new_letters(self):
        """New letters get their state recorded."""
        update = self.ns["update_keyboard"]
        kb = {}
        update(kb, "crane", ['absent', 'present', 'correct', 'absent', 'present'])
        self.assertEqual(kb['c'], 'absent')
        self.assertEqual(kb['r'], 'present')
        self.assertEqual(kb['a'], 'correct')
        self.assertEqual(kb['n'], 'absent')
        self.assertEqual(kb['e'], 'present')

    def test_correct_overrides_present(self):
        """Correct state overrides present state."""
        update = self.ns["update_keyboard"]
        kb = {'a': 'present'}
        update(kb, "axxxx", ['correct', 'absent', 'absent', 'absent', 'absent'])
        self.assertEqual(kb['a'], 'correct')

    def test_correct_overrides_absent(self):
        """Correct state overrides absent state."""
        update = self.ns["update_keyboard"]
        kb = {'a': 'absent'}
        update(kb, "axxxx", ['correct', 'absent', 'absent', 'absent', 'absent'])
        self.assertEqual(kb['a'], 'correct')

    def test_present_overrides_absent(self):
        """Present state overrides absent state."""
        update = self.ns["update_keyboard"]
        kb = {'a': 'absent'}
        update(kb, "axxxx", ['present', 'absent', 'absent', 'absent', 'absent'])
        self.assertEqual(kb['a'], 'present')

    def test_absent_does_not_override_correct(self):
        """Absent state does not downgrade correct state."""
        update = self.ns["update_keyboard"]
        kb = {'a': 'correct'}
        update(kb, "axxxx", ['absent', 'absent', 'absent', 'absent', 'absent'])
        self.assertEqual(kb['a'], 'correct')

    def test_absent_does_not_override_present(self):
        """Absent state does not downgrade present state."""
        update = self.ns["update_keyboard"]
        kb = {'a': 'present'}
        update(kb, "axxxx", ['absent', 'absent', 'absent', 'absent', 'absent'])
        self.assertEqual(kb['a'], 'present')


# =============================================================================
# 7. COLOR INITIALIZATION
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

    def test_has_green_for_correct(self):
        """Correct position letters should use green."""
        self.assertIn("COLOR_GREEN", self.source)

    def test_has_yellow_for_present(self):
        """Wrong position letters should use yellow."""
        self.assertIn("COLOR_YELLOW", self.source)

    def test_has_use_default_colors(self):
        """Must call use_default_colors()."""
        self.assertIn("use_default_colors", self.source)

    def test_has_init_colors_function(self):
        """Must have an init_colors function."""
        functions = find_all_functions(parse_ast())
        self.assertIn("init_colors", functions)

    def test_hides_cursor(self):
        """Must hide the cursor with curs_set(0)."""
        self.assertIn("curs_set", self.source)


# =============================================================================
# 8. VISUAL DISPLAY
# =============================================================================

class TestVisualDisplay(unittest.TestCase):
    """Tests for visual elements: grid, keyboard layout."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.tree = parse_ast()
        cls.functions = find_all_functions(cls.tree)

    def test_has_game_title(self):
        """Must display a game title containing WORDLE."""
        source_lower = self.source.lower()
        self.assertIn("wordle", source_lower)

    def test_has_draw_grid_function(self):
        """Must have a draw_grid function."""
        self.assertIn("draw_grid", self.functions)

    def test_has_draw_keyboard_function(self):
        """Must have a draw_keyboard function."""
        self.assertIn("draw_keyboard", self.functions)

    def test_has_draw_title_function(self):
        """Must have a draw_title function."""
        self.assertIn("draw_title", self.functions)

    def test_has_unicode_decoration(self):
        """Must use Unicode glyphs for decoration."""
        all_chars = "".join(find_all_string_literals(self.tree))
        glyphs = {"★", "●", "◆", "✦", "▲", "▼"}
        found = [g for g in glyphs if g in all_chars]
        self.assertGreater(len(found), 0,
                           "No Unicode decoration glyphs found")

    def test_has_safe_addstr(self):
        """Must have safe_addstr for safe curses rendering."""
        self.assertIn("safe_addstr", self.functions)


# =============================================================================
# 9. INPUT HANDLING
# =============================================================================

class TestInputHandling(unittest.TestCase):
    """Tests that the game handles expected keyboard input."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_handles_letter_keys(self):
        """Must handle a-z letter key input."""
        self.assertTrue(
            "97" in self.source or "ord('a')" in self.source,
            "No a-z letter input handling found")

    def test_handles_quit_key(self):
        """Must handle 'q' key for quit."""
        self.assertIn("ord('q')", self.source)

    def test_handles_new_game_key(self):
        """Must handle 'n' key for new game."""
        self.assertIn("ord('n')", self.source)

    def test_handles_backspace(self):
        """Must handle backspace key."""
        self.assertTrue(
            "KEY_BACKSPACE" in self.source or "127" in self.source,
            "No backspace handling found")

    def test_handles_enter(self):
        """Must handle enter key for submission."""
        self.assertTrue(
            "KEY_ENTER" in self.source or "10" in self.source,
            "No enter key handling found")


# =============================================================================
# 10. PICK WORD
# =============================================================================

class TestPickWord(unittest.TestCase):
    """Tests for pick_word() function."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_pick_word_returns_string(self):
        """pick_word() must return a string from the word list."""
        pick = self.ns["pick_word"]
        word = pick()
        self.assertIsInstance(word, str)
        self.assertIn(word, self.ns["WORDS"])

    def test_pick_word_returns_five_letters(self):
        """pick_word() must return a 5-letter word."""
        pick = self.ns["pick_word"]
        word = pick()
        self.assertEqual(len(word), 5)

    def test_pick_word_varies(self):
        """pick_word() should return different words over many calls."""
        pick = self.ns["pick_word"]
        words = set(pick() for _ in range(50))
        self.assertGreater(len(words), 1,
                           "pick_word() always returns the same word")


# =============================================================================
# 11. GAME STATE KEYWORDS
# =============================================================================

class TestGameStateKeywords(unittest.TestCase):
    """Tests that the source contains essential game state keywords."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_has_correct_keyword(self):
        """Source must reference 'correct' state."""
        self.assertIn("correct", self.source)

    def test_has_present_keyword(self):
        """Source must reference 'present' state."""
        self.assertIn("present", self.source)

    def test_has_absent_keyword(self):
        """Source must reference 'absent' state."""
        self.assertIn("absent", self.source)

    def test_has_game_over_state(self):
        """Source must track game_over state."""
        self.assertIn("game_over", self.source)

    def test_has_win_message(self):
        """Source must have a win message."""
        source_lower = self.source.lower()
        self.assertTrue(
            "brilliant" in source_lower or "win" in source_lower or
            "got it" in source_lower,
            "No win message found")

    def test_has_loss_message(self):
        """Source must reveal the word on loss."""
        self.assertIn("the word was", self.source.lower())


if __name__ == "__main__":
    unittest.main()
