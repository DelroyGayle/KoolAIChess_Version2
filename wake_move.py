from wake_constants import Piece, Rival, FROM, TO


class Move:
    """
    Represents the motion of a piece from an origin square to a target square
    """

    def __init__(self, piece_type_number=None, squares=None):
        self.piece_type_number = piece_type_number
        if squares is not None:
            self.from_square = squares[FROM]
            self.to_square = squares[TO]
        else:
            self.from_square = None
            self.to_square = None
        self.is_capture = False
        self.is_en_passant = False
        self.is_castling = False
        self.is_promotion = False
        self.promote_to = None

    @property
    def rival_identity(self):
        if self.piece_type_number in Piece.PLAYER_PIECES:
            return Rival.PLAYER
        return Rival.COMPUTER


class MoveResult:
    """
    Represents the positional outcome of a move
    """

    def __init__(self):
        self.is_king_in_check = False
        self.is_checkmate = False
        self.is_stalemate = False
        self.is_draw_claim_allowed = False
        self.is_illegal_move = False
        self.fen = ""
