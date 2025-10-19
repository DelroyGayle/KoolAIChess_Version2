import copy  # TODO RE copy/deepcopy

import numpy as np

from typing import Optional

from wake_constants import (
    Rival,
    Piece,
    Square,
    CastleRoute,
    Rank,
    PLAYER_PROMOTION_MAP,
    COMPUTER_PROMOTION_MAP,
    KINGSIDE,
    QUEENSIDE,
    THE_ATTACK,
    THE_PIECE
)

from wake_core import (
    set_bit,
    bitscan_forward,
    bitscan_reverse,
    make_uint64_zero,
    get_squares_from_bitboard,
    switch_rival
)

from wake_rays import (
    get_north_ray,
    get_south_ray,
    get_east_ray,
    get_west_ray,
    get_northeast_ray,
    get_northwest_ray,
    get_southeast_ray,
    get_southwest_ray,
)

from wake_attacks import generate_king_attack_bb_from_square
from wake_board import WakeBoard
from wake_fen import generate_fen
from wake_move import Move, MoveResult

ROOK_RIVAL_MAP = {Rival.PLAYER: Piece.wR, Rival.COMPUTER: Piece.bR}


class PositionState:
    """
    Memento for Position
    """

    def __init__(self, **kwargs):
        # TODO
        pass


