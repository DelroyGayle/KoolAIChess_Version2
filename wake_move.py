from wake_constants import Piece, Rival, FROM, TO


class Move:
    """
    Represents the motion of a piece from an origin square to a target square
    """

    def __init__(self, piece=None, squares=None):
        self.piece_type = piece
        if squares is not None:
            self.from_sq = squares[FROM]
            self.to_sq = squares[TO]
        else:
            self.from_sq = None
            self.to_sq = None
        self.is_capture = False
        self.is_en_passant = False
        self.is_castling = False
        self.is_promotion = False
        self.promote_to = None

    @property
    def rival_piece(self):
        if self.piece_type in Piece.PLAYER_PIECES:
            return Rival.PLAYER
        return Rival.COMPUTER


class MoveResult:
    """
    Represents the positional outcome of a move
    """

    def __init__(self):
        self.is_checkmate = False
        self.is_king_in_check = False
        self.is_stalemate = False
        self.is_draw_claim_allowed = False
        self.is_illegal_move = False
        self.fen = ""
