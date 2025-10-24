import numpy as np
import string


def get_binary_string(bitboard: np.uint64, board_squares: int = 64) -> str:
    """
    Returns the binary string representation of the provided bitboard
    :param bitboard: the bitboard to be represented
    :param board_squares: the number of squares in the bitboard
    :return: string representation of
             the provided n**2 (board_squares) bitboard
    """
    return format(bitboard, "b").zfill(board_squares)


def pprint_bb(bitboard: np.uint64, board_size: int = 8) -> None:
    """
    Pretty-prints the given bitboard as 8 x 8 chess board
    :param bitboard: the bitboard to pretty-print
    :param board_size: the length of the square board
    :return: None
    """
    bitboard = get_binary_string(bitboard)
    val = ""
    display_rank = board_size
    board = [bitboard[i:i + 8] for i in range(0, len(bitboard), board_size)]
    for i, row in enumerate(board):
        val += f"{display_rank} "
        display_rank -= 1
        for square in reversed(row):
            if int(square):
                val += " ▓"
                continue
            val += " ░"
        val += "\n"
    val += "  "
    for char in string.ascii_uppercase[:board_size]:
        val += f" {char}"
    print(val)
