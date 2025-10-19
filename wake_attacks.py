"""
Attack pattern generation functions for chess pieces.

This module provides functions to generate attack patterns for all piece types
on an otherwise empty board, including sliding pieces (rook, bishop, queen)
and non-sliding pieces (king, knight, pawn).
"""

import numpy as np

from wake_constants import File, ONE_BIT, Rank
from wake_core import make_uint64_zero, clear_bit, set_bit
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


# -------------------------------------------------------------
#  ATTACK PATTERNS: KNIGHT
# -------------------------------------------------------------


def generate_knight_attack_bb_from_square(from_square: int) -> np.uint64:
    """
    Generates a static bitboard of squares attacked by a knight
    from the provided `square`

    :param from_square: square index of the knight from which
                        to generate attack squares bitboard

    :return: np.uint64 bitboard of attacked squares by a knight
             on the provided `square`
    """
    attack_bb = make_uint64_zero()
    for i in [6, 15, 17, 10, -6, -15, -17, -10]:
        to_square = from_square + i
        if not 0 <= to_square < 64:
            continue

        attack_bb |= set_bit(attack_bb, to_square)
        # Mask of wrapping
        if from_square in (File.B | File.A):
            attack_bb &= ~(np.uint64(File.HEX_G | File.HEX_H))
        if from_square in (File.G | File.H):
            attack_bb &= ~(np.uint64(File.HEX_A | File.HEX_B))
    return attack_bb


# -------------------------------------------------------------
#  ATTACK PATTERNS: ROOK
# -------------------------------------------------------------


def generate_rank_attack_bb_from_square(square: int) -> np.uint64:
    """
    Generates rank attacks from the provided square
    on an otherwise empty bitboard

    :param square: starting square from which to generate rank attacks

    :return: np.uint64 rank attacks bitboard from the provided square
    """
    attack_bb = make_uint64_zero()
    attack_bb = get_north_ray(attack_bb, square)
    attack_bb = get_south_ray(attack_bb, square)
    attack_bb = clear_bit(attack_bb, square)
    return attack_bb


def generate_file_attack_bb_from_square(square: int) -> np.uint64:
    """
    Generates file attacks from the provided square
    on an otherwise empty bitboard

    :param square: starting square from which to generate file attacks

    :return: np.uint64 file attacks bitboard from the provided square
    """
    attack_bb = make_uint64_zero()
    attack_bb = get_east_ray(attack_bb, square)
    attack_bb = get_west_ray(attack_bb, square)
    attack_bb = clear_bit(attack_bb, square)
    return attack_bb


def generate_rook_attack_bb_from_square(square: int) -> np.uint64:
    """
    Generates rook attacks from the provided square
    on an otherwise empty bitboard

    :param square: starting square from which to generate rook attacks

    :return: np.uint64 rook attacks bitboard from the provided square
    """
    return generate_file_attack_bb_from_square(
        square
    ) | generate_rank_attack_bb_from_square(square)


# -------------------------------------------------------------
#  ATTACK PATTERNS: BISHOP
# -------------------------------------------------------------


def generate_diag_attack_bb_from_square(from_square: int) -> np.uint64:
    """
    Generates all diagonal attacks from the provided square
    on an otherwise empty bitboard

    :param from_square: starting square from which
                        to generate diagonal attacks

    :return: np.uint64 diagonal attacks bitboard from the provided square
    """
    attack_bb = make_uint64_zero()
    original_square = from_square

    attack_bb = get_northeast_ray(attack_bb, from_square)
    attack_bb = get_southwest_ray(attack_bb, from_square)
    attack_bb = get_northwest_ray(attack_bb, from_square)
    attack_bb = get_southeast_ray(attack_bb, from_square)

    attack_bb = clear_bit(attack_bb, original_square)

    return attack_bb


# -------------------------------------------------------------
#  ATTACK PATTERNS: QUEEN
# -------------------------------------------------------------


def generate_queen_attack_bb_from_square(from_square: int) -> np.uint64:
    """
    Returns the queen attack bitboard on an otherwise empty board
    from the provided square

    :param from_square: starting square from which to generate queen attacks

    :return: np.uint64 bitboard representation of queen attacks
             on an otherwise empty board
    """
    return (
        generate_diag_attack_bb_from_square(from_square)
        | generate_file_attack_bb_from_square(from_square)
        | generate_rank_attack_bb_from_square(from_square)
    )


