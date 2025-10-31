import numpy as np
from math import inf
from itertools import product
from typing import Optional, NoReturn, Literal

from extras import CustomException

from wake_constants import (
    Rival,
    Piece,
    Square,
    CastleRoute,
    File,
    Rank,
    SQUARE_MAP,
    PLAYER_PROMOTION_MAP,
    COMPUTER_PROMOTION_MAP,
    KINGSIDE,
    QUEENSIDE,
    THE_ATTACK,
    THE_PIECE,
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
# from wake_position import Position  # TODO
from wake_fen import generate_fen
from wake_move import Move, MoveResult
from wake_debug import pprint_pieces  # TODO

ROOK_RIVAL_MAP = {Rival.PLAYER: Piece.wR, Rival.COMPUTER: Piece.bR}

# These numbers are derived from
# generate_knight_attack_bb_from_square()
LEGAL_KNIGHT_DIFFERENCES = (6, 15, 17, 10, -6, -15, -17, -10)

FILES_AB = File.FILE_A | File.FILE_B
FILES_GH = File.FILE_G | File.FILE_H

INFINITY = inf
MINUS_INFINITY = -INFINITY


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
        for piece_type_number in (
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
            self.piece_map[piece_type_number] = set()

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
        print("MEM")
        quit()  # TODO

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
    def wake_makemove(self,
                      move: Move) -> tuple[MoveResult, dict]:
        # if self.rival_to_move != move.rival_identity:  # TODO
        #     return self.make_illegal_move_result()

        move_result, original = update_wakegame_position(self, move)
        if move_result is not None:
            # a chess move error has occurred
            return move_result, original

        if self.king_in_check[move.rival_identity]:
            print("RESET")  # TODO
            quit()
            # self.reset_state_to(original_position)
            return self.make_king_in_check_result(), original

        other_rival = (Rival.COMPUTER if move.rival_identity == Rival.PLAYER
                       else Rival.PLAYER)

        if (self.king_in_check[other_rival]
           and not self.any_legal_moves(other_rival)):
            return self.make_checkmate_result(), original

        if (not self.king_in_check[other_rival]
           and not self.any_legal_moves(other_rival)):
            return self.make_stalemate_result(), original

        # 50-move rule draw (50 moves by each player = 100 half-moves)
        if self.halfmove_clock >= 100:
            print("Draw by 50-move rule")  # TODO RE HISTORY
            return self.make_draw_result(), original

        if self.is_threefold_repetition():
            print("Draw by 3-fold repetition")  # TODO RE HISTORY
            return self.make_draw_result(), original

        if self.is_insufficient_material():
            print("Draw by insufficient material")  # TODO RE HISTORY
            return self.make_draw_result(), original

        original['position_history'] = len(self.position_history)
        original['rival_to_move'] = self.rival_to_move

        self.position_history.append(generate_fen(self))  # TODO
        self.rival_to_move = switch_rival(self.rival_to_move)

        # print("RET", original)  TODO
        return self.make_move_result(), original

    def promote_pawn(self, move: Move) -> None:
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
            self.piece_map[move.piece_type_number].remove(move.to_square)
            new_piece = self.get_promotion_piece_type(legal_piece, move)
            self.piece_map[new_piece].add(move.to_square)
            self.mailbox[move.to_square] = new_piece
            break

    def any_legal_moves(self, rival_to_move: Literal[1, 0]) -> bool:
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

    def has_king_move(self, rival_to_move: Literal[1, 0]) -> bool:
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
            move = evaluate_move(move, self)
            if not move.is_illegal_move:
                return True

        return False

    def has_rook_move(self, rival_to_move: Literal[1, 0]) -> bool:
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
                move = evaluate_move(move, self)
                if not move.is_illegal_move:
                    return True
        return False

    def has_queen_move(self, rival_to_move: Literal[1, 0]) -> bool:
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
                move = evaluate_move(move, self)
                if not move.is_illegal_move:
                    return True
        return False

    def has_knight_move(self, rival_to_move: Literal[1, 0]) -> bool:
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
                move = evaluate_move(move, self)
                if not move.is_illegal_move:
                    return True
        return False

    def has_bishop_move(self, rival_to_move: Literal[1, 0]) -> bool:
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
                move = evaluate_move(move, self)
                if not move.is_illegal_move:
                    return True
        return False

    def has_pawn_move(self, rival_to_move: Literal[1, 0]) -> bool:
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
                move = evaluate_move(move, self)
                if not move.is_illegal_move:
                    return True
        return False

    def remove_opponent_piece_from_square(self, to_square: int,
                                          original: dict = None) -> dict:
        if original is None:
            original = {}

        target = self.mailbox[to_square]
        if target is not None:
            # target is a number
            map_key = f'piece_map {target}'
            mailbox_key = f'mailbox {to_square}'
            if map_key not in original:  # original value not already saved
                original[map_key] = self.piece_map[target].copy()
            if mailbox_key not in original:  # original value not already saved
                original[mailbox_key] = self.mailbox[to_square]

            self.piece_map[target].remove(to_square)
            self.mailbox[to_square] = None
        return original

    def update_attack_bitboards(self, original: dict = None) -> dict:
        if original is None:
            original = {}
        original = self.reset_attack_bitboards(original)

        for piece, squares in self.piece_map.items():

            # PAWNS
            if piece == Piece.wP:
                original['player_pawn_moves'] = self.player_pawn_moves
                for square in squares:
                    self.update_legal_pawn_moves(square, Rival.PLAYER)
            if piece == Piece.bP:
                original['computer_pawn_moves'] = self.player_pawn_moves
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

        return original

    def adjust_castling_rights(self, move: Move,
                               original: dict = None) -> dict:
        if original is None:
            original = {}

        if move.piece_type_number in {Piece.wK, Piece.bK, Piece.wR, Piece.bR}:
            original['castling_rights'] = list(self.castle_rights)

            # If a KING piece is being moved, then from this point onwards:
            # the KING can no longer be used in a castling move.
            if move.piece_type_number == Piece.wK:
                self.castle_rights[Rival.PLAYER] = [False, False]
            if move.piece_type_number == Piece.bK:
                self.castle_rights[Rival.COMPUTER] = [False, False]

            # If a ROOK piece is being moved, then from this point onwards:
            # which ever side the rook originated from (either
            # kingside or queenside), the KING can no longer be
            # castled to that side.
            if move.piece_type_number == Piece.wR:
                if move.from_square == Square.H1:
                    self.castle_rights[Rival.PLAYER][KINGSIDE] = False
                if move.from_square == Square.A1:
                    self.castle_rights[Rival.PLAYER][QUEENSIDE] = False
            if move.piece_type_number == Piece.bR:
                if move.from_square == Square.H8:
                    self.castle_rights[Rival.COMPUTER][KINGSIDE] = False
                if move.from_square == Square.A8:
                    self.castle_rights[Rival.COMPUTER][QUEENSIDE] = False

        return original

    def move_rooks_for_castling(self, move: Move,
                                original: dict = None) -> dict:
        if original is None:
            original = {}

        square_map = {
            Square.G1: (Square.H1, Square.F1),
            Square.C1: (Square.A1, Square.D1),
            Square.G8: (Square.H8, Square.F8),
            Square.C8: (Square.A8, Square.D8),
        }

        rook_piece = ROOK_RIVAL_MAP[move.rival_identity]
        from_square, to_square = square_map[move.to_square]

        # Update both piece_map and mailbox

        map_key = f'piece_map {rook_piece}'
        assert (map_key not in original)
        original[map_key] = set(self.piece_map[rook_piece])
        from_key = f'mailbox {from_square}'
        assert (from_key not in original)
        original[from_key] = self.mailbox[from_square]
        to_key = f'mailbox {to_square}'
        assert (to_key not in original)
        original[to_key] = self.mailbox[to_square]

        self.piece_map[rook_piece].remove(from_square)
        self.piece_map[rook_piece].add(to_square)
        self.mailbox[from_square] = None
        self.mailbox[to_square] = rook_piece

        return original

    def reset_attack_bitboards(self, original: dict = None) -> dict:
        if original is None:
            original = {}

        original['player_rook_attacks'] = self.player_rook_attacks
        original['computer_rook_attacks'] = self.computer_rook_attacks
        original['player_bishop_attacks'] = self.player_bishop_attacks
        original['computer_bishop_attacks'] = self.computer_bishop_attacks
        original['player_knight_attacks'] = self.player_knight_attacks
        original['computer_knight_attacks'] = self.computer_knight_attacks
        original['player_queen_attacks'] = self.player_queen_attacks
        original['computer_queen_attacks'] = self.computer_queen_attacks
        original['player_king_attacks'] = self.player_king_attacks
        original['computer_king_attacks'] = self.computer_king_attacks
        original['player_pawn_attacks'] = self.player_pawn_attacks
        original['computer_pawn_attacks'] = self.computer_pawn_attacks
        original['player_pawn_moves'] = self.player_pawn_moves
        original['computer_pawn_moves'] = self.computer_pawn_moves

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

        return original

    # -------------------------------------------------------------
    # MOVE LEGALITY CHECKING
    # -------------------------------------------------------------

    def is_legal_move(self, move: Move,
                      original: dict = None) -> tuple[bool, dict] | NoReturn:
        """
        For a given move, returns True if it is legal given the Position state
        """
        if original is None:
            original = {}
        # print("O=", original)
        # sleep(5)  # TODO  REMOVE

        piece_type_number = move.piece_type_number

        if self.is_capture(move):
            move.is_capture = True

        match piece_type_number:
            case Piece.wB | Piece.bB:
                #  print(1, self.is_legal_bishop_move(move))  # TODO REMOVE P
                return self.is_legal_bishop_move(move), original

            case Piece.wR | Piece.bR:
                #  print(2, self.is_legal_rook_move(move))  # TODO REMOVE P
                return self.is_legal_rook_move(move), original

            case Piece.wN | Piece.bN:
                #  print(3, self.is_legal_knight_move(move))  # TODO REMOVE P
                return self.is_legal_knight_move(move), original

            case Piece.wQ | Piece.bQ:
                #  print(4, self.is_legal_queen_move(move))  # TODO REMOVE P
                return self.is_legal_queen_move(move), original

            case Piece.wK | Piece.bK:
                is_legal_king_move = self.is_legal_king_move(move)
                if not is_legal_king_move:
                    #  print(5, "KING")  # TODO REMOVE P
                    return False, original

                if self.is_castling(move):
                    move.is_castling = True
                return True, original

            case Piece.wP | Piece.bP:
                is_legal_pawn_move = self.is_legal_pawn_move(move)

                if not is_legal_pawn_move:
                    return False, original

                if self.is_promotion(move):
                    move.is_promotion = True
                    return True, original

                potential_en_passant_target = (
                    self.try_get_en_passant_target(move))

                if potential_en_passant_target is not None:
                    # print(original) # todo
                    assert ('en_passant_side' not in original)
                    assert ('en_passant_target' not in original)
                    original['en_passant_side'] = self.en_passant_side
                    original['en_passant_target'] = self.en_passant_target
                    # print("EP", self.en_passant_side, self.en_passant_target,
                    #       potential_en_passant_target, move.rival_identity)
                    #  TODO

                    self.en_passant_side = move.rival_identity
                    self.en_passant_target = int(potential_en_passant_target)

                if move.to_square == self.en_passant_target:
                    assert ('en_passant_target' not in original)
                    original['en_passant_target'] = self.en_passant_target

                    self.is_en_passant_capture = True

                return True, original

            case _:
                # Defensive Guard
                raise CustomException("Internal Error: Unknown Piece Number:"
                                      f" {piece_type_number}")

    # TODO 'move'
    def try_get_en_passant_target(self, move) -> Optional[int | np.uint64]:
        """
        Did a pawn perform an initial move of two squares?
        If True, there is a possibility of a subsequence en passant move.
        Return the target square
        """
        if move.piece_type_number not in {Piece.wP, Piece.bP}:
            return None
        if move.rival_identity == Rival.PLAYER:
            if (move.to_square in Rank.RANK_X4 and
               move.from_square in Rank.RANK_X2):
                return move.to_square - 8
        if move.rival_identity == Rival.COMPUTER:
            if (move.to_square in Rank.RANK_X5 and
               move.from_square in Rank.RANK_X7):
                return move.to_square + 8
        return None

    def is_capture(self, move):
        """ Does position 'move.to_square' intersect with any rival pawns? """

        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_square)

        if move.rival_identity == Rival.PLAYER:
            intersects = moving_to_square_bb & self.board.computer_pieces_bb
            if intersects.any():
                return True
        if move.rival_identity == Rival.COMPUTER:
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
        current_square_bb = set_bit(make_uint64_zero(), move.from_square)
        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_square)
        potential_en_passant_target = make_uint64_zero()

        if self.en_passant_target is not None:
            potential_en_passant_target = set_bit(make_uint64_zero(),
                                                  self.en_passant_target)

        if move.piece_type_number == Piece.wP:
            # If the colour of the pawn on the FROM square does not match
            # PLAYER (white), the move is False
            if not (self.board.player_P_bb & current_square_bb):
                return False

            if self.is_not_pawn_motion_or_attack(move):
                return False

            # If it's a pawn motion forward, check that it isn't blocked
            if move.from_square == move.to_square - 8 and (
                moving_to_square_bb & self.board.occupied_squares_bb
            ):
                return False

            # Need to cater for white pawn's two-squares motion forward
            # TODO TEST
            if (move.from_square in Rank.RANK_X2 and
               move.from_square == move.to_square + 16):
                square_between_bb = (set_bit(make_uint64_zero(),
                                     move.to_square + 8))
                if (square_between_bb & self.board.occupied_squares_bb):
                    return False

            # If it's a pawn attack move, check that it
            # intersects with COMPUTER (black) pieces or en passant target
            if (move.from_square == move.to_square - 9 or
               move.from_square == move.to_square - 7):
                if (self.player_pawn_attacks & moving_to_square_bb) & ~(
                    self.board.computer_pieces_bb | potential_en_passant_target
                ):
                    return False
            return True

        if move.piece_type_number == Piece.bP:
            # If the colour of the pawn on the FROM square does not match
            # COMPUTER (black), the move is False
            if not (self.board.computer_P_bb & current_square_bb):
                return False
            if self.is_not_pawn_motion_or_attack(move):
                return False

            # If it's a pawn motion forward, check that it isn't blocked
            if move.from_square == move.to_square + 8 and (
                moving_to_square_bb & self.board.occupied_squares_bb
            ):
                return False

            # Need to cater for black pawn's two-squares motion forward
            # TODO TEST
            if (move.from_square in Rank.RANK_X7 and
               move.from_square == move.to_square - 16):
                square_between_bb = (set_bit(make_uint64_zero(),
                                     move.to_square - 8))
                if (square_between_bb & self.board.occupied_squares_bb):
                    return False

            # If it's a pawn attack move,
            # check that it intersects with PLAYER (white) pieces
            #                               or en passant target
            if (move.from_square == move.to_square + 9
               or move.from_square == move.to_square + 7):
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
        current_square_bb = set_bit(make_uint64_zero(), move.from_square)
        if move.piece_type_number == Piece.wB:
            # If the colour of the bishop on the FROM square does not match
            # PLAYER (white), the move is False
            if not (self.board.player_B_bb & current_square_bb):
                return False
            if self.is_not_bishop_attack(move):
                return False
            return True

        if move.piece_type_number == Piece.bB:
            # If the colour of the bishop on the FROM square does not match
            # COMPUTER (black), the move is False
            if not (self.board.computer_B_bb & current_square_bb):
                return False
            if self.is_not_bishop_attack(move):
                return False
            return True

    def is_legal_rook_move(self, move: Move) -> bool:
        current_square_bb = set_bit(make_uint64_zero(), move.from_square)
        if move.piece_type_number == Piece.wR:
            # If the colour of the rook on the FROM square does not match
            # PLAYER (white), the move is False
            if not (self.board.player_R_bb & current_square_bb):
                return False
            if self.is_not_rook_attack(move):
                return False
            return True

        if move.piece_type_number == Piece.bR:
            # If the colour of the rook on the FROM square does not match
            # COMPUTER (black), the move is False
            if not (self.board.computer_R_bb & current_square_bb):
                return False
            if self.is_not_rook_attack(move):
                return False
            return True

    def is_legal_knight_move(self, move: Move) -> bool:
        current_square_bb = set_bit(make_uint64_zero(), move.from_square)
        if move.piece_type_number == Piece.wN:
            # If the colour of the knight on the FROM square does not match
            # PLAYER (white), the move is False
            if not (self.board.player_N_bb & current_square_bb):
                return False
            if self.is_not_knight_attack(move):
                return False
            return True

        if move.piece_type_number == Piece.bN:
            # If the colour of the knight on the FROM square does not match
            # COMPUTER (black), the move is False
            if not (self.board.computer_N_bb & current_square_bb):
                return False
            if self.is_not_knight_attack(move):
                return False
            return True

    def is_legal_queen_move(self, move: Move) -> bool:
        current_square_bb = set_bit(make_uint64_zero(), move.from_square)
        if move.piece_type_number == Piece.wQ:
            # If the colour of the queen on the FROM square does not match
            # PLAYER (white), the move is False
            if not (self.board.player_Q_bb & current_square_bb):
                return False
            if self.is_not_queen_attack(move):
                return False
            return True

        if move.piece_type_number == Piece.bQ:
            # If the colour of the queen on the FROM square does not match
            # COMPUTER (black), the move is False
            if not (self.board.computer_Q_bb & current_square_bb):
                return False
            if self.is_not_queen_attack(move):
                return False
            return True

    def is_legal_king_move(self, move: Move) -> bool:
        current_square_bb = set_bit(make_uint64_zero(), move.from_square)
        if move.piece_type_number == Piece.wK:
            # If the colour of the king on the FROM square does not match
            # PLAYER (white), the move is False
            if not (self.board.player_K_bb & current_square_bb):
                return False
            if self.is_not_king_attack(move):
                return False
            return True

        if move.piece_type_number == Piece.bK:
            # If the colour of the king on the FROM square does not match
            # COMPUTER (black), the move is False
            if not (self.board.computer_K_bb & current_square_bb):
                return False
            if self.is_not_king_attack(move):
                return False
            return True

    # -------------------------------------------------------------
    # PIECE MOVE LEGALITY CHECKING HELPERS
    # -------------------------------------------------------------

    def is_not_pawn_motion_or_attack(self, move: Move) -> bool:
        to_sq_bb = set_bit(make_uint64_zero(), move.to_square)
        if move.rival_identity == Rival.PLAYER:
            if (
                not (
                    self.board.player_pawn_motion_bbs[move.from_square]
                    | self.board.player_pawn_attack_bbs[move.from_square]
                )
                & to_sq_bb
            ):
                return True

        if move.rival_identity == Rival.COMPUTER:
            if (
                not (
                    self.board.computer_pawn_motion_bbs[move.from_square]
                    | self.board.computer_pawn_attack_bbs[move.from_square]
                )
                & to_sq_bb
            ):
                return True

        return False

    def is_not_bishop_attack(self, move: Move) -> bool:
        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_square)
        if move.rival_identity == Rival.PLAYER:
            if not (self.player_bishop_attacks & moving_to_square_bb):
                return True
        if move.rival_identity == Rival.COMPUTER:
            if not (self.computer_bishop_attacks & moving_to_square_bb):
                return True

        return False

    def is_not_knight_attack(self, move: Move) -> bool:
        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_square)
        if move.rival_identity == Rival.PLAYER:
            if not (self.player_knight_attacks & moving_to_square_bb):
                return True
        if move.rival_identity == Rival.COMPUTER:
            if not (self.computer_knight_attacks & moving_to_square_bb):
                return True

        return False

    def is_not_king_attack(self, move: Move) -> bool:
        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_square)
        if move.rival_identity == Rival.PLAYER:
            if not (self.player_king_attacks & moving_to_square_bb):
                return True
        if move.rival_identity == Rival.COMPUTER:
            if not (self.computer_king_attacks & moving_to_square_bb):
                return True

        return False

    def is_not_queen_attack(self, move: Move) -> bool:
        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_square)
        if move.rival_identity == Rival.PLAYER:
            if not (self.player_queen_attacks & moving_to_square_bb):
                return True
        if move.rival_identity == Rival.COMPUTER:
            if not (self.computer_queen_attacks & moving_to_square_bb):
                return True

        return False

    def is_not_rook_attack(self, move: Move) -> bool:
        moving_to_square_bb = set_bit(make_uint64_zero(), move.to_square)
        if move.rival_identity == Rival.PLAYER:
            if not (self.player_rook_attacks & moving_to_square_bb):
                return True
        if move.rival_identity == Rival.COMPUTER:
            if not (self.computer_rook_attacks & moving_to_square_bb):
                return True

        return False

    @staticmethod
    def is_castling(move: Move) -> bool:
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
        if move.from_square == Square.E1:
            if move.to_square in {Square.G1, Square.C1}:
                return True
        if move.from_square == Square.E8:
            if move.to_square in {Square.G8, Square.C8}:
                return True
        return False

    def is_promotion(self, pawn_move: Move) -> bool:
        """ Has the rival pawn reached the other end of the board? """
        if (pawn_move.rival_identity == Rival.PLAYER and
           pawn_move.to_square in Rank.RANK_X8):
            return True
        if (pawn_move.rival_identity == Rival.COMPUTER and
           pawn_move.to_square in Rank.RANK_X1):
            return True
        return False

    # -------------------------------------------------------------
    # LEGAL KNIGHT MOVES
    # -------------------------------------------------------------

    def update_legal_knight_moves(
        self, move_from_square: np.uint64, rival_to_move: int
    ) -> None:
        """
        Gets the legal knight moves from the given Move instance
        :param move_from_square:
        :param rival_to_move:
        :return: filtered legal moves
        """
        legal_knight_moves = (
            self.board.get_knight_attack_from(move_from_square))

        # Mask out own pieces
        if rival_to_move == Rival.PLAYER:
            legal_knight_moves &= ~self.board.player_pieces_bb
            self.player_knight_attacks |= legal_knight_moves

        if rival_to_move == Rival.COMPUTER:
            legal_knight_moves &= ~self.board.computer_pieces_bb
            self.computer_knight_attacks |= legal_knight_moves

    # -------------------------------------------------------------
    # LEGAL BISHOP MOVES
    # -------------------------------------------------------------

    def update_legal_bishop_moves(
        self, move_from_square: np.uint64, rival_to_move: int
    ) -> None:
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
                                rival_to_move: int) -> None:
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
            Rival.PLAYER: self.board.player_pieces_bb,
            Rival.COMPUTER: self.board.computer_pieces_bb,
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
                                 rival_to_move: int) -> None:
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
                                move_from_square: int,
                                rival_to_move: int) -> None:
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

    @staticmethod
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
        if move.rival_identity == Rival.PLAYER:
            return PLAYER_PROMOTION_MAP[legal_piece]
        if move.rival_identity == Rival.COMPUTER:
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
        #  TODO
        #  print(self.king_in_check)  # TODO REMOVE P K

    def make_move_result(self) -> MoveResult:
        move_result = MoveResult()
        move_result.fen = generate_fen(self)  # TODO
        return move_result

    def make_illegal_move_result(self) -> MoveResult:
        move_result = MoveResult()
        move_result.is_illegal_move = True
        move_result.fen = generate_fen(self)  # TODO
        return move_result

    def make_king_in_check_result(self) -> MoveResult:
        move_result = MoveResult()
        move_result.is_king_in_check = True
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

    # TODO Handle message
    def make_draw_result(self, message: str = "") -> MoveResult:
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

    def get_piece_typenum_on_square(self, from_square: int) -> Optional[int]:
        """
        Returns the piece on the given square using O(1) mailbox lookup.

        Args:
            from_square: Square index (0-63)

        Returns:
            Piece type or None if square is empty
        """
        if 0 <= from_square < 64:
            return self.mailbox[from_square]

        return None

    # -------------------------------------------------------------
    # NEW FUNCTIONALITY BASED ON 'any_legal_moves()'
    # AND 'has_XXX_move()' ROUTINES ABOVE.
    # THIS FUNCTION IS TO GENERATE ALL THE AVAILABLE LEGAL PIECE MOVES.
    # THe GENERATED LIST WILL BE USED BY THE MINIMAX ALGORITHM
    # -------------------------------------------------------------

    def all_legal_moves_list(self,
                             rival_to_move: Literal[1, 0]) -> list[tuple]:
        """
        Returns a list of all the available legal moves (if any)
        for a particular colour i.e. 'rival_to_move'
        """

        all_moves_list = self.all_pawn_moves(rival_to_move)
        all_moves_list.extend(self.all_king_moves(rival_to_move))
        all_moves_list.extend(self.all_rook_moves(rival_to_move))
        all_moves_list.extend(self.all_queen_moves(rival_to_move))
        all_moves_list.extend(self.all_knight_moves(rival_to_move))
        all_moves_list.extend(self.all_bishop_moves(rival_to_move))
        return all_moves_list

    def all_king_moves(self, rival_to_move: int) -> list[tuple]:
        """
        Return a list of all king moves that fit the following criteria:
        True if there is a legal king move
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

        # if no attacks, return []
        if not king_attacks.any():
            return []

        king_piece_map_copy = self.piece_map[king_piece].copy()
        king_from_square = king_piece_map_copy.pop()

        king_squares = get_squares_from_bitboard(king_attacks)

        moves_list = []
        for to_square in king_squares:
            move = Move(king_piece, (king_from_square, to_square))
            move = evaluate_move(move, self)
            if not move.is_illegal_move:
                moves_list.append((king_from_square, to_square))

        return moves_list

    def is_viable_rook_move(self,
                            from_square,
                            to_square,
                            rook_piece):
        pair = (from_square, to_square)
        if not (is_viable_vertical_move(pair) or
                is_viable_horizontal_move(pair)):
            return False

        move = self.filter_evaluate_move(rook_piece,
                                         from_square,
                                         to_square)
        return not move.is_illegal_move

    def all_rook_moves(self, rival_to_move: int) -> list[tuple]:
        rook_rival_map = {
            Rival.PLAYER: (self.player_rook_attacks, Piece.wR),
            Rival.COMPUTER: (self.computer_rook_attacks, Piece.bR),
        }

        rook_attacks = rook_rival_map[rival_to_move][THE_ATTACK]
        rook_piece = rook_rival_map[rival_to_move][THE_PIECE]

        # if no attacks, return []
        if not rook_attacks.any():
            return []

        current_rook_locations = self.piece_map[rook_piece]
        rook_attack_squares = get_squares_from_bitboard(rook_attacks)

        moves_list = [(from_square, to_square)
                      for from_square in current_rook_locations
                      for to_square in rook_attack_squares
                      if self.is_viable_rook_move(from_square,
                                                  to_square,
                                                  rook_piece)]

        #  print("DONE R", moves_list) TODO REMOVE P
        return moves_list

    def all_queen_moves(self, rival_to_move: int) -> list[tuple]:
        queen_rival_map = {
            Rival.PLAYER: (self.player_queen_attacks, Piece.wQ),
            Rival.COMPUTER: (self.computer_queen_attacks, Piece.bQ),
        }

        queen_attacks = queen_rival_map[rival_to_move][THE_ATTACK]
        queen_piece = queen_rival_map[rival_to_move][THE_PIECE]

        # if no attacks, return []
        if not queen_attacks.any():
            return []

        moves_list = []
        current_queen_locations = self.piece_map[queen_piece]
        queen_squares = get_squares_from_bitboard(queen_attacks)

        for queen_from_square in list(current_queen_locations):
            for to_square in queen_squares:
                move = Move(queen_piece, (queen_from_square, to_square))
                move = evaluate_move(move, self)
                if not move.is_illegal_move:
                    moves_list.append((queen_from_square, to_square))

        return moves_list

    def filter_evaluate_move(self, piece, from_square, to_square):
        move = Move(piece, (from_square, to_square))
        move = evaluate_move(move, self)
        return move

    def all_knight_moves(self, rival_to_move: int) -> list[tuple]:
        knight_rival_map = {
            Rival.PLAYER: (self.player_knight_attacks, Piece.wN),
            Rival.COMPUTER: (self.computer_knight_attacks, Piece.bN),
        }

        knight_attacks = knight_rival_map[rival_to_move][THE_ATTACK]
        knight_piece = knight_rival_map[rival_to_move][THE_PIECE]

        # if no attacks, return []
        if not knight_attacks.any() and self.halfmove > 2:
            quit()
            return []

        current_knight_locations = list(self.piece_map[knight_piece])
        knight_squares = get_squares_from_bitboard(knight_attacks)

        #  print("KS", knight_squares)  # TODO REMOVE P
        filtered_knight_moves = (filter(is_viable_knight_move,
                                 product(current_knight_locations,
                                         knight_squares)))

        moves_list = [(from_square, to_square)
                      for from_square, to_square in filtered_knight_moves
                      if ((move := self.filter_evaluate_move(knight_piece,
                                                             from_square,
                                                             to_square)) and
                          not move.is_illegal_move)]

        #  print("DONE N", moves_list) TODO REMOVE P
        #  TODO
        return moves_list

    def all_bishop_moves(self, rival_to_move: int) -> list[tuple]:
        bishop_rival_map = {
            Rival.PLAYER: (self.player_bishop_attacks, Piece.wB),
            Rival.COMPUTER: (self.computer_bishop_attacks, Piece.bB),
        }

        bishop_attacks = bishop_rival_map[rival_to_move][THE_ATTACK]
        bishop_piece = bishop_rival_map[rival_to_move][THE_PIECE]

        # if no attacks, return []
        if not bishop_attacks.any():
            return []

        current_bishop_locations = list(self.piece_map[bishop_piece])
        bishop_squares = get_squares_from_bitboard(bishop_attacks)

        filtered_bishop_moves = (filter(is_viable_diagonal_move,
                                 product(current_bishop_locations,
                                         bishop_squares)))

        moves_list = [(from_square, to_square)
                      for from_square, to_square in filtered_bishop_moves
                      if ((move := self.filter_evaluate_move(bishop_piece,
                                                             from_square,
                                                             to_square))
                          and not move.is_illegal_move)]

        #  print("DONE B", moves_list) TODO REMOVE P
        return moves_list

    def all_pawn_moves(self, rival_to_move: int) -> list[tuple]:
        pawn_rival_map = {
            Rival.PLAYER: (self.player_pawn_attacks
                           | self.player_pawn_moves, Piece.wP),
            Rival.COMPUTER: (self.computer_pawn_attacks
                             | self.computer_pawn_moves, Piece.bP),
        }

        all_pawn_moves = pawn_rival_map[rival_to_move][THE_ATTACK]
        pawn_piece = pawn_rival_map[rival_to_move][THE_PIECE]

        # if no moves, return []
        if not all_pawn_moves.any():
            print("WHYP")  # TODO P
            quit()
            return []

        current_pawn_locations = self.piece_map[pawn_piece]
        pawn_squares = get_squares_from_bitboard(all_pawn_moves)

        moves_list = []
        for pawn_from_square in list(current_pawn_locations):
            for to_square in pawn_squares:
                move = Move(pawn_piece, (pawn_from_square, to_square))
                move = evaluate_move(move, self)
                if not move.is_illegal_move:
                    moves_list.append((pawn_from_square, to_square))

        #  print(pawn_squares) TODO REMOVE P
        #  TODO
        #  print("DONE P", moves_list)
        #  TODO
        return moves_list


def update_wakegame_position(position: Position,
                             move: Move
                             ) -> tuple[Optional[MoveResult], dict]:
    """
    By maintaining a dictionary ('original')
    of any changes made to the Position object,
    if any chess move errors occurs, then any changes
    can be reverted in a lot faster manner then 'deepcopy'
    """

    # empty dictionary of 'changes' to begin with
    original = {}
    legal, original = position.is_legal_move(move)
    if not legal:
        return position.make_illegal_move_result(), original

    if move.is_capture:
        original['halfmove_clock'] = position.halfmove_clock
        position.halfmove_clock = 0
        original = (
            position.remove_opponent_piece_from_square(move.to_square,
                                                       original))

    if position.is_en_passant_capture:
        if move.rival_identity == Rival.PLAYER:
            original = (
                position.remove_opponent_piece_from_square(move.to_square - 8,
                                                           original)
            )
        if move.rival_identity == Rival.COMPUTER:
            original = (
                position.remove_opponent_piece_from_square(move.to_square + 8,
                                                           original)
            )

    original['is_en_passant_capture'] = position.is_en_passant_capture
    position.is_en_passant_capture = False

    if move.piece_type_number in {Piece.wP, Piece.bP}:
        if 'halfmove_clock' not in original:
            original['halfmove_clock'] = position.halfmove_clock
        position.halfmove_clock = 0

    # update both piece_map and mailbox
    map_key = f'piece_map {move.piece_type_number}'

    # The piece_map indexed by 'move.piece_type_number'
    # may have already been changed by the above
    # 'if move.is_capture:, if position.is_en_passant_capture' tests.
    # Hence the reason for the 'not in' test that follows.
    if map_key not in original:
        original[map_key] = position.piece_map[move.piece_type_number].copy()

    # Both the mailboxes indexed by the 'from_key/to_key' fields
    # may have already been changed by the above
    # 'if move.is_capture:, if position.is_en_passant_capture' tests.
    # Hence the reason for the two 'not in' tests that follows.

    from_key = f'mailbox {move.from_square}'
    if from_key not in original:
        original[from_key] = position.mailbox[move.from_square]

    to_key = f'mailbox {move.to_square}'
    if to_key not in original:
        original[to_key] = position.mailbox[move.to_square]

    position.piece_map[move.piece_type_number].remove(move.from_square)
    position.piece_map[move.piece_type_number].add(move.to_square)
    position.mailbox[move.from_square] = None
    position.mailbox[move.to_square] = move.piece_type_number

    # TODO Update Game

    if move.is_promotion:
        position.promote_pawn(move)

    if move.is_castling:
        original = position.move_rooks_for_castling(move,
                                                    original)

    if 'halfmove_clock' not in original:
        original['halfmove_clock'] = position.halfmove_clock
    original['halfmove'] = position.halfmove

    position.halfmove_clock += 1
    position.halfmove += 1

    castle_rights = position.castle_rights[move.rival_identity]

    if any(castle_rights):
        original = position.adjust_castling_rights(move, original)

    if position.en_passant_side != move.rival_identity:
        if 'en_passant_target' not in original:
            original['en_passant_target'] = position.en_passant_target

        position.en_passant_target = None

    original = position.board.update_position_bitboards(position.piece_map,
                                                        original)
    original = position.update_attack_bitboards(original)

    position.evaluate_king_check()

    return None, original


def evaluate_move(move: Move,
                  position: Position) -> MoveResult:
    """
    Evaluates if a move is fully legal
    """

    move_result, original = update_wakegame_position(position, move)
    # Undo all the changes made to the Position object
    undo_changes(position, original)

    if move_result is not None:
        # a move error occurred
        return move_result

    if position.king_in_check[position.rival_to_move]:
        # TODO
        # return position.make_illegal_move_result("own king in check")
        return position.make_illegal_move_result()

    return position.make_move_result()


def undo_changes(position: Position,
                 original: dict) -> None:
    """
    Revert the changes made to the Position object
    without the need to use 'copy.deepcopy'
    """
    for attribute, value in original.items():
        if attribute.startswith('piece_map'):
            # EG piece_map 7 {48, 49, 50, 51, 52, 53, 54, 55}
            [_, str_number] = attribute.split(" ", 1)
            position.piece_map[int(str_number)] = value

        elif attribute.startswith('mailbox'):
            # EG mailbox 47 None, mailbox 62 9
            [_, str_number] = attribute.split(" ", 1)
            position.mailbox[int(str_number)] = value

        elif attribute.endswith('_bb'):
            # EG player_P_bb 268496640
            setattr(position.board, attribute, value)

        elif attribute == 'position_history':
            # EG position_history 1
            position.position_history = position.position_history[:value]

        else:
            # EG player_pawn_attacks 171815403520, rival_to_move 1
            setattr(position, attribute, value)


"""
BUG FIX: Regarding 'all_knight_moves()' and 'has_knight_move()' above.

        for knight_from_square in current_knight_locations:
                for to_square in knight_squares:

