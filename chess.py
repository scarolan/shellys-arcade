#!/usr/bin/env python3
"""Terminal-based Chess game with Unicode pieces and ANSI colored squares."""

import sys

# Unicode chess pieces
PIECES = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
}

# ANSI escape codes
LIGHT_SQ = '\033[48;5;180m'  # warm tan (darker, good contrast with white pieces)
DARK_SQ = '\033[48;5;95m'    # dark brown
RESET = '\033[0m'
WHITE_FG = '\033[97m'        # bright white for white pieces
BLACK_FG = '\033[38;5;16m'   # black for black pieces
BOLD = '\033[1m'
HIGHLIGHT = '\033[48;5;107m' # green highlight for last move
CHECK_HI = '\033[48;5;196m'  # red highlight for king in check

COLS = 'abcdefgh'


def initial_board():
    """Return an 8x8 board with pieces in standard starting position.
    board[row][col] where row 0 = rank 8 (top), row 7 = rank 1 (bottom).
    White pieces are uppercase, black pieces are lowercase, empty is None.
    """
    board = [[None] * 8 for _ in range(8)]
    # Black pieces (row 0 = rank 8, row 1 = rank 7)
    board[0] = list('rnbqkbnr')
    board[1] = list('pppppppp')
    # White pieces (row 6 = rank 2, row 7 = rank 1)
    board[6] = list('PPPPPPPP')
    board[7] = list('RNBQKBNR')
    return board


