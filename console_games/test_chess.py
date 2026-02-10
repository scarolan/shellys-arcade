#!/usr/bin/env python3
"""Test suite for the Chess game (scripts/games/chess.py)."""

import ast
import os
import stat
import sys
import unittest

# ── Path setup ──────────────────────────────────────────────────────
CHESS_PATH = os.path.join(os.path.dirname(__file__), "chess.py")


def load_source():
    """Load chess.py source as a string."""
    with open(CHESS_PATH, "r", encoding="utf-8") as f:
        return f.read()


def parse_ast():
    """Parse chess.py into an AST tree."""
    return ast.parse(load_source())


def get_top_level_names(tree):
    """Extract top-level function, class, and variable names from AST."""
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


def find_all_functions(tree):
    """Walk AST and find all function definitions (including nested)."""
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = node
    return functions


def find_all_string_literals(tree):
    """Extract all string constants from AST."""
    strings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append(node.value)
    return strings


def import_module():
    """Import chess module by stripping __main__ guard and exec'ing."""
    source = load_source()
    tree = ast.parse(source)
    new_body = []
    for node in tree.body:
        if isinstance(node, ast.If):
            test = node.test
            if (isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name)
                    and test.left.id == "__name__"):
                continue
        new_body.append(node)
    tree.body = new_body
    ast.fix_missing_locations(tree)
    code = compile(tree, CHESS_PATH, "exec")
    namespace = {"__file__": CHESS_PATH, "__name__": "chess"}
    exec(code, namespace)
    return namespace


# ════════════════════════════════════════════════════════════════════
#  Test classes
# ════════════════════════════════════════════════════════════════════

class TestFileStructure(unittest.TestCase):
    """Validate file existence, shebang, docstring, and imports."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.tree = parse_ast()

    def test_file_exists(self):
        """chess.py must exist."""
        self.assertTrue(os.path.isfile(CHESS_PATH))

    def test_has_shebang(self):
        """First line should be a Python shebang."""
        self.assertTrue(self.source.startswith("#!/usr/bin/env python3"))

    def test_has_docstring(self):
        """Module-level docstring should be present."""
        module = self.tree
        self.assertIsInstance(module.body[0], ast.Expr)
        self.assertIsInstance(module.body[0].value, ast.Constant)
        self.assertIsInstance(module.body[0].value.value, str)

    def test_syntax_valid(self):
        """Source must parse without syntax errors."""
        try:
            ast.parse(self.source)
        except SyntaxError:
            self.fail("chess.py has syntax errors")

    def test_stdlib_only(self):
        """Only standard library modules should be imported."""
        allowed = {"sys", "os", "copy", "random", "curses"}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split(".")[0], allowed,
                                  f"Non-stdlib import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.assertIn(node.module.split(".")[0], allowed,
                                  f"Non-stdlib import: {node.module}")


class TestRequiredComponents(unittest.TestCase):
    """Validate essential game structure."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.tree = parse_ast()
        cls.names = get_top_level_names(cls.tree)
        cls.functions = find_all_functions(cls.tree)

    def test_has_main_function(self):
        """Must have a main() function."""
        self.assertIn("main", self.functions)

    def test_has_chess_game_class(self):
        """Must have a ChessGame class."""
        self.assertIn("ChessGame", self.names)

    def test_has_initial_board_function(self):
        """Must have an initial_board() function."""
        self.assertIn("initial_board", self.functions)


