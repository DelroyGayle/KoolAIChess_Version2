"""
Board region access functions for bitboards.

This module provides functions to access specific regions of the chess board
as bitboards, including ranks, files, and special regions like center squares,
flanks, and castling sides.
"""

import numpy as np

from wake_constants import Rank, File, DARK_SQUARES, LIGHT_SQUARES


# -------------------------------------------------------------
# RANK ACCESS
# -------------------------------------------------------------


def rank_8_bb() -> np.uint64:
    return np.uint64(Rank.HEX_8)


def rank_7_bb() -> np.uint64:
    return np.uint64(Rank.HEX_7)


def rank_6_bb() -> np.uint64:
    return np.uint64(Rank.HEX_6)


def rank_5_bb() -> np.uint64:
    return np.uint64(Rank.HEX_5)


def rank_4_bb() -> np.uint64:
    return np.uint64(Rank.HEX_4)


def rank_3_bb() -> np.uint64:
    return np.uint64(Rank.HEX_3)


def rank_2_bb() -> np.uint64:
    return np.uint64(Rank.HEX_2)


def rank_1_bb() -> np.uint64:
    return np.uint64(Rank.HEX_1)


# -------------------------------------------------------------
# FILE ACCESS
# -------------------------------------------------------------


def file_h_bb() -> np.uint64:
    return np.uint64(File.HEX_H)


def file_g_bb() -> np.uint64:
    return np.uint64(File.HEX_G)


def file_f_bb() -> np.uint64:
    return np.uint64(File.HEX_F)


def file_e_bb() -> np.uint64:
    return np.uint64(File.HEX_E)


def file_d_bb() -> np.uint64:
    return np.uint64(File.HEX_D)


def file_c_bb() -> np.uint64:
    return np.uint64(File.HEX_C)


def file_b_bb() -> np.uint64:
    return np.uint64(File.HEX_B)


def file_a_bb() -> np.uint64:
    return np.uint64(File.HEX_A)


# -------------------------------------------------------------
# SPECIAL REGIONS
# -------------------------------------------------------------


def dark_squares_bb() -> np.uint64:
    return np.uint64(DARK_SQUARES)


def light_squares_bb() -> np.uint64:
    return np.uint64(LIGHT_SQUARES)


def center_squares_bb():
    return (file_e_bb() | file_d_bb()) & (rank_4_bb() | rank_5_bb())


def flanks_bb():
    return file_a_bb() | file_h_bb()


def center_files_bb():
    return file_c_bb() | file_d_bb() | file_e_bb() | file_f_bb()


def kingside_bb():
    return file_e_bb() | file_f_bb() | file_g_bb() | file_h_bb()


def queenside_bb():
    return file_a_bb() | file_b_bb() | file_c_bb() | file_d_bb()
