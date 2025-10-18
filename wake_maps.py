"""
Static attack map builders for chess pieces.

This module provides functions to build static lookup tables (dictionaries)
that map square indices to precomputed attack bitboards for all piece types.
This allows for O(1) attack pattern lookup during gameplay.
"""

from wake_constants import Square
from wake_core import BOARD_SQUARES
from wake_attacks import (
    generate_knight_attack_bb_from_square,
    generate_rank_attack_bb_from_square,
    generate_file_attack_bb_from_square,
    generate_diag_attack_bb_from_square,
    generate_king_attack_bb_from_square,
    generate_queen_attack_bb_from_square,
    generate_rook_attack_bb_from_square,
    generate_player_pawn_attack_bb_from_square,
    generate_computer_pawn_attack_bb_from_square,
    generate_player_pawn_motion_bb_from_square,
    generate_computer_pawn_motion_bb_from_square,
)


def make_knight_attack_bbs() -> dict:
    """
    Builds a Python dictionary of { square_index: bitboard }
    to represent static knight attack patterns

    :return: dict {square: knight attack bitboard} static square
                 -> bitboard mapping
    """
    knight_attack_map = {}
    for i in range(BOARD_SQUARES):
        knight_attack_map[i] = generate_knight_attack_bb_from_square(i)
    return knight_attack_map


def make_rank_attack_bbs() -> dict:
    """
    Builds a Python dictionary of { square_index: bitboard }
    to represent static rank attack patterns

    :return: dict {square: rank attack bitboard} static square
                 -> bitboard mapping
    """
    rank_attack_map = {}
    for i in range(BOARD_SQUARES):
        rank_attack_map[i] = generate_rank_attack_bb_from_square(i)
    return rank_attack_map


def make_file_attack_bbs() -> dict:
    """
    Builds a Python dictionary of { square_index: bitboard }
    to represent static file attack patterns

    :return: dict {square: file attack bitboard} static square
                  -> bitboard mapping
    """
    file_attack_map = {}
    for i in range(BOARD_SQUARES):
        file_attack_map[i] = generate_file_attack_bb_from_square(i)
    return file_attack_map


def make_diag_attack_bbs() -> dict:
    """
    Builds a Python dictionary of { square_index: bitboard }
    to represent static diagonal attack patterns

    :return: dict {square: diagonal attack bitboard} static square
                 -> bitboard mapping
    """
    diag_attack_map = {}
    for i in range(BOARD_SQUARES):
        diag_attack_map[i] = generate_diag_attack_bb_from_square(i)
    return diag_attack_map


def make_king_attack_bbs() -> dict:
    """
    Builds a Python dictionary of { square_index: bitboard }
    to represent static king attack patterns

    :return: dict {square: king attack bitboard} static square
                 -> bitboard mapping
    """
    king_attack_map = {}
    for i in range(BOARD_SQUARES):
        king_attack_map[i] = generate_king_attack_bb_from_square(i)
    return king_attack_map


def make_queen_attack_bbs() -> dict:
    """
    Builds a Python dictionary of { square_index: bitboard }
    to represent static queen attack patterns

    :return: dict {square: queen attack bitboard} static square
                 -> bitboard mapping
    """
    queen_attack_map = {}
    for i in range(BOARD_SQUARES):
        queen_attack_map[i] = generate_queen_attack_bb_from_square(i)
    return queen_attack_map


def make_rook_attack_bbs() -> dict:
    """
    Builds a Python dictionary of { square_index: bitboard }
    to represent static rook attack patterns

    :return: dict {square: rook attack bitboard} static square
                 -> bitboard mapping
    """
    rook_attack_map = {}
    for i in range(BOARD_SQUARES):
        rook_attack_map[i] = generate_rook_attack_bb_from_square(i)
    return rook_attack_map


def make_player_pawn_attack_bbs() -> dict:
    """
    Builds a Python dictionary of { square_index: bitboard }
    to represent static PLAYER (white) pawn attack patterns

    :return: dict {square: PLAYER pawn attack bitboard} static square
                 -> bitboard mapping
    """
    player_pawn_attack_map = {}
    for i in range(Square.A2, Square.A8):
        player_pawn_attack_map[i] = (
            generate_player_pawn_attack_bb_from_square(i))
    return player_pawn_attack_map


def make_computer_pawn_attack_bbs() -> dict:
    """
    Builds a Python dictionary of { square_index: bitboard }
    to represent static COMPUTER (black) pawn attack patterns

    :return: dict {square: COMPUTER pawn attack bitboard} static square
                 -> bitboard mapping
    """
    computer_pawn_attack_map = {}
    for i in range(Square.A2, Square.A8):
        computer_pawn_attack_map[i] = (
            generate_computer_pawn_attack_bb_from_square(i))
    return computer_pawn_attack_map


def make_player_pawn_motion_bbs() -> dict:
    """
    Builds a Python dictionary of { square_index: bitboard }
    to represent static PLAYER (white) pawn motion patterns

    :return: dict {square: PLAYER pawn motion bitboard} static square
                 -> bitboard mapping
    """
    player_pawn_motion_map = {}
    for i in range(Square.A2, Square.A8):
        player_pawn_motion_map[i] = (
            generate_player_pawn_motion_bb_from_square(i))
    return player_pawn_motion_map


def make_computer_pawn_motion_bbs() -> dict:
    """
    Builds a Python dictionary of { square_index: bitboard }
    to represent static COMPUTER (black) pawn motion patterns

    :return: dict {square: COMPUTER pawn motion bitboard} static square
                 -> bitboard mapping
    """
    computer_pawn_motion_map = {}
    for i in range(Square.A2, Square.A8):
        computer_pawn_motion_map[i] = (
            generate_computer_pawn_motion_bb_from_square(i))
    return computer_pawn_motion_map