class TestBoardInit(unittest.TestCase):
    """Board initialization and piece placement."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()
        cls.board = cls.ns["initial_board"]()

    def test_initial_board_is_8x8(self):
        """initial_board() must return an 8x8 grid."""
        self.assertEqual(len(self.board), 8)
        for row in self.board:
            self.assertEqual(len(row), 8)

    def test_white_has_16_pieces(self):
        """Initial board should have 16 white (uppercase) pieces."""
        count = sum(1 for r in self.board for p in r
                    if p is not None and p.isupper())
        self.assertEqual(count, 16)

    def test_black_has_16_pieces(self):
        """Initial board should have 16 black (lowercase) pieces."""
        count = sum(1 for r in self.board for p in r
                    if p is not None and p.islower())
        self.assertEqual(count, 16)

    def test_white_back_rank(self):
        """White back rank (row 7) should be RNBQKBNR."""
        self.assertEqual(self.board[7], list("RNBQKBNR"))

    def test_black_back_rank(self):
        """Black back rank (row 0) should be rnbqkbnr."""
        self.assertEqual(self.board[0], list("rnbqkbnr"))

    def test_white_pawns_on_rank_2(self):
        """White pawns should be on row 6 (rank 2)."""
        self.assertEqual(self.board[6], list("PPPPPPPP"))

    def test_black_pawns_on_rank_7(self):
        """Black pawns should be on row 1 (rank 7)."""
        self.assertEqual(self.board[1], list("pppppppp"))

    def test_empty_middle_rows(self):
        """Rows 2-5 should be empty at start."""
        for r in range(2, 6):
            self.assertTrue(all(p is None for p in self.board[r]),
                            f"Row {r} should be empty")


class TestMoveValidation(unittest.TestCase):
    """Move parsing and legal move generation."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def _new_game(self):
        return self.ns["ChessGame"]()

    def test_parse_move_e2e4(self):
        """parse_move should parse 'e2e4' correctly."""
        game = self._new_game()
        result = game.parse_move("e2e4")
        self.assertIsNotNone(result)
        fr, fc, tr, tc, promo = result
        self.assertEqual((fr, fc, tr, tc), (6, 4, 4, 4))

    def test_parse_move_with_promotion(self):
        """parse_move should handle promotion suffix like 'e7e8q'."""
        game = self._new_game()
        result = game.parse_move("e7e8q")
        self.assertIsNotNone(result)
        self.assertEqual(result[4], "q")

    def test_parse_move_invalid_input(self):
        """parse_move should return None for invalid input."""
        game = self._new_game()
        self.assertIsNone(game.parse_move("xyz"))
        self.assertIsNone(game.parse_move(""))
        self.assertIsNone(game.parse_move("e2e9"))

    def test_legal_moves_from_start(self):
        """White should have 20 legal moves from the starting position."""
        game = self._new_game()
        moves = game.generate_legal_moves()
        self.assertEqual(len(moves), 20)


class TestPieceMovement(unittest.TestCase):
    """Piece-specific movement rules."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def _new_game(self):
        return self.ns["ChessGame"]()

    def test_pawn_can_move_one_square(self):
        """Pawn should be able to move one square forward."""
        game = self._new_game()
        moves = game.generate_legal_moves()
        # e2e3 should be legal
        self.assertIn(((6, 4), (5, 4)), moves)

    def test_pawn_can_move_two_squares_from_start(self):
        """Pawn should be able to move two squares from starting row."""
        game = self._new_game()
        moves = game.generate_legal_moves()
        self.assertIn(((6, 4), (4, 4)), moves)

    def test_knight_can_jump(self):
        """Knight should be able to jump over pieces."""
        game = self._new_game()
        moves = game.generate_legal_moves()
        # Nb1c3 should be legal
        self.assertIn(((7, 1), (5, 2)), moves)

    def test_bishop_blocked_at_start(self):
        """Bishop should have no moves at game start (blocked by pawns)."""
        game = self._new_game()
        moves = game.generate_legal_moves()
        # No moves starting from c1 (7,2) bishop
        bishop_moves = [m for m in moves if m[0] == (7, 2)]
        self.assertEqual(len(bishop_moves), 0)


class TestCheckDetection(unittest.TestCase):
    """Check and checkmate detection."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def _new_game(self):
        return self.ns["ChessGame"]()

    def test_not_in_check_at_start(self):
        """Neither side should be in check at start."""
        game = self._new_game()
        self.assertFalse(game.in_check("white"))
        self.assertFalse(game.in_check("black"))

    def test_check_detection(self):
        """A king under attack should be detected as in check."""
        game = self._new_game()
        # Clear board and set up a check: white Qd1 attacks black Ke8
        game.board = [[None] * 8 for _ in range(8)]
        game.board[0][4] = "k"  # Black king on e8
        game.board[7][4] = "K"  # White king on e1
        game.board[4][4] = "Q"  # White queen on e4 (attacks along file)
        self.assertTrue(game.in_check("black"))

    def test_scholars_mate(self):
        """Scholar's mate should result in checkmate."""
        game = self._new_game()
        moves = [("e2e4", "e7e5"), ("d1h5", "b8c6"), ("f1c4", "g8f6"),
                 ("h5f7",)]
        for pair in moves:
            for move_str in pair:
                parsed = game.parse_move(move_str)
                fr, fc, tr, tc, promo = parsed
                game.make_move(fr, fc, tr, tc, promo)
        self.assertEqual(game.game_status(), "checkmate")


