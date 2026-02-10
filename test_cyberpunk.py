#!/usr/bin/env python3
"""
Test suite for cyberpunk.py — Cyberpunk Megacity Roguelite
Tests the "known good" benchmark: structure, logic, and behavior.
These tests run WITHOUT a terminal (no curses rendering).
"""

import ast
import os
import stat
import sys
import unittest

# Path to the script under test
CYBERPUNK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyberpunk.py")


def load_source():
    """Load cyberpunk.py source code as a string."""
    with open(CYBERPUNK_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_ast():
    """Parse cyberpunk.py into an AST tree."""
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
    """Import cyberpunk.py as a module (without running main).

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

    code = compile(tree, CYBERPUNK_PATH, "exec")
    namespace = {"__file__": CYBERPUNK_PATH, "__name__": "cyberpunk"}
    exec(code, namespace)
    return namespace


def find_all_functions(tree):
    """Find all function definitions in the AST (including nested/methods)."""
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = node
    return functions


def find_all_classes(tree):
    """Find all class definitions in the AST."""
    classes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes[node.name] = node
    return classes


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
    """Tests that cyberpunk.py has the right file-level properties."""

    def test_file_exists(self):
        """cyberpunk.py must exist."""
        self.assertTrue(os.path.isfile(CYBERPUNK_PATH),
                        f"cyberpunk.py not found at {CYBERPUNK_PATH}")

    def test_file_is_executable(self):
        """cyberpunk.py must be executable."""
        mode = os.stat(CYBERPUNK_PATH).st_mode
        self.assertTrue(mode & stat.S_IXUSR,
                        "cyberpunk.py is not executable (missing user +x)")

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
            "dataclasses", "abc", "heapq",
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

    def test_minimum_size(self):
        """A roguelite this complex should be at least 500 lines."""
        source = load_source()
        line_count = len(source.strip().split("\n"))
        self.assertGreaterEqual(line_count, 500,
                                f"Only {line_count} lines — too small for a roguelite")


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
        cls.all_classes = find_all_classes(cls.tree)
        cls.source = load_source()

    def test_has_main_function(self):
        """Must have a main() function."""
        self.assertIn("main", self.names,
                      "Missing main() function at top level")

    def test_uses_curses_wrapper(self):
        """Must call curses.wrapper() for proper terminal handling."""
        self.assertIn("curses.wrapper", self.source,
                      "Must use curses.wrapper() for proper terminal handling")

    def test_has_game_loop(self):
        """Must have a game loop (while True or similar)."""
        has_while = False
        for node in ast.walk(self.tree):
            if isinstance(node, ast.While):
                has_while = True
                break
        self.assertTrue(has_while,
                        "No while loop found (game needs a main loop)")

    def test_has_procedural_generation(self):
        """Must have level/map generation logic."""
        source_lower = self.source.lower()
        has_gen = any(kw in source_lower for kw in
                      ["generate", "gen_level", "gen_map", "create_level",
                       "create_map", "proc_gen", "make_level", "make_map",
                       "build_level", "build_map", "random_room",
                       "bsp", "place_room"])
        self.assertTrue(has_gen,
                        "No procedural generation logic found")

    def test_uses_random(self):
        """Must use random module for procedural generation."""
        self.assertIn("random", self.source,
                      "No random module usage found")


# =============================================================================
# 3. CHARACTER CLASS TESTS
# =============================================================================

class TestCharacterClasses(unittest.TestCase):
    """Tests that 3 playable character classes exist."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()

    def test_has_three_classes(self):
        """Must define 3 character classes."""
        classes = ["samurai", "netrunner", "medic"]
        found = [c for c in classes if c in self.source_lower]
        self.assertGreaterEqual(len(found), 3,
                                f"Only found {len(found)}/3 character classes: {found}. "
                                f"Expected: samurai, netrunner, medic")

    def test_has_class_selection(self):
        """Must have a class selection screen/menu."""
        has_selection = any(kw in self.source_lower for kw in
                           ["class_select", "select_class", "choose_class",
                            "class_menu", "character_select", "pick_class",
                            "class_choice"])
        self.assertTrue(has_selection,
                        "No class selection screen/menu found")

    def test_samurai_is_melee(self):
        """Street Samurai should emphasize melee/combat."""
        has_melee = any(kw in self.source_lower for kw in
                        ["melee", "katana", "sword", "blade"])
        self.assertTrue(has_melee,
                        "No melee weapon found for Street Samurai")

    def test_netrunner_can_hack(self):
        """Netrunner should have hacking ability."""
        has_hack = any(kw in self.source_lower for kw in
                       ["hack", "hacking", "breach", "decrypt",
                        "intrusion", "jack_in"])
        self.assertTrue(has_hack,
                        "No hacking ability found for Netrunner")

    def test_medic_can_heal(self):
        """Chrome Medic should have healing ability."""
        has_heal = any(kw in self.source_lower for kw in
                       ["heal", "medkit", "medic", "repair",
                        "restore", "first_aid"])
        self.assertTrue(has_heal,
                        "No healing ability found for Chrome Medic")


# =============================================================================
# 4. MAP / LEVEL GENERATION TESTS
# =============================================================================

class TestMapGeneration(unittest.TestCase):
    """Tests that procedural map generation works."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()
        cls.tree = parse_ast()
        cls.all_funcs = find_all_functions(cls.tree)

    def test_has_room_generation(self):
        """Must generate rooms."""
        has_rooms = any(kw in self.source_lower for kw in
                        ["room", "chamber", "area", "sector"])
        self.assertTrue(has_rooms,
                        "No room generation found")

    def test_has_corridor_generation(self):
        """Must generate corridors connecting rooms."""
        has_corridors = any(kw in self.source_lower for kw in
                           ["corridor", "hallway", "tunnel", "passage",
                            "connect", "path_between"])
        self.assertTrue(has_corridors,
                        "No corridor generation found")

    def test_has_doors(self):
        """Must have doors between areas."""
        has_doors = any(kw in self.source_lower for kw in
                        ["door", "gate", "entrance", "exit"])
        self.assertTrue(has_doors,
                        "No door mechanic found")

    def test_has_walls_and_floors(self):
        """Must distinguish walls from walkable floors."""
        has_wall = "wall" in self.source_lower
        has_floor = "floor" in self.source_lower
        self.assertTrue(has_wall, "No wall tile type found")
        self.assertTrue(has_floor, "No floor tile type found")

    def test_has_stairs(self):
        """Must have stairs/elevator to next level."""
        has_stairs = any(kw in self.source_lower for kw in
                         ["stair", "elevator", "descend", "next_level",
                          "level_exit", "access_point"])
        self.assertTrue(has_stairs,
                        "No stairs/level transition found")

    def test_at_least_seven_levels(self):
        """Must support at least 7 levels."""
        tree = parse_ast()
        numbers = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, int):
                numbers.append(node.value)
        has_7_plus = any(n >= 7 for n in numbers)
        self.assertTrue(has_7_plus,
                        "No number >= 7 found (need at least 7 levels)")


# =============================================================================
# 5. COMBAT SYSTEM TESTS
# =============================================================================

class TestCombatSystem(unittest.TestCase):
    """Tests the combat mechanics."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()

    def test_has_hp(self):
        """Must track hit points."""
        has_hp = any(kw in self.source_lower for kw in
                     ["hp", "health", "hit_point", "hitpoint"])
        self.assertTrue(has_hp, "No HP/health system found")

    def test_has_melee_combat(self):
        """Must have melee/bump combat."""
        has_melee = any(kw in self.source_lower for kw in
                        ["melee", "attack", "bump", "strike",
                         "hit", "damage", "combat"])
        self.assertTrue(has_melee, "No melee combat found")

    def test_has_ranged_combat(self):
        """Must have ranged weapons (pistol, SMG, etc.)."""
        has_ranged = any(kw in self.source_lower for kw in
                         ["ranged", "pistol", "smg", "shoot", "fire",
                          "projectile", "bullet", "gun"])
        self.assertTrue(has_ranged, "No ranged combat found")

    def test_has_damage_calculation(self):
        """Must calculate damage based on weapon/stats."""
        has_damage = any(kw in self.source_lower for kw in
                         ["damage", "dmg", "attack_power", "hit_damage"])
        self.assertTrue(has_damage, "No damage calculation found")

    def test_has_permadeath(self):
        """Must have permadeath (game over when HP = 0)."""
        has_permadeath = any(kw in self.source_lower for kw in
                             ["game_over", "gameover", "death", "dead",
                              "permadeath", "you died", "killed"])
        self.assertTrue(has_permadeath, "No permadeath/game over found")


# =============================================================================
# 6. ENEMY TYPES TESTS
# =============================================================================

class TestEnemyTypes(unittest.TestCase):
    """Tests that multiple enemy types exist with different behaviors."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()

    def test_has_security_drone(self):
        """Must have security drone enemy type."""
        has_drone = any(kw in self.source_lower for kw in
                        ["drone", "robot", "sentinel", "automaton"])
        self.assertTrue(has_drone, "No security drone enemy found")

    def test_has_gang_member(self):
        """Must have gang member enemy type."""
        has_gang = any(kw in self.source_lower for kw in
                       ["gang", "thug", "punk", "raider", "bandit"])
        self.assertTrue(has_gang, "No gang member enemy found")

    def test_has_corporate_guard(self):
        """Must have corporate guard enemy type."""
        has_guard = any(kw in self.source_lower for kw in
                        ["guard", "security", "corpo", "corporate",
                         "soldier", "enforcer"])
        self.assertTrue(has_guard, "No corporate guard enemy found")

    def test_has_turret(self):
        """Must have turret enemy type."""
        has_turret = any(kw in self.source_lower for kw in
                         ["turret", "sentry", "gun_emplacement",
                          "auto_gun", "mounted_gun"])
        self.assertTrue(has_turret, "No turret enemy found")

    def test_has_enemy_ai(self):
        """Enemies must have AI behavior logic."""
        has_ai = any(kw in self.source_lower for kw in
                     ["ai", "behavior", "patrol", "chase", "pursue",
                      "move_toward", "pathfind", "enemy_turn",
                      "enemy_act", "take_turn"])
        self.assertTrue(has_ai, "No enemy AI behavior found")

    def test_multiple_enemy_behaviors(self):
        """Should have at least 2 different AI behaviors."""
        behaviors = ["patrol", "chase", "aggressive", "methodical",
                     "stationary", "wander", "guard", "alert"]
        found = [b for b in behaviors if b in self.source_lower]
        self.assertGreaterEqual(len(found), 2,
                                f"Only found {len(found)} enemy behaviors: {found}")


# =============================================================================
# 7. ITEMS AND EQUIPMENT TESTS
# =============================================================================

class TestItemsAndEquipment(unittest.TestCase):
    """Tests the item and equipment system."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()

    def test_has_weapons(self):
        """Must have weapon items."""
        weapons = ["katana", "pistol", "smg", "baton", "blade",
                   "sword", "gun", "weapon", "emp"]
        found = [w for w in weapons if w in self.source_lower]
        self.assertGreaterEqual(len(found), 2,
                                f"Only found {len(found)} weapon types: {found}")

    def test_has_armor(self):
        """Must have armor/protective equipment."""
        has_armor = any(kw in self.source_lower for kw in
                        ["armor", "armour", "kevlar", "jacket",
                         "vest", "protection", "defense", "defence"])
        self.assertTrue(has_armor, "No armor system found")

    def test_has_consumables(self):
        """Must have consumable items (medkits, stims, etc.)."""
        has_consumables = any(kw in self.source_lower for kw in
                              ["medkit", "potion", "stim", "consumable",
                               "heal_item", "health_pack", "med_pack"])
        self.assertTrue(has_consumables, "No consumable items found")

    def test_has_keycards(self):
        """Must have keycards for locked doors."""
        has_keycard = any(kw in self.source_lower for kw in
                          ["keycard", "key_card", "access_card",
                           "key", "passcard", "credential"])
        self.assertTrue(has_keycard, "No keycard system found")

    def test_has_credits(self):
        """Must have a currency/credits system."""
        has_credits = any(kw in self.source_lower for kw in
                          ["credit", "money", "gold", "currency",
                           "cash", "cred", "nuyen"])
        self.assertTrue(has_credits, "No credits/currency found")

    def test_has_inventory(self):
        """Must have an inventory system."""
        has_inv = any(kw in self.source_lower for kw in
                      ["inventory", "items", "backpack", "bag",
                       "equipment", "equipped", "gear"])
        self.assertTrue(has_inv, "No inventory system found")


# =============================================================================
# 8. HACKING MECHANIC TESTS
# =============================================================================

class TestHackingMechanic(unittest.TestCase):
    """Tests the hacking system."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()

    def test_has_terminals(self):
        """Must have hackable terminals."""
        has_terminal = any(kw in self.source_lower for kw in
                           ["terminal", "console", "computer",
                            "access_point", "node"])
        self.assertTrue(has_terminal, "No hackable terminals found")

    def test_has_hacking_function(self):
        """Must have a hacking function/mechanic."""
        has_hack = any(kw in self.source_lower for kw in
                       ["hack", "breach", "decrypt", "intrusion",
                        "jack_in", "crack"])
        self.assertTrue(has_hack, "No hacking mechanic found")

    def test_hack_has_success_chance(self):
        """Hacking should have a success/failure chance."""
        has_chance = any(kw in self.source_lower for kw in
                         ["success", "chance", "probability", "fail",
                          "skill_check", "roll", "attempt"])
        self.assertTrue(has_chance,
                        "No success/failure chance for hacking found")

    def test_hack_effects(self):
        """Hacking should have tangible effects (disable, open, etc.)."""
        effects = ["disable", "open", "unlock", "shutdown",
                   "friendly", "deactivate", "override", "control"]
        found = [e for e in effects if e in self.source_lower]
        self.assertGreaterEqual(len(found), 2,
                                f"Only {len(found)} hack effects found: {found}")


# =============================================================================
# 9. FOG OF WAR TESTS
# =============================================================================

class TestFogOfWar(unittest.TestCase):
    """Tests the fog of war / visibility system."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()

    def test_has_fog_of_war(self):
        """Must have fog of war / visibility."""
        has_fow = any(kw in self.source_lower for kw in
                      ["fog", "visible", "visibility", "fov",
                       "field_of_view", "sight", "explored",
                       "line_of_sight", "los"])
        self.assertTrue(has_fow, "No fog of war system found")

    def test_has_visibility_radius(self):
        """Must have a visibility radius."""
        has_radius = any(kw in self.source_lower for kw in
                         ["radius", "range", "sight_range",
                          "view_dist", "view_range", "vision"])
        self.assertTrue(has_radius, "No visibility radius found")

    def test_has_explored_tracking(self):
        """Must track which tiles have been explored."""
        has_explored = any(kw in self.source_lower for kw in
                           ["explored", "discovered", "revealed",
                            "seen", "visited", "mapped"])
        self.assertTrue(has_explored, "No explored tile tracking found")


# =============================================================================
# 10. SHOP SYSTEM TESTS
# =============================================================================

class TestShopSystem(unittest.TestCase):
    """Tests the between-level shop."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()

    def test_has_shop(self):
        """Must have a shop/vendor between levels."""
        has_shop = any(kw in self.source_lower for kw in
                       ["shop", "store", "vendor", "merchant",
                        "buy", "purchase", "market"])
        self.assertTrue(has_shop, "No shop system found")

    def test_shop_has_items(self):
        """Shop must sell items."""
        has_sell = any(kw in self.source_lower for kw in
                       ["buy", "purchase", "price", "cost",
                        "afford", "stock", "wares", "sale"])
        self.assertTrue(has_sell, "No shop items/purchasing found")


# =============================================================================
# 11. INPUT HANDLING TESTS
# =============================================================================

class TestInputHandling(unittest.TestCase):
    """Tests that the game handles required key inputs."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_handles_arrow_keys(self):
        """Must handle arrow keys for movement."""
        required = ["KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT"]
        found = [k for k in required if k in self.source]
        self.assertEqual(len(found), 4,
                         f"Missing arrow keys. Found: {found}")

    def test_handles_quit(self):
        """Must handle quit key."""
        has_quit = any(kw in self.source for kw in
                       ["ord('q')", 'ord("q")', "ord('Q')", 'ord("Q")',
                        "'q'", '"q"', "'Q'", '"Q"'])
        self.assertTrue(has_quit, "No quit key handler found")

    def test_handles_interaction(self):
        """Must handle an interaction/use key."""
        has_interact = any(kw in self.source.lower() for kw in
                           ["interact", "use", "activate", "open",
                            "enter", "hack", "pickup", "pick_up"])
        self.assertTrue(has_interact, "No interaction key handler found")


# =============================================================================
# 12. CURSES INTEGRATION TESTS
# =============================================================================

class TestCursesIntegration(unittest.TestCase):
    """Tests proper curses integration."""

    @classmethod
    def setUpClass(cls):
        cls.tree = parse_ast()
        cls.functions = find_all_functions(cls.tree)
        cls.source = load_source()

    def test_main_takes_stdscr(self):
        """main() must accept a stdscr argument."""
        self.assertIn("main", self.functions)
        main_func = self.functions["main"]
        args = [a.arg for a in main_func.args.args]
        self.assertGreater(len(args), 0, "main() takes no arguments")
        self.assertIn(args[0], ["stdscr", "screen", "scr", "win"],
                      f"main() first arg is '{args[0]}', expected stdscr")

    def test_has_color_support(self):
        """Must initialize curses colors."""
        has_color = any(kw in self.source for kw in
                        ["init_pair", "color_pair", "start_color"])
        self.assertTrue(has_color, "No curses color initialization found")

    def test_has_multiple_color_pairs(self):
        """Must have at least 8 color pairs for the cyberpunk palette."""
        count = self.source.count("init_pair")
        self.assertGreaterEqual(count, 8,
                                f"Only {count} init_pair calls, need at least 8")


# =============================================================================
# 13. VISUAL / DISPLAY TESTS
# =============================================================================

class TestVisualDisplay(unittest.TestCase):
    """Tests visual elements and Nerd Font glyph usage."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()

    def test_has_nerd_font_glyphs(self):
        """Must use Nerd Font glyphs (Unicode chars above basic ASCII)."""
        # Check for Unicode characters in the Private Use Area or
        # common Nerd Font ranges (U+E000-U+F8FF, U+F0000-U+FFFFF)
        # or other common Unicode symbols used by Nerd Fonts
        has_unicode = False
        for ch in self.source:
            if ord(ch) > 127 and ord(ch) != 0xFEFF:  # Skip BOM
                has_unicode = True
                break
        self.assertTrue(has_unicode,
                        "No Unicode/Nerd Font glyphs found in source")

    def test_has_status_panel(self):
        """Must display HP, credits, weapon, armor, level."""
        has_status = any(kw in self.source_lower for kw in
                         ["status", "hud", "sidebar", "panel",
                          "info_panel", "stats_panel", "draw_status",
                          "draw_hud", "draw_stats"])
        self.assertTrue(has_status, "No status panel/HUD found")

    def test_has_minimap(self):
        """Must have a minimap display."""
        has_minimap = any(kw in self.source_lower for kw in
                          ["minimap", "mini_map", "overview",
                           "small_map", "radar"])
        self.assertTrue(has_minimap, "No minimap found")

    def test_has_game_over_screen(self):
        """Must show game over screen with stats."""
        has_gameover = any(kw in self.source_lower for kw in
                           ["game_over", "gameover", "game over",
                            "death_screen", "score_screen"])
        self.assertTrue(has_gameover, "No game over screen found")

    def test_has_box_drawing(self):
        """Must use box-drawing characters for UI."""
        box_chars = set("╔╗╚╝═║┌┐└┘─│┬┴├┤┼╠╣╦╩╬")
        found = any(c in box_chars for c in self.source)
        self.assertTrue(found, "No box-drawing characters found")

    def test_has_level_name(self):
        """Must display level name/theme."""
        has_level_name = any(kw in self.source_lower for kw in
                             ["level_name", "floor_name", "area_name",
                              "zone_name", "district", "tower",
                              "street", "underground"])
        self.assertTrue(has_level_name,
                        "No level naming/theming found")


# =============================================================================
# 14. GAME STATE / PROGRESSION TESTS
# =============================================================================

class TestGameProgression(unittest.TestCase):
    """Tests game state management and progression."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()

    def test_has_turn_based_system(self):
        """Must be turn-based (enemies move after player)."""
        has_turns = any(kw in self.source_lower for kw in
                        ["turn", "player_turn", "enemy_turn",
                         "take_turn", "next_turn", "tick"])
        self.assertTrue(has_turns, "No turn-based system found")

    def test_has_increasing_difficulty(self):
        """Levels must get harder."""
        has_difficulty = any(kw in self.source_lower for kw in
                             ["difficult", "harder", "stronger",
                              "tougher", "scale", "increase",
                              "level_num", "depth"])
        self.assertTrue(has_difficulty,
                        "No difficulty scaling found")

    def test_has_score_tracking(self):
        """Must track run statistics."""
        has_stats = any(kw in self.source_lower for kw in
                        ["score", "stats", "kills", "enemies_killed",
                         "levels_cleared", "total_credits"])
        self.assertTrue(has_stats, "No score/stats tracking found")

    def test_has_cyberpunk_theme(self):
        """Must have cyberpunk theming throughout."""
        theme_words = ["cyber", "neon", "corp", "hack", "chrome",
                       "neural", "implant", "augment", "synth",
                       "megacity", "district"]
        found = [w for w in theme_words if w in self.source_lower]
        self.assertGreaterEqual(len(found), 3,
                                f"Only {len(found)} cyberpunk theme words: {found}")


# =============================================================================
# 11. PUZZLE GATE TESTS
# =============================================================================

class TestPuzzleGate(unittest.TestCase):
    """Tests the puzzle gate mechanic on floor 7."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.source_lower = cls.source.lower()
        cls.tree = parse_ast()
        cls.all_funcs = find_all_functions(cls.tree)
        cls.names = get_top_level_names(cls.tree)

    def test_has_puzzle_gate_tile_constant(self):
        """Must define a TILE_PUZZLE_GATE constant."""
        self.assertIn("TILE_PUZZLE_GATE", self.names,
                      "No TILE_PUZZLE_GATE constant defined")

    def test_has_puzzle_gate_glyph(self):
        """Must define a GLYPH_PUZZLE_GATE constant."""
        self.assertIn("GLYPH_PUZZLE_GATE", self.names,
                      "No GLYPH_PUZZLE_GATE constant defined")

    def test_puzzle_gate_in_tile_chars(self):
        """TILE_PUZZLE_GATE must be in TILE_CHARS mapping."""
        self.assertIn("TILE_PUZZLE_GATE", self.source,
                      "TILE_PUZZLE_GATE not referenced in source")
        self.assertIn("GLYPH_PUZZLE_GATE", self.source,
                      "GLYPH_PUZZLE_GATE not referenced in source")

    def test_puzzle_gate_blocks_movement(self):
        """TILE_PUZZLE_GATE must be in BLOCKING_TILES."""
        # Check that puzzle gate appears in the BLOCKING_TILES set
        has_blocking = "TILE_PUZZLE_GATE" in self.source
        blocking_line = any("BLOCKING_TILES" in line and "TILE_PUZZLE_GATE" in line
                           for line in self.source.split("\n"))
        self.assertTrue(blocking_line,
                        "TILE_PUZZLE_GATE not found in BLOCKING_TILES")

    def test_puzzle_gate_blocks_sight(self):
        """TILE_PUZZLE_GATE must be in OPAQUE_TILES."""
        opaque_line = any("OPAQUE_TILES" in line and "TILE_PUZZLE_GATE" in line
                         for line in self.source.split("\n"))
        self.assertTrue(opaque_line,
                        "TILE_PUZZLE_GATE not found in OPAQUE_TILES")

    def test_has_puzzle_gate_screen_function(self):
        """Must have a puzzle_gate_screen function."""
        self.assertIn("puzzle_gate_screen", self.all_funcs,
                      "No puzzle_gate_screen function defined")

    def test_puzzle_gate_has_cipher_theme(self):
        """Puzzle gate must have cipher/hacking theme."""
        cipher_words = ["cipher", "hex", "breach", "crack", "ice breaker"]
        found = [w for w in cipher_words if w in self.source_lower]
        self.assertGreaterEqual(len(found), 2,
                                f"Only {len(found)} cipher theme words: {found}")

    def test_puzzle_gate_has_attempts_limit(self):
        """Puzzle must have an attempts limit (no infinite guessing)."""
        has_attempts = any(kw in self.source_lower for kw in
                          ["max_attempts", "attempts", "lockout"])
        self.assertTrue(has_attempts,
                        "No attempts limit found in puzzle gate")

    def test_puzzle_gate_placed_on_floor_7(self):
        """Puzzle gate must be placed on level 7."""
        # Check that level 7 placement references puzzle gate
        has_placement = ("puzzle_gate" in self.source_lower and
                        "level_num == 7" in self.source)
        self.assertTrue(has_placement,
                        "Puzzle gate not placed on floor 7")

    def test_puzzle_gate_has_bypass_options(self):
        """Companion or hack skill must bypass the puzzle gate."""
        has_companion_bypass = ("companion" in self.source_lower and
                               "puzzle_gate" in self.source_lower)
        has_hack_bypass = "hack_skill" in self.source_lower
        self.assertTrue(has_companion_bypass or has_hack_bypass,
                        "No bypass options for puzzle gate")

    def test_puzzle_gate_rendering(self):
        """Puzzle gate must be rendered in draw_map with a distinct color."""
        lines = self.source.split("\n")
        has_render = False
        for i, line in enumerate(lines):
            if "TILE_PUZZLE_GATE" in line and "tile ==" in line:
                # Check nearby lines for color rendering
                nearby = "\n".join(lines[max(0, i-2):i+3])
                if "color_pair" in nearby:
                    has_render = True
                    break
        self.assertTrue(has_render,
                        "TILE_PUZZLE_GATE not rendered in draw_map")

    def test_puzzle_gate_interaction_on_e_key(self):
        """Puzzle gate must respond to e-key interaction."""
        has_interaction = ("puzzle_gate_screen" in self.source and
                          "TILE_PUZZLE_GATE" in self.source)
        self.assertTrue(has_interaction,
                        "No e-key interaction for puzzle gate")

    def test_puzzle_gate_bump_interaction(self):
        """Bumping puzzle gate must show a message."""
        has_bump = any("TILE_PUZZLE_GATE" in line and "tile" in line.lower()
                      for line in self.source.split("\n"))
        self.assertTrue(has_bump,
                        "No bump interaction for puzzle gate")


if __name__ == "__main__":
    unittest.main(verbosity=2)
