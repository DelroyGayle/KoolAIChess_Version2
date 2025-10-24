"""
Core bitboard operations for the Wake chess engine.

This module provides fundamental bitboard operations including:
- Basic bitboard creation and manipulation
- Bit querying (forward/reverse scanning)
- Bit manipulation (set/clear operations)
- Utility functions for bitboard representation
"""

import numpy as np

from wake_constants import Rival, ALGEBRAIC_SQUARE_MAP
from extras import CustomException

# Constants
BOARD_SIZE = 8
BOARD_SQUARES = BOARD_SIZE**2


def make_uint64_zero() -> np.uint64:
    """
    :return: an np.uint64 zero
    """
    return np.uint64(0)


def get_bitboard_as_bytes(bitboard: np.uint64) -> bytes:
    """
    Returns the provided bitboard as Python bytes representation
    :param bitboard:
    :return:
    """
    return bitboard.tobytes()


def get_binary_string(bitboard: np.uint64, board_squares: int = 64) -> str:
    """
    Returns the binary string representation of the provided bitboard
    :param bitboard: the bitboard to be represented
    :param board_squares: the number of squares in the bitboard
    :return:
        string representation of the provided n**2 (board_squares) bitboard
    """
    return format(bitboard, "b").zfill(board_squares)


def get_squares_from_bitboard(bitboard: np.uint64) -> list:
    """
    Returns a list of square indices where bits are set in the bitboard
    :param bitboard: the bitboard to analyze
    :return: list of square indices (0-63) where bits are set
    """
    squares = []
    temp = np.uint64(bitboard)

    # Efficient bit manipulation to find all set bits
    index = 0
    while temp != 0:
        if temp & 1:
            squares.append(index)
        temp >>= 1
        index += 1

    return squares


# -------------------------------------------------------------
# BIT QUERYING
# -------------------------------------------------------------

def bitscan_forward(bitboard: np.uint64) -> int:
    """
    Returns the least significant one bit from the provided bitboard
    :param bitboard: bitboard to can
    :return: int significant one bit binary string index
    """
    i = 1
    while not (bitboard >> np.uint64(i)) % 2:
        i += 1
    return i


def bitscan_reverse(bitboard: np.uint64) -> np.uint64 | int:
    """
    @author Eugene Nalimov
    @return index (0..63) of most significant one bit
    :param bitboard: bitboard to scan
    :return: np.uint64 most significant one bit binary string index
    """

    def lookup_most_significant_1_bit(bit: np.uint64) -> int:
        if bit > np.uint64(127):
            return np.uint64(7)
        if bit > np.uint64(63):
            return np.uint64(6)
        if bit > np.uint64(31):
            return np.uint64(5)
        if bit > np.uint64(15):
            return np.uint64(4)
        if bit > np.uint64(7):
            return np.uint64(3)
        if bit > np.uint64(3):
            return np.uint64(2)
        if bit > np.uint64(1):
            return np.uint64(1)
        return np.uint64(0)

    if not bitboard:
        raise CustomException("Cannot reverse scan on empty bitboard")

    result = np.uint64(0)

    if bitboard > 0xFFFFFFFF:
        bitboard >>= np.uint(32)
        result = np.uint(32)

    if bitboard > 0xFFFF:
        bitboard >>= np.uint(16)
        result += np.uint(16)

    if bitboard > 0xFF:
        bitboard >>= np.uint(8)
        result += np.uint(8)

    return result + lookup_most_significant_1_bit(bitboard)


# -------------------------------------------------------------
# BIT MANIPULATION
# -------------------------------------------------------------


def set_bit(bitboard: np.uint64, bit: int) -> np.uint64:
    """
    Sets a bit in the provided unsigned 64-bit integer bitboard representation
    to 1

    :param bitboard: np.uint64 number
    :param bit: the binary index to turn on
    :return: a copy of the bitboard with the specified `bit` set to 1
    """
    return np.uint64(bitboard | np.uint64(1) << np.uint64(bit))


def clear_bit(bitboard: np.uint64, bit: int | np.uint64) -> np.uint64:
    """
    Sets a bit in the provided unsigned 64-bit integer bitboard representation
    to 0

    :param bitboard: np.uint64 number
    :param bit: the binary index to turn off
    :return: a copy of the bitboard with the specified `bit` set to 0
    """
    return bitboard & ~(np.uint64(1) << np.uint64(bit))

# -------------------------------------------------------------
# MISCELLANEOUS FUNCTIONS
# -------------------------------------------------------------


def switch_rival(rival: int) -> int:
    return (Rival.COMPUTER if rival == Rival.PLAYER
            else Rival.PLAYER)
