#!/usr/bin/env python3
"""
Test suite for space_invaders.py — Terminal Space Invaders
Tests the "known good" benchmark: structure, logic, and behavior.
These tests run WITHOUT a terminal (no curses rendering).
"""

import ast
import os
import stat
import sys
import unittest

# Path to the script under test
INVADERS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "space_invaders.py")


def load_source():
    """Load space_invaders.py source code as a string."""
    with open(INVADERS_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_ast():
    """Parse space_invaders.py into an AST tree."""
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
    """Import space_invaders.py as a module (without running main).

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

    code = compile(tree, INVADERS_PATH, "exec")
    namespace = {"__file__": INVADERS_PATH, "__name__": "space_invaders"}
    exec(code, namespace)
    return namespace


def find_all_functions(tree):
    """Find all function definitions in the AST (including nested)."""
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = node
    return functions


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
    """Tests that space_invaders.py has the right file-level properties."""

    def test_file_exists(self):
        """space_invaders.py must exist."""
        self.assertTrue(os.path.isfile(INVADERS_PATH),
                        f"space_invaders.py not found at {INVADERS_PATH}")

    def test_file_is_executable(self):
        """space_invaders.py must be executable."""
        mode = os.stat(INVADERS_PATH).st_mode
        self.assertTrue(mode & stat.S_IXUSR,
                        "space_invaders.py is not executable (missing user +x)")

    def test_has_shebang(self):
        """Must start with a Python shebang."""
        source = load_source()
        self.assertTrue(source.startswith("#!/"), "Missing shebang line")
        first_line = source.split("\n")[0]
        self.assertIn("python", first_line.lower(),
                      "Shebang doesn't reference python")

    def test_has_docstring(self):
        """Must have a module-level docstring."""
        tree = parse_ast()
        docstring = ast.get_docstring(tree)
        self.assertIsNotNone(docstring, "Missing module docstring")
        self.assertGreater(len(docstring), 10, "Docstring too short")

    def test_syntax_valid(self):
        """Must parse without syntax errors."""
        try:
            parse_ast()
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
        tree = parse_ast()
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
        tree = parse_ast()
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
        cls.tree = parse_ast()
        cls.names = get_top_level_names(cls.tree)
        cls.all_funcs = find_all_functions(cls.tree)
        cls.source = load_source()

    def test_has_main_function(self):
        """Must have a main() function."""
        self.assertIn("main", self.names,
                      "Missing main() function at top level")

    def test_has_player_definition(self):
        """Must define a player/ship entity."""
        source_lower = self.source.lower()
        has_player = any(kw in source_lower for kw in
                         ["player", "ship", "cannon", "defender"])
        self.assertTrue(has_player,
                        "No player/ship definition found in source")

    def test_has_alien_definitions(self):
        """Must define alien/invader entities."""
        source_lower = self.source.lower()
        has_aliens = any(kw in source_lower for kw in
                         ["alien", "invader", "enemy", "enemies"])
        self.assertTrue(has_aliens,
                        "No alien/invader definitions found in source")

    def test_has_bullet_definition(self):
        """Must define bullet/projectile entities."""
        source_lower = self.source.lower()
        has_bullet = any(kw in source_lower for kw in
                         ["bullet", "projectile", "missile", "shot"])
        self.assertTrue(has_bullet,
                        "No bullet/projectile definition found in source")

    def test_has_shield_definition(self):
        """Must define shields/barriers."""
        source_lower = self.source.lower()
        has_shield = any(kw in source_lower for kw in
                         ["shield", "barrier", "bunker", "cover"])
        self.assertTrue(has_shield,
                        "No shield/barrier definition found in source")

    def test_has_game_loop(self):
        """Must have a game loop (while True or similar)."""
        has_while = False
        for node in ast.walk(self.tree):
            if isinstance(node, ast.While):
                has_while = True
                break
        self.assertTrue(has_while,
                        "No while loop found (game needs a main loop)")

    def test_has_collision_detection(self):
        """Must have collision detection logic."""
        source_lower = self.source.lower()
        has_collision = any(kw in source_lower for kw in
                           ["collision", "collide", "hit", "intersect",
                            "check_hit", "detect_hit"])
        self.assertTrue(has_collision,
                        "No collision detection logic found in source")

    def test_uses_curses_wrapper(self):
        """Must call curses.wrapper() for proper terminal handling."""
        self.assertIn("curses.wrapper", self.source,
                      "Must use curses.wrapper() for proper terminal handling")


# =============================================================================
# 3. ALIEN FORMATION TESTS
# =============================================================================

class TestAlienFormation(unittest.TestCase):
    """Tests that aliens are correctly defined with rows and point values."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()
        cls.tree = parse_ast()
        cls.numbers = find_all_number_literals(cls.tree)

    def test_has_multiple_alien_rows(self):
        """Must have multiple rows of aliens (at least 3-4 types)."""
        # Look for row definitions or alien type distinctions
        has_rows = any(kw in self.source_lower for kw in
                       ["row", "alien_type", "alien_row", "formation",
                        "invader_type", "enemy_type"])
        self.assertTrue(has_rows,
                        "No alien row/type definitions found")

    def test_has_alien_point_values(self):
        """Aliens must have point values (10, 20, 30, 40)."""
        has_10 = 10 in self.numbers
        has_20 = 20 in self.numbers
        has_30 = 30 in self.numbers
        has_40 = 40 in self.numbers
        self.assertTrue(has_10 and has_20 and has_30 and has_40,
                        f"Missing alien point values. Need 10, 20, 30, 40. "
                        f"Found 10={has_10}, 20={has_20}, 30={has_30}, 40={has_40}")

    def test_has_alien_movement(self):
        """Aliens must march as a formation (left-right + descend)."""
        has_movement = any(kw in self.source_lower for kw in
                           ["direction", "march", "move_alien", "move_invader",
                            "descend", "drop_down", "shift"])
        self.assertTrue(has_movement,
                        "No alien formation movement logic found")

    def test_aliens_speed_up(self):
        """Aliens must speed up as fewer remain."""
        has_speedup = any(kw in self.source_lower for kw in
                          ["speed_up", "speed up", "faster", "speed",
                           "interval", "tick_rate", "delay"])
        self.assertTrue(has_speedup,
                        "No alien speed-up logic found")

    def test_has_alien_ascii_art(self):
        """Aliens should use ASCII art characters (not just single chars)."""
        # Look for the specified alien art patterns or similar
        art_chars = ["/oo\\", "{@@}", "<**>", "|##|",
                     "oo", "@@", "**", "##"]
        found = any(art in self.source for art in art_chars)
        self.assertTrue(found,
                        "No recognizable alien ASCII art found in source")

    def test_has_alien_animation(self):
        """Aliens should have two-frame animation (alternating sprites)."""
        has_animation = any(kw in self.source_lower for kw in
                            ["frame", "anim", "sprite", "alt",
                             "toggle", "phase", "tick"])
        self.assertTrue(has_animation,
                        "No alien animation frames found (need two-frame alternating sprites)")

    def test_has_alien_shooting(self):
        """Aliens must shoot back at the player."""
        has_alien_shoot = any(kw in self.source_lower for kw in
                              ["alien_shoot", "alien_bullet", "enemy_bullet",
                               "alien_fire", "enemy_fire", "invader_shoot",
                               "invader_bullet", "enemy_shot"])
        self.assertTrue(has_alien_shoot,
                        "No alien shooting logic found")


# =============================================================================
# 4. UFO / BONUS TARGET TESTS
# =============================================================================

class TestUFO(unittest.TestCase):
    """Tests that the UFO bonus target exists."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()
        cls.numbers = find_all_number_literals(parse_ast())

    def test_has_ufo(self):
        """Must have a UFO/bonus target."""
        has_ufo = any(kw in self.source_lower for kw in
                      ["ufo", "bonus", "mystery", "saucer",
                       "flying_saucer", "mother_ship", "mothership"])
        self.assertTrue(has_ufo,
                        "No UFO/bonus target found in source")

    def test_ufo_has_bonus_points(self):
        """UFO must be worth 50-300 bonus points."""
        has_50 = 50 in self.numbers
        has_300 = 300 in self.numbers
        self.assertTrue(has_50 or has_300,
                        "No UFO bonus point values (50 or 300) found")

    def test_ufo_has_ascii_art(self):
        """UFO should have ASCII art representation."""
        ufo_art = ["<==>", "<===>", "(-)", "<=>", "UFO"]
        found = any(art in self.source for art in ufo_art)
        # Also check for ufo drawing logic
        has_draw = "ufo" in self.source_lower and "draw" in self.source_lower
        self.assertTrue(found or has_draw,
                        "No UFO ASCII art found")


# =============================================================================
# 5. SHIELD / BARRIER TESTS
# =============================================================================

class TestShields(unittest.TestCase):
    """Tests that shields/barriers exist and can erode."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()

    def test_shields_exist(self):
        """Must define shields/barriers."""
        has_shield = any(kw in self.source_lower for kw in
                         ["shield", "barrier", "bunker", "cover"])
        self.assertTrue(has_shield,
                        "No shield/barrier system found")

    def test_shields_erode(self):
        """Shields must erode when hit."""
        has_erosion = any(kw in self.source_lower for kw in
                          ["erode", "damage", "destroy", "hit",
                           "degrade", "break", "remove"])
        self.assertTrue(has_erosion,
                        "No shield erosion/damage logic found")

    def test_multiple_shields(self):
        """Should have multiple shield positions (typically 3-4)."""
        # Look for shield count or list of shield positions
        has_multiple = any(kw in self.source_lower for kw in
                           ["shields", "barriers", "bunkers",
                            "num_shield", "shield_count"])
        self.assertTrue(has_multiple,
                        "No indication of multiple shields")


# =============================================================================
# 6. LIVES AND SCORING TESTS
# =============================================================================

class TestLivesAndScoring(unittest.TestCase):
    """Tests the lives and scoring system."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()
        cls.numbers = find_all_number_literals(parse_ast())

    def test_has_lives(self):
        """Must track player lives."""
        has_lives = any(kw in self.source_lower for kw in
                        ["lives", "life", "remaining", "health"])
        self.assertTrue(has_lives,
                        "No lives/health system found")

    def test_starts_with_3_lives(self):
        """Player should start with 3 lives."""
        self.assertIn(3, self.numbers,
                      "Number 3 not found (expected for starting lives)")

    def test_has_score(self):
        """Must track player score."""
        has_score = "score" in self.source_lower
        self.assertTrue(has_score,
                        "No score tracking found")

    def test_has_game_over(self):
        """Must have game over detection."""
        has_gameover = any(kw in self.source_lower for kw in
                          ["game_over", "gameover", "game over",
                           "game_end", "is_over"])
        self.assertTrue(has_gameover,
                        "No game over detection found")

    def test_game_over_when_aliens_reach_bottom(self):
        """Game over should trigger when aliens reach bottom."""
        has_reach_bottom = any(kw in self.source_lower for kw in
                               ["reach", "bottom", "invasion",
                                "invaded", "too_low", "landed"])
        self.assertTrue(has_reach_bottom,
                        "No alien-reaches-bottom game over condition found")


# =============================================================================
# 7. WAVE / LEVEL SYSTEM TESTS
# =============================================================================

class TestWaveSystem(unittest.TestCase):
    """Tests the wave/level progression system."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()

    def test_has_waves(self):
        """Must have wave/level progression."""
        has_wave = any(kw in self.source_lower for kw in
                       ["wave", "level", "stage", "round"])
        self.assertTrue(has_wave,
                        "No wave/level system found")

    def test_waves_get_harder(self):
        """Subsequent waves must increase difficulty."""
        has_difficulty = any(kw in self.source_lower for kw in
                             ["faster", "speed", "harder", "difficult",
                              "increase", "accelerate"])
        self.assertTrue(has_difficulty,
                        "No wave difficulty increase found")

    def test_wave_reset_aliens(self):
        """New wave must spawn a fresh set of aliens."""
        has_reset = any(kw in self.source_lower for kw in
                        ["new_wave", "next_wave", "spawn", "reset",
                         "init_alien", "create_alien", "setup_alien",
                         "init_invader", "create_invader"])
        self.assertTrue(has_reset,
                        "No wave reset/alien respawn logic found")


# =============================================================================
# 8. INPUT HANDLING TESTS
# =============================================================================

class TestInputHandling(unittest.TestCase):
    """Tests that the game handles required key inputs."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_handles_left_right(self):
        """Must handle left/right arrow keys for player movement."""
        has_left = "KEY_LEFT" in self.source
        has_right = "KEY_RIGHT" in self.source
        self.assertTrue(has_left, "Missing KEY_LEFT handler")
        self.assertTrue(has_right, "Missing KEY_RIGHT handler")

    def test_handles_space_bar(self):
        """Must handle space bar for shooting."""
        has_space = any(kw in self.source for kw in
                        ["ord(' ')", 'ord(" ")', "== 32",
                         "== ' '", '== " "', "' '", '" "'])
        self.assertTrue(has_space,
                        "No space bar handler found (needed for shooting)")

    def test_handles_quit_key(self):
        """Must handle q/Q to quit the game."""
        has_quit = any(kw in self.source for kw in
                       ["ord('q')", 'ord("q")', "ord('Q')", 'ord("Q")',
                        "'q'", '"q"', "'Q'", '"Q"'])
        self.assertTrue(has_quit,
                        "No quit key (q/Q) handler found")


# =============================================================================
# 9. CURSES INTEGRATION TESTS
# =============================================================================

class TestCursesIntegration(unittest.TestCase):
    """Tests proper curses integration."""

    @classmethod
    def setUpClass(cls):
        cls.tree = parse_ast()
        cls.functions = find_all_functions(cls.tree)
        cls.source = load_source()

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

    def test_has_color_support(self):
        """Must initialize curses colors."""
        has_color = any(kw in self.source for kw in
                        ["init_pair", "color_pair", "start_color",
                         "use_default_colors"])
        self.assertTrue(has_color,
                        "No curses color initialization found")


# =============================================================================
# 10. VISUAL / DISPLAY TESTS
# =============================================================================

class TestVisualDisplay(unittest.TestCase):
    """Tests that required visual elements are present."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()

    def test_has_score_display(self):
        """Must display score to the player."""
        has_score_display = "score" in self.source_lower
        self.assertTrue(has_score_display,
                        "No score display found")

    def test_has_lives_display(self):
        """Must display remaining lives."""
        has_lives_display = any(kw in self.source_lower for kw in
                                ["lives", "life"])
        self.assertTrue(has_lives_display,
                        "No lives display found")

    def test_has_player_ascii_art(self):
        """Player ship should have ASCII art."""
        player_art = ["/^^\\", "/^\\", "/_\\", "/||\\", "[^]", "(-)",
                      "player", "ship"]
        found = any(art in self.source for art in player_art)
        has_draw_player = any(kw in self.source_lower for kw in
                              ["draw_player", "render_player", "player_sprite",
                               "player_char", "ship_char"])
        self.assertTrue(found or has_draw_player,
                        "No player ASCII art found")

    def test_has_game_over_screen(self):
        """Must show a game over screen."""
        has_gameover_screen = any(kw in self.source_lower for kw in
                                  ["game over", "game_over", "gameover"])
        self.assertTrue(has_gameover_screen,
                        "No game over screen found")

    def test_has_high_score(self):
        """Must have high score tracking."""
        has_highscore = any(kw in self.source_lower for kw in
                            ["high_score", "highscore", "high score",
                             "best_score", "top_score", "hiscore"])
        self.assertTrue(has_highscore,
                        "No high score tracking found")


# =============================================================================
# 11. GAME LOGIC FUNCTION TESTS
# =============================================================================

class TestGameLogicFunctions(unittest.TestCase):
    """Tests that essential game logic functions exist."""

    @classmethod
    def setUpClass(cls):
        cls.tree = parse_ast()
        cls.all_funcs = find_all_functions(cls.tree)
        cls.source_lower = load_source().lower()

    def test_has_collision_function(self):
        """Must have a collision detection function."""
        collision_funcs = [n for n in self.all_funcs
                           if any(kw in n.lower() for kw in
                                  ["collision", "collide", "hit",
                                   "check_hit", "intersect", "detect"])]
        # Also accept inline collision logic
        has_inline = any(kw in self.source_lower for kw in
                         ["collision", "collide", "check_hit"])
        self.assertTrue(len(collision_funcs) > 0 or has_inline,
                        f"No collision function found. Functions: "
                        f"{list(self.all_funcs.keys())}")

    def test_has_draw_or_render_function(self):
        """Must have drawing/rendering functions."""
        draw_funcs = [n for n in self.all_funcs
                      if any(kw in n.lower() for kw in
                             ["draw", "render", "display", "paint"])]
        self.assertGreater(len(draw_funcs), 0,
                           f"No draw/render function found. Functions: "
                           f"{list(self.all_funcs.keys())}")

    def test_has_update_function(self):
        """Must have an update/tick function for game state."""
        update_funcs = [n for n in self.all_funcs
                        if any(kw in n.lower() for kw in
                               ["update", "tick", "step", "advance",
                                "move", "process"])]
        self.assertGreater(len(update_funcs), 0,
                           f"No update/tick function found. Functions: "
                           f"{list(self.all_funcs.keys())}")

    def test_uses_random(self):
        """Must use random module (for alien shooting, UFO timing)."""
        source = load_source()
        has_random = "random" in source
        self.assertTrue(has_random,
                        "No random module usage found (needed for alien shooting, UFO)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