class TestSpecialMoves(unittest.TestCase):
    """Castling, en passant, and promotion."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def _new_game(self):
        return self.ns["ChessGame"]()

    def test_kingside_castle(self):
        """White should be able to castle kingside when path is clear."""
        game = self._new_game()
        # Clear f1 and g1
        game.board[7][5] = None
        game.board[7][6] = None
        moves = game.generate_legal_moves()
        # King e1 to g1 (castling)
        self.assertIn(((7, 4), (7, 6)), moves)

    def test_queenside_castle(self):
        """White should be able to castle queenside when path is clear."""
        game = self._new_game()
        # Clear b1, c1, d1
        game.board[7][1] = None
        game.board[7][2] = None
        game.board[7][3] = None
        moves = game.generate_legal_moves()
        self.assertIn(((7, 4), (7, 2)), moves)

    def test_en_passant(self):
        """En passant capture should be available after opponent double-push."""
        game = self._new_game()
        # Set up: white pawn on e5, black pawn double-pushes d7d5
        game.board = [[None] * 8 for _ in range(8)]
        game.board[0][4] = "k"
        game.board[7][4] = "K"
        game.board[3][4] = "P"  # White pawn on e5
        game.board[1][3] = "p"  # Black pawn on d7
        game.turn = "black"
        game.make_move(1, 3, 3, 3)  # d7d5
        # Now white should have en passant capture e5xd6
        moves = game.generate_legal_moves()
        self.assertIn(((3, 4), (2, 3)), moves)

    def test_pawn_promotion(self):
        """Pawn reaching the last rank should be promoted."""
        game = self._new_game()
        game.board = [[None] * 8 for _ in range(8)]
        game.board[7][4] = "K"
        game.board[0][4] = "k"
        game.board[1][0] = "P"  # White pawn on a7
        game.turn = "white"
        game.make_move(1, 0, 0, 0, "q")
        self.assertEqual(game.board[0][0], "Q")


class TestColorContrast(unittest.TestCase):
    """ANSI color scheme should provide adequate contrast."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def _ansi_256_index(self, code):
        """Extract the 256-color index from an ANSI escape string like
        '\\033[48;5;180m' -> 180, or return None for non-256 codes."""
        if ";5;" in code:
            return int(code.split(";5;")[1].rstrip("m"))
        return None

    def test_light_square_not_too_bright(self):
        """Light square background should not be too bright (avoid near-white)."""
        light = self.ns["LIGHT_SQ"]
        idx = self._ansi_256_index(light)
        # 256-color indexes 223-231 are very bright yellows/whites; avoid them
        if idx is not None:
            self.assertNotIn(idx, range(223, 232),
                             f"Light square color {idx} is too bright for white pieces")

    def test_dark_square_is_dark(self):
        """Dark square should use a dark 256-color index."""
        dark = self.ns["DARK_SQ"]
        idx = self._ansi_256_index(dark)
        if idx is not None:
            # Should be in the darker range (< 150 for 256-color)
            self.assertLess(idx, 150,
                            f"Dark square color {idx} is too bright")

    def test_white_fg_uses_bright(self):
        """White pieces foreground should use bright/bold white (97 or 255)."""
        white_fg = self.ns["WHITE_FG"]
        bright = "97" in white_fg or "255" in white_fg or "231" in white_fg
        self.assertTrue(bright,
                        "White piece foreground should be bright white")

    def test_black_fg_uses_dark(self):
        """Black pieces foreground should use a very dark color."""
        black_fg = self.ns["BLACK_FG"]
        dark = "16" in black_fg or "0m" in black_fg or "30" in black_fg
        self.assertTrue(dark,
                        "Black piece foreground should be dark/black")