class Position:
    """
    Represents the internal state of a chess position
    # TODO: position_state NEVER USED!
    """

    def __init__(self, board=None, position_state=None):
        if board is None:
            self.board = WakeBoard()
        else:
            self.board = board

        self.piece_map = {}
        self.mailbox = [None] * 64  # Mailbox array for O(1) piece lookup

        self.rival_to_move = Rival.PLAYER

        # [kingside, queenside] castle rights
        self.castle_rights = {Rival.PLAYER: [True, True],
                              Rival.COMPUTER: [True, True]}

        self.halfmove_clock = 0
        self.halfmove = 2
        self.en_passant_target = None
        self.en_passant_side = Rival.PLAYER
        self.is_en_passant_capture = False

        # [player/white, computer/black] boolean king is in check
        self.king_in_check = [False, False]

        # Position history for 3-fold repetition detection
        self.position_history = []  # TODO Move to game.py

        self.set_initial_piece_locations()

        # Initialise mailbox after setting piece locations
        self.sync_mailbox_from_piece_map()

        self.player_pawn_moves = make_uint64_zero()
        self.player_pawn_attacks = make_uint64_zero()
        self.player_rook_attacks = make_uint64_zero()
        self.player_knight_attacks = make_uint64_zero()
        self.player_bishop_attacks = make_uint64_zero()
        self.player_queen_attacks = make_uint64_zero()
        self.player_king_attacks = make_uint64_zero()

        self.computer_pawn_moves = make_uint64_zero()
        self.computer_pawn_attacks = make_uint64_zero()
        self.computer_rook_attacks = make_uint64_zero()
        self.computer_knight_attacks = make_uint64_zero()
        self.computer_bishop_attacks = make_uint64_zero()
        self.computer_queen_attacks = make_uint64_zero()
        self.computer_king_attacks = make_uint64_zero()

    def set_initial_piece_locations(self):
        # init all piece types with empty sets first
        for piece_type in (
            Piece.wP,
            Piece.wR,
            Piece.wN,
            Piece.wB,
            Piece.wQ,
            Piece.wK,
            Piece.bP,
            Piece.bR,
            Piece.bN,
            Piece.bB,
            Piece.bQ,
            Piece.bK,
        ):
            self.piece_map[piece_type] = set()

        # Set initial piece positions
        self.piece_map[Piece.wP] = set([i for i in range(8, 16)])
        self.piece_map[Piece.wR] = {0, 7}
        self.piece_map[Piece.wN] = {1, 6}
        self.piece_map[Piece.wB] = {2, 5}
        self.piece_map[Piece.wQ] = {3}
        self.piece_map[Piece.wK] = {4}

        self.piece_map[Piece.bP] = set([i for i in range(48, 56)])
        self.piece_map[Piece.bR] = {56, 63}
        self.piece_map[Piece.bN] = {57, 62}
        self.piece_map[Piece.bB] = {58, 61}
        self.piece_map[Piece.bQ] = {59}
        self.piece_map[Piece.bK] = {60}

    def sync_mailbox_from_piece_map(self):
        """
        Synchronizes the mailbox array with the current piece_map state.
        This provides O(1) piece lookup by square index.
        """
        self.mailbox = [None] * 64
        for piece, squares in self.piece_map.items():
            for square in squares:
                self.mailbox[square] = piece

    # TODO remove!
    def reset_state_to(self, memento: PositionState) -> None:
        for k, v in memento.__dict__.items():
            setattr(self, k, v)

    @property
    def occupied_squares_by_rival(self):
        return {
            Rival.COMPUTER: self.board.computer_pieces_bb,
            Rival.PLAYER: self.board.player_pieces_bb,
        }

    @property
    def computer_attacked_squares(self):
        return (
            self.computer_rook_attacks
            | self.computer_bishop_attacks
            | self.computer_knight_attacks
            | self.computer_pawn_attacks
            | self.computer_queen_attacks
            | self.computer_king_attacks
        )

    @property
    def player_attacked_squares(self):
        return (
            self.player_rook_attacks
            | self.player_bishop_attacks
            | self.player_knight_attacks
            | self.player_pawn_attacks
            | self.player_queen_attacks
            | self.player_king_attacks
        )

    # -------------------------------------------------------------
    # MAKE MOVE
    # -------------------------------------------------------------

    # TODO
    def make_move(self, move) -> MoveResult:
        if self.rival_to_move != move.rival:  # TODO
            return self.make_illegal_move_result("Not your move!")

        original_position = PositionState(copy.deepcopy(self.__dict__))

        if not self.is_legal_move(move):
            return self.make_illegal_move_result("Illegal move")

        if move.is_capture:
            self.halfmove_clock = 0
            self.remove_opponent_piece_from_square(move.to_sq)

        if self.is_en_passant_capture:
            if move.rival == Rival.PLAYER:
                self.remove_opponent_piece_from_square(move.to_sq - 8)
            if move.rival == Rival.COMPUTER:
                self.remove_opponent_piece_from_square(move.to_sq + 8)

        self.is_en_passant_capture = False

        if move.piece in {Piece.wP, Piece.bP}:
            self.halfmove_clock = 0

        # update both piece_map and mailbox
        self.piece_map[move.piece].remove(move.from_sq)
        self.piece_map[move.piece].add(move.to_sq)
        self.mailbox[move.from_sq] = None
        self.mailbox[move.to_sq] = move.piece

        if move.is_promotion:
            self.promote_pawn(move)

        if move.is_castling:
            self.move_rooks_for_castling(move)

        self.halfmove_clock += 1
        self.halfmove += 1

        castle_rights = self.castle_rights[move.rival]

        if any(castle_rights):
            self.adjust_castling_rights(move)

        if self.en_passant_side != move.rival:
            self.en_passant_target = None

        self.board.update_position_bitboards(self.piece_map)
        self.update_attack_bitboards()

        self.evaluate_king_check()

        if self.king_in_check[move.rival]:
            self.reset_state_to(original_position)
            return self.make_illegal_move_result("own king in check")

        other_player = (Rival.COMPUTER if move.rival == Rival.PLAYER
                        else Rival.PLAYER)

        if (self.king_in_check[other_player]
           and not self.any_legal_moves(other_player)):
            print("Checkmate")  # TODO
            return self.make_checkmate_result()

        if (not self.king_in_check[other_player]
           and not self.any_legal_moves(other_player)):
            print("Stalemate")  # TODO
            return self.make_stalemate_result()

        # 50-move rule draw (50 moves by each player = 100 half-moves)
        if self.halfmove_clock >= 100:
            print("Draw by 50-move rule")
            return self.make_draw_result()

        if self.is_threefold_repetition():
            print("Draw by 3-fold repetition")
            return self.make_draw_result()

        if self.is_insufficient_material():
            print("Draw by insufficient material")
            return self.make_draw_result()

        self.position_history.append(generate_fen(self))  # TODO
        self.rival_to_move = switch_rival(self.rival_to_move)

        return self.make_move_result()

    def promote_pawn(self, move):
        while True:
            promotion_piece = input("Choose promotion piece.")
            promotion_piece = promotion_piece.lower()
            # TODO
            # legal_piece = user_promotion_input.get(promotion_piece)
            legal_piece = ""
            # ## TODO ABOVE ##
            if not legal_piece:
                print("Please choose a legal piece")  # TODO
                continue

            # Update both piece_map and mailbox
            self.piece_map[move.piece].remove(move.to_sq)
            new_piece = self.get_promotion_piece_type(legal_piece, move)
            self.piece_map[new_piece].add(move.to_sq)
            self.mailbox[move.to_sq] = new_piece
            break

    def any_legal_moves(self, rival_to_move):
        """
        Returns True if there are any legal moves
        """

        if self.has_king_move(rival_to_move):
            return True
        if self.has_rook_move(rival_to_move):
            return True
        if self.has_queen_move(rival_to_move):
            return True
        if self.has_knight_move(rival_to_move):
            return True
        if self.has_bishop_move(rival_to_move):
            return True
        if self.has_pawn_move(rival_to_move):
            return True
        return False

    def has_king_move(self, rival_to_move):
        """
        Returns True if there is a legal king move
        for the given colour/rival from the given square
        in the current Position instance
        """
        king_rival_map = {
            Rival.PLAYER: (self.player_king_attacks, Piece.wK),
            Rival.COMPUTER: (self.computer_king_attacks, Piece.bK),
        }

        attacked_squares = {
            Rival.PLAYER: self.player_attacked_squares,
            Rival.COMPUTER: self.computer_attacked_squares,
        }

        not_rival_to_move = switch_rival(rival_to_move)
        king_attacks = (
            king_rival_map[rival_to_move][THE_ATTACK] &
            ~attacked_squares[not_rival_to_move]
        )
        king_piece = king_rival_map[rival_to_move][THE_PIECE]

        # if no attacks, return False
        if not king_attacks.any():
            return False

        king_piece_map_copy = self.piece_map[king_piece].copy()
        king_from_square = king_piece_map_copy.pop()

        king_squares = get_squares_from_bitboard(king_attacks)

        for to_square in king_squares:
            move = Move(king_piece, (king_from_square, to_square))
            move = evaluate_move(move, copy.deepcopy(self))
            if not move.is_illegal_move:
                return True

        return False

    def has_rook_move(self, rival_to_move):
        rook_rival_map = {
            Rival.PLAYER: (self.player_rook_attacks, Piece.wR),
            Rival.COMPUTER: (self.computer_rook_attacks, Piece.bR),
        }

        rook_attacks = rook_rival_map[rival_to_move][THE_ATTACK]
        rook_piece = rook_rival_map[rival_to_move][THE_PIECE]

        # if no attacks, return False
        if not rook_attacks.any():
            return False

        current_rook_locations = self.piece_map[rook_piece]
        rook_attack_squares = get_squares_from_bitboard(rook_attacks)

        for rook_from_square in list(current_rook_locations):
            for to_square in rook_attack_squares:
                move = Move(rook_piece, (rook_from_square, to_square))
                move = evaluate_move(move, copy.deepcopy(self))
                if not move.is_illegal_move:
                    return True
        return False

    def has_queen_move(self, rival_to_move):
        queen_rival_map = {
            Rival.PLAYER: (self.player_queen_attacks, Piece.wQ),
            Rival.COMPUTER: (self.computer_queen_attacks, Piece.bQ),
        }

        queen_attacks = queen_rival_map[rival_to_move][THE_ATTACK]
        queen_piece = queen_rival_map[rival_to_move][THE_PIECE]

        # if no attacks, return False
        if not queen_attacks.any():
            return False

        current_queen_locations = self.piece_map[queen_piece]
        queen_squares = get_squares_from_bitboard(queen_attacks)

        for queen_from_square in list(current_queen_locations):
            for to_square in queen_squares:
                move = Move(queen_piece, (queen_from_square, to_square))
                move = evaluate_move(move, copy.deepcopy(self))
                if not move.is_illegal_move:
                    return True
        return False

    def has_knight_move(self, rival_to_move):
        knight_rival_map = {
            Rival.PLAYER: (self.player_knight_attacks, Piece.wN),
            Rival.COMPUTER: (self.computer_knight_attacks, Piece.bN),
        }

        knight_attacks = knight_rival_map[rival_to_move][THE_ATTACK]
        knight_piece = knight_rival_map[rival_to_move][THE_PIECE]

        # if no attacks, return False
        if not knight_attacks.any():
            return False

        current_knight_locations = list(self.piece_map[knight_piece])
        knight_squares = get_squares_from_bitboard(knight_attacks)

        for knight_from_square in current_knight_locations:
            for to_square in knight_squares:
                move = Move(knight_piece, (knight_from_square, to_square))
                move = evaluate_move(move, copy.deepcopy(self))
                if not move.is_illegal_move:
                    return True
        return False

    def has_bishop_move(self, rival_to_move):
        bishop_rival_map = {
            Rival.PLAYER: (self.player_bishop_attacks, Piece.wB),
            Rival.COMPUTER: (self.computer_bishop_attacks, Piece.bB),
        }

        bishop_attacks = bishop_rival_map[rival_to_move][THE_ATTACK]
        bishop_piece = bishop_rival_map[rival_to_move][THE_PIECE]

        # if no attacks, return False
        if not bishop_attacks.any():
            return False

        current_bishop_locations = list(self.piece_map[bishop_piece])
        bishop_squares = get_squares_from_bitboard(bishop_attacks)

        for bishop_from_square in current_bishop_locations:
            for to_square in bishop_squares:
                move = Move(bishop_piece, (bishop_from_square, to_square))
                move = evaluate_move(move, copy.deepcopy(self))
                if not move.is_illegal_move:
                    return True
        return False

    def has_pawn_move(self, rival_to_move):
        pawn_rival_map = {
            Rival.PLAYER: (self.player_pawn_attacks
                           & self.player_pawn_moves, Piece.wP),
            Rival.COMPUTER: (self.computer_pawn_attacks
                             & self.computer_pawn_moves, Piece.bP),
        }

        all_pawn_moves = pawn_rival_map[rival_to_move][THE_ATTACK]
        pawn_piece = pawn_rival_map[rival_to_move][THE_PIECE]

        # if no attacks, return False
        if not all_pawn_moves.any():
            return False

        current_pawn_locations = self.piece_map[pawn_piece]
        pawn_squares = get_squares_from_bitboard(all_pawn_moves)

        for pawn_from_square in list(current_pawn_locations):
            for to_square in pawn_squares:
                move = Move(pawn_piece, (pawn_from_square, to_square))
                move = evaluate_move(move, copy.deepcopy(self))
                if not move.is_illegal_move:
                    return True
        return False

    def remove_opponent_piece_from_square(self, to_sq):
        target = self.mailbox[to_sq]
        if target is not None:
            self.piece_map[target].remove(to_sq)
            self.mailbox[to_sq] = None

    def update_attack_bitboards(self):
        self.reset_attack_bitboards()
        for piece, squares in self.piece_map.items():

            # PAWNS
            if piece == Piece.wP:
                for square in squares:
                    self.update_legal_pawn_moves(square, Rival.PLAYER)
            if piece == Piece.bP:
                for square in squares:
                    self.update_legal_pawn_moves(square, Rival.COMPUTER)

            # ROOKS
            if piece == Piece.wR:
                for square in squares:
                    self.update_legal_rook_moves(square, Rival.PLAYER)
            if piece == Piece.bR:
                for square in squares:
                    self.update_legal_rook_moves(square, Rival.COMPUTER)

            # KNIGHTS
            if piece == Piece.wN:
                for square in squares:
                    self.update_legal_knight_moves(square, Rival.PLAYER)
            if piece == Piece.bN:
                for square in squares:
                    self.update_legal_knight_moves(square, Rival.COMPUTER)

            # BISHOPS
            if piece == Piece.wB:
                for square in squares:
                    self.update_legal_bishop_moves(square, Rival.PLAYER)
            if piece == Piece.bB:
                for square in squares:
                    self.update_legal_bishop_moves(square, Rival.COMPUTER)

            # QUEENS
            if piece == Piece.wQ:
                for square in squares:
                    self.update_legal_queen_moves(square, Rival.PLAYER)
            if piece == Piece.bQ:
                for square in squares:
                    self.update_legal_queen_moves(square, Rival.COMPUTER)

            # KINGS
            if piece == Piece.wK:
                for square in squares:
                    self.update_legal_king_moves(square, Rival.PLAYER)

            if piece == Piece.bK:
                for square in squares:
                    self.update_legal_king_moves(square, Rival.COMPUTER)

    def adjust_castling_rights(self, move):
        if move.piece in {Piece.wK, Piece.bK, Piece.wR, Piece.bR}:

            # If a KING piece is being moved, then from this point onwards:
            # the KING can no longer be used in a castling move.
            if move.piece == Piece.wK:
                self.castle_rights[Rival.PLAYER] = [False, False]
            if move.piece == Piece.bK:
                self.castle_rights[Rival.COMPUTER] = [False, False]

            # If a ROOK piece is being moved, then from this point onwards:
            # which ever side the rook originated from (either
            # kingside or queenside), the KING can no longer be
            # castled to that side.
            if move.piece == Piece.wR:
                if move.from_sq == Square.H1:
                    self.castle_rights[Rival.PLAYER][KINGSIDE] = False
                if move.from_sq == Square.A1:
                    self.castle_rights[Rival.PLAYER][QUEENSIDE] = False
            if move.piece == Piece.bR:
                if move.from_sq == Square.H8:
                    self.castle_rights[Rival.COMPUTER][KINGSIDE] = False
                if move.from_sq == Square.A8:
                    self.castle_rights[Rival.COMPUTER][QUEENSIDE] = False

    def move_rooks_for_castling(self, move):

        square_map = {
            Square.G1: (Square.H1, Square.F1),
            Square.C1: (Square.A1, Square.D1),
            Square.G8: (Square.H8, Square.F8),
            Square.C8: (Square.A8, Square.D8),
        }

        rook_piece = ROOK_RIVAL_MAP[move.rival]
        from_sq, to_sq = square_map[move.to_sq]

        # Update both piece_map and mailbox
        self.piece_map[rook_piece].remove(from_sq)
        self.piece_map[rook_piece].add(to_sq)
        self.mailbox[from_sq] = None
        self.mailbox[to_sq] = rook_piece

    def reset_attack_bitboards(self):
        self.player_rook_attacks = make_uint64_zero()
        self.computer_rook_attacks = make_uint64_zero()
        self.player_bishop_attacks = make_uint64_zero()
        self.computer_bishop_attacks = make_uint64_zero()
        self.player_knight_attacks = make_uint64_zero()
        self.computer_knight_attacks = make_uint64_zero()
        self.player_queen_attacks = make_uint64_zero()
        self.computer_queen_attacks = make_uint64_zero()
        self.player_king_attacks = make_uint64_zero()
        self.computer_king_attacks = make_uint64_zero()

    # -------------------------------------------------------------
    # MOVE LEGALITY CHECKING
    # -------------------------------------------------------------

    def is_legal_move(self, move: Move) -> bool:
        """
        For a given move, returns True if it is legal given the Position state
        """
        piece = move.piece_type

        if self.is_capture(move):
            move.is_capture = True

        match piece:
            case Piece.wB | Piece.bB:
                return self.is_legal_bishop_move(move)

            case Piece.wR | Piece.bR:
                return self.is_legal_rook_move(move)

            case Piece.wN | Piece.bN:
                return self.is_legal_knight_move(move)

            case Piece.wQ | Piece.bQ:
                return self.is_legal_queen_move(move)

            case Piece.wK | Piece.bK:
                is_legal_king_move = self.is_legal_king_move(move)
                if not is_legal_king_move:
                    return False
                if self.is_castling(move):
                    move.is_castling = True
                return True

            case Piece.wP | Piece.bP:
                is_legal_pawn_move = self.is_legal_pawn_move(move)

                if not is_legal_pawn_move:
                    return False

                if self.is_promotion(move):
                    move.is_promotion = True
                    return True

                potential_en_passant_target = (
                    self.try_get_en_passant_target(move))

                if potential_en_passant_target is not None:
                    self.en_passant_side = move.rival
                    self.en_passant_target = int(potential_en_passant_target)

                if move.to_sq == self.en_passant_target:
                    self.is_en_passant_capture = True

                return True

    # TODO 'move'
    def try_get_en_passant_target(self, move) -> Optional[int | np.uint64]:
        """
        Did a pawn perform an initial move of two squares?
        If True, there is a possibility of a subsequence en passant move.
        Return the target square
        """
        if move.piece not in {Piece.wP, Piece.bP}:
            return None
        if move.rival == Rival.PLAYER:
            if move.to_sq in Rank.RANK_X4 and move.from_sq in Rank.RANK_X2:
                return move.to_sq - 8
        if move.rival == Rival.COMPUTER:
            if move.to_sq in Rank.RANK_X5 and move.from_sq in Rank.RANK_X7:
                return move.to_sq + 8
        return None

    def is_capture(self, move):
        """ Does position 'move.to_sq' intersect with any rival pawns? """

        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_sq)

        if move.rival == Rival.PLAYER:
            intersects = moving_to_square_bb & self.board.computer_pieces_bb
            if intersects.any():
                return True
        if move.rival == Rival.COMPUTER:
            intersects = moving_to_square_bb & self.board.player_pieces_bb
            if intersects.any():
                return True
        return False

    # -------------------------------------------------------------
    # PIECE MOVE LEGALITY BY PIECE
    # -------------------------------------------------------------

    def is_legal_pawn_move(self, move: Move) -> bool:
        """
        Returns True if the given pawn move is legal - i.e.
        - the to square intersects with pawn "motion" (forward) bitboard
        - the to square is an attack and intersects with opponent piece
                        or en passant target bitboard
        """
        current_square_bb = set_bit(make_uint64_zero(), move.from_sq)
        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_sq)
        potential_en_passant_target = make_uint64_zero()

        if self.en_passant_target is not None:
            potential_en_passant_target = set_bit(make_uint64_zero(),
                                                  self.en_passant_target)

        if move.piece_type == Piece.wP:
            if not (self.board.player_P_bb & current_square_bb):
                return False

            if self.is_not_pawn_motion_or_attack(move):
                return False

            # If it's a pawn motion forward, check that it isn't blocked
            if move.from_sq == move.to_sq - 8 and (
                moving_to_square_bb & self.board.occupied_squares_bb
            ):
                return False

            # If it's a pawn attack move, check that it
            # intersects with COMPUTER (black) pieces or en passant target
            if (move.from_sq == move.to_sq - 9 or
               move.from_sq == move.to_sq - 7):
                if (self.player_pawn_attacks & moving_to_square_bb) & ~(
                    self.board.computer_pieces_bb | potential_en_passant_target
                ):
                    return False
            return True

        if move.piece_type == Piece.bP:
            if not (self.board.computer_P_bb & current_square_bb):
                return False
            if self.is_not_pawn_motion_or_attack(move):
                return False

            # If it's a pawn motion forward, check that it isn't blocked
            if move.from_sq == move.to_sq + 8 and (
                moving_to_square_bb & self.board.occupied_squares_bb
            ):
                return False

            # If it's a pawn attack move,
            # check that it intersects with PLAYER (white) pieces
            #                               or en passant target
            if (move.from_sq == move.to_sq + 9
               or move.from_sq == move.to_sq + 7):
                if (self.computer_pawn_attacks & moving_to_square_bb) & ~(
                    self.board.player_pieces_bb | potential_en_passant_target
                ):
                    return False
            return True

    def is_legal_bishop_move(self, move: Move) -> bool:
        """
        Returns True if the given bishop move is legal - i.e.
        - the to move intersects with the bishop attack bitboard
        """
        current_square_bb = set_bit(make_uint64_zero(), move.from_sq)
        if move.piece_type == Piece.wB:
            if not (self.board.player_B_bb & current_square_bb):
                return False
            if self.is_not_bishop_attack(move):
                return False
            return True

        if move.piece_type == Piece.bB:
            if not (self.board.computer_B_bb & current_square_bb):
                return False
            if self.is_not_bishop_attack(move):
                return False
            return True

    def is_legal_rook_move(self, move: Move) -> bool:
        current_square_bb = set_bit(make_uint64_zero(), move.from_sq)
        if move.piece_type == Piece.wR:
            if not (self.board.player_R_bb & current_square_bb):
                return False
            if self.is_not_rook_attack(move):
                return False
            return True

        if move.piece_type == Piece.bR:
            if not (self.board.computer_R_bb & current_square_bb):
                return False
            if self.is_not_rook_attack(move):
                return False
            return True

    def is_legal_knight_move(self, move):
        current_square_bb = set_bit(make_uint64_zero(), move.from_sq)
        if move.piece == Piece.wN:
            if not (self.board.player_N_bb & current_square_bb):
                return False
            if self.is_not_knight_attack(move):
                return False
            return True

        if move.piece == Piece.bN:
            if not (self.board.computer_N_bb & current_square_bb):
                return False
            if self.is_not_knight_attack(move):
                return False
            return True

    def is_legal_queen_move(self, move):
        current_square_bb = set_bit(make_uint64_zero(), move.from_sq)
        if move.piece == Piece.wQ:
            if not (self.board.player_Q_bb & current_square_bb):
                return False
            if self.is_not_queen_attack(move):
                return False
            return True

        if move.piece == Piece.bQ:
            if not (self.board.computer_Q_bb & current_square_bb):
                return False
            if self.is_not_queen_attack(move):
                return False
            return True

    def is_legal_king_move(self, move):
        current_square_bb = set_bit(make_uint64_zero(), move.from_sq)
        if move.piece == Piece.wK:
            if not (self.board.player_K_bb & current_square_bb):
                return False
            if self.is_not_king_attack(move):
                return False
            return True

        if move.piece == Piece.bK:
            if not (self.board.computer_K_bb & current_square_bb):
                return False
            if self.is_not_king_attack(move):
                return False
            return True

    # -------------------------------------------------------------
    # PIECE MOVE LEGALITY CHECKING HELPERS
    # -------------------------------------------------------------

    def is_not_pawn_motion_or_attack(self, move):
        to_sq_bb = set_bit(make_uint64_zero(), move.to_sq)
        if move.rival == Rival.PLAYER:
            if (
                not (
                    self.board.player_pawn_motion_bbs[move.from_sq]
                    | self.board.player_pawn_attack_bbs[move.from_sq]
                )
                & to_sq_bb
            ):
                return True

        if move.rival == Rival.COMPUTER:
            if (
                not (
                    self.board.computer_pawn_motion_bbs[move.from_sq]
                    | self.board.computer_pawn_attack_bbs[move.from_sq]
                )
                & to_sq_bb
            ):
                return True

        return False

    def is_not_bishop_attack(self, move):
        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_sq)
        if move.rival == Rival.PLAYER:
            if not (self.player_bishop_attacks & moving_to_square_bb):
                return True
        if move.rival == Rival.COMPUTER:
            if not (self.computer_bishop_attacks & moving_to_square_bb):
                return True

        return False

    def is_not_knight_attack(self, move):
        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_sq)
        if move.rival == Rival.PLAYER:
            if not (self.player_knight_attacks & moving_to_square_bb):
                return True
        if move.rival == Rival.COMPUTER:
            if not (self.computer_knight_attacks & moving_to_square_bb):
                return True

        return False

    def is_not_king_attack(self, move):
        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_sq)
        if move.rival == Rival.PLAYER:
            if not (self.player_king_attacks & moving_to_square_bb):
                return True
        if move.rival == Rival.COMPUTER:
            if not (self.computer_king_attacks & moving_to_square_bb):
                return True

        return False

    def is_not_queen_attack(self, move):
        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_sq)
        if move.rival == Rival.PLAYER:
            if not (self.player_queen_attacks & moving_to_square_bb):
                return True
        if move.rival == Rival.COMPUTER:
            if not (self.computer_queen_attacks & moving_to_square_bb):
                return True

        return False

    def is_not_rook_attack(self, move):
        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_sq)
        if move.rival == Rival.PLAYER:
            if not (self.player_rook_attacks & moving_to_square_bb):
                return True
        if move.rival == Rival.COMPUTER:
            if not (self.computer_rook_attacks & moving_to_square_bb):
                return True

        return False

    def is_castling(move):
        """
        Is this a possible castling move?
        If there is a king piece on E1,
        then True i.e. E1 to G1 (white kingside)
                       E1 to C1 (white queenside)
        If there is a king piece on E8,
        then True i.e. E8 to G8 (black kingside)
                       E8 to C8 (white queenside)
        Otherwise cannot be a castling move
        """
        if move.from_sq == Square.E1:
            if move.to_sq in {Square.G1, Square.C1}:
                return True
        if move.from_sq == Square.E8:
            if move.to_sq in {Square.G8, Square.C8}:
                return True
        return False

    def is_promotion(self, pawn_move):
        """ Has the rival pawn reached the other end of the board? """
        if pawn_move.rival == Rival.PLAYER and pawn_move.to_sq in Rank.RANK_X8:
            return True
        if (pawn_move.rival == Rival.COMPUTER and
           pawn_move.to_sq in Rank.RANK_X1):
            return True
        return False

    # -------------------------------------------------------------
    # LEGAL KNIGHT MOVES
    # -------------------------------------------------------------

    def update_legal_knight_moves(
        self, move_from_sq: np.uint64, rival_to_move: int
    ) -> np.uint64:
        """
        Gets the legal knight moves from the given Move instance
        :param move_from_sq:
        :param rival_to_move:
        :return: filtered legal moves
        """
        legal_knight_moves = self.board.get_knight_attack_from(move_from_sq)

        # Mask out own pieces
        if rival_to_move == Rival.PLAYER:
            legal_knight_moves &= ~self.board.player_pieces_bb
            self.player_knight_attacks |= legal_knight_moves

        if rival_to_move == Rival.COMPUTER:
            legal_knight_moves &= ~self.board.computer_pieces_bb
            self.computer_knight_attacks |= legal_knight_moves

        return legal_knight_moves

    # -------------------------------------------------------------
    # LEGAL BISHOP MOVES
    # -------------------------------------------------------------

    def update_legal_bishop_moves(
        self, move_from_square: np.uint64, rival_to_move: int
    ) -> np.uint64:
        """
        Pseudo-Legal Bishop Moves
        Implements the classical approach
        for determining legal sliding-piece moves for diagonal directions.

        Gets first blocker with forward or reverse bitscan
        based on the ray direction and XORs the open board ray
        with the ray continuation from the blocked square.

        :param move_from_square: the proposed square
                                 from which the bishop is to move

        :param rival_to_move: the current colour/rival to move

        :return: True if Move is legal
        """
        bitboard = make_uint64_zero()
        occupied = self.board.occupied_squares_bb

        northwest_ray = get_northwest_ray(bitboard, move_from_square)

        intersection = occupied & northwest_ray
        if intersection:
            first_blocker = bitscan_forward(intersection)
            block_ray = get_northwest_ray(bitboard, first_blocker)
            northwest_ray ^= block_ray

        northeast_ray = get_northeast_ray(bitboard, move_from_square)
        intersection = occupied & northeast_ray
        if intersection:
            first_blocker = bitscan_forward(intersection)
            block_ray = get_northeast_ray(bitboard, first_blocker)
            northeast_ray ^= block_ray

        southwest_ray = get_southwest_ray(bitboard, move_from_square)
        intersection = occupied & southwest_ray
        if intersection:
            first_blocker = bitscan_reverse(intersection)
            block_ray = get_southwest_ray(bitboard, first_blocker)
            southwest_ray ^= block_ray

        southeast_ray = get_southeast_ray(bitboard, move_from_square)
        intersection = occupied & southeast_ray
        if intersection:
            first_blocker = bitscan_reverse(intersection)
            block_ray = get_southeast_ray(bitboard, first_blocker)
            southeast_ray ^= block_ray

        legal_moves = (northwest_ray | northeast_ray |
                       southwest_ray | southeast_ray)

        # remove own piece targets
        own_piece_targets = self.occupied_squares_by_rival[rival_to_move]
        if own_piece_targets:
            legal_moves &= ~own_piece_targets

        if rival_to_move == Rival.PLAYER:
            self.player_bishop_attacks |= legal_moves

        if rival_to_move == Rival.COMPUTER:
            self.computer_bishop_attacks |= legal_moves

        return legal_moves

    # -------------------------------------------------------------
    # LEGAL ROOK MOVES
    # -------------------------------------------------------------

    def update_legal_rook_moves(
        self, move_from_square: np.uint64, rival_to_move: int
    ) -> np.uint64:
        """
        Pseudo-Legal Rook Moves
        Implements the classical approach
        for determining legal sliding-piece moves for rank and file directions.

        Gets first blocker with forward or reverse bitscan based on
        the ray direction and XORs the open board ray with the ray continuation
        from the blocked square.

        :param move_from_square: the proposed square from which
                                 the rook is to move

        :param rival_to_move: the current colour/rival to move

        :return: True if Move is legal
        """
        bitboard = make_uint64_zero()
        occupied = self.board.occupied_squares_bb

        north_ray = get_north_ray(bitboard, move_from_square)
        intersection = occupied & north_ray
        if intersection:
            first_blocker = bitscan_forward(intersection)
            block_ray = get_north_ray(bitboard, first_blocker)
            north_ray ^= block_ray

        east_ray = get_east_ray(bitboard, move_from_square)
        intersection = occupied & east_ray
        if intersection:
            first_blocker = bitscan_forward(intersection)
            block_ray = get_east_ray(bitboard, first_blocker)
            east_ray ^= block_ray

        south_ray = get_south_ray(bitboard, move_from_square)
        intersection = occupied & south_ray
        if intersection:
            first_blocker = bitscan_reverse(intersection)
            block_ray = get_south_ray(bitboard, first_blocker)
            south_ray ^= block_ray

        west_ray = get_west_ray(bitboard, move_from_square)
        intersection = occupied & west_ray
        if intersection:
            first_blocker = bitscan_reverse(intersection)
            block_ray = get_west_ray(bitboard, first_blocker)
            west_ray ^= block_ray

        legal_moves = north_ray | east_ray | south_ray | west_ray

        # Remove own piece targets
        own_piece_targets = self.occupied_squares_by_rival[rival_to_move]

        if own_piece_targets:
            legal_moves &= ~own_piece_targets

        if rival_to_move == Rival.PLAYER:
            self.player_rook_attacks |= legal_moves

        if rival_to_move == Rival.COMPUTER:
            self.computer_rook_attacks |= legal_moves

    # -------------------------------------------------------------
    # LEGAL PAWN MOVES
    # -------------------------------------------------------------

    def update_legal_pawn_moves(self,
                                move_from_square: np.uint64,
                                rival_to_move: int):
        """
        Pseudo-Legal Pawn Moves:
        - Pawn non-attacks that don't intersect with occupied squares
        - Pawn attacks that intersect with opponent pieces

        :param move_from_square: the proposed square
                                 from which the pawn is to move

        :param rival_to_move: the current colour/rival to move

        :return: True if Move is legal
        """
        bitboard = make_uint64_zero()

        self.player_pawn_attacks = self.board.player_pawn_attacks
        self.computer_pawn_attacks = self.board.computer_pawn_attacks

        legal_non_attack_moves = {
            Rival.PLAYER:
                self.board.player_pawn_motion_bbs[move_from_square],
            Rival.COMPUTER:
                self.board.computer_pawn_motion_bbs[move_from_square],
        }

        legal_non_attack_moves[rival_to_move] &= self.board.empty_squares_bb

        legal_attack_moves = {
            Rival.PLAYER:
                self.board.player_pawn_attack_bbs[move_from_square],
            Rival.COMPUTER:
                self.board.computer_pawn_attack_bbs[move_from_square],
        }

        # Handle en-passant targets
        if self.en_passant_target is not None:
            en_passant_bb = set_bit(bitboard, self.en_passant_target)
            en_passant_move = legal_attack_moves[rival_to_move] & en_passant_bb
            if en_passant_move:
                legal_attack_moves[rival_to_move] |= en_passant_move

        legal_moves = (legal_non_attack_moves[rival_to_move] |
                       legal_attack_moves[rival_to_move])

        # Handle removing own piece targets
        occupied_squares = {
            Rival.COMPUTER: self.board.computer_pieces_bb,
            Rival.PLAYER: self.board.player_pieces_bb,
        }

        # Remove own piece targets
        own_piece_targets = occupied_squares[rival_to_move]

        if own_piece_targets:
            legal_moves &= ~own_piece_targets

        if rival_to_move == Rival.PLAYER:
            self.player_pawn_attacks |= legal_attack_moves[Rival.PLAYER]
            self.player_pawn_moves |= legal_non_attack_moves[Rival.PLAYER]

        if rival_to_move == Rival.COMPUTER:
            self.computer_pawn_attacks |= legal_attack_moves[Rival.COMPUTER]
            self.computer_pawn_moves |= legal_non_attack_moves[Rival.COMPUTER]

    # -------------------------------------------------------------
    # LEGAL QUEEN MOVES
    # -------------------------------------------------------------

    def update_legal_queen_moves(self, move_from_square: np.uint64,
                                 rival_to_move: int):
        """
        Pseudo-Legal Queen Moves:  bitwise OR of legal Bishop moves, Rook moves

        :param move_from_square: the proposed square
                                 from which the queen is to move

        :param rival_to_move: the current colour/rival to move

        :return: True if Move is legal
        """

        # TODO: Reduce duplication

        bitboard = make_uint64_zero()
        occupied = self.board.occupied_squares_bb

        north_ray = get_north_ray(bitboard, move_from_square)
        intersection = occupied & north_ray
        if intersection:
            first_blocker = bitscan_forward(intersection)
            block_ray = get_north_ray(bitboard, first_blocker)
            north_ray ^= block_ray

        east_ray = get_east_ray(bitboard, move_from_square)
        intersection = occupied & east_ray
        if intersection:
            first_blocker = bitscan_forward(intersection)
            block_ray = get_east_ray(bitboard, first_blocker)
            east_ray ^= block_ray

        south_ray = get_south_ray(bitboard, move_from_square)
        intersection = occupied & south_ray
        if intersection:
            first_blocker = bitscan_reverse(intersection)
            block_ray = get_south_ray(bitboard, first_blocker)
            south_ray ^= block_ray

        west_ray = get_west_ray(bitboard, move_from_square)
        intersection = occupied & west_ray
        if intersection:
            first_blocker = bitscan_reverse(intersection)
            block_ray = get_west_ray(bitboard, first_blocker)
            west_ray ^= block_ray

        northwest_ray = get_northwest_ray(bitboard, move_from_square)
        intersection = occupied & northwest_ray
        if intersection:
            first_blocker = bitscan_forward(intersection)
            block_ray = get_northwest_ray(bitboard, first_blocker)
            northwest_ray ^= block_ray

        northeast_ray = get_northeast_ray(bitboard, move_from_square)
        intersection = occupied & northeast_ray
        if intersection:
            first_blocker = bitscan_forward(intersection)
            block_ray = get_northeast_ray(bitboard, first_blocker)
            northeast_ray ^= block_ray

        southwest_ray = get_southwest_ray(bitboard, move_from_square)
        intersection = occupied & southwest_ray
        if intersection:
            first_blocker = bitscan_reverse(intersection)
            block_ray = get_southwest_ray(bitboard, first_blocker)
            southwest_ray ^= block_ray

        southeast_ray = get_southeast_ray(bitboard, move_from_square)
        intersection = occupied & southeast_ray
        if intersection:
            first_blocker = bitscan_reverse(intersection)
            block_ray = get_southeast_ray(bitboard, first_blocker)
            southeast_ray ^= block_ray

        legal_moves = (
            north_ray
            | east_ray
            | south_ray
            | west_ray
            | northeast_ray
            | southeast_ray
            | southwest_ray
            | northwest_ray
        )

        # Remove own piece targets
        own_piece_targets = self.occupied_squares_by_rival[rival_to_move]

        if own_piece_targets:
            legal_moves &= ~own_piece_targets

        if rival_to_move == Rival.PLAYER:
            self.player_queen_attacks |= legal_moves

        if rival_to_move == Rival.COMPUTER:
            self.computer_queen_attacks |= legal_moves

    # -------------------------------------------------------------
    # LEGAL KING MOVES
    # -------------------------------------------------------------

    def update_legal_king_moves(self,
                                move_from_square: int, rival_to_move: int):
        """
        Pseudo-Legal King Moves: one step in any direction

        :param move_from_square: the proposed square
                                 from which the king is to move

        :param rival_to_move: the current colour/rival to move

        :return: True if Move is legal
        """

        king_moves = generate_king_attack_bb_from_square(move_from_square)

        own_piece_targets = None

        if rival_to_move == Rival.PLAYER:
            own_piece_targets = self.board.player_pieces_bb

        if rival_to_move == Rival.COMPUTER:
            own_piece_targets = self.board.computer_pieces_bb

        if own_piece_targets.any():
            king_moves &= ~own_piece_targets

        # Handle Castling
        can_castle_pair = self.can_castle(rival_to_move)

        if any(can_castle_pair):
            king_moves |= self.add_castling_moves(king_moves,
                                                  can_castle_pair,
                                                  rival_to_move)

        if rival_to_move == Rival.PLAYER:
            self.player_king_attacks |= king_moves

        if rival_to_move == Rival.COMPUTER:
            self.computer_king_attacks |= king_moves

    def add_castling_moves(
        bitboard: np.uint64, can_castle: list, rival_to_move
    ) -> np.uint64:
        """
        Adds castling squares to the bitboard
        :param bitboard: numpy uint64 bitboard
        :return:
        """
        if rival_to_move == Rival.PLAYER:
            if can_castle[KINGSIDE]:
                bitboard |= set_bit(bitboard, Square.G1)
            if can_castle[QUEENSIDE]:
                bitboard |= set_bit(bitboard, Square.C1)

        if rival_to_move == Rival.COMPUTER:
            if can_castle[KINGSIDE]:
                bitboard |= set_bit(bitboard, Square.G8)
            if can_castle[QUEENSIDE]:
                bitboard |= set_bit(bitboard, Square.C8)

        return bitboard

    def can_castle(self, rival_to_move) -> list:
        """
        Returns a tuple of (bool, bool) can castle on (kingside, queenside)
        and can move through the castling squares without being in check.
        :return: List (bool, bool) if the rival_to_move has castling rights
        and can move through the castling squares without being
        in check on (kingside, queenside)
        """
        castle_rights = self.castle_rights[rival_to_move]

        if not castle_rights[KINGSIDE] or not castle_rights[QUEENSIDE]:
            return [False, False]

        if rival_to_move == Rival.PLAYER:
            kingside_blocked = (
                self.computer_attacked_squares
                | (self.board.player_pieces_bb & ~self.board.player_K_bb)
            ) & CastleRoute.PLAYER_KINGSIDE
            queenside_blocked = (
                self.computer_attacked_squares
                | (self.board.player_pieces_bb & ~self.board.player_K_bb)
            ) & CastleRoute.PLAYER_QUEENSIDE
            is_rook_on_h1 = (self.board.player_R_bb &
                             set_bit(make_uint64_zero(), Square.H1))
            is_rook_on_a1 = (self.board.player_R_bb &
                             set_bit(make_uint64_zero(), Square.A1))
            return [
                not kingside_blocked.any() and is_rook_on_h1.any(),
                not queenside_blocked.any() and is_rook_on_a1.any(),
            ]

        if rival_to_move == Rival.COMPUTER:
            kingside_blocked = (
                self.player_attacked_squares
                | (self.board.computer_pieces_bb & ~self.board.computer_K_bb)
            ) & CastleRoute.COMPUTER_KINGSIDE
            queenside_blocked = (
                self.player_attacked_squares
                | (self.board.computer_pieces_bb & ~self.board.computer_K_bb)
            ) & CastleRoute.COMPUTER_QUEENSIDE
            is_rook_on_h8 = (self.board.computer_R_bb &
                             set_bit(make_uint64_zero(), Square.H8))
            is_rook_on_a8 = (self.board.computer_R_bb &
                             set_bit(make_uint64_zero(), Square.A8))
            return [
                not kingside_blocked.any() and is_rook_on_h8.any(),
                not queenside_blocked.any() and is_rook_on_a8.any(),
            ]

    def get_promotion_piece_type(self, legal_piece, move):
        if move.rival == Rival.PLAYER:
            return PLAYER_PROMOTION_MAP[legal_piece]
        if move.rival == Rival.COMPUTER:
            return COMPUTER_PROMOTION_MAP[legal_piece]

    def evaluate_king_check(self):
        """
        Evaluates instance state for intersection of
        attacked squares and opposing king position.
        Updates instance state `king_in_check` for the corresponding rival
        """
        if self.computer_attacked_squares & self.board.player_K_bb:
            self.king_in_check[Rival.PLAYER] = True
        else:
            self.king_in_check[Rival.PLAYER] = False

        if self.player_attacked_squares & self.board.computer_K_bb:
            self.king_in_check[Rival.COMPUTER] = True
        else:
            self.king_in_check[Rival.COMPUTER] = False

    def make_move_result(self) -> MoveResult:
        move_result = MoveResult()
        move_result.fen = generate_fen(self)  # TODO
        return move_result

    # TODO message IS NEVER USED!
    def make_illegal_move_result(self, message: str) -> MoveResult:
        move_result = MoveResult()
        move_result.is_illegal_move = True
        move_result.fen = generate_fen(self)  # TODO
        return move_result

    def make_checkmate_result(self) -> MoveResult:
        move_result = MoveResult()
        move_result.is_checkmate = True
        move_result.fen = generate_fen(self)  # TODO
        return move_result

    def make_stalemate_result(self) -> MoveResult:
        move_result = MoveResult()
        move_result.is_stalemate = True
        move_result.fen = generate_fen(self)  # TODO
        return move_result

    def make_draw_result(self) -> MoveResult:
        move_result = MoveResult()
        move_result.is_draw_claim_allowed = True
        move_result.fen = generate_fen(self)  # TODO
        return move_result

    def is_threefold_repetition(self) -> bool:
        """
        Check if the current position has occurred 3 times.
        Returns True if 3-fold repetition has occurred.
        """
        current_fen = generate_fen(self)  # TODO X 2

        # Count occurrences of current position in history
        # TODO regarding position_history
        position_count = self.position_history.count(current_fen)

        # If this position has occurred 2 times before, this would be the 3rd
        return position_count >= 2

    def is_insufficient_material(self) -> bool:
        """
        Check if there is insufficient material to continue the game.
        Returns True if neither side has enough material to checkmate.
        """
        # Count pieces for each side
        white_pieces = {
            "pawns": len(self.piece_map.get(Piece.wP, set())),
            "rooks": len(self.piece_map.get(Piece.wR, set())),
            "knights": len(self.piece_map.get(Piece.wN, set())),
            "bishops": len(self.piece_map.get(Piece.wB, set())),
            "queens": len(self.piece_map.get(Piece.wQ, set())),
            "kings": len(self.piece_map.get(Piece.wK, set())),
        }

        black_pieces = {
            "pawns": len(self.piece_map.get(Piece.bP, set())),
            "rooks": len(self.piece_map.get(Piece.bR, set())),
            "knights": len(self.piece_map.get(Piece.bN, set())),
            "bishops": len(self.piece_map.get(Piece.bB, set())),
            "queens": len(self.piece_map.get(Piece.bQ, set())),
            "kings": len(self.piece_map.get(Piece.bK, set())),
        }

        # If any side has pawns, rooks, or queens, there's sufficient material
        if (
            white_pieces["pawns"] > 0
            or white_pieces["rooks"] > 0
            or white_pieces["queens"] > 0
            or black_pieces["pawns"] > 0
            or black_pieces["rooks"] > 0
            or black_pieces["queens"] > 0
        ):
            return False

        # Count total minor pieces (knights + bishops) for each side
        white_minor = white_pieces["knights"] + white_pieces["bishops"]
        black_minor = black_pieces["knights"] + black_pieces["bishops"]

        # King vs King
        if white_minor == 0 and black_minor == 0:
            return True

        # King + minor piece vs King
        if (white_minor <= 1 and black_minor == 0) or (
            black_minor <= 1 and white_minor == 0
        ):
            return True

        # King + Bishop vs King + Bishop (same colour squares)
        if (
            white_pieces["bishops"] == 1
            and white_pieces["knights"] == 0
            and white_minor == 1
            and black_pieces["bishops"] == 1
            and black_pieces["knights"] == 0
            and black_minor == 1
        ):
            # Check if bishops are on same colour squares
            white_bishop_squares = list(self.piece_map.get(Piece.wB, set()))
            black_bishop_squares = list(self.piece_map.get(Piece.bB, set()))

            if white_bishop_squares and black_bishop_squares:
                # if both lists are not empty then
                # Check if both bishops are on the same colour squares
                # (sum of coordinates is even/odd)
                white_bishop_square = white_bishop_squares[0]
                black_bishop_square = black_bishop_squares[0]

                white_colour = ((white_bishop_square // 8 +
                                white_bishop_square % 8) % 2)
                black_colour = ((black_bishop_square // 8 +
                                black_bishop_square % 8) % 2)

                if white_colour == black_colour:
                    return True

        return False

    def get_piece_on_square(self, from_sq):
        """
        Returns the piece on the given square using O(1) mailbox lookup.

        Args:
            from_sq: Square index (0-63)

        Returns:
            Piece type or None if square is empty
        """
        if 0 <= from_sq < 64:
            return self.mailbox[from_sq]
        return None