# -------------------------------------------------------------
#  ATTACK PATTERNS: KING
# -------------------------------------------------------------


def generate_king_attack_bb_from_square(from_square: int) -> np.uint64:
    """
    Generates a static bitboard of squares attacked by a king
    from the provided `square`

    :param from_square: square index of the king from which
                        to generate attack squares bitboard

    :return: np.uint64 bitboard of attacked squares by a king
             on the provided `square`
    """
    attack_bb = make_uint64_zero()
    for i in [-1, -7, -8, -9, 1, 7, 8, 9]:
        to_square = from_square + i
        if not 0 <= to_square < 64:
            continue
        attack_bb |= ONE_BIT << np.uint64(to_square)
    # Mask of wrapping
    if from_square in File.A:
        attack_bb &= ~np.uint64(File.HEX_H)
    if from_square in File.H:
        attack_bb &= ~np.uint64(File.HEX_A)
    return attack_bb


# -------------------------------------------------------------
#  ATTACK PATTERNS: PAWN
# -------------------------------------------------------------


def generate_player_pawn_attack_bb_from_square(from_square: int) -> np.uint64:
    """
    Generates a static bitboard of squares attacked by
    rival PLAYER (white) pawn from the provided `square`

    :param from_square: square index of the PLAYER pawn from which
                        to generate attack squares bitboard

    :return: np.uint64 bitboard of attacked squares
             by a PLAYER pawn on the provided `square`
    """
    attack_bb = make_uint64_zero()
    for i in [7, 9]:
        to_square = from_square + i
        if not 0 <= to_square < 64:
            continue
        attack_bb |= ONE_BIT << np.uint64(to_square)
    # Mask of wrapping
    if from_square in File.A:
        attack_bb &= ~np.uint64(File.HEX_H)
    if from_square in File.H:
        attack_bb &= ~np.uint64(File.HEX_A)
    return attack_bb


def generate_computer_pawn_attack_bb_from_square(
    from_square: int
) -> np.uint64:
    """
    Generates a static bitboard of squares attacked by
    rival COMPUTER (black) pawn from the provided `square`

    :param from_square: square index of the COMPUTER pawn
                        from which to generate attack squares bitboard

    :return: np.uint64 bitboard of attacked squares
             by a COMPUTER pawn on the provided `square`
    """
    attack_bb = make_uint64_zero()
    for i in [-7, -9]:
        to_square = from_square + i
        if not 0 <= to_square < 64:
            continue
        attack_bb |= ONE_BIT << np.uint64(to_square)
    # Mask of wrapping
    if from_square in File.A:
        attack_bb &= ~np.uint64(File.HEX_H)
    if from_square in File.H:
        attack_bb &= ~np.uint64(File.HEX_A)
    return attack_bb


def generate_player_pawn_motion_bb_from_square(from_square: int) -> np.uint64:
    """
    Returns the rival PLAYER (white) pawn motion bitboard
    on an otherwise empty board from the provided square

    :param from_square: starting square
                        from which to generate the PLAYER pawn motions

    :return: np.uint64 bitboard representation of the PLAYER pawn motions
             on an otherwise empty board
    """
    motion_bb = make_uint64_zero()

    # Check boundary - white pawns cannot move beyond the 8th rank
    if from_square >= 56:  # 8th rank
        return motion_bb

    motion_bb |= ONE_BIT << np.uint64(from_square + 8)
    if from_square in Rank.X2:
        motion_bb |= ONE_BIT << np.uint64(from_square + 16)
    return motion_bb


def generate_computer_pawn_motion_bb_from_square(
    from_square: int
) -> np.uint64:
    """
    Returns the rival COMPUTER (black) pawn motion bitboard
    on an otherwise empty board from the provided square

    :param from_square: starting square from which
                        to generate COMPUTER pawn motions

    :return: np.uint64 bitboard representation of COMPUTER pawn motions
             on an otherwise empty board
    """
    motion_bb = make_uint64_zero()

    # Check boundary - black pawns cannot move beyond the 1st rank
    if from_square < 8:  # 1st rank
        return motion_bb

    motion_bb |= ONE_BIT << np.uint64(from_square - 8)
    if from_square in Rank.X7:
        motion_bb |= ONE_BIT << np.uint64(from_square - 16)
    return motion_bb