class ChessGame:
    def __init__(self):
        self.board = initial_board()
        self.turn = 'white'  # 'white' or 'black'
        self.move_history = []
        self.last_move = None  # ((from_r, from_c), (to_r, to_c))
        # Castling rights
        self.castle = {'K': True, 'Q': True, 'k': True, 'q': True}
        # En passant target square (row, col) or None
        self.en_passant = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        # Captured pieces tracking
        self.captured = {'white': [], 'black': []}  # pieces captured BY each side
        # Undo stack: save full state before each move
        self.undo_stack = []
        # AI mode
        self.ai_mode = False

    def piece_at(self, r, c):
        return self.board[r][c]

    def is_white(self, piece):
        return piece is not None and piece.isupper()

    def is_black(self, piece):
        return piece is not None and piece.islower()

    def is_own(self, piece):
        if self.turn == 'white':
            return self.is_white(piece)
        return self.is_black(piece)

    def is_enemy(self, piece):
        if piece is None:
            return False
        if self.turn == 'white':
            return self.is_black(piece)
        return self.is_white(piece)

    def find_king(self, color=None):
        """Find position of the king for the given color (or current turn)."""
        if color is None:
            color = self.turn
        target = 'K' if color == 'white' else 'k'
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == target:
                    return (r, c)
        return None

    def is_square_attacked(self, r, c, by_color):
        """Check if square (r,c) is attacked by any piece of by_color."""
        for sr in range(8):
            for sc in range(8):
                piece = self.board[sr][sc]
                if piece is None:
                    continue
                if by_color == 'white' and not piece.isupper():
                    continue
                if by_color == 'black' and not piece.islower():
                    continue
                if self._can_attack(sr, sc, r, c, piece):
                    return True
        return False

    def _can_attack(self, sr, sc, tr, tc, piece):
        """Check if piece at (sr,sc) can attack (tr,tc). Does not check for pins."""
        pt = piece.lower()
        dr = tr - sr
        dc = tc - sc

        if pt == 'p':
            direction = -1 if piece.isupper() else 1
            return dr == direction and abs(dc) == 1

        if pt == 'n':
            return (abs(dr), abs(dc)) in [(1, 2), (2, 1)]

        if pt == 'b':
            return self._check_diagonal(sr, sc, tr, tc)

        if pt == 'r':
            return self._check_straight(sr, sc, tr, tc)

        if pt == 'q':
            return self._check_diagonal(sr, sc, tr, tc) or self._check_straight(sr, sc, tr, tc)

        if pt == 'k':
            return abs(dr) <= 1 and abs(dc) <= 1 and (dr != 0 or dc != 0)

        return False

    def _check_straight(self, sr, sc, tr, tc):
        if sr != tr and sc != tc:
            return False
        dr = 0 if tr == sr else (1 if tr > sr else -1)
        dc = 0 if tc == sc else (1 if tc > sc else -1)
        r, c = sr + dr, sc + dc
        while (r, c) != (tr, tc):
            if self.board[r][c] is not None:
                return False
            r += dr
            c += dc
        return True

    def _check_diagonal(self, sr, sc, tr, tc):
        if abs(tr - sr) != abs(tc - sc) or tr == sr:
            return False
        dr = 1 if tr > sr else -1
        dc = 1 if tc > sc else -1
        r, c = sr + dr, sc + dc
        while (r, c) != (tr, tc):
            if self.board[r][c] is not None:
                return False
            r += dr
            c += dc
        return True

    def in_check(self, color=None):
        if color is None:
            color = self.turn
        king_pos = self.find_king(color)
        if king_pos is None:
            return False
        enemy = 'black' if color == 'white' else 'white'
        return self.is_square_attacked(king_pos[0], king_pos[1], enemy)

    def generate_legal_moves(self):
        """Generate all legal moves for the current turn as ((fr,fc),(tr,tc)) tuples."""
        moves = []
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if not self.is_own(piece):
                    continue
                for tr, tc in self._pseudo_moves(r, c, piece):
                    if self._is_legal(r, c, tr, tc):
                        moves.append(((r, c), (tr, tc)))
        return moves

    def _pseudo_moves(self, r, c, piece):
        """Generate pseudo-legal destination squares for a piece."""
        pt = piece.lower()
        targets = []

        if pt == 'p':
            targets = self._pawn_moves(r, c, piece)
        elif pt == 'n':
            for dr, dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
                tr, tc = r+dr, c+dc
                if 0 <= tr < 8 and 0 <= tc < 8 and not self.is_own(self.board[tr][tc]):
                    targets.append((tr, tc))
        elif pt == 'b':
            targets = self._slide(r, c, [(-1,-1),(-1,1),(1,-1),(1,1)])
        elif pt == 'r':
            targets = self._slide(r, c, [(-1,0),(1,0),(0,-1),(0,1)])
        elif pt == 'q':
            targets = self._slide(r, c, [(-1,-1),(-1,1),(1,-1),(1,1),(-1,0),(1,0),(0,-1),(0,1)])
        elif pt == 'k':
            for dr in [-1,0,1]:
                for dc in [-1,0,1]:
                    if dr == 0 and dc == 0:
                        continue
                    tr, tc = r+dr, c+dc
                    if 0 <= tr < 8 and 0 <= tc < 8 and not self.is_own(self.board[tr][tc]):
                        targets.append((tr, tc))
            # Castling
            targets.extend(self._castle_moves(r, c))

        return targets

    def _pawn_moves(self, r, c, piece):
        targets = []
        direction = -1 if piece.isupper() else 1
        start_row = 6 if piece.isupper() else 1

        # Forward one
        tr = r + direction
        if 0 <= tr < 8 and self.board[tr][c] is None:
            targets.append((tr, c))
            # Forward two from starting position
            tr2 = r + 2 * direction
            if r == start_row and self.board[tr2][c] is None:
                targets.append((tr2, c))

        # Captures
        for dc in [-1, 1]:
            tc = c + dc
            tr = r + direction
            if 0 <= tr < 8 and 0 <= tc < 8:
                if self.is_enemy(self.board[tr][tc]):
                    targets.append((tr, tc))
                # En passant
                if self.en_passant == (tr, tc):
                    targets.append((tr, tc))

        return targets

    def _slide(self, r, c, directions):
        targets = []
        for dr, dc in directions:
            tr, tc = r + dr, c + dc
            while 0 <= tr < 8 and 0 <= tc < 8:
                dest = self.board[tr][tc]
                if dest is None:
                    targets.append((tr, tc))
                elif self.is_enemy(dest):
                    targets.append((tr, tc))
                    break
                else:
                    break
                tr += dr
                tc += dc
        return targets

    def _castle_moves(self, r, c):
        targets = []
        if self.turn == 'white' and r == 7 and c == 4:
            enemy = 'black'
            if self.castle['K'] and self.board[7][5] is None and self.board[7][6] is None:
                if not self.is_square_attacked(7, 4, enemy) and \
                   not self.is_square_attacked(7, 5, enemy) and \
                   not self.is_square_attacked(7, 6, enemy):
                    targets.append((7, 6))
            if self.castle['Q'] and self.board[7][3] is None and self.board[7][2] is None and self.board[7][1] is None:
                if not self.is_square_attacked(7, 4, enemy) and \
                   not self.is_square_attacked(7, 3, enemy) and \
                   not self.is_square_attacked(7, 2, enemy):
                    targets.append((7, 2))
        elif self.turn == 'black' and r == 0 and c == 4:
            enemy = 'white'
            if self.castle['k'] and self.board[0][5] is None and self.board[0][6] is None:
                if not self.is_square_attacked(0, 4, enemy) and \
                   not self.is_square_attacked(0, 5, enemy) and \
                   not self.is_square_attacked(0, 6, enemy):
                    targets.append((0, 6))
            if self.castle['q'] and self.board[0][3] is None and self.board[0][2] is None and self.board[0][1] is None:
                if not self.is_square_attacked(0, 4, enemy) and \
                   not self.is_square_attacked(0, 3, enemy) and \
                   not self.is_square_attacked(0, 2, enemy):
                    targets.append((0, 2))
        return targets

    def _is_legal(self, fr, fc, tr, tc):
        """Check if a move is legal (doesn't leave own king in check)."""
        # Save state
        captured = self.board[tr][tc]
        piece = self.board[fr][fc]
        ep_captured = None

        # Handle en passant capture
        if piece.lower() == 'p' and (tr, tc) == self.en_passant:
            ep_row = fr  # the captured pawn is on the same row as the moving pawn
            ep_captured = self.board[ep_row][tc]
            self.board[ep_row][tc] = None

        self.board[tr][tc] = piece
        self.board[fr][fc] = None

        # Handle castling - move the rook too for check detection
        rook_move = None
        if piece.lower() == 'k' and abs(fc - tc) == 2:
            if tc == 6:  # kingside
                rook_move = (fr, 7, fr, 5)
                self.board[fr][5] = self.board[fr][7]
                self.board[fr][7] = None
            elif tc == 2:  # queenside
                rook_move = (fr, 0, fr, 3)
                self.board[fr][3] = self.board[fr][0]
                self.board[fr][0] = None

        legal = not self.in_check(self.turn)

        # Restore state
        self.board[fr][fc] = piece
        self.board[tr][tc] = captured
        if ep_captured is not None:
            self.board[ep_row][tc] = ep_captured
        if rook_move:
            rr_from, rc_from, rr_to, rc_to = rook_move
            self.board[rr_from][rc_from] = self.board[rr_to][rc_to]
            self.board[rr_to][rc_to] = None

        return legal

    def save_state(self):
        """Save full game state for undo."""
        return {
            'board': [row[:] for row in self.board],
            'turn': self.turn,
            'castle': dict(self.castle),
            'en_passant': self.en_passant,
            'halfmove_clock': self.halfmove_clock,
            'fullmove_number': self.fullmove_number,
            'last_move': self.last_move,
            'move_history': list(self.move_history),
            'captured': {'white': list(self.captured['white']),
                         'black': list(self.captured['black'])},
        }

    def restore_state(self, state):
        """Restore game state from a saved snapshot."""
        self.board = [row[:] for row in state['board']]
        self.turn = state['turn']
        self.castle = dict(state['castle'])
        self.en_passant = state['en_passant']
        self.halfmove_clock = state['halfmove_clock']
        self.fullmove_number = state['fullmove_number']
        self.last_move = state['last_move']
        self.move_history = list(state['move_history'])
        self.captured = {'white': list(state['captured']['white']),
                         'black': list(state['captured']['black'])}

    def make_move(self, fr, fc, tr, tc, promotion=None):
        """Execute a move. Returns a description string."""
        # Save state for undo
        self.undo_stack.append(self.save_state())

        piece = self.board[fr][fc]
        captured = self.board[tr][tc]
        desc_parts = []

        # En passant capture
        ep_capture = False
        if piece.lower() == 'p' and (tr, tc) == self.en_passant:
            ep_capture = True
            ep_row = fr
            captured = self.board[ep_row][tc]
            self.board[ep_row][tc] = None
            desc_parts.append(f"{COLS[fc]}x{COLS[tc]}{8-tr} e.p.")

        # Castling
        castled = False
        if piece.lower() == 'k' and abs(fc - tc) == 2:
            castled = True
            if tc == 6:  # kingside
                self.board[fr][5] = self.board[fr][7]
                self.board[fr][7] = None
                desc_parts.append("O-O")
            else:  # queenside
                self.board[fr][3] = self.board[fr][0]
                self.board[fr][0] = None
                desc_parts.append("O-O-O")

        # Update en passant target
        self.en_passant = None
        if piece.lower() == 'p' and abs(fr - tr) == 2:
            self.en_passant = ((fr + tr) // 2, fc)

        # Move the piece
        self.board[tr][tc] = piece
        self.board[fr][fc] = None

        # Pawn promotion
        if piece.lower() == 'p' and tr in (0, 7):
            if promotion is None:
                promotion = 'q'
            promo_piece = promotion.upper() if piece.isupper() else promotion.lower()
            self.board[tr][tc] = promo_piece
            if not desc_parts:
                desc_parts.append(f"{COLS[fc]}{8-tr}={promotion.upper()}")

        # Build description
        if not desc_parts:
            piece_name = piece.upper()
            if piece_name == 'P':
                if captured:
                    desc_parts.append(f"{COLS[fc]}x{COLS[tc]}{8-tr}")
                else:
                    desc_parts.append(f"{COLS[tc]}{8-tr}")
            else:
                cap = 'x' if captured else ''
                desc_parts.append(f"{piece_name}{COLS[fc]}{8-fr}{cap}{COLS[tc]}{8-tr}")

        # Update castling rights
        if piece == 'K':
            self.castle['K'] = False
            self.castle['Q'] = False
        elif piece == 'k':
            self.castle['k'] = False
            self.castle['q'] = False
        if piece == 'R':
            if fr == 7 and fc == 7:
                self.castle['K'] = False
            elif fr == 7 and fc == 0:
                self.castle['Q'] = False
        elif piece == 'r':
            if fr == 0 and fc == 7:
                self.castle['k'] = False
            elif fr == 0 and fc == 0:
                self.castle['q'] = False
        # If a rook is captured
        if captured:
            if (tr, tc) == (7, 7):
                self.castle['K'] = False
            elif (tr, tc) == (7, 0):
                self.castle['Q'] = False
            elif (tr, tc) == (0, 7):
                self.castle['k'] = False
            elif (tr, tc) == (0, 0):
                self.castle['q'] = False

        # Track captured pieces
        if captured:
            capturing_side = 'white' if piece.isupper() else 'black'
            self.captured[capturing_side].append(captured)

        # Update clocks
        if piece.lower() == 'p' or captured:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        self.last_move = ((fr, fc), (tr, tc))
        self.move_history.append(desc_parts[0])

        # Switch turn
        if self.turn == 'black':
            self.fullmove_number += 1
        self.turn = 'black' if self.turn == 'white' else 'white'

        # Check/checkmate annotation
        if self.in_check():
            if not self.generate_legal_moves():
                self.move_history[-1] += '#'
            else:
                self.move_history[-1] += '+'

        return self.move_history[-1]

    def insufficient_material(self):
        """Check if neither side has enough material to checkmate."""
        pieces = {'white': [], 'black': []}
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p is None:
                    continue
                color = 'white' if p.isupper() else 'black'
                pieces[color].append((p.lower(), r, c))

        white = pieces['white']
        black = pieces['black']

        # Strip kings for comparison
        w_non_king = [(p, r, c) for p, r, c in white if p != 'k']
        b_non_king = [(p, r, c) for p, r, c in black if p != 'k']

        w_count = len(w_non_king)
        b_count = len(b_non_king)

        # K vs K
        if w_count == 0 and b_count == 0:
            return True
        # K vs K+B or K vs K+N
        if w_count == 0 and b_count == 1 and b_non_king[0][0] in ('b', 'n'):
            return True
        if b_count == 0 and w_count == 1 and w_non_king[0][0] in ('b', 'n'):
            return True
        # K+B vs K+B with bishops on same color
        if w_count == 1 and b_count == 1:
            wp, wr, wc = w_non_king[0]
            bp, br, bc = b_non_king[0]
            if wp == 'b' and bp == 'b':
                if (wr + wc) % 2 == (br + bc) % 2:
                    return True

        return False

    def game_status(self):
        """Return game status: 'playing', 'checkmate', 'stalemate', or 'draw'."""
        legal = self.generate_legal_moves()
        if not legal:
            if self.in_check():
                return 'checkmate'
            return 'stalemate'
        if self.halfmove_clock >= 100:
            return 'draw'  # 50-move rule
        if self.insufficient_material():
            return 'draw'  # insufficient material
        return 'playing'

    # --- AI Engine (Step 6) ---

    PIECE_VALUES = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 0}
    CENTER_SQUARES = {(3, 3), (3, 4), (4, 3), (4, 4)}  # d4,d5,e4,e5

    def evaluate(self):
        """Evaluate board position. Positive = white advantage."""
        score = 0.0
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece is None:
                    continue
                val = self.PIECE_VALUES[piece.lower()]
                # Center control bonus
                if (r, c) in self.CENTER_SQUARES:
                    val += 0.1
                if piece.isupper():
                    score += val
                else:
                    score -= val
        return score

    def ai_move(self, depth=3):
        """Find the best move for the current side using minimax with alpha-beta."""
        legal = self.generate_legal_moves()
        if not legal:
            return None

        best_move = None
        is_maximizing = (self.turn == 'white')
        best_score = float('-inf') if is_maximizing else float('inf')
        saved_undo = list(self.undo_stack)

        for (fr, fc), (tr, tc) in legal:
            piece = self.board[fr][fc]
            promo = 'q' if piece.lower() == 'p' and tr in (0, 7) else None

            state = self.save_state()
            self.make_move(fr, fc, tr, tc, promo)
            score = self._minimax(depth - 1, float('-inf'), float('inf'), not is_maximizing)
            self.restore_state(state)
            self.undo_stack = list(saved_undo)

            if is_maximizing:
                if score > best_score:
                    best_score = score
                    best_move = ((fr, fc), (tr, tc), promo)
            else:
                if score < best_score:
                    best_score = score
                    best_move = ((fr, fc), (tr, tc), promo)

        self.undo_stack = saved_undo
        return best_move

    def _minimax(self, depth, alpha, beta, is_maximizing):
        """Minimax with alpha-beta pruning."""
        if depth == 0:
            return self.evaluate()

        legal = self.generate_legal_moves()
        if not legal:
            if self.in_check():
                return float('-inf') if is_maximizing else float('inf')
            return 0.0  # stalemate

        if is_maximizing:
            max_eval = float('-inf')
            for (fr, fc), (tr, tc) in legal:
                piece = self.board[fr][fc]
                promo = 'q' if piece.lower() == 'p' and tr in (0, 7) else None
                state = self.save_state()
                saved = list(self.undo_stack)
                self.make_move(fr, fc, tr, tc, promo)
                eval_score = self._minimax(depth - 1, alpha, beta, False)
                self.restore_state(state)
                self.undo_stack = saved
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for (fr, fc), (tr, tc) in legal:
                piece = self.board[fr][fc]
                promo = 'q' if piece.lower() == 'p' and tr in (0, 7) else None
                state = self.save_state()
                saved = list(self.undo_stack)
                self.make_move(fr, fc, tr, tc, promo)
                eval_score = self._minimax(depth - 1, alpha, beta, True)
                self.restore_state(state)
                self.undo_stack = saved
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            return min_eval

    def parse_move(self, text):
        """Parse user input like 'e2e4', 'e2 e4', 'e7e8q' (promotion).
        Returns (fr, fc, tr, tc, promotion) or None on failure.
        """
        text = text.strip().lower().replace(' ', '').replace('-', '')

        if len(text) < 4 or len(text) > 5:
            return None

        fc_ch, fr_ch, tc_ch, tr_ch = text[0], text[1], text[2], text[3]
        promotion = text[4] if len(text) == 5 else None

        if fc_ch not in COLS or tc_ch not in COLS:
            return None
        if fr_ch not in '12345678' or tr_ch not in '12345678':
            return None

        fc = COLS.index(fc_ch)
        fr = 8 - int(fr_ch)
        tc = COLS.index(tc_ch)
        tr = 8 - int(tr_ch)

        if promotion and promotion not in 'qrbn':
            return None

        return (fr, fc, tr, tc, promotion)

    def display(self):
        """Print the board with ANSI colors."""
        in_check_white = self.in_check('white')
        in_check_black = self.in_check('black')
        wk = self.find_king('white')
        bk = self.find_king('black')

        # Move history header
        print()
        if self.move_history:
            moves_str = ''
            for i, m in enumerate(self.move_history):
                if i % 2 == 0:
                    moves_str += f" {i//2+1}. {m}"
                else:
                    moves_str += f" {m}"
            print(f"  Moves:{moves_str}")
            print()

        print('    a  b  c  d  e  f  g  h')
        print('  +------------------------+')

        for r in range(8):
            rank = 8 - r
            row_str = f'{rank} |'
            for c in range(8):
                # Determine square background color
                is_light = (r + c) % 2 == 0

                # Highlight last move squares
                if self.last_move and (r, c) in self.last_move:
                    bg = HIGHLIGHT
                # Highlight king in check
                elif in_check_white and (r, c) == wk:
                    bg = CHECK_HI
                elif in_check_black and (r, c) == bk:
                    bg = CHECK_HI
                else:
                    bg = LIGHT_SQ if is_light else DARK_SQ

                piece = self.board[r][c]
                if piece is None:
                    row_str += f'{bg}   {RESET}'
                else:
                    fg = WHITE_FG if piece.isupper() else BLACK_FG
                    symbol = PIECES[piece]
                    row_str += f'{bg}{fg}{BOLD} {symbol} {RESET}'

            row_str += f'| {rank}'
            print(row_str)

        print('  +------------------------+')
        print('    a  b  c  d  e  f  g  h')

        # Display captured pieces
        w_captured = self.captured.get('white', [])
        b_captured = self.captured.get('black', [])
        if w_captured:
            symbols = ' '.join(PIECES.get(p, p) for p in sorted(w_captured, key=lambda x: 'qrbnp'.index(x.lower())))
            print(f'  White captured: {symbols}')
        if b_captured:
            symbols = ' '.join(PIECES.get(p, p) for p in sorted(b_captured, key=lambda x: 'qrbnp'.index(x.lower())))
            print(f'  Black captured: {symbols}')
        print()


