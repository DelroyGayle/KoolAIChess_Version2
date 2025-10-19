import numpy as np

from wake_core import (
    make_uint64_zero,
    set_bit,
    make_knight_attack_bbs,
    make_king_attack_bbs,
    make_player_pawn_attack_bbs,
    make_computer_pawn_attack_bbs,
    make_diag_attack_bbs,
    make_rook_attack_bbs,
    make_player_pawn_motion_bbs,
    make_computer_pawn_motion_bbs,
    make_queen_attack_bbs,
)
from wake_constants import Piece, Rival, File


class WakeBoard:

    def __init__(self):

        # PLAYER (white) piece groups
        self.player_R_bb = make_uint64_zero()
        self.player_K_bb = make_uint64_zero()
        self.player_B_bb = make_uint64_zero()
        self.player_P_bb = make_uint64_zero()
        self.player_N_bb = make_uint64_zero()
        self.player_Q_bb = make_uint64_zero()

        # COMPUTER (black) piece groups
        self.computer_R_bb = make_uint64_zero()
        self.computer_K_bb = make_uint64_zero()
        self.computer_B_bb = make_uint64_zero()
        self.computer_P_bb = make_uint64_zero()
        self.computer_N_bb = make_uint64_zero()
        self.computer_Q_bb = make_uint64_zero()

        self.init_pieces()

        # static bitboards
        self.knight_attack_bbs = make_knight_attack_bbs()
        self.bishop_attack_bbs = make_diag_attack_bbs()
        self.king_attack_bbs = make_king_attack_bbs()
        self.rook_attack_bbs = make_rook_attack_bbs()
        self.queen_attack_bbs = make_queen_attack_bbs()

        self.player_pawn_attack_bbs = make_player_pawn_attack_bbs()
        self.computer_pawn_attack_bbs = make_computer_pawn_attack_bbs()
        self.player_pawn_motion_bbs = make_player_pawn_motion_bbs()
        self.computer_pawn_motion_bbs = make_computer_pawn_motion_bbs()

    # -------------------------------------------------------------
    #  BITBOARD ACCESS: PIECE LOCATIONS
    # -------------------------------------------------------------

    @property
    def player_pieces_bb(self):
        return (
            self.player_P_bb
            | self.player_R_bb
            | self.player_N_bb
            | self.player_B_bb
            | self.player_K_bb
            | self.player_Q_bb
        )

    @property
    def computer_pieces_bb(self):
        return (
            self.computer_P_bb
            | self.computer_R_bb
            | self.computer_N_bb
            | self.computer_B_bb
            | self.computer_K_bb
            | self.computer_Q_bb
        )

    @property
    def empty_squares_bb(self):
        return ~self.occupied_squares_bb

    @property
    def occupied_squares_bb(self):
        return self.player_pieces_bb | self.computer_pieces_bb

    @property
    def player_pawn_east_attacks(self):
        # PLAYER (white) pawn east attacks are
        # north east (+9) AND NOT the A File
        return (self.player_P_bb << np.uint64(9)) & ~np.uint64(File.HEX_A)

    @property
    def player_pawn_west_attacks(self):
        # PLAYER (white) pawn west attacks are
        # north west (+7) AND NOT the H File
        return (self.player_P_bb << np.uint64(7)) & ~np.uint64(File.HEX_H)

    @property
    def player_pawn_attacks(self):
        return self.player_pawn_east_attacks | self.player_pawn_west_attacks

    @property
    def computer_pawn_east_attacks(self):
        # COMPUTER (black) pawn east attacks
        # are south east (-7) AND NOT the A File
        return (self.computer_P_bb >> np.uint64(7)) & ~np.uint64(File.HEX_A)

    @property
    def computer_pawn_west_attacks(self):
        # COMPUTER (black) pawn west attacks
        # are south west (-9) AND NOT the H File
        return (self.computer_P_bb >> np.uint64(9)) & ~np.uint64(File.HEX_H)

    @property
    def computer_pawn_attacks(self):
        return (self.computer_pawn_east_attacks |
                self.computer_pawn_west_attacks)

    # -------------------------------------------------------------
    #  BOARD SETUP
    # -------------------------------------------------------------

    def init_pieces(self):
        self._set_for_player()
        self._set_for_computer()

    def _set_for_player(self):
        for i in range(8, 16):
            self.player_P_bb |= set_bit(self.player_P_bb, i)
        self.player_R_bb |= set_bit(self.player_R_bb, 0)
        self.player_R_bb |= set_bit(self.player_R_bb, 7)
        self.player_N_bb |= set_bit(self.player_N_bb, 1)
        self.player_N_bb |= set_bit(self.player_N_bb, 6)
        self.player_B_bb |= set_bit(self.player_B_bb, 2)
        self.player_B_bb |= set_bit(self.player_B_bb, 5)
        self.player_Q_bb |= set_bit(self.player_Q_bb, 3)
        self.player_K_bb |= set_bit(self.player_K_bb, 4)

    def _set_for_computer(self):
        for bit in range(48, 56):
            self.computer_P_bb |= set_bit(self.computer_P_bb, bit)
        self.computer_R_bb |= set_bit(self.computer_R_bb, 63)
        self.computer_R_bb |= set_bit(self.computer_R_bb, 56)
        self.computer_N_bb |= set_bit(self.computer_N_bb, 57)
        self.computer_N_bb |= set_bit(self.computer_N_bb, 62)
        self.computer_B_bb |= set_bit(self.computer_B_bb, 61)
        self.computer_B_bb |= set_bit(self.computer_B_bb, 58)
        self.computer_Q_bb |= set_bit(self.computer_Q_bb, 59)
        self.computer_K_bb |= set_bit(self.computer_K_bb, 60)

    # -------------------------------------------------------------
    #  BOARD UPDATES
    # -------------------------------------------------------------

    def update_position_bitboards(self, piece_map):
        for key, val in piece_map.items():

            # PLAYER (White) Pieces
            if key == Piece.wP:
                self.player_P_bb = np.uint64(0)
                for bit in val:
                    self.player_P_bb |= (
                        set_bit(self.player_P_bb, np.uint64(bit)))

            elif key == Piece.wR:
                self.player_R_bb = np.uint64(0)
                for bit in val:
                    self.player_R_bb |= (
                        set_bit(self.player_R_bb, np.uint64(bit)))

            elif key == Piece.wN:
                self.player_N_bb = np.uint64(0)
                for bit in val:
                    self.player_N_bb |= (
                        set_bit(self.player_N_bb, np.uint64(bit)))

            elif key == Piece.wB:
                self.player_B_bb = np.uint64(0)
                for bit in val:
                    self.player_B_bb |= (
                        set_bit(self.player_B_bb, np.uint64(bit)))

            elif key == Piece.wQ:
                self.player_Q_bb = np.uint64(0)
                for bit in val:
                    self.player_Q_bb |= (
                        set_bit(self.player_Q_bb, np.uint64(bit)))

            elif key == Piece.wK:
                self.player_K_bb = np.uint64(0)
                for bit in val:
                    self.player_K_bb |= (
                        set_bit(self.player_K_bb, np.uint64(bit)))

            # COMPUTER (Black) Pieces
            if key == Piece.bP:
                self.computer_P_bb = np.uint64(0)
                for bit in val:
                    self.computer_P_bb |= (
                        set_bit(self.computer_P_bb, np.uint64(bit)))

            elif key == Piece.bR:
                self.computer_R_bb = np.uint64(0)
                for bit in val:
                    self.computer_R_bb |= (
                        set_bit(self.computer_R_bb, np.uint64(bit)))

            elif key == Piece.bN:
                self.computer_N_bb = np.uint64(0)
                for bit in val:
                    self.computer_N_bb |= (
                        set_bit(self.computer_N_bb, np.uint64(bit)))

            elif key == Piece.bB:
                self.computer_B_bb = np.uint64(0)
                for bit in val:
                    self.computer_B_bb |= (
                        set_bit(self.computer_B_bb, np.uint64(bit)))

            elif key == Piece.bQ:
                self.computer_Q_bb = np.uint64(0)
                for bit in val:
                    self.computer_Q_bb |= (
                        set_bit(self.computer_Q_bb, np.uint64(bit)))

            elif key == Piece.bK:
                self.computer_K_bb = np.uint64(0)
                for bit in val:
                    self.computer_K_bb |= (
                        set_bit(self.computer_K_bb, np.uint64(bit)))

    # -------------------------------------------------------------
    #  SLIDING PIECE MOVEMENT
    # -------------------------------------------------------------

    def get_bishop_attack_from(self, square):
        return self.bishop_attack_bbs[square]

    def get_rook_attack_from(self, square):
        return self.rook_attack_bbs[square]

    def get_queen_attack_from(self, square):
        return self.queen_attack_bbs[square]

    # -------------------------------------------------------------
    #  PAWN MOVEMENTS
    # -------------------------------------------------------------

    def get_pawn_attack_from(self, the_rival, square):
        if the_rival == Rival.PLAYER:
            return self.player_pawn_attack_bbs[square]
        return self.computer_pawn_attack_bbs[square]

    def get_pawn_movements_from(self, the_rival, square):
        if the_rival == Rival.PLAYER:
            return self.player_pawn_motion_bbs[square]
        return self.computer_pawn_motion_bbs[square]

    # -------------------------------------------------------------
    #  KNIGHT MOVEMENTS
    # -------------------------------------------------------------

    def get_knight_attack_from(self, square):
        return self.knight_attack_bbs[square]

    # -------------------------------------------------------------
    #  KING MOVEMENTS
    # -------------------------------------------------------------

    def get_king_attack_from(self, square):
        return self.king_attack_bbs[square]