simply produces the Cartesian product of these two lists
( Identical to: itertools.product(current_knight_locations, knight_squares)) )

However some of these numbers are NOT moves that KNIGHTS can make
e.g. (57, 47) WHICH IS b8-h6
This is not a Knight Move!

However, such moves were being considered 'valid' by 'all_knights_moves()'
(Likewise 'has_knight_move()' from which most of the code of
'all_knights_moves()' is copied from.)

That is, 'has_knight_move()' does NOT check that
an actual 'possible' KNIGHT move has been received.
It simply assumes it! This 'feature' appears to be present
in Wes Doyle's original code!

Solution: The difference between the FROM_SQUARE
          and the TO_SQUARE must be in this list:
          [6, 15, 17, 10, -6, -15, -17, -10]
          (Taken from 'generate_knight_attack_bb_from_square()'
          in wakes_attacks.py)
Also following the logic of 'generate_knight_attack_bb_from_square()'
IF THE FROM SQUARE IS Bx OR Ax, THE TO SQUARE CANNOT BE Gx OR Hx
IF THE FROM SQUARE IS Gx OR Hx, THE TO SQUARE CANNOT BE Ax OR Bx
"""


def is_viable_knight_move(pair: tuple[int]) -> bool:
    from_square, to_square = pair
    return ((from_square - to_square) in LEGAL_KNIGHT_DIFFERENCES and
            not ((from_square in FILES_AB and to_square in FILES_GH) or
                 from_square in FILES_GH and to_square in FILES_AB))


def is_viable_diagonal_move(pair: tuple[int]) -> bool:
    """
    Used for BISHOP and QUEEN moves
    Numbers 7 and 9 derived from the functions
    get_southeast_ray, get_northwest_ray, get_southwest_ray, get_northeast_ray
    in wake_rays.py
    """
    from_square, to_square = pair
    difference = abs(from_square - to_square)
    return (difference % 7 == 0) or (difference % 9 == 0)


def is_viable_vertical_move(pair: tuple[int]) -> bool:
    """
    Used for ROOK and QUEEN moves
    Vertical move: Are the files identical?
    """
    from_square, to_square = pair
    return SQUARE_MAP[from_square][0] == SQUARE_MAP[to_square][0]


def is_viable_horizontal_move(pair: tuple[int]) -> bool:
    """
    Used for ROOK and QUEEN moves
    Horizontal move: Are the ranks identical?
    """
    from_square, to_square = pair
    return SQUARE_MAP[from_square][1] == SQUARE_MAP[to_square][1]