class TestUnicodeChessPieces(unittest.TestCase):
    """Unicode chess piece glyphs must be present."""

    @classmethod
    def setUpClass(cls):
        cls.source = load_source()

    def test_has_white_king_glyph(self):
        """Must have white king glyph ♔."""
        self.assertIn("♔", self.source)

    def test_has_white_queen_glyph(self):
        """Must have white queen glyph ♕."""
        self.assertIn("♕", self.source)

    def test_has_black_king_glyph(self):
        """Must have black king glyph ♚."""
        self.assertIn("♚", self.source)

    def test_has_black_queen_glyph(self):
        """Must have black queen glyph ♛."""
        self.assertIn("♛", self.source)

    def test_has_all_white_piece_glyphs(self):
        """Must have all six white piece glyphs (♔♕♖♗♘♙)."""
        for glyph in "♔♕♖♗♘♙":
            self.assertIn(glyph, self.source, f"Missing white glyph {glyph}")

    def test_has_all_black_piece_glyphs(self):
        """Must have all six black piece glyphs (♚♛♜♝♞♟)."""
        for glyph in "♚♛♜♝♞♟":
            self.assertIn(glyph, self.source, f"Missing black glyph {glyph}")


class TestLastMoveDisplay(unittest.TestCase):
    """Last move highlighting and move history display."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def _new_game(self):
        return self.ns["ChessGame"]()

    def test_last_move_tracked(self):
        """last_move should be updated after a move."""
        game = self._new_game()
        game.make_move(6, 4, 4, 4)  # e2e4
        self.assertEqual(game.last_move, ((6, 4), (4, 4)))

    def test_move_history_recorded(self):
        """move_history should grow after each move."""
        game = self._new_game()
        game.make_move(6, 4, 4, 4)  # e2e4
        self.assertEqual(len(game.move_history), 1)

    def test_highlight_escape_code_exists(self):
        """HIGHLIGHT escape code for last-move squares must be defined."""
        self.assertIn("HIGHLIGHT", self.ns)

    def test_display_function_exists(self):
        """ChessGame must have a display() method."""
        game = self._new_game()
        self.assertTrue(hasattr(game, "display"))


class TestGameStatus(unittest.TestCase):
    """Game status and draw conditions."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def _new_game(self):
        return self.ns["ChessGame"]()

    def test_status_playing_at_start(self):
        """Game status should be 'playing' at start."""
        game = self._new_game()
        self.assertEqual(game.game_status(), "playing")

    def test_stalemate_detection(self):
        """Stalemate should be detected when no legal moves and not in check."""
        game = self._new_game()
        game.board = [[None] * 8 for _ in range(8)]
        game.board[0][0] = "k"  # Black king in corner
        game.board[2][1] = "Q"  # White queen traps king
        game.board[7][7] = "K"  # White king far away
        game.turn = "black"
        self.assertEqual(game.game_status(), "stalemate")

    def test_insufficient_material_k_vs_k(self):
        """K vs K should be insufficient material."""
        game = self._new_game()
        game.board = [[None] * 8 for _ in range(8)]
        game.board[0][0] = "k"
        game.board[7][7] = "K"
        self.assertTrue(game.insufficient_material())


class TestUndoAndCapture(unittest.TestCase):
    """Undo functionality and captured piece tracking."""

    @classmethod
    def setUpClass(cls):
        cls.ns = import_module()

    def _new_game(self):
        return self.ns["ChessGame"]()

    def test_undo_restores_board(self):
        """Undo should restore the board to the previous state."""
        game = self._new_game()
        board_before = [row[:] for row in game.board]
        game.make_move(6, 4, 4, 4)  # e2e4
        game.restore_state(game.undo_stack.pop())
        self.assertEqual(game.board, board_before)

    def test_captured_pieces_tracked(self):
        """Captured pieces should be recorded."""
        game = self._new_game()
        # Set up a capture scenario
        game.board = [[None] * 8 for _ in range(8)]
        game.board[7][4] = "K"
        game.board[0][4] = "k"
        game.board[4][4] = "P"  # White pawn
        game.board[3][3] = "p"  # Black pawn to capture
        game.turn = "white"
        game.make_move(4, 4, 3, 3)  # Pxd5
        self.assertIn("p", game.captured["white"])


# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    unittest.main()
