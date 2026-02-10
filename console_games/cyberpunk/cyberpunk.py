#!/usr/bin/env python3
"""Cyberpunk Megacity Roguelite — a neon-drenched terminal roguelite set in
Neo-Shibuya, 2087. Navigate procedurally generated city blocks, corporate towers,
and the underground. Fight drones, gangs, guards, and turrets. Hack terminals,
loot data chips, and try to survive seven floors of megacity conspiracy.

Controls:
  Arrow keys / WASD  — Move (turn-based) / bump to open doors
  f                  — Fire ranged weapon
  h                  — Hack adjacent terminal
  e                  — Interact / pick up / open door
  i                  — Inventory
  a                  — Toggle auto-pickup (default: ON)
  q                  — Quit
"""

import collections
import copy
import curses
import json
import math
import os
import random
import sys
import time

# ═══════════════════════════════════════════════════════════════════════════════
# Nerd Font Glyphs (single-width Private Use Area codepoints)
# ═══════════════════════════════════════════════════════════════════════════════

GLYPH_PLAYER = "\uf007"        # nf-fa-user
GLYPH_DRONE = "\U000f06a9"     # nf-md-robot
GLYPH_DRONE_ANGRY = "\U000f169d" # nf-md-robot_angry
GLYPH_DRONE_DEAD = "\U000f16a1"  # nf-md-robot_dead
GLYPH_DRONE_CONFUSED = "\U000f169f" # nf-md-robot_confused
GLYPH_DRONE_HAPPY = "\U000f1719" # nf-md-robot_happy
GLYPH_GANG = "\U0000ee15"      # nf-fa-skull
GLYPH_GUARD = "\uf132"         # shield
GLYPH_TURRET = "\uf05b"        # crosshairs
GLYPH_NETRUNNER = "\uf120"     # terminal

GLYPH_MEDKIT = "\uf0fa"        # medkit
GLYPH_CREDITS = "\uf15a"       # bitcoin
GLYPH_WEAPON = "\uf05b"        # crosshairs
GLYPH_KEY = "\uf084"           # key
GLYPH_CHIP = "\uf2db"          # microchip
GLYPH_TERMINAL = "\uf108"      # desktop
GLYPH_STAIRS = "\U000f04cd"    # nf-md-stairs
GLYPH_SHOP = "\uf07a"          # shopping cart
GLYPH_HEART = "\uf004"         # heart
GLYPH_BOLT = "\uf0e7"          # bolt
GLYPH_SHIELD = "\U000f0498"    # nf-md-shield
GLYPH_DOOR = "\U0000edf5"      # nf-fa-door_open
GLYPH_LOCK = "\uf023"          # lock
GLYPH_STAR = "\uf005"          # star
GLYPH_EYE = "\uf06e"           # eye
GLYPH_BOMB = "\uf1e2"          # bomb
GLYPH_STIM = "\uf0e7"          # bolt (reuse for stim)
GLYPH_JACK_IN = "\U000f0322"   # nf-md-laptop (cyberspace jack-in)
GLYPH_RAVEN = "\uf0fc"         # nf-fa-bar_chart (bartender NPC)

# ═══════════════════════════════════════════════════════════════════════════════
# Box-drawing characters
# ═══════════════════════════════════════════════════════════════════════════════

BOX_TL = "╔"
BOX_TR = "╗"
BOX_BL = "╚"
BOX_BR = "╝"
BOX_H = "═"
BOX_V = "║"
BOX_TL2 = "┌"
BOX_TR2 = "┐"
BOX_BL2 = "└"
BOX_BR2 = "┘"
BOX_H2 = "─"
BOX_V2 = "│"

# ═══════════════════════════════════════════════════════════════════════════════
# Color pair IDs
# ═══════════════════════════════════════════════════════════════════════════════

C_CYAN = 1
C_MAGENTA = 2
C_GREEN = 3
C_RED = 4
C_YELLOW = 5
C_WHITE = 6
C_GRAY = 7
C_BLUE = 8
C_PLAYER = 9
C_ENEMY = 10
C_ITEM = 11
C_WALL = 12
C_FLOOR = 13
C_FOG = 14
C_TITLE = 15
C_SHOP_BG = 16

# ═══════════════════════════════════════════════════════════════════════════════
# Tile types
# ═══════════════════════════════════════════════════════════════════════════════

TILE_WALL = 0
TILE_FLOOR = 1
TILE_DOOR = 2
TILE_DOOR_LOCKED = 3
TILE_STAIRS = 4
TILE_CORRIDOR = 5
TILE_TERMINAL = 6
TILE_SHOP_TILE = 7
TILE_DOOR_OPEN = 8
TILE_JACK_IN = 9

TILE_CHARS = {
    TILE_WALL: "█",
    TILE_FLOOR: "·",
    TILE_DOOR: "+",
    TILE_DOOR_LOCKED: GLYPH_LOCK,
    TILE_STAIRS: GLYPH_STAIRS,
    TILE_CORRIDOR: "·",
    TILE_TERMINAL: GLYPH_TERMINAL,
    TILE_SHOP_TILE: GLYPH_SHOP,
    TILE_DOOR_OPEN: "·",
}

# ═══════════════════════════════════════════════════════════════════════════════
# Tileset loading (JSON config + settings persistence)
# ═══════════════════════════════════════════════════════════════════════════════

_TILES_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyberpunk_tiles.json")
_SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".cyberpunk_settings")

# Current tile mode — "nerdfont" (default) or "ascii"
_tile_mode = "nerdfont"


def _load_settings():
    """Load persisted settings from ~/.cyberpunk_settings."""
    global _tile_mode
    try:
        with open(_SETTINGS_FILE, "r") as f:
            data = json.load(f)
        _tile_mode = data.get("tile_mode", "nerdfont")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        _tile_mode = "nerdfont"


def _save_settings():
    """Persist current settings to ~/.cyberpunk_settings."""
    try:
        with open(_SETTINGS_FILE, "w") as f:
            json.dump({"tile_mode": _tile_mode}, f)
    except OSError:
        pass


def _apply_tileset():
    """Load glyphs and tile chars from cyberpunk_tiles.json for current mode."""
    global GLYPH_PLAYER, GLYPH_DRONE, GLYPH_DRONE_ANGRY, GLYPH_DRONE_DEAD
    global GLYPH_DRONE_CONFUSED, GLYPH_DRONE_HAPPY, GLYPH_GANG, GLYPH_GUARD
    global GLYPH_TURRET, GLYPH_NETRUNNER, GLYPH_MEDKIT, GLYPH_CREDITS
    global GLYPH_WEAPON, GLYPH_KEY, GLYPH_CHIP, GLYPH_TERMINAL, GLYPH_STAIRS
    global GLYPH_SHOP, GLYPH_HEART, GLYPH_BOLT, GLYPH_SHIELD, GLYPH_DOOR
    global GLYPH_LOCK, GLYPH_STAR, GLYPH_EYE, GLYPH_BOMB, GLYPH_STIM
    global GLYPH_JACK_IN, GLYPH_RAVEN
    global TILE_CHARS

    try:
        with open(_TILES_JSON, "r", encoding="utf-8") as f:
            tilesets = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return  # Keep compiled-in defaults on error

    mode = _tile_mode if _tile_mode in tilesets else "nerdfont"
    ts = tilesets.get(mode)
    if not ts:
        return

    g = ts.get("glyphs", {})
    GLYPH_PLAYER = g.get("GLYPH_PLAYER", GLYPH_PLAYER)
    GLYPH_DRONE = g.get("GLYPH_DRONE", GLYPH_DRONE)
    GLYPH_DRONE_ANGRY = g.get("GLYPH_DRONE_ANGRY", GLYPH_DRONE_ANGRY)
    GLYPH_DRONE_DEAD = g.get("GLYPH_DRONE_DEAD", GLYPH_DRONE_DEAD)
    GLYPH_DRONE_CONFUSED = g.get("GLYPH_DRONE_CONFUSED", GLYPH_DRONE_CONFUSED)
    GLYPH_DRONE_HAPPY = g.get("GLYPH_DRONE_HAPPY", GLYPH_DRONE_HAPPY)
    GLYPH_GANG = g.get("GLYPH_GANG", GLYPH_GANG)
    GLYPH_GUARD = g.get("GLYPH_GUARD", GLYPH_GUARD)
    GLYPH_TURRET = g.get("GLYPH_TURRET", GLYPH_TURRET)
    GLYPH_NETRUNNER = g.get("GLYPH_NETRUNNER", GLYPH_NETRUNNER)
    GLYPH_MEDKIT = g.get("GLYPH_MEDKIT", GLYPH_MEDKIT)
    GLYPH_CREDITS = g.get("GLYPH_CREDITS", GLYPH_CREDITS)
    GLYPH_WEAPON = g.get("GLYPH_WEAPON", GLYPH_WEAPON)
    GLYPH_KEY = g.get("GLYPH_KEY", GLYPH_KEY)
    GLYPH_CHIP = g.get("GLYPH_CHIP", GLYPH_CHIP)
    GLYPH_TERMINAL = g.get("GLYPH_TERMINAL", GLYPH_TERMINAL)
    GLYPH_STAIRS = g.get("GLYPH_STAIRS", GLYPH_STAIRS)
    GLYPH_SHOP = g.get("GLYPH_SHOP", GLYPH_SHOP)
    GLYPH_HEART = g.get("GLYPH_HEART", GLYPH_HEART)
    GLYPH_BOLT = g.get("GLYPH_BOLT", GLYPH_BOLT)
    GLYPH_SHIELD = g.get("GLYPH_SHIELD", GLYPH_SHIELD)
    GLYPH_DOOR = g.get("GLYPH_DOOR", GLYPH_DOOR)
    GLYPH_LOCK = g.get("GLYPH_LOCK", GLYPH_LOCK)
    GLYPH_STAR = g.get("GLYPH_STAR", GLYPH_STAR)
    GLYPH_EYE = g.get("GLYPH_EYE", GLYPH_EYE)
    GLYPH_BOMB = g.get("GLYPH_BOMB", GLYPH_BOMB)
    GLYPH_STIM = g.get("GLYPH_STIM", GLYPH_STIM)
    GLYPH_JACK_IN = g.get("GLYPH_JACK_IN", GLYPH_JACK_IN)
    GLYPH_RAVEN = g.get("GLYPH_RAVEN", GLYPH_RAVEN)

    # Tile name → tile constant mapping
    _tile_name_map = {
        "TILE_WALL": TILE_WALL,
        "TILE_FLOOR": TILE_FLOOR,
        "TILE_DOOR": TILE_DOOR,
        "TILE_DOOR_LOCKED": TILE_DOOR_LOCKED,
        "TILE_STAIRS": TILE_STAIRS,
        "TILE_CORRIDOR": TILE_CORRIDOR,
        "TILE_TERMINAL": TILE_TERMINAL,
        "TILE_SHOP_TILE": TILE_SHOP_TILE,
        "TILE_DOOR_OPEN": TILE_DOOR_OPEN,
    }
    t = ts.get("tiles", {})
    for name, char in t.items():
        if name in _tile_name_map:
            TILE_CHARS[_tile_name_map[name]] = char

    # Refresh data structures that captured glyph values at definition time
    _refresh_glyph_refs()


