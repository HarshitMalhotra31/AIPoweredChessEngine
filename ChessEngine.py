class CastlingRights:
    def __init__(self, wks, wqs, bks, bqs):
        self.wks = wks
        self.wqs = wqs
        self.bks = bks
        self.bqs = bqs


class GameState:
    def __init__(self):
        self.board = [
            ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
            ["bP"] * 8,
            ["--"] * 8,
            ["--"] * 8,
            ["--"] * 8,
            ["--"] * 8,
            ["wP"] * 8,
            ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"]
        ]
        self.whiteToMove = True
        self.moveLog = []
        self.redoLog = []
        self.whiteKingLocation = (7, 4)
        self.blackKingLocation = (0, 4)
        self.enPassantPossible = ()  # tuple (row,col) or empty
        self.currentCastlingRights = CastlingRights(True, True, True, True)

    # ---------------------- Move Class ----------------------
    class Move:
        ranksToRows = {"1": 7, "2": 6, "3": 5, "4": 4,
                       "5": 3, "6": 2, "7": 1, "8": 0}
        rowsToRanks = {v: k for k, v in ranksToRows.items()}
        filesToCols = {"a": 0, "b": 1, "c": 2, "d": 3,
                       "e": 4, "f": 5, "g": 6, "h": 7}
        colsToFiles = {v: k for k, v in filesToCols.items()}

        def __init__(self, startSq, endSq, board, isEnPassantMove=False, isCastleMove=False, promotionChoice=None):
            self.startRow, self.startCol = startSq
            self.endRow, self.endCol = endSq
            self.pieceMoved = board[self.startRow][self.startCol]
            self.pieceCaptured = board[self.endRow][self.endCol]

            # Special moves
            self.isEnPassantMove = isEnPassantMove
            if self.isEnPassantMove:
                # captured pawn is behind the end square
                self.pieceCaptured = 'bP' if self.pieceMoved[0] == 'w' else 'wP'
            self.isCastleMove = isCastleMove
            self.promotionChoice = promotionChoice
            # saved castling rights for undo
            self.castlingRightsBefore = None

        def getChessNotation(self):
            return self.getRankFile(self.startRow, self.startCol) + self.getRankFile(self.endRow, self.endCol)

        def getRankFile(self, r, c):
            return self.colsToFiles[c] + self.rowsToRanks[r]

        def __eq__(self, other):
            if not isinstance(other, GameState.Move):
                return False
            return (self.startRow == other.startRow and
                    self.startCol == other.startCol and
                    self.endRow == other.endRow and
                    self.endCol == other.endCol and
                    self.pieceMoved == other.pieceMoved and
                    self.pieceCaptured == other.pieceCaptured)

    # ---------------------- Move Logic ----------------------
    def make_move(self, move):
        # move pieces on board
        self.board[move.endRow][move.endCol] = move.pieceMoved
        self.board[move.startRow][move.startCol] = "--"

        # Pawn promotion (default to Queen)
        if move.pieceMoved[1] == "P" and (move.endRow == 0 or move.endRow == 7):
            if move.promotionChoice is None:
                self.board[move.endRow][move.endCol] = move.pieceMoved[0] + "Q"
            else:
                self.board[move.endRow][move.endCol] = move.pieceMoved[0] + move.promotionChoice

        # En passant capture removal
        if move.isEnPassantMove:
            # captured pawn is on the start row's file, not the end square
            if move.pieceMoved[0] == 'w':
                self.board[move.endRow + 1][move.endCol] = "--"
            else:
                self.board[move.endRow - 1][move.endCol] = "--"

        # Update king location
        if move.pieceMoved == "wK":
            self.whiteKingLocation = (move.endRow, move.endCol)
        elif move.pieceMoved == "bK":
            self.blackKingLocation = (move.endRow, move.endCol)

        # Castling: move the rook accordingly
        if move.isCastleMove:
            # king-side
            if move.endCol - move.startCol == 2:
                # rook comes from column 7 to endCol-1
                self.board[move.endRow][move.endCol - 1] = self.board[move.endRow][7]
                self.board[move.endRow][7] = "--"
            else:
                # queen-side rook from column 0 to endCol+1
                self.board[move.endRow][move.endCol + 1] = self.board[move.endRow][0]
                self.board[move.endRow][0] = "--"

        # Store castling rights before updating for undo
        move.castlingRightsBefore = CastlingRights(
            self.currentCastlingRights.wks,
            self.currentCastlingRights.wqs,
            self.currentCastlingRights.bks,
            self.currentCastlingRights.bqs
        )

        # Update castling rights after the move
        self.update_castle_rights(move)

        # Update en passant possibility
        self.enPassantPossible = ()
        if move.pieceMoved[1] == "P" and abs(move.startRow - move.endRow) == 2:
            # square behind the pawn where en-passant capture is possible
            self.enPassantPossible = ((move.startRow + move.endRow) // 2, move.startCol)

        # finalize move logs and toggle turn
        self.moveLog.append(move)
        self.redoLog.clear()
        self.whiteToMove = not self.whiteToMove

    def update_castle_rights(self, move):
        """Update castling rights when king or rooks move or are captured"""
        # If king moves, lose both rights for that color
        if move.pieceMoved == "wK":
            self.currentCastlingRights.wks = False
            self.currentCastlingRights.wqs = False
        elif move.pieceMoved == "bK":
            self.currentCastlingRights.bks = False
            self.currentCastlingRights.bqs = False

        # If rook moves from original squares, lose corresponding right
        if move.pieceMoved == "wR":
            if move.startRow == 7 and move.startCol == 0:
                self.currentCastlingRights.wqs = False
            elif move.startRow == 7 and move.startCol == 7:
                self.currentCastlingRights.wks = False
        elif move.pieceMoved == "bR":
            if move.startRow == 0 and move.startCol == 0:
                self.currentCastlingRights.bqs = False
            elif move.startRow == 0 and move.startCol == 7:
                self.currentCastlingRights.bks = False

        # If rook was captured on its starting square, update rights
        if move.pieceCaptured == "wR":
            if move.endRow == 7 and move.endCol == 0:
                self.currentCastlingRights.wqs = False
            elif move.endRow == 7 and move.endCol == 7:
                self.currentCastlingRights.wks = False
        elif move.pieceCaptured == "bR":
            if move.endRow == 0 and move.endCol == 0:
                self.currentCastlingRights.bqs = False
            elif move.endRow == 0 and move.endCol == 7:
                self.currentCastlingRights.bks = False

    def undo_move(self):
        if not self.moveLog:
            return
        move = self.moveLog.pop()
        # put pieces back
        self.board[move.startRow][move.startCol] = move.pieceMoved
        self.board[move.endRow][move.endCol] = move.pieceCaptured

        # undo king location
        if move.pieceMoved == "wK":
            self.whiteKingLocation = (move.startRow, move.startCol)
        elif move.pieceMoved == "bK":
            self.blackKingLocation = (move.startRow, move.startCol)

        # undo en passant capture restoration
        if move.isEnPassantMove:
            if move.pieceMoved[0] == 'w':
                # white had captured black pawn that was on endRow+1 originally
                self.board[move.endRow + 1][move.endCol] = "bP"
            else:
                self.board[move.endRow - 1][move.endCol] = "wP"
            # clear the end square (already set to pieceCaptured above as "--")
            self.board[move.endRow][move.endCol] = "--"

        # undo castling: move rook back
        if move.isCastleMove:
            if move.endCol - move.startCol == 2:  # king-side
                self.board[move.endRow][7] = self.board[move.endRow][move.endCol - 1]
                self.board[move.endRow][move.endCol - 1] = "--"
            else:  # queen-side
                self.board[move.endRow][0] = self.board[move.endRow][move.endCol + 1]
                self.board[move.endRow][move.endCol + 1] = "--"

        # restore castling rights
        if hasattr(move, 'castlingRightsBefore') and move.castlingRightsBefore is not None:
            self.currentCastlingRights = move.castlingRightsBefore

        # restore enPassantPossible (best-effort: recompute from previous move if exists)
        self.enPassantPossible = ()
        if self.moveLog:
            last = self.moveLog[-1]
            if last.pieceMoved[1] == "P" and abs(last.startRow - last.endRow) == 2:
                self.enPassantPossible = ((last.startRow + last.endRow) // 2, last.startCol)

        self.whiteToMove = not self.whiteToMove
        self.redoLog.append(move)

    def redo_move(self):
        if self.redoLog:
            move = self.redoLog.pop()
            self.make_move(move)

    # ---------------------- Check/Checkmate/Stalemate ----------------------
    def get_game_status(self):
        """Returns the current game status: 'ongoing', 'check', 'checkmate', or 'stalemate'"""
        valid_moves = self.get_valid_moves()
        in_check = self.in_check_for_current_player()

        if not valid_moves:
            if in_check:
                return "checkmate"
            else:
                return "stalemate"
        elif in_check:
            return "check"
        else:
            return "ongoing"

    def checkmate_or_stalemate(self):
        """Legacy method - use get_game_status() instead"""
        status = self.get_game_status()
        if status in ["checkmate", "stalemate"]:
            return status
        return None

    # ---------------------- Move Generation ----------------------
    def get_valid_moves(self):
        """
        Generate all legal moves by simulating pseudo-legal moves for the side to move
        and filtering out moves that leave the mover's king in check.
        """
        moves = self.get_all_possible_moves()
        validMoves = []
        side_moving_is_white = self.whiteToMove
        for move in moves:
            self.make_move(move)
            # After make_move, self.whiteToMove is toggled; check whether the side that just moved
            # (side_moving_is_white) has its king attacked now.
            if side_moving_is_white:
                king_in_check_after = self.square_under_attack(*self.whiteKingLocation, by_color='b')
            else:
                king_in_check_after = self.square_under_attack(*self.blackKingLocation, by_color='w')

            if not king_in_check_after:
                validMoves.append(move)
            self.undo_move()
        return validMoves

    def in_check_for_current_player(self):
        """Check if the current player's king is in check"""
        if self.whiteToMove:
            return self.square_under_attack(*self.whiteKingLocation, by_color='b')
        else:
            return self.square_under_attack(*self.blackKingLocation, by_color='w')

    def can_give_check(self):
        """Check if current player can give check to opponent (in current position)"""
        if self.whiteToMove:
            return self.square_under_attack(*self.blackKingLocation, by_color='w')
        else:
            return self.square_under_attack(*self.whiteKingLocation, by_color='b')

    def would_give_check(self, move):
        """Check if a specific move would put the opponent in check"""
        # Simulate the move
        self.make_move(move)
        # After make_move the player to move is the opponent; in_check_for_current_player
        # therefore tells us whether the opponent is in check (i.e., whether the move gave check).
        gives_check = self.in_check_for_current_player()
        # undo the move and return
        self.undo_move()
        return gives_check

    def square_under_attack(self, r, c, by_color=None):
        """Check if a square is under attack by any piece of by_color (if specified)"""
        colors_to_check = [by_color] if by_color else ['w', 'b']

        for color in colors_to_check:
            for row in range(8):
                for col in range(8):
                    piece = self.board[row][col]
                    if piece == "--" or piece[0] != color:
                        continue
                    moves = []
                    ptype = piece[1]
                    if ptype == 'P':
                        # generate attack pseudo-moves (not forward moves)
                        self.get_pawn_attacks(row, col, moves, color)
                    elif ptype == 'R':
                        self._slide_moves(row, col, [(-1, 0), (1, 0), (0, -1), (0, 1)], moves, color)
                    elif ptype == 'B':
                        self._slide_moves(row, col, [(-1, -1), (-1, 1), (1, -1), (1, 1)], moves, color)
                    elif ptype == 'Q':
                        self._slide_moves(row, col, [(-1, 0), (1, 0), (0, -1), (0, 1),
                                                     (-1, -1), (-1, 1), (1, -1), (1, 1)], moves, color)
                    elif ptype == 'N':
                        self.get_knight_moves(row, col, moves, color)
                    elif ptype == 'K':
                        # king attacks adjacent squares
                        self.get_king_moves_simple(row, col, moves, color)
                    for m in moves:
                        if m.endRow == r and m.endCol == c:
                            return True
        return False

    def get_all_possible_moves(self):
        """Generate all pseudo-legal moves (ignores leaving king in check) for side to move"""
        moves = []
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece == "--":
                    continue
                if (self.whiteToMove and piece[0] != "w") or (not self.whiteToMove and piece[0] != "b"):
                    continue
                if piece[1] == "P":
                    self.get_pawn_moves(r, c, moves)
                elif piece[1] == "R":
                    self.get_rook_moves(r, c, moves)
                elif piece[1] == "N":
                    self.get_knight_moves(r, c, moves)
                elif piece[1] == "B":
                    self.get_bishop_moves(r, c, moves)
                elif piece[1] == "Q":
                    self.get_queen_moves(r, c, moves)
                elif piece[1] == "K":
                    self.get_king_moves(r, c, moves)
        return moves

    # ---------------------- Piece Move Generators ----------------------
    def get_pawn_moves(self, r, c, moves):
        direction = -1 if self.whiteToMove else 1
        startRow = 6 if self.whiteToMove else 1
        # forward one
        if 0 <= r + direction < 8 and self.board[r + direction][c] == "--":
            if r + direction == 0 or r + direction == 7:  # promotion
                self.add_promotion_moves(r, c, r + direction, c, moves)
            else:
                moves.append(self.Move((r, c), (r + direction, c), self.board))
            # double step
            if r == startRow and self.board[r + 2 * direction][c] == "--":
                moves.append(self.Move((r, c), (r + 2 * direction, c), self.board))
        # captures (including en passant)
        for dc in [-1, 1]:
            endR, endC = r + direction, c + dc
            if 0 <= endR < 8 and 0 <= endC < 8:
                target = self.board[endR][endC]
                if target != "--" and target[0] != ("w" if self.whiteToMove else "b"):
                    if endR == 0 or endR == 7:
                        self.add_promotion_moves(r, c, endR, endC, moves)
                    else:
                        moves.append(self.Move((r, c), (endR, endC), self.board))
                # en passant capture check
                elif self.enPassantPossible and (endR, endC) == self.enPassantPossible:
                    moves.append(self.Move((r, c), (endR, endC), self.board, isEnPassantMove=True))

    def add_promotion_moves(self, r, c, endR, endC, moves):
        promotion_pieces = ['Q', 'R', 'B', 'N']
        for piece in promotion_pieces:
            moves.append(self.Move((r, c), (endR, endC), self.board, promotionChoice=piece))

    def get_pawn_attacks(self, r, c, moves, color):
        # only add diagonal attack moves (used for square_under_attack)
        direction = -1 if color == 'w' else 1
        for dc in [-1, 1]:
            endR, endC = r + direction, c + dc
            if 0 <= endR < 8 and 0 <= endC < 8:
                moves.append(self.Move((r, c), (endR, endC), self.board))

    def get_knight_moves(self, r, c, moves, color=None):
        knightMoves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
        allyColor = color if color is not None else ('w' if self.whiteToMove else 'b')
        for dr, dc in knightMoves:
            endR, endC = r + dr, c + dc
            if 0 <= endR < 8 and 0 <= endC < 8:
                endPiece = self.board[endR][endC]
                if endPiece == "--" or endPiece[0] != allyColor:
                    moves.append(self.Move((r, c), (endR, endC), self.board))

    def _slide_moves(self, r, c, directions, moves, color=None):
        allyColor = color if color is not None else ('w' if self.whiteToMove else 'b')
        for dr, dc in directions:
            for i in range(1, 8):
                endR, endC = r + dr * i, c + dc * i
                if 0 <= endR < 8 and 0 <= endC < 8:
                    endPiece = self.board[endR][endC]
                    if endPiece == "--":
                        moves.append(self.Move((r, c), (endR, endC), self.board))
                    elif endPiece[0] != allyColor:
                        moves.append(self.Move((r, c), (endR, endC), self.board))
                        break
                    else:
                        break
                else:
                    break

    def get_rook_moves(self, r, c, moves):
        self._slide_moves(r, c, [(-1, 0), (1, 0), (0, -1), (0, 1)], moves)

    def get_bishop_moves(self, r, c, moves):
        self._slide_moves(r, c, [(-1, -1), (-1, 1), (1, -1), (1, 1)], moves)

    def get_queen_moves(self, r, c, moves):
        self._slide_moves(r, c, [(-1, 0), (1, 0), (0, -1), (0, 1),
                                 (-1, -1), (-1, 1), (1, -1), (1, 1)], moves)

    def get_king_moves(self, r, c, moves):
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        allyColor = 'w' if self.whiteToMove else 'b'
        for dr, dc in directions:
            endR, endC = r + dr, c + dc
            if 0 <= endR < 8 and 0 <= endC < 8:
                endPiece = self.board[endR][endC]
                if endPiece == "--" or endPiece[0] != allyColor:
                    moves.append(self.Move((r, c), (endR, endC), self.board))
        # castling
        self.get_castle_moves(r, c, moves, allyColor)

    def get_king_moves_simple(self, r, c, moves, color):
        # used for square attack detection (does not check castling or square occupancy by allies)
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dr, dc in directions:
            endR, endC = r + dr, c + dc
            if 0 <= endR < 8 and 0 <= endC < 8:
                moves.append(self.Move((r, c), (endR, endC), self.board))

    def get_castle_moves(self, r, c, moves, allyColor):
        # Can't castle if king is currently in check
        if self.in_check_for_current_player():
            return
        # king-side
        if (self.whiteToMove and self.currentCastlingRights.wks) or (not self.whiteToMove and self.currentCastlingRights.bks):
            if c + 2 < 8 and self.board[r][c + 1] == "--" and self.board[r][c + 2] == "--":
                opponent_color = 'b' if self.whiteToMove else 'w'
                if not self.square_under_attack(r, c + 1, by_color=opponent_color) and not self.square_under_attack(r, c + 2, by_color=opponent_color):
                    # ensure rook exists at expected square
                    if self.board[r][7] == (allyColor + "R"):
                        moves.append(self.Move((r, c), (r, c + 2), self.board, isCastleMove=True))
        # queen-side
        if (self.whiteToMove and self.currentCastlingRights.wqs) or (not self.whiteToMove and self.currentCastlingRights.bqs):
            if c - 3 >= 0 and self.board[r][c - 1] == "--" and self.board[r][c - 2] == "--" and self.board[r][c - 3] == "--":
                opponent_color = 'b' if self.whiteToMove else 'w'
                if not self.square_under_attack(r, c - 1, by_color=opponent_color) and not self.square_under_attack(r, c - 2, by_color=opponent_color):
                    if self.board[r][0] == (allyColor + "R"):
                        moves.append(self.Move((r, c), (r, c - 2), self.board, isCastleMove=True))

    # ---------------------- Utility Methods ----------------------
    def is_valid_move(self, move):
        """Check if a move is valid (doesn't put own king in check)"""
        return move in self.get_valid_moves()

    def get_piece_at(self, row, col):
        """Get the piece at a specific position"""
        if 0 <= row < 8 and 0 <= col < 8:
            return self.board[row][col]
        return None

    def is_king_in_check(self, color):
        """Check if the king of the specified color is in check"""
        if color == 'w':
            return self.square_under_attack(*self.whiteKingLocation, by_color='b')
        else:
            return self.square_under_attack(*self.blackKingLocation, by_color='w')

    def get_king_position(self, color):
        """Get the position of the king for the specified color"""
        if color == 'w':
            return self.whiteKingLocation
        else:
            return self.blackKingLocation

    def get_all_pieces(self, color):
        """Get all pieces of a specific color"""
        pieces = []
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece != "--" and piece[0] == color:
                    pieces.append((piece, row, col))
        return pieces

    def is_game_over(self):
        """Check if the game is over (checkmate or stalemate)"""
        status = self.get_game_status()
        return status in ["checkmate", "stalemate"]

    def get_winner(self):
        """Get the winner if the game is over"""
        status = self.get_game_status()
        if status == "checkmate":
            # winner is the side that is not to move (the side that delivered mate)
            return "white" if not self.whiteToMove else "black"
        elif status == "stalemate":
            return "draw"
        return None

    def get_checking_moves(self):
        """Get all moves that would put the opponent in check"""
        checking_moves = []
        all_moves = self.get_all_possible_moves()
        for move in all_moves:
            if self.would_give_check(move):
                checking_moves.append(move)
        return checking_moves

    def get_moves_for_piece(self, row, col):
        """
        Return all *legal* moves for the piece at (row,col) in the current position.
        This filters through get_valid_moves to ensure moves don't leave own king in check.
        """
        piece = self.get_piece_at(row, col)
        if piece == "--" or piece is None:
            return []
        valid = self.get_valid_moves()
        return [m for m in valid if m.startRow == row and m.startCol == col]




