#!/usr/bin/env python3
"""
Test suite for hangman.py — Terminal Hangman Game
Tests the "known good" benchmark: structure, logic, and behavior.
These tests run WITHOUT a terminal (no curses rendering).
"""

import ast
import os
import stat
import unittest

# Path to the script under test
HANGMAN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "hangman.py")


def load_source():
    """Load hangman.py source code as a string."""
    with open(HANGMAN_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_ast():
    """Parse hangman.py into an AST tree."""
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
    """Import hangman.py as a module (without running main).

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

    code = compile(tree, HANGMAN_PATH, "exec")
    namespace = {"__file__": HANGMAN_PATH, "__name__": "hangman"}
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
    """Tests that hangman.py has the right file-level properties."""

    def test_file_exists(self):
        """hangman.py must exist."""
        self.assertTrue(os.path.isfile(HANGMAN_PATH),
                        "hangman.py not found")

    def test_file_is_executable(self):
        """hangman.py must have the executable bit set."""
        mode = os.stat(HANGMAN_PATH).st_mode
        self.assertTrue(mode & stat.S_IXUSR,
                        "hangman.py is not executable")

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
        """Must have a word list or dictionary."""
        self.assertIn("WORDS", self.names,
                       "Missing WORDS list")

    def test_word_list_has_words(self):
        """WORDS must contain at least 10 words."""
        ns = import_module()
        words = ns["WORDS"]
        self.assertIsInstance(words, list)
        self.assertGreaterEqual(len(words), 10,
                                "WORDS list too small")

    def test_has_hangman_stages(self):
        """Must have hangman stages (at least 6 body parts)."""
        self.assertIn("HANGMAN_STAGES", self.names,
                       "Missing HANGMAN_STAGES")

    def test_stages_count(self):
        """Must have at least 7 stages (empty + 6 body parts)."""
        ns = import_module()
        stages = ns["HANGMAN_STAGES"]
        self.assertIsInstance(stages, list)
        self.assertGreaterEqual(len(stages), 7,
                                "Need at least 7 hangman stages")

    def test_has_game_loop(self):
        """Must have a game loop (while True)."""
        tree = parse_ast()
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value:
                    return
        self.fail("No game loop (while True) found")


# =============================================================================
# 3. GAME LOGIC — WORD AND GUESSING
# =============================================================================

class TestGameLogic(unittest.TestCase):
    """Tests for core game logic functions."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_pick_word_returns_string(self):
        """pick_word() must return a string from the word list."""
        pick = self.ns["pick_word"]
        word = pick()
        self.assertIsInstance(word, str)
        self.assertIn(word, self.ns["WORDS"])

    def test_get_revealed_all_hidden(self):
        """get_revealed() with no guesses shows all underscores."""
        get_revealed = self.ns["get_revealed"]
        result = get_revealed("python", set())
        self.assertEqual(result, "______")

    def test_get_revealed_partial(self):
        """get_revealed() shows guessed letters and hides the rest."""
        get_revealed = self.ns["get_revealed"]
        result = get_revealed("python", {"p", "t"})
        self.assertEqual(result, "p_t___")

    def test_get_revealed_all_found(self):
        """get_revealed() shows full word when all letters guessed."""
        get_revealed = self.ns["get_revealed"]
        result = get_revealed("cat", {"c", "a", "t"})
        self.assertEqual(result, "cat")

    def test_check_win_true(self):
        """check_win() returns True when all letters guessed."""
        check_win = self.ns["check_win"]
        self.assertTrue(check_win("cat", {"c", "a", "t", "x"}))

    def test_check_win_false(self):
        """check_win() returns False when letters remain."""
        check_win = self.ns["check_win"]
        self.assertFalse(check_win("cat", {"c", "a"}))

    def test_check_loss_true(self):
        """check_loss() returns True when wrong guesses reach max."""
        check_loss = self.ns["check_loss"]
        max_wrong = self.ns["MAX_WRONG"]
        wrong = set(chr(i) for i in range(ord('a'), ord('a') + max_wrong))
        self.assertTrue(check_loss(wrong))

    def test_check_loss_false(self):
        """check_loss() returns False when wrong guesses under max."""
        check_loss = self.ns["check_loss"]
        self.assertFalse(check_loss({"x"}))


# =============================================================================
# 4. GUESS PROCESSING
# =============================================================================

class TestGuessProcessing(unittest.TestCase):
    """Tests for process_guess() logic."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_correct_guess(self):
        """Correct guess adds to guessed set."""
        process_guess = self.ns["process_guess"]
        guessed = set()
        wrong = set()
        already, correct = process_guess("p", "python", guessed, wrong)
        self.assertFalse(already)
        self.assertTrue(correct)
        self.assertIn("p", guessed)

    def test_wrong_guess(self):
        """Wrong guess adds to wrong_guesses set."""
        process_guess = self.ns["process_guess"]
        guessed = set()
        wrong = set()
        already, correct = process_guess("z", "python", guessed, wrong)
        self.assertFalse(already)
        self.assertFalse(correct)
        self.assertIn("z", wrong)

    def test_already_guessed_correct(self):
        """Re-guessing a correct letter returns already=True."""
        process_guess = self.ns["process_guess"]
        guessed = {"p"}
        wrong = set()
        already, correct = process_guess("p", "python", guessed, wrong)
        self.assertTrue(already)

    def test_already_guessed_wrong(self):
        """Re-guessing a wrong letter returns already=True."""
        process_guess = self.ns["process_guess"]
        guessed = set()
        wrong = {"z"}
        already, correct = process_guess("z", "python", guessed, wrong)
        self.assertTrue(already)

    def test_guess_does_not_mutate_extra(self):
        """Correct guess doesn't add to wrong; wrong guess doesn't add to guessed."""
        process_guess = self.ns["process_guess"]
        guessed = set()
        wrong = set()
        process_guess("p", "python", guessed, wrong)
        self.assertEqual(len(wrong), 0)
        process_guess("z", "python", guessed, wrong)
        self.assertEqual(guessed, {"p"})
        self.assertEqual(wrong, {"z"})


# =============================================================================
# 5. WIN AND LOSS DETECTION
# =============================================================================

class TestWinLoss(unittest.TestCase):
    """Tests for win and loss detection in game context."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_win_after_all_letters(self):
        """Win is detected when all unique letters are guessed."""
        check_win = self.ns["check_win"]
        word = "hello"
        guessed = {"h", "e", "l", "o"}
        self.assertTrue(check_win(word, guessed))

    def test_no_win_with_missing_letters(self):
        """No win when some letters remain hidden."""
        check_win = self.ns["check_win"]
        word = "hello"
        guessed = {"h", "e", "l"}
        self.assertFalse(check_win(word, guessed))

    def test_loss_at_max_wrong(self):
        """Loss detected when wrong_guesses equals MAX_WRONG."""
        check_loss = self.ns["check_loss"]
        max_wrong = self.ns["MAX_WRONG"]
        wrong = set(chr(i) for i in range(ord('a'), ord('a') + max_wrong))
        self.assertTrue(check_loss(wrong))

    def test_no_loss_below_max(self):
        """No loss when wrong guesses are below maximum."""
        check_loss = self.ns["check_loss"]
        max_wrong = self.ns["MAX_WRONG"]
        wrong = set(chr(i) for i in range(ord('a'), ord('a') + max_wrong - 1))
        self.assertFalse(check_loss(wrong))


# =============================================================================
# 6. USED-LETTER TRACKING
# =============================================================================

class TestUsedLetterTracking(unittest.TestCase):
    """Tests that letter tracking is correct across guesses."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_guessed_set_grows(self):
        """Correct guesses accumulate in guessed set."""
        process_guess = self.ns["process_guess"]
        guessed = set()
        wrong = set()
        process_guess("p", "python", guessed, wrong)
        process_guess("y", "python", guessed, wrong)
        self.assertEqual(guessed, {"p", "y"})

    def test_wrong_set_grows(self):
        """Wrong guesses accumulate in wrong_guesses set."""
        process_guess = self.ns["process_guess"]
        guessed = set()
        wrong = set()
        process_guess("z", "python", guessed, wrong)
        process_guess("x", "python", guessed, wrong)
        self.assertEqual(wrong, {"z", "x"})

    def test_sets_are_disjoint(self):
        """Correct and wrong sets never overlap."""
        process_guess = self.ns["process_guess"]
        guessed = set()
        wrong = set()
        for ch in "pythonzxqwm":
            process_guess(ch, "python", guessed, wrong)
        self.assertEqual(len(guessed & wrong), 0)


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
        """Correct letters should use green."""
        self.assertIn("COLOR_GREEN", self.source)

    def test_has_red_for_wrong(self):
        """Wrong guesses should use red."""
        self.assertIn("COLOR_RED", self.source)

    def test_has_yellow_for_hangman(self):
        """Hangman figure should use yellow."""
        self.assertIn("COLOR_YELLOW", self.source)

    def test_has_cyan_for_word(self):
        """Word blanks should use cyan."""
        self.assertIn("COLOR_CYAN", self.source)

    def test_has_init_colors_function(self):
        """Must have an init_colors function."""
        functions = find_all_functions(parse_ast())
        self.assertIn("init_colors", functions)

    def test_hides_cursor(self):
        """Must hide the cursor with curs_set(0)."""
        self.assertIn("curs_set", self.source)


# =============================================================================
# 8. BOX-DRAWING AND VISUAL DISPLAY
# =============================================================================

class TestVisualDisplay(unittest.TestCase):
    """Tests for visual elements: box-drawing, layout."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.tree = parse_ast()
        cls.strings = find_all_string_literals(cls.tree)

    def test_has_box_drawing_borders(self):
        """Must use box-drawing characters for borders."""
        box_chars = set("╔╗╚╝═║")
        all_chars = "".join(self.strings)
        found = [ch for ch in box_chars if ch in all_chars]
        self.assertGreaterEqual(len(found), 5,
                                f"Insufficient box-drawing characters: {found}")

    def test_has_gallows_drawing(self):
        """Hangman stages must contain gallows characters."""
        all_chars = "".join(self.strings)
        gallows_chars = {"┌", "┐", "│", "─", "╧"}
        found = [ch for ch in gallows_chars if ch in all_chars]
        self.assertGreater(len(found), 2,
                           "Insufficient gallows drawing characters")

    def test_has_game_title(self):
        """Must display a game title containing HANGMAN."""
        source_lower = self.source.lower()
        self.assertIn("hangman", source_lower)

    def test_has_draw_box_function(self):
        """Must have a draw_box function for borders."""
        functions = find_all_functions(self.tree)
        self.assertIn("draw_box", functions)

    def test_has_draw_hangman_function(self):
        """Must have a draw_hangman function."""
        functions = find_all_functions(self.tree)
        self.assertIn("draw_hangman", functions)

    def test_has_draw_word_display_function(self):
        """Must have a draw_word_display function."""
        functions = find_all_functions(self.tree)
        self.assertIn("draw_word_display", functions)

    def test_has_star_or_unicode_glyph(self):
        """Must use Unicode glyphs for decoration."""
        all_chars = "".join(self.strings)
        glyphs = {"★", "●", "◆", "✦", "▲", "▼"}
        found = [g for g in glyphs if g in all_chars]
        self.assertGreater(len(found), 0,
                           "No Unicode decoration glyphs found")


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
        # Check for letter range handling (97 = ord('a'), 122 = ord('z'))
        self.assertTrue(
            "97" in self.source or "ord('a')" in self.source,
            "No a-z letter input handling found")

    def test_handles_quit_key(self):
        """Must handle 'q' key for quit."""
        self.assertIn("ord('q')", self.source)

    def test_handles_new_game_key(self):
        """Must handle 'n' key for new game."""
        self.assertIn("ord('n')", self.source)


# =============================================================================
# 10. HANGMAN STAGES CONTENT
# =============================================================================

class TestHangmanStages(unittest.TestCase):
    """Tests for the hangman ASCII art stages."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def test_first_stage_empty(self):
        """First stage should have empty gallows (no body)."""
        stages = self.ns["HANGMAN_STAGES"]
        first = "\n".join(stages[0])
        self.assertNotIn("O", first,
                          "First stage should not have a head")

    def test_last_stage_has_head(self):
        """Last stage should have the head (O)."""
        stages = self.ns["HANGMAN_STAGES"]
        last = "\n".join(stages[-1])
        self.assertIn("O", last,
                       "Last stage must have the head")

    def test_last_stage_has_body(self):
        """Last stage should have the body (|)."""
        stages = self.ns["HANGMAN_STAGES"]
        last = "\n".join(stages[-1])
        # Body line should have | that's part of the figure (not gallows)
        self.assertIn("/", last, "Last stage must have limbs")
        self.assertIn("\\", last, "Last stage must have limbs")

    def test_stages_progress(self):
        """Each stage should have equal or more non-space content than the previous."""
        stages = self.ns["HANGMAN_STAGES"]
        prev_content = 0
        for i, stage in enumerate(stages):
            combined = "".join(stage)
            content = len(combined.replace(" ", ""))
            if i > 0:
                self.assertGreaterEqual(content, prev_content,
                                        f"Stage {i} has less content than stage {i-1}")
            prev_content = content

    def test_max_wrong_matches_stages(self):
        """MAX_WRONG should be len(HANGMAN_STAGES) - 1."""
        ns = self.ns
        self.assertEqual(ns["MAX_WRONG"], len(ns["HANGMAN_STAGES"]) - 1)


if __name__ == "__main__":
    unittest.main()