def _refresh_glyph_refs():
    """Update dicts that cached glyph values at import time."""
    _enemy_glyph = {
        "Security Drone": GLYPH_DRONE,
        "Gang Member": GLYPH_GANG,
        "Corporate Guard": GLYPH_GUARD,
        "Turret": GLYPH_TURRET,
        "Netrunner ICE": GLYPH_NETRUNNER,
    }
    for name, glyph in _enemy_glyph.items():
        if name in ENEMY_TYPES:
            ENEMY_TYPES[name]["glyph"] = glyph

    _cons_glyph = {
        "Medkit": GLYPH_MEDKIT,
        "Stim Pack": GLYPH_STIM,
        "EMP Grenade": GLYPH_BOMB,
    }
    for name, glyph in _cons_glyph.items():
        if name in CONSUMABLES:
            CONSUMABLES[name]["glyph"] = glyph


def _toggle_tile_mode():
    """Switch between nerdfont and ascii modes, persist, and reload glyphs."""
    global _tile_mode
    _tile_mode = "ascii" if _tile_mode == "nerdfont" else "nerdfont"
    _apply_tileset()
    _save_settings()


def is_ascii_mode():
    """Return True when the current tile mode is ASCII."""
    return _tile_mode == "ascii"


# Tiles that block movement
BLOCKING_TILES = {TILE_WALL, TILE_DOOR, TILE_DOOR_LOCKED}

# Tiles that block line of sight / FOV
OPAQUE_TILES = {TILE_WALL, TILE_DOOR, TILE_DOOR_LOCKED}

# ═══════════════════════════════════════════════════════════════════════════════
# Level themes
# ═══════════════════════════════════════════════════════════════════════════════

LEVEL_THEMES = [
    {"level_name": "Chiba City Limits", "zone": "street"},
    {"level_name": "Kabuki Market Underground", "zone": "underground"},
    {"level_name": "Koroshi Tower - Lower Floors", "zone": "corporate"},
    {"level_name": "Freeside Underworks", "zone": "underground"},
    {"level_name": "Koroshi Tower - Executive Suite", "zone": "corporate"},
    {"level_name": "Neo-Tokyo Bōsōzoku Turf", "zone": "street"},
    {"level_name": "Koroshi Tower - Server Core", "zone": "corporate"},
    {"level_name": "Neural Nexus - Deep Underground", "zone": "underground"},
    {"level_name": "Tessier-Ashpool Spire - Apex", "zone": "corporate"},
]

MAX_LEVELS = 9

# ═══════════════════════════════════════════════════════════════════════════════
# Character classes
# ═══════════════════════════════════════════════════════════════════════════════

CLASS_SAMURAI = "Street Samurai"
CLASS_NETRUNNER = "Netrunner"
CLASS_MEDIC = "Chrome Medic"