def evaluate_move(move, position: Position) -> MoveResult:
    """
    Evaluates if a move is fully legal
    """

    if not position.is_legal_move(move):
        return position.make_illegal_move_result("Illegal move")

    if move.is_capture:
        position.halfmove_clock = 0
        position.remove_opponent_piece_from_square(move.to_sq)

    if position.is_en_passant_capture:
        if position.rival_to_move == Rival.PLAYER:
            position.remove_opponent_piece_from_square(move.to_sq - 8)
        if position.rival_to_move == Rival.COMPUTER:
            position.remove_opponent_piece_from_square(move.to_sq + 8)

    position.is_en_passant_capture = False

    if move.piece in {Piece.wP, Piece.bP}:
        position.halfmove_clock = 0
    # update both piece_map and mailbox
    position.piece_map[move.piece].remove(move.from_sq)
    position.piece_map[move.piece].add(move.to_sq)
    position.mailbox[move.from_sq] = None
    position.mailbox[move.to_sq] = move.piece

    if move.is_promotion:
        position.promote_pawn(move)

    if move.is_castling:
        position.move_rooks_for_castling(move)

    position.halfmove_clock += 1
    position.halfmove += 1

    castle_rights = position.castle_rights[position.rival_to_move]

    if any(castle_rights):
        position.adjust_castling_rights(move)

    if position.en_passant_side != position.rival_to_move:
        position.en_passant_target = None

    position.board.update_position_bitboards(position.piece_map)
    position.update_attack_bitboards()
    position.evaluate_king_check()

    if position.king_in_check[position.rival_to_move]:
        return position.make_illegal_move_result("own king in check")

    return position.make_move_result()
