#!/usr/bin/env python3
"""
Test suite for neon_drift.py -- Terminal Racing Game (Neon Drift)
Tests the "known good" benchmark: structure, logic, and behavior.
These tests run WITHOUT a terminal (no curses rendering).
"""

import ast
import os
import stat
import sys
import unittest

# Path to the script under test
DRIFT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "neon_drift.py")


def load_source():
    """Load neon_drift.py source code as a string."""
    with open(DRIFT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_ast():
    """Parse neon_drift.py into an AST tree."""
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
    """Import neon_drift.py as a module (without running main).

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

    code = compile(tree, DRIFT_PATH, "exec")
    namespace = {"__file__": DRIFT_PATH, "__name__": "neon_drift"}
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
    """Tests that neon_drift.py has the right file-level properties."""

    def test_file_exists(self):
        """neon_drift.py must exist."""
        self.assertTrue(os.path.isfile(DRIFT_PATH),
                        f"neon_drift.py not found at {DRIFT_PATH}")

    def test_file_is_executable(self):
        """neon_drift.py must be executable."""
        mode = os.stat(DRIFT_PATH).st_mode
        self.assertTrue(mode & stat.S_IXUSR,
                        "neon_drift.py is not executable (missing user +x)")

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
        """Must define a player/hoverbike entity."""
        source_lower = self.source.lower()
        has_player = any(kw in source_lower for kw in
                         ["player", "bike", "hoverbike", "racer"])
        self.assertTrue(has_player,
                        "No player/hoverbike definition found in source")

    def test_has_obstacle_definitions(self):
        """Must define obstacle entities."""
        source_lower = self.source.lower()
        has_obstacles = any(kw in source_lower for kw in
                            ["obstacle", "traffic", "barrier", "debris"])
        self.assertTrue(has_obstacles,
                        "No obstacle definitions found in source")

    def test_has_pickup_definition(self):
        """Must define pickup entities."""
        source_lower = self.source.lower()
        has_pickup = any(kw in source_lower for kw in
                         ["pickup", "powerup", "power_up", "collectible",
                          "nitro", "sats", "repair"])
        self.assertTrue(has_pickup,
                        "No pickup/powerup definition found in source")

    def test_has_lane_system(self):
        """Must have a lane-based movement system."""
        source_lower = self.source.lower()
        has_lanes = any(kw in source_lower for kw in
                        ["lane", "num_lanes", "lane_center"])
        self.assertTrue(has_lanes,
                        "No lane system found in source")

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
                           ["collision", "collide", "hit", "check_player",
                            "detect_hit"])
        self.assertTrue(has_collision,
                        "No collision detection logic found in source")

    def test_uses_curses_wrapper(self):
        """Must call curses.wrapper() for proper terminal handling."""
        self.assertIn("curses.wrapper", self.source,
                      "Must use curses.wrapper() for proper terminal handling")


# =============================================================================
# 3. PLAYER DEFINITION TESTS
# =============================================================================

class TestPlayerDefinition(unittest.TestCase):
    """Tests the player/hoverbike entity and its properties."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()
        cls.tree = parse_ast()
        cls.all_funcs = find_all_functions(cls.tree)

    def test_has_create_player(self):
        """Must have a function to create the player entity."""
        player_funcs = [n for n in self.all_funcs
                        if any(kw in n.lower() for kw in
                               ["player", "bike", "racer"])]
        self.assertGreater(len(player_funcs), 0,
                           "No player creation function found")

    def test_player_has_shield(self):
        """Player must have a shield/health system."""
        has_shield = any(kw in self.source_lower for kw in
                         ["shield", "health", "hp", "hit_points"])
        self.assertTrue(has_shield,
                        "No player shield/health system found")

    def test_starting_shield(self):
        """Player should start with 3 shield points."""
        numbers = find_all_number_literals(self.tree)
        self.assertIn(3, numbers,
                      "Number 3 not found (expected for starting shield)")

    def test_player_has_speed(self):
        """Player must track speed."""
        has_speed = "speed" in self.source_lower
        self.assertTrue(has_speed,
                        "No speed tracking found")

    def test_player_has_nitro(self):
        """Player must have a nitro/boost system."""
        has_nitro = any(kw in self.source_lower for kw in
                        ["nitro", "boost", "turbo"])
        self.assertTrue(has_nitro,
                        "No nitro/boost system found")

    def test_player_has_lane(self):
        """Player must have a lane position."""
        has_lane = "lane" in self.source_lower
        self.assertTrue(has_lane,
                        "No lane position found for player")


# =============================================================================
# 4. OBSTACLE SYSTEM TESTS
# =============================================================================

class TestObstacleSystem(unittest.TestCase):
    """Tests the obstacle spawning and type system."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()
        cls.tree = parse_ast()
        cls.all_funcs = find_all_functions(cls.tree)

    def test_has_obstacle_types(self):
        """Must define multiple obstacle types."""
        types_found = sum(1 for kw in ["car", "truck", "barrier", "drone"]
                          if kw in self.source_lower)
        self.assertGreaterEqual(types_found, 3,
                                "Need at least 3 different obstacle types")

    def test_has_spawn_function(self):
        """Must have an obstacle spawning function."""
        spawn_funcs = [n for n in self.all_funcs
                       if any(kw in n.lower() for kw in
                              ["spawn", "create_obs", "generate"])]
        self.assertGreater(len(spawn_funcs), 0,
                           "No obstacle spawn function found")

    def test_has_weighted_selection(self):
        """Obstacle type selection should be weighted by difficulty."""
        has_weight = any(kw in self.source_lower for kw in
                         ["weight", "ratio", "weighted", "probability"])
        self.assertTrue(has_weight,
                        "No weighted obstacle selection found")

    def test_has_gap_enforcement(self):
        """Must enforce minimum gap between obstacles."""
        has_gap = any(kw in self.source_lower for kw in
                      ["gap", "min_obstacle", "spacing", "too_close"])
        self.assertTrue(has_gap,
                        "No obstacle gap enforcement found")

    def test_obstacles_scroll_down(self):
        """Obstacles must scroll downward (toward player)."""
        has_scroll = any(kw in self.source_lower for kw in
                         ["scroll", "move_down", "shift", "y += 1",
                          'y"] += 1', "y'] += 1"])
        self.assertTrue(has_scroll,
                        "No obstacle scrolling logic found")


# =============================================================================
# 5. PICKUP SYSTEM TESTS
# =============================================================================

class TestPickupSystem(unittest.TestCase):
    """Tests the pickup/powerup system."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()
        cls.tree = parse_ast()

    def test_has_nitro_pickup(self):
        """Must have nitro/boost pickups."""
        has_nitro = any(kw in self.source_lower for kw in
                        ["nitro", "boost", "turbo"])
        self.assertTrue(has_nitro,
                        "No nitro pickup type found")

    def test_has_sats_pickup(self):
        """Must have sats/coin score pickups."""
        has_sats = any(kw in self.source_lower for kw in
                       ["sats", "coin", "money", "dollar", "credit"])
        self.assertTrue(has_sats,
                        "No sats/coin pickup type found")

    def test_has_repair_pickup(self):
        """Must have repair/health pickups."""
        has_repair = any(kw in self.source_lower for kw in
                         ["repair", "heal", "medkit", "restore"])
        self.assertTrue(has_repair,
                        "No repair/health pickup type found")

    def test_pickup_spawn_function(self):
        """Must have a pickup spawning function."""
        all_funcs = find_all_functions(self.tree)
        pickup_funcs = [n for n in all_funcs
                        if "pickup" in n.lower() and
                        any(kw in n.lower() for kw in
                            ["spawn", "create", "pick"])]
        has_spawn = len(pickup_funcs) > 0 or "spawn_pickup" in self.source_lower
        self.assertTrue(has_spawn,
                        "No pickup spawn function found")


# =============================================================================
# 6. COLLISION DETECTION TESTS
# =============================================================================

class TestCollisionDetection(unittest.TestCase):
    """Tests the collision detection system."""

    @classmethod
    def setUpClass(cls):
        cls.mod = import_module()
        cls.source = load_source()
        cls.source_lower = cls.source.lower()

    def test_obstacle_collision_function_exists(self):
        """Must have an obstacle collision detection function."""
        has_func = any(kw in self.source_lower for kw in
                       ["check_player_obstacle", "player_obstacle_collision",
                        "obstacle_collision", "check_collision"])
        self.assertTrue(has_func,
                        "No obstacle collision function found")

    def test_pickup_collision_function_exists(self):
        """Must have a pickup collision detection function."""
        has_func = any(kw in self.source_lower for kw in
                       ["check_player_pickup", "player_pickup_collision",
                        "pickup_collision", "collect_pickup"])
        self.assertTrue(has_func,
                        "No pickup collision function found")

    def test_obstacle_collision_uses_lane(self):
        """Collision detection should use lane comparison."""
        has_lane_check = "lane" in self.source_lower
        self.assertTrue(has_lane_check,
                        "Collision detection doesn't appear to use lanes")

    def test_obstacle_collision_logic(self):
        """check_player_obstacle_collision should detect same-lane overlap."""
        func = self.mod.get("check_player_obstacle_collision")
        if func is None:
            self.skipTest("check_player_obstacle_collision not found")
        player = {"lane": 2, "y": 20}
        obstacles = [
            {"lane": 0, "y": 20},   # different lane
            {"lane": 2, "y": 20},   # same lane, same y
        ]
        result = func(player, obstacles)
        self.assertIsNotNone(result, "Should detect collision in same lane")
        self.assertEqual(result["lane"], 2)

    def test_obstacle_collision_miss(self):
        """Should return None when no collision."""
        func = self.mod.get("check_player_obstacle_collision")
        if func is None:
            self.skipTest("check_player_obstacle_collision not found")
        player = {"lane": 0, "y": 20}
        obstacles = [
            {"lane": 2, "y": 20},
            {"lane": 3, "y": 10},
        ]
        result = func(player, obstacles)
        self.assertIsNone(result, "Should not detect collision in different lane")

    def test_pickup_collision_logic(self):
        """check_player_pickup_collision should detect same-lane overlap."""
        func = self.mod.get("check_player_pickup_collision")
        if func is None:
            self.skipTest("check_player_pickup_collision not found")
        player = {"lane": 1, "y": 15}
        pickups = [
            {"lane": 1, "y": 15, "type": "sats"},
        ]
        result = func(player, pickups)
        self.assertIsNotNone(result, "Should detect pickup in same lane")


# =============================================================================
# 7. SCORING SYSTEM TESTS
# =============================================================================

class TestScoringSystem(unittest.TestCase):
    """Tests the scoring and high score system."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()
        cls.tree = parse_ast()
        cls.all_funcs = find_all_functions(cls.tree)

    def test_has_score_tracking(self):
        """Must track player score."""
        has_score = "score" in self.source_lower
        self.assertTrue(has_score,
                        "No score tracking found")

    def test_has_distance_tracking(self):
        """Must track distance traveled."""
        has_distance = "distance" in self.source_lower
        self.assertTrue(has_distance,
                        "No distance tracking found")

    def test_has_sats_scoring(self):
        """Sats should contribute to score."""
        has_sats_score = "sats" in self.source_lower
        self.assertTrue(has_sats_score,
                        "No sats scoring component found")

    def test_has_high_score_load(self):
        """Must have high score load function."""
        has_load = "load_high_score" in self.source
        self.assertTrue(has_load,
                        "No load_high_score function found")

    def test_has_high_score_save(self):
        """Must have high score save function."""
        has_save = "save_high_score" in self.source
        self.assertTrue(has_save,
                        "No save_high_score function found")

    def test_high_score_file_path(self):
        """High score should be saved to ~/.shelly-ops/ directory."""
        has_path = "shelly-ops" in self.source
        self.assertTrue(has_path,
                        "High score not saved to ~/.shelly-ops/")

    def test_has_game_over(self):
        """Must have game over detection."""
        has_gameover = any(kw in self.source_lower for kw in
                          ["game_over", "gameover", "game over"])
        self.assertTrue(has_gameover,
                        "No game over detection found")


# =============================================================================
# 8. INPUT HANDLING TESTS
# =============================================================================

class TestInputHandling(unittest.TestCase):
    """Tests that the game handles required key inputs."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_handles_left_right(self):
        """Must handle left/right arrow keys for steering."""
        has_left = "KEY_LEFT" in self.source
        has_right = "KEY_RIGHT" in self.source
        self.assertTrue(has_left, "Missing KEY_LEFT handler")
        self.assertTrue(has_right, "Missing KEY_RIGHT handler")

    def test_handles_wasd(self):
        """Must handle A/D keys for steering."""
        has_a = any(kw in self.source for kw in
                    ["ord('a')", 'ord("a")', "ord('A')", 'ord("A")'])
        has_d = any(kw in self.source for kw in
                    ["ord('d')", 'ord("d")', "ord('D')", 'ord("D")'])
        self.assertTrue(has_a, "Missing A key handler")
        self.assertTrue(has_d, "Missing D key handler")

    def test_handles_space_bar(self):
        """Must handle space bar for nitro activation."""
        has_space = any(kw in self.source for kw in
                        ["ord(' ')", 'ord(" ")', "== 32"])
        self.assertTrue(has_space,
                        "No space bar handler found (needed for nitro)")

    def test_handles_quit_key(self):
        """Must handle q/Q to quit the game."""
        has_quit = any(kw in self.source for kw in
                       ["ord('q')", 'ord("q")', "ord('Q')", 'ord("Q")'])
        self.assertTrue(has_quit,
                        "No quit key (q/Q) handler found")

    def test_handles_restart_key(self):
        """Must handle r/R to restart after game over."""
        has_restart = any(kw in self.source for kw in
                          ["ord('r')", 'ord("r")', "ord('R')", 'ord("R")'])
        self.assertTrue(has_restart,
                        "No restart key (r/R) handler found")

    def test_handles_toggle_key(self):
        """Must handle t/T to toggle NerdFont/ASCII mode."""
        has_toggle = any(kw in self.source for kw in
                         ["ord('t')", 'ord("t")', "ord('T')", 'ord("T")'])
        self.assertTrue(has_toggle,
                        "No toggle key (t/T) handler found")


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

    def test_has_nodelay(self):
        """Must use nodelay mode for non-blocking input."""
        has_nodelay = "nodelay" in self.source
        self.assertTrue(has_nodelay,
                        "No nodelay mode found (needed for real-time input)")

    def test_has_cursor_hidden(self):
        """Must hide the cursor."""
        has_curs_set = "curs_set" in self.source
        self.assertTrue(has_curs_set,
                        "No curs_set found (cursor should be hidden)")


# =============================================================================
# 10. VISUAL DISPLAY TESTS
# =============================================================================

class TestVisualDisplay(unittest.TestCase):
    """Tests that required visual elements are present."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()
        cls.all_funcs = find_all_functions(parse_ast())

    def test_has_score_display(self):
        """Must display score to the player."""
        has_score_display = "score" in self.source_lower
        self.assertTrue(has_score_display,
                        "No score display found")

    def test_has_shield_display(self):
        """Must display shield/health status."""
        has_shield_display = any(kw in self.source_lower for kw in
                                 ["shield", "heart", "health"])
        self.assertTrue(has_shield_display,
                        "No shield display found")

    def test_has_nitro_gauge(self):
        """Must display nitro fuel gauge."""
        has_nitro_gauge = any(kw in self.source_lower for kw in
                              ["nitro", "fuel", "gauge", "bar"])
        self.assertTrue(has_nitro_gauge,
                        "No nitro gauge display found")

    def test_has_speed_display(self):
        """Must display current speed."""
        has_speed = any(kw in self.source_lower for kw in
                        ["spd", "speed"])
        self.assertTrue(has_speed,
                        "No speed display found")

    def test_has_game_over_screen(self):
        """Must show a game over screen."""
        has_gameover_screen = any(kw in self.source_lower for kw in
                                  ["game over", "game_over", "gameover"])
        self.assertTrue(has_gameover_screen,
                        "No game over screen found")

    def test_has_title_screen(self):
        """Must have a title/start screen."""
        has_title = any(kw in self.source_lower for kw in
                        ["title", "start_screen", "title_screen",
                         "press any key", "press to start"])
        self.assertTrue(has_title,
                        "No title screen found")

    def test_has_high_score_display(self):
        """Must display high score."""
        has_highscore = any(kw in self.source_lower for kw in
                            ["high_score", "highscore", "high score",
                             "best_score", "hi:"])
        self.assertTrue(has_highscore,
                        "No high score display found")

    def test_has_nerd_font_glyphs(self):
        """Must have Nerd Font glyph definitions."""
        has_nerd = any(kw in self.source_lower for kw in
                       ["nerd", "glyph", "nf_", "\\uf"])
        self.assertTrue(has_nerd,
                        "No Nerd Font glyph definitions found")

    def test_has_ascii_fallback(self):
        """Must have ASCII fallback mode."""
        has_ascii = any(kw in self.source_lower for kw in
                        ["ascii", "fallback", "toggle"])
        self.assertTrue(has_ascii,
                        "No ASCII fallback mode found")

    def test_has_draw_functions(self):
        """Must have multiple draw functions."""
        draw_funcs = [n for n in self.all_funcs
                      if any(kw in n.lower() for kw in
                             ["draw", "render"])]
        self.assertGreaterEqual(len(draw_funcs), 4,
                                f"Need at least 4 draw functions, found: "
                                f"{[n for n in draw_funcs]}")

    def test_has_road_drawing(self):
        """Must draw road edges and lane dividers."""
        has_road = any(kw in self.source_lower for kw in
                       ["draw_road", "road_edge", "lane_divider",
                        "road", "divider"])
        self.assertTrue(has_road,
                        "No road drawing found")

    def test_has_rain_effect(self):
        """Must have a rain visual effect."""
        has_rain = "rain" in self.source_lower
        self.assertTrue(has_rain,
                        "No rain effect found")

    def test_has_building_margins(self):
        """Must have building/parallax margin visuals."""
        has_buildings = any(kw in self.source_lower for kw in
                            ["building", "margin", "parallax"])
        self.assertTrue(has_buildings,
                        "No building margins found")


# =============================================================================
# 11. GAME LOGIC FUNCTION TESTS
# =============================================================================

class TestGameLogicFunctions(unittest.TestCase):
    """Tests essential game logic functions exist and work."""

    @classmethod
    def setUpClass(cls):
        cls.tree = parse_ast()
        cls.all_funcs = find_all_functions(cls.tree)
        cls.source_lower = load_source().lower()
        cls.mod = import_module()

    def test_has_collision_function(self):
        """Must have a collision detection function."""
        collision_funcs = [n for n in self.all_funcs
                           if any(kw in n.lower() for kw in
                                  ["collision", "collide", "hit",
                                   "check_player"])]
        self.assertGreater(len(collision_funcs), 0,
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
                                "scroll", "spawn"])]
        self.assertGreater(len(update_funcs), 0,
                           f"No update/tick function found. Functions: "
                           f"{list(self.all_funcs.keys())}")

    def test_uses_random(self):
        """Must use random module (for obstacle spawning, pickup spawning)."""
        source = load_source()
        has_random = "random" in source
        self.assertTrue(has_random,
                        "No random module usage found")

    def test_calculate_layout_exists(self):
        """Must have a layout calculation function."""
        func = self.mod.get("calculate_layout")
        self.assertIsNotNone(func,
                             "calculate_layout function not found")

    def test_calculate_layout_returns_dict(self):
        """calculate_layout should return a layout dict."""
        func = self.mod.get("calculate_layout")
        if func is None:
            self.skipTest("calculate_layout not found")
        layout = func(40, 80)
        self.assertIsInstance(layout, dict)
        self.assertIn("road_left", layout)
        self.assertIn("road_right", layout)
        self.assertIn("lane_centers", layout)

    def test_layout_has_correct_lane_count(self):
        """Layout should have NUM_LANES lane centers."""
        func = self.mod.get("calculate_layout")
        num_lanes = self.mod.get("NUM_LANES", 5)
        if func is None:
            self.skipTest("calculate_layout not found")
        layout = func(40, 80)
        self.assertEqual(len(layout["lane_centers"]), num_lanes)

    def test_create_player_exists(self):
        """Must have a player creation function."""
        func = self.mod.get("create_player")
        self.assertIsNotNone(func,
                             "create_player function not found")

    def test_create_player_returns_dict(self):
        """create_player should return a player dict."""
        calc_layout = self.mod.get("calculate_layout")
        create_player = self.mod.get("create_player")
        if calc_layout is None or create_player is None:
            self.skipTest("Required functions not found")
        layout = calc_layout(40, 80)
        player = create_player(layout)
        self.assertIsInstance(player, dict)
        self.assertIn("lane", player)
        self.assertIn("shield", player)
        self.assertIn("speed", player)

    def test_update_scroll_function(self):
        """Must have a scroll update function."""
        func = self.mod.get("update_scroll")
        self.assertIsNotNone(func,
                             "update_scroll function not found")

    def test_update_nitro_function(self):
        """Must have a nitro update function."""
        func = self.mod.get("update_nitro")
        self.assertIsNotNone(func,
                             "update_nitro function not found")

    def test_nitro_drains(self):
        """Nitro should drain fuel when active."""
        func = self.mod.get("update_nitro")
        if func is None:
            self.skipTest("update_nitro not found")
        player = {"nitro_active": True, "nitro_fuel": 50}
        func(player)
        self.assertLess(player["nitro_fuel"], 50,
                        "Nitro fuel should decrease when active")

    def test_nitro_deactivates_when_empty(self):
        """Nitro should deactivate when fuel reaches 0."""
        func = self.mod.get("update_nitro")
        if func is None:
            self.skipTest("update_nitro not found")
        player = {"nitro_active": True, "nitro_fuel": 1}
        func(player)
        self.assertFalse(player["nitro_active"],
                         "Nitro should deactivate when fuel is empty")

    def test_get_char_nerd_mode(self):
        """get_char should return Nerd Font glyph in nerd mode."""
        func = self.mod.get("get_char")
        if func is None:
            self.skipTest("get_char not found")
        result = func("bike", True)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_get_char_ascii_mode(self):
        """get_char should return ASCII char in ASCII mode."""
        func = self.mod.get("get_char")
        if func is None:
            self.skipTest("get_char not found")
        result = func("bike", False)
        self.assertIsInstance(result, str)
        self.assertTrue(result.isascii(),
                        "ASCII mode should return ASCII characters")


# =============================================================================
# 12. DIFFICULTY PROGRESSION TESTS
# =============================================================================

class TestDifficultyProgression(unittest.TestCase):
    """Tests that difficulty increases over time."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()
        cls.tree = parse_ast()
        cls.mod = import_module()

    def test_speed_increases(self):
        """Speed must increase over time."""
        has_speed_increase = any(kw in self.source_lower for kw in
                                 ["speed_increment", "speed +=", "speed_up",
                                  "accelerate", "faster"])
        self.assertTrue(has_speed_increase,
                        "No speed increase mechanic found")

    def test_has_max_speed(self):
        """Must have a maximum speed cap."""
        has_max = any(kw in self.source_lower for kw in
                      ["max_speed", "speed_cap", "speed_limit"])
        self.assertTrue(has_max,
                        "No maximum speed cap found")

    def test_obstacle_difficulty_scales(self):
        """Obstacle types should scale with speed/difficulty."""
        has_scaling = any(kw in self.source_lower for kw in
                          ["weight", "ratio", "speed", "difficulty",
                           "pick_obstacle_type"])
        self.assertTrue(has_scaling,
                        "No difficulty scaling for obstacles found")

    def test_pick_obstacle_type_exists(self):
        """Must have a function to pick obstacle types."""
        func = self.mod.get("pick_obstacle_type")
        self.assertIsNotNone(func,
                             "pick_obstacle_type function not found")

    def test_invincibility_frames(self):
        """Player must get invincibility frames after being hit."""
        has_iframes = any(kw in self.source_lower for kw in
                          ["invincib", "i_frame", "iframe", "invulner",
                           "grace_period"])
        self.assertTrue(has_iframes,
                        "No invincibility frames found after collision")

    def test_terminal_size_check(self):
        """Must check for minimum terminal size."""
        has_size_check = any(kw in self.source_lower for kw in
                             ["too small", "min_width", "min_height",
                              "getmaxyx", "terminal"])
        self.assertTrue(has_size_check,
                        "No terminal size check found")


if __name__ == "__main__":
    unittest.main(verbosity=2)