def main():
    game = ChessGame()
    print()
    print('  ==============================')
    print('  Terminal Chess  (pure Python)')
    print('  ==============================')
    print('  Commands: e2e4, moves, undo, ai, quit')
    print()
    game.display()

    while True:
        status = game.game_status()
        if status == 'checkmate':
            winner = 'Black' if game.turn == 'white' else 'White'
            print(f'  Checkmate! {winner} wins!')
            break
        elif status == 'stalemate':
            print('  Stalemate! The game is a draw.')
            break
        elif status == 'draw':
            if game.insufficient_material():
                print('  Draw by insufficient material.')
            else:
                print('  Draw by 50-move rule.')
            break

        turn_label = 'White' if game.turn == 'white' else 'Black'
        if game.in_check():
            print(f'  {turn_label} is in CHECK!')

        # AI plays black automatically
        if game.ai_mode and game.turn == 'black':
            print('  AI is thinking...')
            result = game.ai_move(depth=3)
            if result is None:
                print('  AI has no moves.')
                break
            (fr, fc), (tr, tc), promo = result
            desc = game.make_move(fr, fc, tr, tc, promo)
            move_str = f"{COLS[fc]}{8-fr}{COLS[tc]}{8-tr}"
            print(f'  AI plays: {move_str} -> {desc}')
            game.display()
            continue

        try:
            move_input = input(f'  {turn_label} to move (e.g. e2e4): ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\n  Game ended.')
            break

        cmd = move_input.lower()

        if cmd in ('quit', 'exit', 'q'):
            print('  Thanks for playing!')
            break

        if cmd == 'ai':
            game.ai_mode = not game.ai_mode
            state_str = 'ON' if game.ai_mode else 'OFF'
            print(f'  AI mode: {state_str} (AI plays black)')
            continue

        if cmd == 'undo':
            if not game.undo_stack:
                print('  Nothing to undo.')
                continue
            game.restore_state(game.undo_stack.pop())
            print('  Last move undone.')
            game.display()
            continue

        if cmd == 'moves':
            legal = game.generate_legal_moves()
            move_strs = []
            for (fr, fc), (tr, tc) in legal:
                move_strs.append(f"{COLS[fc]}{8-fr}{COLS[tc]}{8-tr}")
            print(f'  Legal moves: {", ".join(sorted(move_strs))}')
            continue

        parsed = game.parse_move(move_input)
        if parsed is None:
            print('  Invalid format. Use e.g. "e2e4" or "e7e8q" for promotion.')
            continue

        fr, fc, tr, tc, promotion = parsed
        piece = game.piece_at(fr, fc)

        if piece is None or not game.is_own(piece):
            print('  No friendly piece on that square.')
            continue

        # Check if this is a legal move
        legal_moves = game.generate_legal_moves()
        if ((fr, fc), (tr, tc)) not in legal_moves:
            print('  Illegal move.')
            continue

        # Handle promotion prompt
        if piece.lower() == 'p' and tr in (0, 7) and promotion is None:
            try:
                promo = input('  Promote to (q/r/b/n) [q]: ').strip().lower()
            except (EOFError, KeyboardInterrupt):
                print('\n  Game ended.')
                break
            if promo == '':
                promo = 'q'
            if promo not in 'qrbn':
                print('  Invalid promotion piece.')
                continue
            promotion = promo

        desc = game.make_move(fr, fc, tr, tc, promotion)
        print(f'  -> {desc}')
        game.display()


if __name__ == '__main__':
    main()