CLASS_STATS = {
    CLASS_SAMURAI: {
        "hp": 120, "max_hp": 120, "attack": 14, "defense": 6,
        "hack_skill": 15, "melee_bonus": 8, "ranged_bonus": 2,
        "vision": 6, "heal_power": 0,
        "desc": "High melee damage and armor. Trained in the Kusanagi style.",
        "weapon": "Katana", "weapon_type": "melee", "weapon_dmg": 14,
        "armor": "Leather Jacket", "armor_def": 3,
    },
    CLASS_NETRUNNER: {
        "hp": 80, "max_hp": 80, "attack": 8, "defense": 2,
        "hack_skill": 85, "melee_bonus": 0, "ranged_bonus": 4,
        "vision": 8, "heal_power": 0,
        "desc": "Console cowboy. Disable drones, breach terminals.",
        "weapon": "Pistol", "weapon_type": "ranged", "weapon_dmg": 10,
        "armor": "Synth Coat", "armor_def": 1,
    },
    CLASS_MEDIC: {
        "hp": 100, "max_hp": 100, "attack": 10, "defense": 4,
        "hack_skill": 40, "melee_bonus": 3, "ranged_bonus": 3,
        "vision": 7, "heal_power": 20,
        "desc": "Self-heal, poison resistance, balanced combat.",
        "weapon": "Stun Baton", "weapon_type": "melee", "weapon_dmg": 10,
        "armor": "Kevlar Vest", "armor_def": 4,
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# Weapons / Armor / Items
# ═══════════════════════════════════════════════════════════════════════════════

WEAPONS = {
    "Katana": {"type": "melee", "damage": 14, "price": 0},
    "Stun Baton": {"type": "melee", "damage": 10, "price": 60},
    "Kusanagi Blade": {"type": "melee", "damage": 18, "price": 200},
    "Pistol": {"type": "ranged", "damage": 10, "range": 6, "price": 80},
    "SMG": {"type": "ranged", "damage": 15, "range": 5, "price": 180},
    "Ono-Sendai Zapper": {"type": "ranged", "damage": 20, "range": 4, "price": 300},
}

ARMORS = {
    "Leather Jacket": {"defense": 3, "price": 0},
    "Synth Coat": {"defense": 1, "price": 0},
    "Kevlar Vest": {"defense": 4, "price": 100},
    "Kiroshi Body Armor": {"defense": 8, "price": 300},
    "Chrome Plating": {"defense": 12, "price": 500},
}

CONSUMABLES = {
    "Medkit": {"heal": 30, "price": 40, "glyph": GLYPH_MEDKIT},
    "Stim Pack": {"heal": 0, "attack_boost": 5, "duration": 10, "price": 60, "glyph": GLYPH_STIM},
    "EMP Grenade": {"emp_damage": 40, "price": 80, "glyph": GLYPH_BOMB},
}

# ═══════════════════════════════════════════════════════════════════════════════
# Raven — bartender NPC (shared-universe tie-in with Neon Shadows IF)
# ═══════════════════════════════════════════════════════════════════════════════

RAVEN_DIALOGUE = [
    "Raven slides a drink across the bar. 'What'll it be, runner?'",
    "Raven polishes a glass. 'Heard the corps are hiring new muscle upstairs.'",
    "Raven leans in. 'Watch yourself out there. The ICE is getting thicker.'",
    "Raven nods. 'You look like you've seen some things. Browse my stock.'",
    "Raven grins. 'Sats talk, runner. Let's do business.'",
    "Raven eyes you over the counter. 'The Neon Lotus never closes.'",
    "Raven stares past you. 'Knew a mnemonic courier once. Carried half a gig in his skull. Corp flatlined him for it.'",
    "Raven wipes the bar slowly. 'Old fixer called the Finn used to say — data wants to be free. So do runners.'",
    "Raven pours two fingers of synth-whiskey. 'Some replicant down in Kabuki swears he saw tears in the rain last night. Poetic for a skin-job.'",
    "Raven chuckles. 'Met a freelance hacker once — called himself a protagonist. Delivered pizza before he started slicing through the Metaverse.'",
    "Raven lowers his voice. 'They say under Neo-Tokyo there's a kid who woke something up. Military project. Whole district went dark overnight.'",
    "Raven taps the bar twice. 'Your ghost — the part of you that's really you — don't ever let them separate it from your shell. That's how Section 9 loses operatives.'",
    "Raven glances at a faded photo on the wall. 'Armitage. That was a name people used to whisper. Ran a crew into Straylight once. None of them came back the same.'",
]


# ═══════════════════════════════════════════════════════════════════════════════
# Enemy definitions
# ═══════════════════════════════════════════════════════════════════════════════

ENEMY_TYPES = {
    "Security Drone": {
        "glyph": GLYPH_DRONE, "hp": 25, "attack": 8, "defense": 2,
        "behavior": "patrol", "xp": 10, "credits": 15,
        "desc": "Nexus-series drone. Patrols fixed paths, alerts others.",
    },
    "Gang Member": {
        "glyph": GLYPH_GANG, "hp": 30, "attack": 10, "defense": 1,
        "behavior": "aggressive", "xp": 12, "credits": 20,
        "desc": "Bōsōzoku street thug. Charges at you on sight.",
    },
    "Corporate Guard": {
        "glyph": GLYPH_GUARD, "hp": 45, "attack": 12, "defense": 5,
        "behavior": "methodical", "xp": 18, "credits": 30,
        "desc": "Turing Police enforcer. Methodical, uses cover.",
    },
    "Turret": {
        "glyph": GLYPH_TURRET, "hp": 35, "attack": 16, "defense": 8,
        "behavior": "stationary", "xp": 15, "credits": 25,
        "desc": "Sentry turret. Stationary but high damage. Hackable.",
    },
    "Netrunner ICE": {
        "glyph": GLYPH_NETRUNNER, "hp": 20, "attack": 6, "defense": 1,
        "behavior": "wander", "xp": 8, "credits": 10,
        "desc": "Laughing Man ICE. Wanders erratically, hijacks neural links.",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# Shop items for sale between levels
# ═══════════════════════════════════════════════════════════════════════════════

def get_shop_stock(level_num):
    """Generate shop wares scaled to current depth."""
    stock = []
    stock.append({"name": "Medkit", "type": "consumable", "price": 40 + level_num * 5,
                  "heal": 30, "glyph": GLYPH_MEDKIT})
    stock.append({"name": "Stim Pack", "type": "consumable", "price": 60 + level_num * 5,
                  "attack_boost": 5, "duration": 10, "glyph": GLYPH_STIM})
    if level_num >= 2:
        stock.append({"name": "SMG", "type": "weapon", "price": 180,
                      "damage": 15, "weapon_type": "ranged", "range": 5, "glyph": GLYPH_WEAPON})
    if level_num >= 3:
        stock.append({"name": "Kevlar Vest", "type": "armor", "price": 100,
                      "armor_def": 4, "glyph": GLYPH_SHIELD})
    if level_num >= 4:
        stock.append({"name": "EMP Grenade", "type": "consumable", "price": 80 + level_num * 5,
                      "emp_damage": 40, "glyph": GLYPH_BOMB})
    if level_num >= 5:
        stock.append({"name": "Kiroshi Body Armor", "type": "armor", "price": 300,
                      "armor_def": 8, "glyph": GLYPH_SHIELD})
    if level_num >= 6:
        stock.append({"name": "Kusanagi Blade", "type": "weapon", "price": 200,
                      "damage": 18, "weapon_type": "melee", "glyph": GLYPH_WEAPON})
        stock.append({"name": "Ono-Sendai Zapper", "type": "weapon", "price": 300,
                      "damage": 20, "weapon_type": "ranged", "range": 4, "glyph": GLYPH_WEAPON})
    return stock


# ═══════════════════════════════════════════════════════════════════════════════
# Player class
# ═══════════════════════════════════════════════════════════════════════════════

class Player:
    """The player character."""

    def __init__(self, char_class):
        stats = CLASS_STATS[char_class]
        self.char_class = char_class
        self.x = 0
        self.y = 0
        self.hp = stats["hp"]
        self.max_hp = stats["max_hp"]
        self.attack = stats["attack"]
        self.defense = stats["defense"]
        self.hack_skill = stats["hack_skill"]
        self.melee_bonus = stats["melee_bonus"]
        self.ranged_bonus = stats["ranged_bonus"]
        self.vision = stats["vision"]
        self.heal_power = stats["heal_power"]
        self.weapon = stats["weapon"]
        self.weapon_type = stats["weapon_type"]
        self.weapon_dmg = stats["weapon_dmg"]
        self.armor = stats["armor"]
        self.armor_def = stats["armor_def"]
        self.credits = 50
        self.keycards = 0
        self.data_chips = 0
        self.inventory = []
        self.stim_turns = 0
        self.stim_bonus = 0
        self.auto_pickup = True
        # Stats tracking
        self.enemies_killed = 0
        self.levels_cleared = 0
        self.total_credits = 50
        self.damage_dealt = 0
        self.damage_taken = 0
        self.hacks_attempted = 0
        self.hacks_succeeded = 0
        self.items_used = 0
        self.turns_taken = 0

    @property
    def alive(self):
        return self.hp > 0

    def take_damage(self, dmg):
        """Apply damage after armor reduction."""
        actual = max(1, dmg - self.armor_def)
        self.hp -= actual
        self.damage_taken += actual
        if self.hp < 0:
            self.hp = 0
        return actual

    def deal_melee_damage(self):
        base = self.weapon_dmg + self.melee_bonus + self.stim_bonus
        return max(1, base + random.randint(-2, 3))

    def deal_ranged_damage(self):
        base = self.weapon_dmg + self.ranged_bonus + self.stim_bonus
        return max(1, base + random.randint(-3, 2))

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def use_medkit(self):
        """Use a medkit from inventory."""
        for i, item in enumerate(self.inventory):
            if item.get("name") == "Medkit":
                self.heal(item.get("heal", 30))
                self.inventory.pop(i)
                self.items_used += 1
                return True
        return False

    def use_stim(self):
        """Use a stim pack from inventory."""
        for i, item in enumerate(self.inventory):
            if item.get("name") == "Stim Pack":
                self.stim_turns = item.get("duration", 10)
                self.stim_bonus = item.get("attack_boost", 5)
                self.inventory.pop(i)
                self.items_used += 1
                return True
        return False

    def tick_stim(self):
        """Decrease stim duration each turn."""
        if self.stim_turns > 0:
            self.stim_turns -= 1
            if self.stim_turns <= 0:
                self.stim_bonus = 0


# ═══════════════════════════════════════════════════════════════════════════════
# Enemy class
# ═══════════════════════════════════════════════════════════════════════════════

class Enemy:
    """An enemy entity on the map."""

    def __init__(self, enemy_type, x, y, level_num=1):
        template = ENEMY_TYPES[enemy_type]
        self.name = enemy_type
        self.x = x
        self.y = y
        self.glyph = template["glyph"]
        # Scale with level_num for increasing difficulty
        scale = 1.0 + (level_num - 1) * 0.15
        self.hp = int(template["hp"] * scale)
        self.max_hp = self.hp
        self.attack = int(template["attack"] * scale)
        self.defense = int(template["defense"] * scale)
        self.behavior = template["behavior"]
        self.xp = template["xp"]
        self.credits = int(template["credits"] * scale)
        self.alert = False
        self.patrol_dir = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
        self.disabled = False

    @property
    def alive(self):
        return self.hp > 0

    @property
    def state_glyph(self):
        """Return the appropriate glyph based on enemy state."""
        if self.name != "Security Drone":
            return self.glyph
        if not self.alive:
            return GLYPH_DRONE_DEAD
        if self.disabled:
            return GLYPH_DRONE_CONFUSED
        if self.hp < self.max_hp * 0.3:
            return GLYPH_DRONE_ANGRY
        if self.alert:
            return GLYPH_DRONE_ANGRY
        return self.glyph

    def take_damage(self, dmg):
        actual = max(1, dmg - self.defense)
        self.hp -= actual
        if self.hp < 0:
            self.hp = 0
        return actual

    def take_turn(self, game_map, player, enemies):
        """Enemy AI: move based on behavior type."""
        if self.disabled or not self.alive:
            return None

        dx, dy = 0, 0
        dist = abs(self.x - player.x) + abs(self.y - player.y)

        if self.behavior == "stationary":
            # Turrets don't move but shoot if player in range
            if dist <= 5 and self._has_line_of_sight(game_map, player.x, player.y):
                return ("shoot", player)
            return None

        if self.behavior == "aggressive" or (self.alert and dist <= 8):
            # Chase the player directly
            dx, dy = self._chase(player, game_map, enemies)
        elif self.behavior == "patrol":
            # Patrol until player spotted, then chase
            if dist <= 5 and self._has_line_of_sight(game_map, player.x, player.y):
                self.alert = True
                dx, dy = self._chase(player, game_map, enemies)
            else:
                dx, dy = self.patrol_dir
        elif self.behavior == "methodical":
            # Methodical guards: approach carefully
            if dist <= 6 and self._has_line_of_sight(game_map, player.x, player.y):
                self.alert = True
                dx, dy = self._chase(player, game_map, enemies)
            elif self.alert:
                dx, dy = self._chase(player, game_map, enemies)
            else:
                dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
        elif self.behavior == "wander":
            dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])

        nx, ny = self.x + dx, self.y + dy

        # Check for bump-attack on player
        if nx == player.x and ny == player.y:
            dmg = max(1, self.attack + random.randint(-2, 2))
            actual = player.take_damage(dmg)
            return ("attack", actual)

        # Check passability — enemies cannot walk through walls or closed doors
        if (0 <= ny < len(game_map) and 0 <= nx < len(game_map[0]) and
                game_map[ny][nx] not in BLOCKING_TILES and
                not self._enemy_at(nx, ny, enemies)):
            self.x = nx
            self.y = ny
            # Reverse patrol direction if at wall or closed door
            if self.behavior == "patrol":
                nnx, nny = self.x + self.patrol_dir[0], self.y + self.patrol_dir[1]
                if (nny < 0 or nny >= len(game_map) or nnx < 0 or nnx >= len(game_map[0])
                        or game_map[nny][nnx] in BLOCKING_TILES):
                    self.patrol_dir = (-self.patrol_dir[0], -self.patrol_dir[1])

        return None

    def _chase(self, player, game_map, enemies):
        from collections import deque
        sx, sy = self.x, self.y
        gx, gy = player.x, player.y
        max_radius = 20
        # Build set of tiles occupied by other living enemies
        enemy_positions = set()
        for e in enemies:
            if e is not self and e.alive:
                enemy_positions.add((e.x, e.y))
        visited = {(sx, sy): None}
        queue = deque([(sx, sy)])
        found = False
        while queue:
            x, y = queue.popleft()
            if x == gx and y == gy:
                found = True
                break
            if abs(x - sx) + abs(y - sy) >= max_radius:
                continue
            for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + ddx, y + ddy
                if (nx, ny) in visited:
                    continue
                if not (0 <= ny < len(game_map) and 0 <= nx < len(game_map[0])):
                    continue
                if game_map[ny][nx] in BLOCKING_TILES:
                    continue
                # Allow moving onto the player's tile (goal) but not onto other enemies
                if (nx, ny) != (gx, gy) and (nx, ny) in enemy_positions:
                    continue
                visited[(nx, ny)] = (x, y)
                queue.append((nx, ny))
        if found:
            # Trace back from goal to find first step
            step = (gx, gy)
            while visited[step] != (sx, sy):
                step = visited[step]
            return (step[0] - sx, step[1] - sy)
        # Fallback: greedy move
        dx = 0 if gx == sx else (1 if gx > sx else -1)
        dy = 0 if gy == sy else (1 if gy > sy else -1)
        if abs(gx - sx) >= abs(gy - sy):
            return (dx, 0)
        return (0, dy)

    def _enemy_at(self, x, y, enemies):
        for e in enemies:
            if e is not self and e.alive and e.x == x and e.y == y:
                return True
        return False

    def _has_line_of_sight(self, game_map, tx, ty):
        """Simple line of sight check (Bresenham-like)."""
        x0, y0 = self.x, self.y
        ddx = abs(tx - x0)
        ddy = abs(ty - y0)
        sx = 1 if tx > x0 else -1
        sy = 1 if ty > y0 else -1
        err = ddx - ddy
        while True:
            if x0 == tx and y0 == ty:
                return True
            if (0 <= y0 < len(game_map) and 0 <= x0 < len(game_map[0])):
                if game_map[y0][x0] in OPAQUE_TILES:
                    return False
            else:
                return False
            e2 = 2 * err
            if e2 > -ddy:
                err -= ddy
                x0 += sx
            if e2 < ddx:
                err += ddx
                y0 += sy
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Item (on the ground)
# ═══════════════════════════════════════════════════════════════════════════════

class Item:
    """An item lying on the map."""

    def __init__(self, name, x, y, item_type="consumable", **kwargs):
        self.name = name
        self.x = x
        self.y = y
        self.item_type = item_type
        self.props = kwargs
        # Assign glyph based on type
        if item_type == "weapon":
            self.glyph = GLYPH_WEAPON
        elif item_type == "armor":
            self.glyph = GLYPH_SHIELD
        elif item_type == "keycard":
            self.glyph = GLYPH_KEY
        elif item_type == "data_chip":
            self.glyph = GLYPH_CHIP
        elif item_type == "credits":
            self.glyph = GLYPH_CREDITS
        elif name == "Medkit":
            self.glyph = GLYPH_MEDKIT
        elif name == "Stim Pack":
            self.glyph = GLYPH_STIM
        elif name == "EMP Grenade":
            self.glyph = GLYPH_BOMB
        else:
            self.glyph = GLYPH_STAR


# ═══════════════════════════════════════════════════════════════════════════════
# Procedural Level Generation
# ═══════════════════════════════════════════════════════════════════════════════

MAP_W = 60
MAP_H = 30
MIN_ROOM_SIZE = 4
MAX_ROOM_SIZE = 10
MAX_ROOMS = 12


class Room:
    """A rectangular room on the map."""

    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    @property
    def center(self):
        return (self.x + self.w // 2, self.y + self.h // 2)

    def intersects(self, other):
        return (self.x <= other.x + other.w and self.x + self.w >= other.x and
                self.y <= other.y + other.h and self.y + self.h >= other.y)


def _can_reach(game_map, start, goal):
    """BFS flood fill to check if goal is reachable from start.

    Only walks through non-blocking tiles (walls, closed doors, and
    locked doors block movement).
    """
    from collections import deque
    sx, sy = start
    gx, gy = goal
    visited = set()
    visited.add((sx, sy))
    queue = deque([(sx, sy)])
    while queue:
        x, y = queue.popleft()
        if x == gx and y == gy:
            return True
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if (nx, ny) in visited:
                continue
            if 0 <= ny < len(game_map) and 0 <= nx < len(game_map[0]):
                tile = game_map[ny][nx]
                if tile not in BLOCKING_TILES:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
    return False


def generate_level(level_num):
    """Generate a procedural level with rooms, corridors, doors, and entities.

    Returns (game_map, rooms, player_start, stairs_pos, enemies, items, terminals, raven_pos).
    """
    game_map = [[TILE_WALL for _ in range(MAP_W)] for _ in range(MAP_H)]
    rooms = []

    num_rooms = min(MAX_ROOMS, 5 + level_num)

    attempts = 0
    while len(rooms) < num_rooms and attempts < 200:
        attempts += 1
        w = random.randint(MIN_ROOM_SIZE, MAX_ROOM_SIZE)
        h = random.randint(MIN_ROOM_SIZE, MAX_ROOM_SIZE - 2)
        x = random.randint(1, MAP_W - w - 1)
        y = random.randint(1, MAP_H - h - 1)
        new_room = Room(x, y, w, h)
        if any(new_room.intersects(r) for r in rooms):
            continue
        # Carve room
        place_room(game_map, new_room)
        rooms.append(new_room)

    # Connect rooms with corridors
    for i in range(1, len(rooms)):
        connect_rooms(game_map, rooms[i - 1], rooms[i])

    # Place doors at corridor-room transitions
    doors = place_doors(game_map, rooms)

    # Player starts in first room
    player_start = rooms[0].center

    # Stairs in last room
    stairs_pos = rooms[-1].center
    game_map[stairs_pos[1]][stairs_pos[0]] = TILE_STAIRS

    # Place locked doors — only lock doors that don't block the only path
    locked_count = min(level_num, 3)
    if doors:
        random.shuffle(doors)
        locked_doors = []
        for dx, dy in doors:
            if len(locked_doors) >= locked_count:
                break
            # Tentatively lock the door
            game_map[dy][dx] = TILE_DOOR_LOCKED
            # Check if player can still reach stairs without going through locked doors
            if _can_reach(game_map, player_start, stairs_pos):
                locked_doors.append((dx, dy))
            else:
                # Revert — this door would cause a softlock
                game_map[dy][dx] = TILE_DOOR

    # Place terminals
    terminals = []
    terminal_rooms = random.sample(rooms[1:-1], min(2 + level_num // 2, len(rooms[1:-1])))
    for room in terminal_rooms:
        tx = random.randint(room.x + 1, room.x + room.w - 2)
        ty = random.randint(room.y + 1, room.y + room.h - 2)
        if game_map[ty][tx] == TILE_FLOOR:
            game_map[ty][tx] = TILE_TERMINAL
            terminals.append((tx, ty))

    # Place enemies
    enemies = place_enemies(game_map, rooms, level_num, player_start)

    # Place items — ensure keycards are reachable without locked doors
    items = place_items(game_map, rooms, level_num, player_start)

    # Place Raven the bartender in a mid-range room (not start or stairs room)
    # Raven only appears on level 3+
    raven_pos = None
    if level_num >= 3 and len(rooms) > 2:
        mid_rooms = rooms[1:-1]
        raven_room = random.choice(mid_rooms)
        rx = random.randint(raven_room.x + 1, raven_room.x + raven_room.w - 2)
        ry = random.randint(raven_room.y + 1, raven_room.y + raven_room.h - 2)
        if game_map[ry][rx] == TILE_FLOOR:
            raven_pos = (rx, ry)

    return game_map, rooms, player_start, stairs_pos, enemies, items, terminals, raven_pos


def place_room(game_map, room):
    """Carve a room into the map."""
    for y in range(room.y, room.y + room.h):
        for x in range(room.x, room.x + room.w):
            game_map[y][x] = TILE_FLOOR


def connect_rooms(game_map, room_a, room_b):
    """Dig a corridor between two rooms."""
    cx1, cy1 = room_a.center
    cx2, cy2 = room_b.center
    if random.random() < 0.5:
        _h_corridor(game_map, cx1, cx2, cy1)
        _v_corridor(game_map, cy1, cy2, cx2)
    else:
        _v_corridor(game_map, cy1, cy2, cx1)
        _h_corridor(game_map, cx1, cx2, cy2)


def _h_corridor(game_map, x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        if 0 <= y < MAP_H and 0 <= x < MAP_W:
            if game_map[y][x] == TILE_WALL:
                game_map[y][x] = TILE_CORRIDOR


def _v_corridor(game_map, y1, y2, x):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        if 0 <= y < MAP_H and 0 <= x < MAP_W:
            if game_map[y][x] == TILE_WALL:
                game_map[y][x] = TILE_CORRIDOR


def place_doors(game_map, rooms):
    """Place doors between two wall tiles (acting as a doorframe).

    A valid door position is a floor/corridor tile with walls on two
    opposite sides (N/S or E/W) and walkable tiles on the other two sides,
    located where a corridor meets a room edge.
    """
    doors = []
    placed = set()
    for room in rooms:
        # Check perimeter for corridor adjacency
        for x in range(room.x, room.x + room.w):
            for y in [room.y, room.y + room.h - 1]:
                if (x, y) not in placed and _is_door_candidate(game_map, x, y):
                    game_map[y][x] = TILE_DOOR
                    doors.append((x, y))
                    placed.add((x, y))
        for y in range(room.y, room.y + room.h):
            for x in [room.x, room.x + room.w - 1]:
                if (x, y) not in placed and _is_door_candidate(game_map, x, y):
                    game_map[y][x] = TILE_DOOR
                    doors.append((x, y))
                    placed.add((x, y))
    return doors


def _is_door_candidate(game_map, x, y):
    """Check if position is a good door candidate.

    A door must sit between two wall tiles on opposite sides (N/S or E/W)
    with walkable tiles on the perpendicular axis — this ensures the door
    is framed by walls like a real doorway.
    """
    if x <= 0 or x >= MAP_W - 1 or y <= 0 or y >= MAP_H - 1:
        return False
    tile = game_map[y][x]
    if tile not in (TILE_FLOOR, TILE_CORRIDOR):
        return False

    # Must be adjacent to at least one corridor tile
    adj_corridor = False
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nx, ny = x + dx, y + dy
        if 0 <= ny < MAP_H and 0 <= nx < MAP_W:
            if game_map[ny][nx] == TILE_CORRIDOR:
                adj_corridor = True
                break
    if not adj_corridor:
        return False

    n = game_map[y - 1][x]
    s = game_map[y + 1][x]
    w = game_map[y][x - 1]
    e = game_map[y][x + 1]

    walkable = {TILE_FLOOR, TILE_CORRIDOR}

    # Walls on N/S with walkable on E/W
    if n == TILE_WALL and s == TILE_WALL and w in walkable and e in walkable:
        return True
    # Walls on E/W with walkable on N/S
    if w == TILE_WALL and e == TILE_WALL and n in walkable and s in walkable:
        return True
    return False


def place_enemies(game_map, rooms, level_num, player_start):
    """Scatter enemies across rooms, scaling with level_num."""
    enemies = []
    enemy_count = 3 + level_num * 2
    # Weight enemy types by zone/level
    available = list(ENEMY_TYPES.keys())
    for room in rooms[1:]:
        if len(enemies) >= enemy_count:
            break
        n = random.randint(1, min(3, 1 + level_num // 2))
        for _ in range(n):
            if len(enemies) >= enemy_count:
                break
            ex = random.randint(room.x + 1, room.x + room.w - 2)
            ey = random.randint(room.y + 1, room.y + room.h - 2)
            if (ex, ey) == player_start:
                continue
            if game_map[ey][ex] in (TILE_FLOOR, TILE_CORRIDOR):
                etype = random.choice(available)
                enemies.append(Enemy(etype, ex, ey, level_num))
    return enemies


def place_items(game_map, rooms, level_num, player_start):
    """Scatter items across rooms."""
    items = []
    # Drop keycards if there are locked doors
    keycard_count = min(level_num, 3)
    for _ in range(keycard_count):
        room = random.choice(rooms[1:]) if len(rooms) > 1 else rooms[0]
        ix = random.randint(room.x + 1, room.x + room.w - 2)
        iy = random.randint(room.y + 1, room.y + room.h - 2)
        if game_map[iy][ix] in (TILE_FLOOR, TILE_CORRIDOR):
            items.append(Item("Keycard", ix, iy, "keycard"))

    # Medkits
    for _ in range(2 + level_num // 2):
        room = random.choice(rooms)
        ix = random.randint(room.x + 1, room.x + room.w - 2)
        iy = random.randint(room.y + 1, room.y + room.h - 2)
        if game_map[iy][ix] in (TILE_FLOOR, TILE_CORRIDOR):
            items.append(Item("Medkit", ix, iy, "consumable", heal=30))

    # Satoshi pickups
    for _ in range(3 + level_num):
        room = random.choice(rooms)
        ix = random.randint(room.x + 1, room.x + room.w - 2)
        iy = random.randint(room.y + 1, room.y + room.h - 2)
        if game_map[iy][ix] in (TILE_FLOOR, TILE_CORRIDOR):
            amt = random.randint(10, 30) + level_num * 5
            items.append(Item(f"{amt} Sats", ix, iy, "credits", amount=amt))

    # Data chips
    for _ in range(1 + level_num // 3):
        room = random.choice(rooms[1:]) if len(rooms) > 1 else rooms[0]
        ix = random.randint(room.x + 1, room.x + room.w - 2)
        iy = random.randint(room.y + 1, room.y + room.h - 2)
        if game_map[iy][ix] in (TILE_FLOOR, TILE_CORRIDOR):
            items.append(Item("Data Chip", ix, iy, "data_chip", value=50 + level_num * 20))

    # Occasional weapon/armor drop
    if random.random() < 0.3 + level_num * 0.05:
        room = random.choice(rooms[1:]) if len(rooms) > 1 else rooms[0]
        ix = random.randint(room.x + 1, room.x + room.w - 2)
        iy = random.randint(room.y + 1, room.y + room.h - 2)
        if game_map[iy][ix] in (TILE_FLOOR, TILE_CORRIDOR):
            if level_num < 4:
                items.append(Item("Pistol", ix, iy, "weapon", damage=10, weapon_type="ranged", range=6))
            else:
                items.append(Item("SMG", ix, iy, "weapon", damage=15, weapon_type="ranged", range=5))

    return items


# ═══════════════════════════════════════════════════════════════════════════════
# Fog of war / Visibility
# ═══════════════════════════════════════════════════════════════════════════════

def compute_fov(game_map, px, py, radius):
    """Compute field of view — returns set of (x, y) tiles visible.

    Closed doors and locked doors block FOV just like walls.
    """
    visible = set()
    for angle in range(360):
        rad = math.radians(angle)
        dx = math.cos(rad)
        dy = math.sin(rad)
        x, y = float(px), float(py)
        for _ in range(radius):
            ix, iy = int(round(x)), int(round(y))
            if iy < 0 or iy >= len(game_map) or ix < 0 or ix >= len(game_map[0]):
                break
            visible.add((ix, iy))
            if game_map[iy][ix] in OPAQUE_TILES:
                break
            x += dx
            y += dy
    return visible


# ═══════════════════════════════════════════════════════════════════════════════
# Hacking mechanic
# ═══════════════════════════════════════════════════════════════════════════════

def attempt_hack(player, target_type="terminal"):
    """Attempt to hack a terminal or device.

    Success chance is based on player hack_skill.
    Returns (success: bool, message: str).
    """
    player.hacks_attempted += 1
    chance = player.hack_skill
    roll = random.randint(1, 100)
    if roll <= chance:
        player.hacks_succeeded += 1
        return True, "Hack successful!"
    return False, f"Hack failed (rolled {roll}, needed <= {chance})"


# ── ICE Breaker minigame ─────────────────────────────────────────────────────

# Hex symbol pool used by the code-breaker puzzle
_ICE_SYMBOLS = "0123456789ABCDEF"


def _ice_params(player, level_num):
    """Return (code_length, max_attempts, pool_size) scaled by floor and skill.

    Higher hack_skill  -> more attempts, smaller symbol pool (easier).
    Higher level_num   -> longer code, larger symbol pool (harder).
    """
    # Code length: 3 on floor 1, up to 6 on floor 9
    code_length = min(3 + (level_num - 1) // 2, 6)

    # Symbol pool: base 8, +1 per 2 floors, reduced by high hack_skill
    pool = 8 + (level_num - 1) // 2
    if player.hack_skill >= 70:
        pool -= 2
    elif player.hack_skill >= 35:
        pool -= 1
    pool = max(4, min(pool, len(_ICE_SYMBOLS)))

    # Attempts: base 6, +2 for Netrunner-tier skill, +1 for mid skill
    max_attempts = 6
    if player.hack_skill >= 70:
        max_attempts += 2
    elif player.hack_skill >= 35:
        max_attempts += 1

    return code_length, max_attempts, pool


def _ice_evaluate(secret, guess):
    """Return (exact, misplaced) counts for *guess* vs *secret*.

    exact    — correct symbol in the correct position.
    misplaced — correct symbol but wrong position.
    """
    exact = sum(s == g for s, g in zip(secret, guess))
    # Count misplaced: shared symbol frequency minus exact matches
    s_counts = collections.Counter(secret)
    g_counts = collections.Counter(guess)
    total_shared = sum((s_counts & g_counts).values())
    misplaced = total_shared - exact
    return exact, misplaced


def hack_minigame(stdscr, player, level_num):
    """Interactive ICE Breaker code-cracking minigame.

    Returns True on success, False on failure.
    """
    code_length, max_attempts, pool_size = _ice_params(player, level_num)
    symbols = _ICE_SYMBOLS[:pool_size]
    secret = [random.choice(symbols) for _ in range(code_length)]

    guesses = []          # list of (guess_list, exact, misplaced)
    current = [0] * code_length  # indices into *symbols*
    cursor = 0            # which digit the cursor is on
    player.hacks_attempted += 1

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # ── title ────────────────────────────────────────────────────
        title = f"╔══ ICE BREAKER — Floor {level_num} ══╗"
        cx = max(0, w // 2 - len(title) // 2)
        safe_addstr(stdscr, 1, cx, title,
                    curses.color_pair(C_CYAN) | curses.A_BOLD)

        # ── info line ────────────────────────────────────────────────
        remaining = max_attempts - len(guesses)
        info = (f"  Crack the {code_length}-symbol code  |  "
                f"Symbols: {symbols}  |  "
                f"Attempts left: {remaining}")
        safe_addstr(stdscr, 3, cx, info, curses.color_pair(C_WHITE))

        # ── previous guesses ─────────────────────────────────────────
        row = 5
        for gi, (g, ex, mis) in enumerate(guesses):
            code_str = " ".join(g)
            # Color each symbol: green=exact, yellow=misplaced-counted
            # (simple: just show aggregate counts to the right)
            line = f"  {''.join(g)}  "
            safe_addstr(stdscr, row, cx, line, curses.color_pair(C_GRAY))
            # Feedback glyphs
            fb = (f"  {'●' * ex}{'○' * mis}{'·' * (code_length - ex - mis)}"
                  f"  ({ex} exact, {mis} close)")
            safe_addstr(stdscr, row, cx + code_length + 4, fb,
                        curses.color_pair(C_YELLOW if mis else
                                          (C_GREEN if ex else C_RED)))
            row += 1

        # ── current guess (editable) ────────────────────────────────
        row = max(row, 5 + max_attempts) + 1
        safe_addstr(stdscr, row, cx, "  YOUR GUESS:",
                    curses.color_pair(C_MAGENTA) | curses.A_BOLD)
        row += 1
        for i in range(code_length):
            sym = symbols[current[i]]
            if i == cursor:
                attr = curses.color_pair(C_GREEN) | curses.A_BOLD | curses.A_UNDERLINE
            else:
                attr = curses.color_pair(C_WHITE) | curses.A_BOLD
            safe_addstr(stdscr, row, cx + 2 + i * 3, f"[{sym}]", attr)

        # ── controls ────────────────────────────────────────────────
        ctrl_y = row + 2
        safe_addstr(stdscr, ctrl_y, cx,
                    "  ←/→ move cursor  ↑/↓ change symbol  ENTER submit  ESC abort",
                    curses.color_pair(C_YELLOW))

        stdscr.refresh()

        # ── input ───────────────────────────────────────────────────
        key = stdscr.getch()

        if key == 27:  # ESC — abort (counts as failure)
            return False
        elif key in (curses.KEY_LEFT, ord('a'), ord('A')):
            cursor = (cursor - 1) % code_length
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            cursor = (cursor + 1) % code_length
        elif key in (curses.KEY_UP, ord('w'), ord('W')):
            current[cursor] = (current[cursor] + 1) % pool_size
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            current[cursor] = (current[cursor] - 1) % pool_size
        elif key in (10, 13, curses.KEY_ENTER):
            guess = [symbols[c] for c in current]
            exact, misplaced = _ice_evaluate(secret, guess)

            if exact == code_length:
                # ── SUCCESS ──────────────────────────────────────────
                player.hacks_succeeded += 1
                stdscr.clear()
                msg = "ACCESS GRANTED — ICE BROKEN"
                safe_addstr(stdscr, h // 2, max(0, w // 2 - len(msg) // 2),
                            msg,
                            curses.color_pair(C_GREEN) | curses.A_BOLD)
                stdscr.refresh()
                curses.napms(1200)
                return True

            guesses.append((guess, exact, misplaced))

            if len(guesses) >= max_attempts:
                # ── FAILURE ──────────────────────────────────────────
                ans = "".join(secret)
                stdscr.clear()
                msg = f"ICE LOCKOUT — Code was {ans}"
                safe_addstr(stdscr, h // 2, max(0, w // 2 - len(msg) // 2),
                            msg,
                            curses.color_pair(C_RED) | curses.A_BOLD)
                stdscr.refresh()
                curses.napms(1200)
                return False


def _find_spawn_pos(game_map, enemies, cx, cy):
    """Find an empty walkable tile adjacent to (cx, cy) for spawning."""
    for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
        nx, ny = cx + ddx, cy + ddy
        if 0 <= ny < len(game_map) and 0 <= nx < len(game_map[0]):
            if game_map[ny][nx] not in BLOCKING_TILES:
                if not any(e.alive and e.x == nx and e.y == ny for e in enemies):
                    return nx, ny
    return None


def hack_terminal_effects(player, game_map, enemies, tx, ty,
                          stdscr=None, level_num=1):
    """Apply hack effects: disable nearby drones, unlock doors, override turrets.

    When *stdscr* is provided the interactive ICE Breaker minigame is used
    instead of the passive dice-roll.
    """
    if stdscr is not None:
        success = hack_minigame(stdscr, player, level_num)
        msg = "Hack successful!" if success else "Hack failed — ICE held."
    else:
        success, msg = attempt_hack(player, "terminal")
    if not success:
        # ~30% chance to spawn a security drone on failure
        if random.random() < 0.3:
            pos = _find_spawn_pos(game_map, enemies, tx, ty)
            if pos:
                drone = Enemy("Security Drone", pos[0], pos[1])
                drone.alert = True
                drone.glyph = GLYPH_DRONE_ANGRY
                enemies.append(drone)
                return msg + " SECURITY ALERT: Drone dispatched!"
        return msg

    effects_applied = []
    # Disable nearby drones and make turrets friendly
    for e in enemies:
        if e.alive and abs(e.x - tx) <= 5 and abs(e.y - ty) <= 5:
            if e.name == "Security Drone" or e.name == "Turret":
                e.disabled = True
                e.hp = 0
                effects_applied.append(f"Disabled {e.name}")
                player.enemies_killed += 1

    # Unlock nearby locked doors
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            nx, ny = tx + dx, ty + dy
            if 0 <= ny < len(game_map) and 0 <= nx < len(game_map[0]):
                if game_map[ny][nx] == TILE_DOOR_LOCKED:
                    game_map[ny][nx] = TILE_DOOR_OPEN
                    effects_applied.append("Unlocked door")

    # Download data for sats
    bonus = random.randint(20, 60)
    player.credits += bonus
    player.total_credits += bonus
    effects_applied.append(f"Downloaded data (+{bonus} sats)")

    if effects_applied:
        return "Hack successful! " + ", ".join(effects_applied)
    return "Hack successful! No devices in range."


# ═══════════════════════════════════════════════════════════════════════════════
# Ranged combat (line of sight shooting)
# ═══════════════════════════════════════════════════════════════════════════════

def find_shoot_target(player, enemies, game_map):
    """Find the closest visible enemy in firing range."""
    weapon_range = 6
    if player.weapon in WEAPONS and WEAPONS[player.weapon].get("range"):
        weapon_range = WEAPONS[player.weapon]["range"]

    best = None
    best_dist = weapon_range + 1
    for e in enemies:
        if not e.alive:
            continue
        dist = abs(e.x - player.x) + abs(e.y - player.y)
        if dist <= weapon_range and dist < best_dist:
            if _line_of_sight(game_map, player.x, player.y, e.x, e.y):
                best = e
                best_dist = dist
    return best


def _line_of_sight(game_map, x0, y0, x1, y1):
    """Bresenham line-of-sight check. Closed doors block sight."""
    ddx = abs(x1 - x0)
    ddy = abs(y1 - y0)
    sx = 1 if x1 > x0 else -1
    sy = 1 if y1 > y0 else -1
    err = ddx - ddy
    cx, cy = x0, y0
    while True:
        if cx == x1 and cy == y1:
            return True
        if game_map[cy][cx] in OPAQUE_TILES:
            return False
        e2 = 2 * err
        if e2 > -ddy:
            err -= ddy
            cx += sx
        if e2 < ddx:
            err += ddx
            cy += sy
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# Drawing helpers
# ═══════════════════════════════════════════════════════════════════════════════

def init_colors():
    """Initialize curses color pairs for the cyberpunk palette."""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_CYAN, curses.COLOR_CYAN, -1)
    curses.init_pair(C_MAGENTA, curses.COLOR_MAGENTA, -1)
    curses.init_pair(C_GREEN, curses.COLOR_GREEN, -1)
    curses.init_pair(C_RED, curses.COLOR_RED, -1)
    curses.init_pair(C_YELLOW, curses.COLOR_YELLOW, -1)
    curses.init_pair(C_WHITE, curses.COLOR_WHITE, -1)
    curses.init_pair(C_GRAY, curses.COLOR_WHITE, -1)
    curses.init_pair(C_BLUE, curses.COLOR_BLUE, -1)
    curses.init_pair(C_PLAYER, curses.COLOR_GREEN, -1)
    curses.init_pair(C_ENEMY, curses.COLOR_RED, -1)
    curses.init_pair(C_ITEM, curses.COLOR_YELLOW, -1)
    curses.init_pair(C_WALL, curses.COLOR_CYAN, -1)
    curses.init_pair(C_FLOOR, curses.COLOR_WHITE, -1)
    curses.init_pair(C_FOG, curses.COLOR_WHITE, -1)
    curses.init_pair(C_TITLE, curses.COLOR_MAGENTA, -1)
    curses.init_pair(C_SHOP_BG, curses.COLOR_YELLOW, -1)


def safe_addstr(win, y, x, text, attr=0):
    """Write string to window, catching curses errors at edges."""
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x < 0:
        return
    # Truncate if needed
    available = w - x
    if available <= 0:
        return
    text = text[:available]
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


def draw_box(win, y, x, h, w, title="", color_pair=C_CYAN):
    """Draw a box-drawing border."""
    attr = curses.color_pair(color_pair) | curses.A_BOLD
    safe_addstr(win, y, x, BOX_TL + BOX_H * (w - 2) + BOX_TR, attr)
    for row in range(y + 1, y + h - 1):
        safe_addstr(win, row, x, BOX_V, attr)
        safe_addstr(win, row, x + w - 1, BOX_V, attr)
    safe_addstr(win, y + h - 1, x, BOX_BL + BOX_H * (w - 2) + BOX_BR, attr)
    if title:
        safe_addstr(win, y, x + 2, f" {title} ", attr)


def _tile_char_and_attr(game_map, mx, my):
    """Return the (character, curses_attr) for the tile at (mx, my)."""
    if 0 <= my < MAP_H and 0 <= mx < MAP_W:
        tile = game_map[my][mx]
        ch = TILE_CHARS.get(tile, " ")
        if tile == TILE_WALL:
            return ch, curses.color_pair(C_WALL)
        elif tile == TILE_STAIRS:
            return ch, curses.color_pair(C_GREEN) | curses.A_BOLD
        elif tile == TILE_TERMINAL:
            return ch, curses.color_pair(C_MAGENTA) | curses.A_BOLD
        elif tile == TILE_DOOR:
            return ch, curses.color_pair(C_YELLOW)
        elif tile == TILE_DOOR_LOCKED:
            return ch, curses.color_pair(C_RED)
        elif tile == TILE_SHOP_TILE:
            return ch, curses.color_pair(C_YELLOW) | curses.A_BOLD
        else:
            return ch, curses.color_pair(C_FLOOR)
    return " ", curses.color_pair(C_FLOOR)


def draw_map(win, game_map, visible, explored, player, enemies, items,
             cam_x, cam_y, view_w, view_h, map_y_off, map_x_off,
             raven_pos=None):
    """Render the visible portion of the game map."""
    for sy in range(view_h):
        my = cam_y + sy
        for sx in range(view_w):
            mx = cam_x + sx
            screen_y = map_y_off + sy
            screen_x = map_x_off + sx

            if my < 0 or my >= MAP_H or mx < 0 or mx >= MAP_W:
                safe_addstr(win, screen_y, screen_x, " ")
                continue

            if (mx, my) in visible:
                # Draw entity or tile
                drawn = False
                # Player
                if mx == player.x and my == player.y:
                    safe_addstr(win, screen_y, screen_x, GLYPH_PLAYER,
                                curses.color_pair(C_PLAYER) | curses.A_BOLD)
                    drawn = True
                # Raven (after player, before enemies)
                if not drawn and raven_pos and mx == raven_pos[0] and my == raven_pos[1]:
                    safe_addstr(win, screen_y, screen_x, GLYPH_RAVEN,
                                curses.color_pair(C_MAGENTA) | curses.A_BOLD)
                    if not is_ascii_mode() and screen_x + 1 < view_w + map_x_off:
                        nch, nattr = _tile_char_and_attr(game_map, mx + 1, my)
                        safe_addstr(win, screen_y, screen_x + 1, nch, nattr)
                    drawn = True
                # Enemies
                if not drawn:
                    for e in enemies:
                        if e.alive and e.x == mx and e.y == my:
                            glyph = e.state_glyph
                            safe_addstr(win, screen_y, screen_x, glyph,
                                        curses.color_pair(C_ENEMY) | curses.A_BOLD)
                            # Fix wide glyph color bleed: redraw next cell
                            # with the correct background tile (nerdfont only)
                            if not is_ascii_mode() and screen_x + 1 < view_w + map_x_off:
                                nch, nattr = _tile_char_and_attr(
                                    game_map, mx + 1, my)
                                safe_addstr(win, screen_y, screen_x + 1,
                                            nch, nattr)
                            drawn = True
                            break
                # Items
                if not drawn:
                    for it in items:
                        if it.x == mx and it.y == my:
                            safe_addstr(win, screen_y, screen_x, it.glyph,
                                        curses.color_pair(C_ITEM) | curses.A_BOLD)
                            drawn = True
                            break
                # Tile
                if not drawn:
                    tile = game_map[my][mx]
                    ch = TILE_CHARS.get(tile, " ")
                    if tile == TILE_WALL:
                        safe_addstr(win, screen_y, screen_x, ch,
                                    curses.color_pair(C_WALL))
                    elif tile == TILE_STAIRS:
                        safe_addstr(win, screen_y, screen_x, ch,
                                    curses.color_pair(C_GREEN) | curses.A_BOLD)
                    elif tile == TILE_TERMINAL:
                        safe_addstr(win, screen_y, screen_x, ch,
                                    curses.color_pair(C_MAGENTA) | curses.A_BOLD)
                        # Fix wide glyph color bleed: redraw next cell (nerdfont only)
                        if not is_ascii_mode() and screen_x + 1 < view_w + map_x_off:
                            nch, nattr = _tile_char_and_attr(
                                game_map, mx + 1, my)
                            safe_addstr(win, screen_y, screen_x + 1,
                                        nch, nattr)
                    elif tile == TILE_DOOR:
                        safe_addstr(win, screen_y, screen_x, ch,
                                    curses.color_pair(C_YELLOW))
                    elif tile == TILE_DOOR_LOCKED:
                        safe_addstr(win, screen_y, screen_x, ch,
                                    curses.color_pair(C_RED))
                    elif tile == TILE_DOOR_OPEN:
                        safe_addstr(win, screen_y, screen_x, ch,
                                    curses.color_pair(C_FLOOR))
                    elif tile == TILE_SHOP_TILE:
                        safe_addstr(win, screen_y, screen_x, ch,
                                    curses.color_pair(C_YELLOW) | curses.A_BOLD)
                    else:
                        safe_addstr(win, screen_y, screen_x, ch,
                                    curses.color_pair(C_FLOOR))
            elif (mx, my) in explored:
                # Show explored but not currently visible in dim
                tile = game_map[my][mx]
                ch = TILE_CHARS.get(tile, " ")
                safe_addstr(win, screen_y, screen_x, ch,
                            curses.color_pair(C_FOG) | curses.A_DIM)
            else:
                safe_addstr(win, screen_y, screen_x, "░",
                            curses.color_pair(C_FOG) | curses.A_DIM)


def draw_minimap(win, game_map, explored, player, y_off, x_off, mw=15, mh=10):
    """Draw a small minimap showing explored areas."""
    draw_box(win, y_off, x_off, mh + 2, mw + 2, "MINIMAP", C_CYAN)
    scale_x = MAP_W / mw
    scale_y = MAP_H / mh
    for sy in range(mh):
        for sx in range(mw):
            mx = int(sx * scale_x)
            my = int(sy * scale_y)
            if mx >= MAP_W or my >= MAP_H:
                continue
            screen_y = y_off + 1 + sy
            screen_x = x_off + 1 + sx
            if mx == player.x // 1 and my == player.y // 1:
                # Close enough for minimap
                px_s = int(player.x / scale_x)
                py_s = int(player.y / scale_y)
                if sx == px_s and sy == py_s:
                    safe_addstr(win, screen_y, screen_x, "@",
                                curses.color_pair(C_GREEN) | curses.A_BOLD)
                    continue
            if (mx, my) in explored:
                tile = game_map[my][mx]
                if tile == TILE_WALL:
                    safe_addstr(win, screen_y, screen_x, "#",
                                curses.color_pair(C_CYAN) | curses.A_DIM)
                else:
                    safe_addstr(win, screen_y, screen_x, "·",
                                curses.color_pair(C_WHITE) | curses.A_DIM)
            else:
                safe_addstr(win, screen_y, screen_x, " ")


def draw_status_panel(win, player, level_num, y_off, x_off, panel_w=20):
    """Draw the status/HUD panel on the right side."""
    theme = LEVEL_THEMES[level_num - 1] if level_num <= len(LEVEL_THEMES) else LEVEL_THEMES[-1]
    draw_box(win, y_off, x_off, 14, panel_w, "STATUS", C_CYAN)

    row = y_off + 1
    # HP bar
    hp_pct = player.hp / max(1, player.max_hp)
    hp_color = C_GREEN if hp_pct > 0.5 else (C_YELLOW if hp_pct > 0.25 else C_RED)
    safe_addstr(win, row, x_off + 1, f"{GLYPH_HEART} HP: {player.hp}/{player.max_hp}",
                curses.color_pair(hp_color) | curses.A_BOLD)
    row += 1
    bar_w = panel_w - 4
    filled = int(hp_pct * bar_w)
    bar = "█" * filled + "░" * (bar_w - filled)
    safe_addstr(win, row, x_off + 2, bar, curses.color_pair(hp_color))

    row += 1
    safe_addstr(win, row, x_off + 1, f"{GLYPH_CREDITS} SAT: {player.credits}",
                curses.color_pair(C_YELLOW))
    row += 1
    safe_addstr(win, row, x_off + 1, f"{GLYPH_WEAPON} WPN: {player.weapon}",
                curses.color_pair(C_WHITE))
    row += 1
    safe_addstr(win, row, x_off + 1, f"{GLYPH_SHIELD} ARM: {player.armor}",
                curses.color_pair(C_CYAN))
    row += 1
    safe_addstr(win, row, x_off + 1, f"{GLYPH_KEY} Keys: {player.keycards}",
                curses.color_pair(C_MAGENTA))
    row += 1
    safe_addstr(win, row, x_off + 1, f"{GLYPH_CHIP} Data: {player.data_chips}",
                curses.color_pair(C_MAGENTA))
    row += 1
    safe_addstr(win, row, x_off + 1, f"{GLYPH_EYE} Vision: {player.vision}",
                curses.color_pair(C_WHITE))
    row += 1
    safe_addstr(win, row, x_off + 1, f"Class: {player.char_class[:10]}",
                curses.color_pair(C_WHITE))
    row += 1
    safe_addstr(win, row, x_off + 1, f"Level: {level_num}",
                curses.color_pair(C_CYAN))
    row += 1
    safe_addstr(win, row, x_off + 1, f"Kills: {player.enemies_killed}",
                curses.color_pair(C_RED))
    row += 1
    if player.stim_turns > 0:
        safe_addstr(win, row, x_off + 1, f"{GLYPH_BOLT} Stim: {player.stim_turns}t",
                    curses.color_pair(C_MAGENTA) | curses.A_BOLD)


def draw_message_log(win, messages, y_off, x_off, log_w, log_h=4):
    """Draw recent game messages."""
    draw_box(win, y_off, x_off, log_h + 2, log_w, "LOG", C_CYAN)
    recent = messages[-(log_h):]
    for i, msg in enumerate(recent):
        color = C_WHITE
        if "damage" in msg.lower() or "hit" in msg.lower() or "attack" in msg.lower():
            color = C_RED
        elif "hack" in msg.lower():
            color = C_MAGENTA
        elif "pick" in msg.lower() or "sat" in msg.lower() or "found" in msg.lower():
            color = C_YELLOW
        elif "heal" in msg.lower() or "medkit" in msg.lower():
            color = C_GREEN
        safe_addstr(win, y_off + 1 + i, x_off + 1, msg[:log_w - 3],
                    curses.color_pair(color))


# ═══════════════════════════════════════════════════════════════════════════════
# Class Selection Screen
# ═══════════════════════════════════════════════════════════════════════════════

def select_class(stdscr):
    """Display character class selection screen. Returns chosen class string."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    classes = [CLASS_SAMURAI, CLASS_NETRUNNER, CLASS_MEDIC]
    selected = 0

    while True:
        stdscr.clear()
        # Title
        title = "╔══ CYBERPUNK MEGACITY ROGUELITE ═╗"
        subtitle = "║   Neo-Shibuya, 2087             ║"
        bottom = "╚═════════════════════════════════╝"
        cx = max(0, w // 2 - len(title) // 2)
        safe_addstr(stdscr, 2, cx, title, curses.color_pair(C_CYAN) | curses.A_BOLD)
        safe_addstr(stdscr, 3, cx, subtitle, curses.color_pair(C_CYAN))
        safe_addstr(stdscr, 4, cx, bottom, curses.color_pair(C_CYAN))

        safe_addstr(stdscr, 6, cx, "Choose your class:", curses.color_pair(C_WHITE) | curses.A_BOLD)

        for i, cls_name in enumerate(classes):
            stats = CLASS_STATS[cls_name]
            y = 8 + i * 4
            if i == selected:
                marker = f"▸ {cls_name}"
                attr = curses.color_pair(C_GREEN) | curses.A_BOLD
            else:
                marker = f"  {cls_name}"
                attr = curses.color_pair(C_WHITE)
            safe_addstr(stdscr, y, cx, marker, attr)
            safe_addstr(stdscr, y + 1, cx + 4, stats["desc"],
                        curses.color_pair(C_GRAY))
            stat_line = (f"HP:{stats['hp']} ATK:{stats['attack']} DEF:{stats['defense']} "
                         f"HACK:{stats['hack_skill']}%")
            safe_addstr(stdscr, y + 2, cx + 4, stat_line,
                        curses.color_pair(C_CYAN))

        mode_label = "NerdFont" if _tile_mode == "nerdfont" else "ASCII"
        safe_addstr(stdscr, 21, cx, f"Tile Mode: {mode_label}  (v to toggle)",
                    curses.color_pair(C_MAGENTA))
        safe_addstr(stdscr, 22, cx, "Arrow keys to select, ENTER to confirm",
                    curses.color_pair(C_YELLOW))
        safe_addstr(stdscr, 23, cx, "q to quit",
                    curses.color_pair(C_GRAY))

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_UP, ord('w'), ord('W')):
            selected = (selected - 1) % len(classes)
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            selected = (selected + 1) % len(classes)
        elif key in (ord('v'), ord('V')):
            _toggle_tile_mode()
        elif key in (10, 13, curses.KEY_ENTER):
            return classes[selected]
        elif key in (ord('q'), ord('Q')):
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# Shop Screen (Raven NPC)
# ═══════════════════════════════════════════════════════════════════════════════

def shop_screen(stdscr, player, level_num):
    """Display Raven's shop. Player can buy items with satoshis."""
    stock = get_shop_stock(level_num)
    selected = 0
    messages = []

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        title = f"╔══ RAVEN'S SHOP — Level {level_num} ══╗"
        cx = max(0, w // 2 - len(title) // 2)

        safe_addstr(stdscr, 1, cx, title, curses.color_pair(C_MAGENTA) | curses.A_BOLD)
        safe_addstr(stdscr, 2, cx, f"  {GLYPH_CREDITS} Satoshis: {player.credits}",
                    curses.color_pair(C_YELLOW) | curses.A_BOLD)
        safe_addstr(stdscr, 3, cx, "  Browse Raven's wares.", curses.color_pair(C_WHITE))
        safe_addstr(stdscr, 4, cx, BOX_H * len(title), curses.color_pair(C_MAGENTA))

        for i, item in enumerate(stock):
            y = 6 + i * 2
            afford = player.credits >= item["price"]
            if i == selected:
                marker = "▸ "
                attr = curses.color_pair(C_GREEN if afford else C_RED) | curses.A_BOLD
            else:
                marker = "  "
                attr = curses.color_pair(C_WHITE if afford else C_GRAY)
            price_str = f"  ₿{item['price']}"
            safe_addstr(stdscr, y, cx, f"{marker}{item.get('glyph', GLYPH_STAR)} {item['name']}{price_str}", attr)

        foot_y = 6 + len(stock) * 2 + 1
        safe_addstr(stdscr, foot_y, cx, "  ENTER = purchase, C = close shop",
                    curses.color_pair(C_YELLOW))

        for i, msg in enumerate(messages[-3:]):
            safe_addstr(stdscr, foot_y + 2 + i, cx + 2, msg, curses.color_pair(C_GREEN))

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_UP, ord('w'), ord('W')):
            selected = (selected - 1) % max(1, len(stock))
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            selected = (selected + 1) % max(1, len(stock))
        elif key in (10, 13, curses.KEY_ENTER):
            if stock and selected < len(stock):
                item = stock[selected]
                if player.credits >= item["price"]:
                    player.credits -= item["price"]
                    if item["type"] == "weapon":
                        player.weapon = item["name"]
                        player.weapon_type = item.get("weapon_type", "melee")
                        player.weapon_dmg = item.get("damage", 10)
                        messages.append(f"Equipped {item['name']}!")
                    elif item["type"] == "armor":
                        player.armor = item["name"]
                        player.armor_def = item.get("armor_def", 3)
                        messages.append(f"Equipped {item['name']}!")
                    elif item["type"] == "consumable":
                        player.inventory.append(item)
                        messages.append(f"Bought {item['name']}!")
                else:
                    messages.append("Can't afford that!")
        elif key in (ord('c'), ord('C')):
            break
        elif key in (ord('q'), ord('Q')):
            break


# ═══════════════════════════════════════════════════════════════════════════════
# Inventory Screen
# ═══════════════════════════════════════════════════════════════════════════════

def inventory_screen(stdscr, player):
    """Show player inventory and allow using consumables."""
    selected = 0
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        safe_addstr(stdscr, 1, 2, "╔══ INVENTORY ══╗",
                    curses.color_pair(C_CYAN) | curses.A_BOLD)
        safe_addstr(stdscr, 2, 2, f"  Items: {len(player.inventory)}",
                    curses.color_pair(C_WHITE))

        if not player.inventory:
            safe_addstr(stdscr, 4, 4, "Empty. Pick up items in the megacity.",
                        curses.color_pair(C_GRAY))
        else:
            for i, item in enumerate(player.inventory):
                y = 4 + i
                attr = curses.color_pair(C_GREEN) | curses.A_BOLD if i == selected else curses.color_pair(C_WHITE)
                name = item.get("name", "Unknown")
                safe_addstr(stdscr, y, 4, f"{'▸ ' if i == selected else '  '}{name}", attr)

        foot = max(4 + len(player.inventory) + 2, 10)
        safe_addstr(stdscr, foot, 2, "ENTER = use, ESC/i = close",
                    curses.color_pair(C_YELLOW))

        stdscr.refresh()
        key = stdscr.getch()

        if key in (27, ord('i'), ord('I')):
            break
        elif key in (curses.KEY_UP, ord('w'), ord('W')):
            if player.inventory:
                selected = (selected - 1) % len(player.inventory)
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            if player.inventory:
                selected = (selected + 1) % len(player.inventory)
        elif key in (10, 13, curses.KEY_ENTER):
            if player.inventory and selected < len(player.inventory):
                item = player.inventory[selected]
                if item.get("name") == "Medkit":
                    player.use_medkit()
                    break
                elif item.get("name") == "Stim Pack":
                    player.use_stim()
                    break


# ═══════════════════════════════════════════════════════════════════════════════
# Game Over Screen
# ═══════════════════════════════════════════════════════════════════════════════

def game_over_screen(stdscr, player, level_num, won=False):
    """Display game over / death screen with run stats."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    if won:
        title = "╔══ MISSION COMPLETE ══╗"
        subtitle = "You escaped the megacity!"
        color = C_GREEN
    else:
        title = "╔══ GAME OVER ══╗"
        subtitle = "You died in the neon-lit streets..."
        color = C_RED

    cx = max(0, w // 2 - len(title) // 2)

    safe_addstr(stdscr, 3, cx, title,
                curses.color_pair(color) | curses.A_BOLD)
    safe_addstr(stdscr, 5, cx, subtitle, curses.color_pair(color))

    safe_addstr(stdscr, 7, cx, f"  {GLYPH_STAR} Final Stats {GLYPH_STAR}",
                curses.color_pair(C_YELLOW) | curses.A_BOLD)

    stats = [
        f"  Class: {player.char_class}",
        f"  Levels Cleared: {player.levels_cleared}",
        f"  Enemies Killed: {player.enemies_killed}",
        f"  Total Satoshis Earned: {player.total_credits}",
        f"  Data Chips Found: {player.data_chips}",
        f"  Damage Dealt: {player.damage_dealt}",
        f"  Damage Taken: {player.damage_taken}",
        f"  Hacks Attempted: {player.hacks_attempted}",
        f"  Hacks Succeeded: {player.hacks_succeeded}",
        f"  Items Used: {player.items_used}",
        f"  Turns Survived: {player.turns_taken}",
    ]

    for i, line in enumerate(stats):
        safe_addstr(stdscr, 9 + i, cx, line, curses.color_pair(C_WHITE))

    score = (player.enemies_killed * 100 + player.levels_cleared * 500 +
             player.total_credits + player.data_chips * 200)
    safe_addstr(stdscr, 9 + len(stats) + 1, cx,
                f"  {GLYPH_STAR} Score: {score} {GLYPH_STAR}",
                curses.color_pair(C_YELLOW) | curses.A_BOLD)

    # Jack-out sequence
    jack_row = 9 + len(stats) + 3
    jack_rows = show_jack_out(stdscr, jack_row, cx, won=won)

    safe_addstr(stdscr, jack_row + jack_rows + 1, cx,
                "  Press any key to quit...",
                curses.color_pair(C_GRAY))

    stdscr.refresh()
    stdscr.getch()


# ═══════════════════════════════════════════════════════════════════════════════
# Item pickup helper
# ═══════════════════════════════════════════════════════════════════════════════

def _pickup_item(player, item, items, messages):
    """Pick up a single item, applying its effects and removing it from the map."""
    if item.item_type == "credits":
        amt = item.props.get("amount", 10)
        player.credits += amt
        player.total_credits += amt
        messages.append(f"Picked up {item.name}!")
    elif item.item_type == "keycard":
        player.keycards += 1
        messages.append("Found a keycard!")
    elif item.item_type == "data_chip":
        player.data_chips += 1
        val = item.props.get("value", 50)
        player.credits += val
        player.total_credits += val
        messages.append(f"Found Data Chip! +{val} sats")
    elif item.item_type == "weapon":
        player.weapon = item.name
        player.weapon_type = item.props.get("weapon_type", "melee")
        player.weapon_dmg = item.props.get("damage", 10)
        messages.append(f"Equipped {item.name}!")
    elif item.item_type == "armor":
        player.armor = item.name
        player.armor_def = item.props.get("defense", 3)
        messages.append(f"Equipped {item.name}!")
    else:
        player.inventory.append({"name": item.name, **item.props})
        messages.append(f"Picked up {item.name}!")
    items.remove(item)


# ═══════════════════════════════════════════════════════════════════════════════
# Jack-In / Jack-Out Sequences
# ═══════════════════════════════════════════════════════════════════════════════

def show_jack_in(stdscr, char_class):
    """Display immersive jack-in sequence after class selection."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    cx = max(0, w // 2 - 25)

    lines = [
        (f"  {GLYPH_JACK_IN}  Neural implant activating...", C_CYAN),
        ("  Synaptic bridge: ONLINE", C_GREEN),
        ("  Biometric signature verified.", C_WHITE),
        (f"  Operator class: {char_class}", C_YELLOW),
        ("  Establishing uplink to Neo-Shibuya net...", C_CYAN),
        ("  Gargoyle relays locked. Bandwidth is nominal.", C_WHITE),
        ("  ██████████████████████████ 100%", C_GREEN),
        ("  The sky is the color of a dead channel...", C_MAGENTA),
        (f"  {GLYPH_JACK_IN}  CONNECTION ESTABLISHED", C_GREEN),
    ]

    for i, (text, color) in enumerate(lines):
        safe_addstr(stdscr, 4 + i * 2, cx, text,
                    curses.color_pair(color) | curses.A_BOLD)
        stdscr.refresh()
        time.sleep(0.45)

    safe_addstr(stdscr, 4 + len(lines) * 2 + 1, cx,
                "  Press any key to enter the megacity...",
                curses.color_pair(C_GRAY))
    stdscr.refresh()
    stdscr.getch()


def show_jack_out(stdscr, row, cx, won=False):
    """Display jack-out flavor text on game-over/victory screen.

    Returns the number of rows consumed so callers can offset below.
    """
    if won:
        lines = [
            (f"  {GLYPH_JACK_IN}  Initiating disconnect...", C_CYAN),
            ("  Neural link severed cleanly.", C_GREEN),
            ("  You pull the jack from your temple.", C_WHITE),
            ("  The neon fades. Reality floods back.", C_MAGENTA),
            (f"  {GLYPH_JACK_IN}  JACKED OUT — MISSION COMPLETE", C_GREEN),
        ]
    else:
        lines = [
            (f"  {GLYPH_JACK_IN}  WARNING: Biometrics critical", C_RED),
            ("  Neural link destabilizing...", C_YELLOW),
            ("  Emergency disconnect triggered.", C_RED),
            ("  All those moments — lost, like tears in rain.", C_MAGENTA),
            (f"  {GLYPH_JACK_IN}  SIGNAL LOST", C_RED),
        ]

    for i, (text, color) in enumerate(lines):
        safe_addstr(stdscr, row + i, cx, text,
                    curses.color_pair(color) | curses.A_BOLD)
    return len(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Main Game Loop
# ═══════════════════════════════════════════════════════════════════════════════

def main(stdscr):
    """Main game function called via curses.wrapper()."""
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    init_colors()

    # Load tileset preference and apply
    _load_settings()
    _apply_tileset()

    # Class selection (includes tile mode toggle)
    char_class = select_class(stdscr)
    if char_class is None:
        return

    # Jack-in sequence
    show_jack_in(stdscr, char_class)

    player = Player(char_class)
    level_num = 1
    messages = ["Jacked in. Find the stairs to descend deeper."]

    # Generate first level
    game_map, rooms, start, stairs, enemies, items, terminals, raven_pos = generate_level(level_num)
    player.x, player.y = start
    explored = set()

    game_running = True

    while game_running:
        h, w = stdscr.getmaxyx()
        stdscr.erase()

        # Compute visibility (fog of war with vision radius)
        visible = compute_fov(game_map, player.x, player.y, player.vision)
        explored.update(visible)

        # Camera
        view_w = min(MAP_W, w - 24)
        view_h = min(MAP_H, h - 8)
        cam_x = max(0, min(player.x - view_w // 2, MAP_W - view_w))
        cam_y = max(0, min(player.y - view_h // 2, MAP_H - view_h))

        # Top bar
        theme = LEVEL_THEMES[level_num - 1] if level_num <= len(LEVEL_THEMES) else LEVEL_THEMES[-1]
        top_title = f"╔═ {theme['level_name'].upper()} — LEVEL {level_num} "
        top_title += BOX_H * max(1, view_w - len(top_title)) + BOX_TR
        safe_addstr(stdscr, 0, 0, top_title, curses.color_pair(C_CYAN) | curses.A_BOLD)

        # Draw map area
        map_y_off = 1
        map_x_off = 1
        draw_map(stdscr, game_map, visible, explored, player, enemies, items,
                 cam_x, cam_y, view_w, view_h, map_y_off, map_x_off,
                 raven_pos=raven_pos)

        # Bottom border of map
        bot_border = BOX_BL + BOX_H * view_w + BOX_BR
        safe_addstr(stdscr, map_y_off + view_h, 0, bot_border,
                    curses.color_pair(C_CYAN))

        # Status panel (right side)
        panel_x = view_w + 3
        draw_status_panel(stdscr, player, level_num, 0, panel_x, panel_w=min(20, w - panel_x - 1))

        # Minimap
        mini_y = 15
        draw_minimap(stdscr, game_map, explored, player, mini_y, panel_x)

        # Message log (below map)
        log_y = map_y_off + view_h + 1
        draw_message_log(stdscr, messages, log_y, 0, view_w + 2, min(4, h - log_y - 3))

        # Help line
        help_y = h - 1
        ap_str = "ON" if player.auto_pickup else "OFF"
        help_text = f" Move:←↑↓→  Space:Wait  f:Fire  h:Hack  e:Interact  i:Inv  m:Medkit  a:Auto({ap_str})  q:Quit "
        safe_addstr(stdscr, help_y, 0, help_text[:w - 1], curses.color_pair(C_GRAY))

        stdscr.refresh()

        # Input
        key = stdscr.getch()
        dx, dy = 0, 0
        action = None

        if key in (curses.KEY_UP, ord('w'), ord('W')):
            dy = -1
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            dy = 1
        elif key in (curses.KEY_LEFT, ord('a'), ord('A')):
            dx = -1
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            dx = 1
        elif key in (ord('q'), ord('Q')):
            game_running = False
            continue
        elif key in (ord('f'), ord('F')):
            action = "fire"
        elif key in (ord('h'), ord('H')):
            action = "hack"
        elif key in (ord('e'), ord('E')):
            action = "interact"
        elif key in (ord('i'), ord('I')):
            inventory_screen(stdscr, player)
            continue
        elif key in (ord('m'), ord('M')):
            if player.use_medkit():
                messages.append(f"Used Medkit. HP: {player.hp}/{player.max_hp}")
            else:
                messages.append("No Medkits in inventory!")
            continue
        elif key in (ord('t'), ord('T')):
            if player.use_stim():
                messages.append(f"Used Stim Pack! +{player.stim_bonus} attack for {player.stim_turns} turns.")
            else:
                messages.append("No Stim Packs in inventory!")
            continue
        elif key in (ord('a'),):
            player.auto_pickup = not player.auto_pickup
            state = "ON" if player.auto_pickup else "OFF"
            messages.append(f"Auto-pickup: {state}")
            continue
        elif key == ord(' '):
            action = "wait"
        else:
            continue

        player.turns_taken += 1
        player.tick_stim()

        # Handle actions
        if action == "fire":
            if player.weapon_type != "ranged":
                messages.append("No ranged weapon equipped!")
            else:
                target = find_shoot_target(player, enemies, game_map)
                if target:
                    dmg = player.deal_ranged_damage()
                    actual = target.take_damage(dmg)
                    player.damage_dealt += actual
                    messages.append(f"Shot {target.name} for {actual} damage!")
                    if not target.alive:
                        player.enemies_killed += 1
                        player.credits += target.credits
                        player.total_credits += target.credits
                        messages.append(f"{target.name} destroyed! +{target.credits} sats")
                else:
                    messages.append("No target in range!")

        elif action == "hack":
            # Find adjacent terminal
            hacked = False
            for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)]:
                tx, ty = player.x + ddx, player.y + ddy
                if 0 <= ty < MAP_H and 0 <= tx < MAP_W:
                    if game_map[ty][tx] == TILE_TERMINAL:
                        msg = hack_terminal_effects(
                            player, game_map, enemies, tx, ty,
                            stdscr=stdscr, level_num=level_num)
                        messages.append(msg)
                        hacked = True
                        break
            if not hacked:
                messages.append("No terminal nearby to hack!")

        elif action == "interact":
            # Check for adjacent Raven NPC
            interacted_raven = False
            if raven_pos:
                for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)]:
                    tx, ty = player.x + ddx, player.y + ddy
                    if (tx, ty) == raven_pos:
                        messages.append(random.choice(RAVEN_DIALOGUE))
                        shop_screen(stdscr, player, level_num)
                        interacted_raven = True
                        break
            # Open adjacent doors (checked before items so locked doors
            # aren't blocked by standing on a pickup)
            opened_door = False
            if not interacted_raven:
                for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    tx, ty = player.x + ddx, player.y + ddy
                    if 0 <= ty < MAP_H and 0 <= tx < MAP_W:
                        if game_map[ty][tx] == TILE_DOOR:
                            game_map[ty][tx] = TILE_DOOR_OPEN
                            messages.append("Opened door.")
                            opened_door = True
                            break
                        elif game_map[ty][tx] == TILE_DOOR_LOCKED:
                            if player.keycards > 0:
                                player.keycards -= 1
                                game_map[ty][tx] = TILE_DOOR_OPEN
                                messages.append("Used keycard — unlocked door!")
                                opened_door = True
                            else:
                                messages.append("Door locked! Need a keycard or hack.")
                            break
            # Pick up items at current position
            if not interacted_raven and not opened_door:
                for it in items[:]:
                    if it.x == player.x and it.y == player.y:
                        _pickup_item(player, it, items, messages)

        elif dx != 0 or dy != 0:
            nx, ny = player.x + dx, player.y + dy
            if 0 <= ny < MAP_H and 0 <= nx < MAP_W:
                tile = game_map[ny][nx]

                # Raven blocks movement but is not attackable
                if raven_pos and (nx, ny) == raven_pos:
                    messages.append("Raven blocks your path. Press 'e' to talk.")

                # Check for enemy (bump-to-attack / melee combat)
                elif (target_enemy := next(
                    (e for e in enemies if e.alive and e.x == nx and e.y == ny), None
                )):
                    dmg = player.deal_melee_damage()
                    actual = target_enemy.take_damage(dmg)
                    player.damage_dealt += actual
                    messages.append(f"Hit {target_enemy.name} for {actual} damage!")
                    if not target_enemy.alive:
                        player.enemies_killed += 1
                        player.credits += target_enemy.credits
                        player.total_credits += target_enemy.credits
                        messages.append(f"{target_enemy.name} destroyed! +{target_enemy.credits} sats")

                elif tile == TILE_DOOR:
                    # Bump to open unlocked doors — door disappears
                    game_map[ny][nx] = TILE_DOOR_OPEN
                    player.x = nx
                    player.y = ny
                    messages.append("Opened door.")

                elif tile == TILE_DOOR_LOCKED:
                    # Bump locked door — hint to use 'e' instead
                    if player.keycards > 0:
                        messages.append("Door locked! Press 'e' to use a keycard.")
                    else:
                        messages.append("Door locked! Need a keycard or hack.")

                elif tile in (TILE_FLOOR, TILE_CORRIDOR, TILE_DOOR_OPEN,
                              TILE_STAIRS, TILE_TERMINAL, TILE_SHOP_TILE):
                    player.x = nx
                    player.y = ny

                    # Auto-pickup items on the tile
                    if player.auto_pickup:
                        for it in items[:]:
                            if it.x == player.x and it.y == player.y:
                                _pickup_item(player, it, items, messages)

                    # Check stairs
                    if tile == TILE_STAIRS:
                        # Confirm before descending
                        prompt = "Descend to the next level? (y/n)"
                        safe_addstr(stdscr, h - 2, 1, prompt, curses.color_pair(C_YELLOW) | curses.A_BOLD)
                        stdscr.refresh()
                        confirm = stdscr.getch()
                        if confirm not in (ord('y'), ord('Y')):
                            messages.append("You stay on this level.")
                            continue
                        player.levels_cleared += 1
                        if level_num >= MAX_LEVELS:
                            # Victory!
                            game_over_screen(stdscr, player, level_num, won=True)
                            game_running = False
                            continue
                        else:
                            level_num += 1
                            game_map, rooms, start, stairs, enemies, items, terminals, raven_pos = generate_level(level_num)
                            player.x, player.y = start
                            explored = set()
                            messages.append(f"Descended to Level {level_num}...")
                            theme = LEVEL_THEMES[level_num - 1] if level_num <= len(LEVEL_THEMES) else LEVEL_THEMES[-1]
                            messages.append(f"Entering: {theme['level_name']}")
                            continue

                # Wall or other blocking tile — can't move
            else:
                pass  # Out of bounds

        # Enemy turn
        for e in enemies:
            if e.alive and not e.disabled:
                result = e.take_turn(game_map, player, enemies)
                if result:
                    if result[0] == "attack":
                        messages.append(f"{e.name} attacks you for {result[1]} damage!")
                    elif result[0] == "shoot":
                        dmg = max(1, e.attack + random.randint(-2, 2))
                        actual = player.take_damage(dmg)
                        messages.append(f"{e.name} shoots you for {actual} damage!")

        # Chrome Medic passive heal
        if player.char_class == CLASS_MEDIC and player.heal_power > 0:
            if player.turns_taken % 5 == 0 and player.hp < player.max_hp:
                heal_amt = min(player.heal_power // 4, player.max_hp - player.hp)
                if heal_amt > 0:
                    player.heal(heal_amt)
                    messages.append(f"Chrome Medic auto-heal: +{heal_amt} HP")

        # Check death (permadeath)
        if not player.alive:
            game_over_screen(stdscr, player, level_num, won=False)
            game_running = False

        # Keep message log trimmed
        if len(messages) > 50:
            messages = messages[-50:]


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    curses.wrapper(main)
