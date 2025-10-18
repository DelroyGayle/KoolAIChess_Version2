import numpy as np

from wake_constants import Rival, SQUARE_MAP


def generate_fen(position) -> str:
    """
    Generates an FEN given the provided Position
    """
    computer_pawn_bin = np.binary_repr(position.board.computer_P_bb, 64)
    computer_rook_bin = np.binary_repr(position.board.computer_R_bb, 64)
    computer_knight_bin = np.binary_repr(position.board.computer_N_bb, 64)
    computer_bishop_bin = np.binary_repr(position.board.computer_B_bb, 64)
    computer_queen_bin = np.binary_repr(position.board.computer_Q_bb, 64)
    computer_king_bin = np.binary_repr(position.board.computer_K_bb, 64)
    player_pawn_bin = np.binary_repr(position.board.player_P_bb, 64)
    player_rook_bin = np.binary_repr(position.board.player_R_bb, 64)
    player_knight_bin = np.binary_repr(position.board.player_N_bb, 64)
    player_bishop_bin = np.binary_repr(position.board.player_B_bb, 64)
    player_queen_bin = np.binary_repr(position.board.player_Q_bb, 64)
    player_king_bin = np.binary_repr(position.board.player_K_bb, 64)

    computer_pawn_squares = [
        i for i in range(len(computer_pawn_bin)) if int(computer_pawn_bin[i])
    ]
    computer_rook_squares = [
        i for i in range(len(computer_rook_bin)) if int(computer_rook_bin[i])
    ]
    computer_knight_squares = [
        i for i in range(len(computer_knight_bin))
        if int(computer_knight_bin[i])
    ]
    computer_bishop_squares = [
        i for i in range(len(computer_bishop_bin))
        if int(computer_bishop_bin[i])
    ]
    computer_queen_squares = [
        i for i in range(len(computer_queen_bin)) if int(computer_queen_bin[i])
    ]
    computer_king_square = [
        i for i in range(len(computer_king_bin)) if int(computer_king_bin[i])
    ]
    player_pawn_squares = [
        i for i in range(len(player_pawn_bin)) if int(player_pawn_bin[i])
    ]
    player_rook_squares = [
        i for i in range(len(player_rook_bin)) if int(player_rook_bin[i])
    ]
    player_knight_squares = [
        i for i in range(len(player_knight_bin)) if int(player_knight_bin[i])
    ]
    player_bishop_squares = [
        i for i in range(len(player_bishop_bin)) if int(player_bishop_bin[i])
    ]
    player_queen_squares = [
        i for i in range(len(player_queen_bin)) if int(player_queen_bin[i])
    ]
    player_king_square = [
        i for i in range(len(player_king_bin)) if int(player_king_bin[i])
    ]

    fen_dict = {i: None for i in range(64)}

    for s in computer_pawn_squares:
        fen_dict[s] = "p"
    for s in computer_rook_squares:
        fen_dict[s] = "r"
    for s in computer_knight_squares:
        fen_dict[s] = "n"
    for s in computer_bishop_squares:
        fen_dict[s] = "b"
    for s in computer_queen_squares:
        fen_dict[s] = "q"
    for s in computer_king_square:
        fen_dict[s] = "k"
    for s in player_pawn_squares:
        fen_dict[s] = "P"
    for s in player_rook_squares:
        fen_dict[s] = "R"
    for s in player_knight_squares:
        fen_dict[s] = "N"
    for s in player_bishop_squares:
        fen_dict[s] = "B"
    for s in player_queen_squares:
        fen_dict[s] = "Q"
    for s in player_king_square:
        fen_dict[s] = "K"

    fen = ""
    empty = 0
    row = ""

    for k, v in fen_dict.items():
        if not k % 8 and not k == 0:
            if empty:
                row += str(empty)
                empty = 0
            fen += row[::-1] + "/"
            row = ""

        if not v:
            empty += 1
            continue

        if empty:
            row += str(empty)
            empty = 0

        row += v
    fen += row[::-1]

    side_to_move_map = {Rival.PLAYER: "w", Rival.COMPUTER: "b"}

    fen += f" {side_to_move_map[position.rival_to_move]}"

    w_castle_king = position.castle_rights[Rival.PLAYER][0] is True
    w_castle_queen = position.castle_rights[Rival.PLAYER][1] is True
    b_castle_king = position.castle_rights[Rival.COMPUTER][0] is True
    b_castle_queen = position.castle_rights[Rival.COMPUTER][1] is True

    fen += " "

    if w_castle_king:
        fen += "K"
    if w_castle_queen:
        fen += "Q"
    if b_castle_king:
        fen += "k"
    if b_castle_queen:
        fen += "q"

    if (
        not w_castle_king
        and not w_castle_queen
        and not b_castle_king
        and not b_castle_queen
    ):
        fen += "-"

    fen += " "

    if position.en_passant_target:
        fen += str(SQUARE_MAP[position.en_passant_target])
    else:
        fen += "-"

    # Halfmove clock
    fen += f" {str(position.halfmove_clock)}"

    # Full-move Number
    fen += f" {str(position.halfmove // 2)}"

    return fen
