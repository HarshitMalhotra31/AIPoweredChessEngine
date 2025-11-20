# ChessEngine.py
from copy import deepcopy

class CastlingRights:
    def __init__(self, wks, wqs, bks, bqs):
        self.wks = wks
        self.wqs = wqs
        self.bks = bks
        self.bqs = bqs

    def copy(self):
        return CastlingRights(self.wks, self.wqs, self.bks, self.bqs)

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
        self.isEnPassantMove = isEnPassantMove
        if self.isEnPassantMove:
            # captured pawn is behind the target square
            self.pieceCaptured = ('bp' if self.pieceMoved[0].lower() == 'w' else 'wp')
        self.isCastleMove = isCastleMove
        self.promotionChoice = promotionChoice
        # For undoing / restoring state
        self.castlingRightsBefore = None
        self.enPassantBefore = None
        self.moveID = self.startRow * 1000 + self.startCol * 100 + self.endRow * 10 + self.endCol

    def __eq__(self, other):
        return isinstance(other, Move) and self.moveID == other.moveID

    def getRankFile(self, r, c):
        return self.colsToFiles[c] + self.rowsToRanks[r]

    def getChessNotation(self):
        if self.isCastleMove:
            return "O-O" if self.endCol == 6 else "O-O-O"
        return self.getRankFile(self.startRow, self.startCol) + self.getRankFile(self.endRow, self.endCol)

class GameState:
    def __init__(self):
        # Board uses strings like 'wR', 'bp', '--'
        self.board = [
            ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
            ["bp", "bp", "bp", "bp", "bp", "bp", "bp", "bp"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["wp", "wp", "wp", "wp", "wp", "wp", "wp", "wp"],
            ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"]
        ]
        self.whiteToMove = True
        self.moveLog = []
        self.redoLog = []
        self.whiteKingLocation = (7, 4)
        self.blackKingLocation = (0, 4)
        self.enPassantPossible = ()  # (r, c) or ()
        self.currentCastlingRights = CastlingRights(True, True, True, True)
        self.castleRightsLog = [self.currentCastlingRights.copy()]

        # flags for convenience 
        self.checkmate = False
        self.stalemate = False

        # simple cache for valid moves
        self._valid_moves_cache = None
        self._valid_moves_cache_key = (None, None)  # (len(moveLog), whiteToMove)

    # ---------------- Move execution / undo ----------------
    def makeMove(self, move):
        # snapshot castle and en-passant
        move.castlingRightsBefore = self.currentCastlingRights.copy()
        move.enPassantBefore = self.enPassantPossible

        # move piece
        self.board[move.endRow][move.endCol] = move.pieceMoved
        self.board[move.startRow][move.startCol] = "--"

        # handle pawn promotion (default to Q if no choice)
        if len(move.pieceMoved) >= 2 and move.pieceMoved[1].lower() == 'p':
            if move.endRow == 0 or move.endRow == 7:
                choice = (move.promotionChoice or 'Q').upper()
                self.board[move.endRow][move.endCol] = move.pieceMoved[0] + choice

        # en-passant capture: remove pawn behind target
        if move.isEnPassantMove:
            if move.pieceMoved[0].lower() == 'w':
                # white moves up, captured pawn is below endRow
                self.board[move.endRow + 1][move.endCol] = "--"
            else:
                self.board[move.endRow - 1][move.endCol] = "--"

        # update king location
        if len(move.pieceMoved) >= 2 and move.pieceMoved[1].upper() == 'K':
            if move.pieceMoved[0].lower() == 'w':
                self.whiteKingLocation = (move.endRow, move.endCol)
            else:
                self.blackKingLocation = (move.endRow, move.endCol)

        # castling rook move
        if move.isCastleMove:
            # king-side (move.endCol == startCol+2)
            if move.endCol - move.startCol == 2:
                # rook moves from h-file to f-file
                self.board[move.endRow][move.endCol - 1] = self.board[move.endRow][7]
                self.board[move.endRow][7] = "--"
            else:
                # queen-side: rook from a-file to d-file
                self.board[move.endRow][move.endCol + 1] = self.board[move.endRow][0]
                self.board[move.endRow][0] = "--"

        # update castling rights
        self.update_castle_rights(move)
        self.castleRightsLog.append(self.currentCastlingRights.copy())

        # update enPassantPossible
        self.enPassantPossible = ()
        if len(move.pieceMoved) >= 2 and move.pieceMoved[1].lower() == 'p' and abs(move.startRow - move.endRow) == 2:
            self.enPassantPossible = ((move.startRow + move.endRow) // 2, move.startCol)

        # logs and flip turn
        self.moveLog.append(move)
        self.redoLog.clear()
        self.whiteToMove = not self.whiteToMove

        # invalidate cache
        self._valid_moves_cache = None
        self._valid_moves_cache_key = (None, None)

    def make_move(self, move):
        return self.makeMove(move)

    def undoMove(self):
        if not self.moveLog:
            return
        move = self.moveLog.pop()

        # restore board squares
        self.board[move.startRow][move.startCol] = move.pieceMoved
        # for en-passant the captured pawn is not on end square
        if move.isEnPassantMove:
            # remove pawn that may currently be on the end square and restore captured pawn behind
            self.board[move.endRow][move.endCol] = "--"
            if move.pieceMoved[0].lower() == 'w':
                self.board[move.endRow + 1][move.endCol] = 'bp'
            else:
                self.board[move.endRow - 1][move.endCol] = 'wp'
        else:
            self.board[move.endRow][move.endCol] = move.pieceCaptured

        # undo castling rook movement if needed
        if move.isCastleMove:
            if move.endCol - move.startCol == 2:
                # king-side
                self.board[move.endRow][7] = self.board[move.endRow][move.endCol - 1]
                self.board[move.endRow][move.endCol - 1] = "--"
            else:
                # queen-side
                self.board[move.endRow][0] = self.board[move.endRow][move.endCol + 1]
                self.board[move.endRow][move.endCol + 1] = "--"

        # restore king location if king moved
        if len(move.pieceMoved) >= 2 and move.pieceMoved[1].upper() == 'K':
            if move.pieceMoved[0].lower() == 'w':
                self.whiteKingLocation = (move.startRow, move.startCol)
            else:
                self.blackKingLocation = (move.startRow, move.startCol)

        # restore castling rights snapshot
        if move.castlingRightsBefore is not None:
            self.currentCastlingRights = move.castlingRightsBefore.copy()
        else:
            # fallback: pop last stored rights if available
            if self.castleRightsLog:
                self.castleRightsLog.pop()
                if self.castleRightsLog:
                    self.currentCastlingRights = self.castleRightsLog[-1].copy()
                else:
                    self.currentCastlingRights = CastlingRights(True, True, True, True)

        # restore enPassantPossible from move snapshot
        self.enPassantPossible = move.enPassantBefore if move.enPassantBefore is not None else ()

        # flip turn and push to redo
        self.whiteToMove = not self.whiteToMove
        self.redoLog.append(move)

        # invalidate cache
        self._valid_moves_cache = None
        self._valid_moves_cache_key = (None, None)

    def undo_move(self):
        return self.undoMove()

    def redoMove(self):
        if self.redoLog:
            move = self.redoLog.pop()
            self.makeMove(move)

    def redo_move(self):
        return self.redoMove()

    # ---------------- castling rights update ----------------
    def update_castle_rights(self, move):
        # king moved: remove both castling rights for that color
        if len(move.pieceMoved) >= 2 and move.pieceMoved[1].upper() == 'K':
            if move.pieceMoved[0].lower() == 'w':
                self.currentCastlingRights.wks = False
                self.currentCastlingRights.wqs = False
            else:
                self.currentCastlingRights.bks = False
                self.currentCastlingRights.bqs = False

        # rook moved: remove relevant castling right
        if len(move.pieceMoved) >= 2 and move.pieceMoved[1].upper() == 'R':
            if move.pieceMoved[0].lower() == 'w':
                if move.startRow == 7 and move.startCol == 0:
                    self.currentCastlingRights.wqs = False
                elif move.startRow == 7 and move.startCol == 7:
                    self.currentCastlingRights.wks = False
            else:
                if move.startRow == 0 and move.startCol == 0:
                    self.currentCastlingRights.bqs = False
                elif move.startRow == 0 and move.startCol == 7:
                    self.currentCastlingRights.bks = False

        # rook captured: update rights
        if move.pieceCaptured != "--" and len(move.pieceCaptured) >= 2 and move.pieceCaptured[1].upper() == 'R':
            if move.endRow == 7 and move.endCol == 0:
                self.currentCastlingRights.wqs = False
            elif move.endRow == 7 and move.endCol == 7:
                self.currentCastlingRights.wks = False
            elif move.endRow == 0 and move.endCol == 0:
                self.currentCastlingRights.bqs = False
            elif move.endRow == 0 and move.endCol == 7:
                self.currentCastlingRights.bks = False

    # ---------------- game status helpers ----------------
    def get_game_status(self):
        valid_moves = self.getValidMoves()
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
        status = self.get_game_status()
        return status if status in ["checkmate", "stalemate"] else None

    def is_game_over(self):
        return self.get_game_status() in ["checkmate", "stalemate"]

    # ---------------- move generation ----------------
    def getValidMoves(self):
        """Return legal moves (filter out those leaving own king in check).
           Uses a simple cache keyed by (len(moveLog), side_to_move) for speed."""
        cache_key = (len(self.moveLog), self.whiteToMove)
        if self._valid_moves_cache is not None and self._valid_moves_cache_key == cache_key:
            return deepcopy(self._valid_moves_cache)

        moves = self.get_all_possible_moves()
        validMoves = []
        side_white = self.whiteToMove
        for move in moves:
            self.makeMove(move)
            # after moving, check whether the moving side's king is in check
            if side_white:
                in_check_after = self.square_under_attack(self.whiteKingLocation[0], self.whiteKingLocation[1], by_color='b')
            else:
                in_check_after = self.square_under_attack(self.blackKingLocation[0], self.blackKingLocation[1], by_color='w')
            if not in_check_after:
                validMoves.append(move)
            self.undoMove()

        # update checkmate/stalemate flags for convenience
        if not validMoves:
            if self.in_check_for_current_player():
                self.checkmate = True
                self.stalemate = False
            else:
                self.stalemate = True
                self.checkmate = False
        else:
            self.checkmate = False
            self.stalemate = False

        # cache result
        self._valid_moves_cache = deepcopy(validMoves)
        self._valid_moves_cache_key = cache_key

        return deepcopy(validMoves)

    def get_valid_moves(self):
        return self.getValidMoves()

    def in_check_for_current_player(self):
        king = self.whiteKingLocation if self.whiteToMove else self.blackKingLocation
        return self.square_under_attack(king[0], king[1], by_color=('b' if self.whiteToMove else 'w'))

    # ---------------- attack detection (no recursion) ----------------
    def square_under_attack(self, r, c, by_color=None):
        attacker = by_color if by_color is not None else ('b' if self.whiteToMove else 'w')
        attacker = attacker.lower()

        # pawn attacks (attacker pawns attack diagonally towards opponent)
        if attacker == 'w':
            # white pawns attack one row up (r-1) from their perspective,
            # so a white pawn that attacks (r,c) must be at (r+1,c±1)
            for dc in (-1, 1):
                rr = r + 1
                cc = c + dc
                if 0 <= rr <= 7 and 0 <= cc <= 7:
                    p = self.board[rr][cc]
                    if p != "--" and p[0].lower() == 'w' and p[1].lower() == 'p':
                        return True
        else:
            # black pawns attack one row down (r+1) from their perspective,
            # so a black pawn that attacks (r,c) must be at (r-1,c±1)
            for dc in (-1, 1):
                rr = r - 1
                cc = c + dc
                if 0 <= rr <= 7 and 0 <= cc <= 7:
                    p = self.board[rr][cc]
                    if p != "--" and p[0].lower() == 'b' and p[1].lower() == 'p':
                        return True

        # knight attacks
        knight_offsets = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        for dr, dc in knight_offsets:
            rr = r + dr
            cc = c + dc
            if 0 <= rr <= 7 and 0 <= cc <= 7:
                p = self.board[rr][cc]
                if p != "--" and p[0].lower() == attacker and p[1].upper() == 'N':
                    return True

        # sliding pieces: rook/queen (orthogonal), bishop/queen (diagonal)
        # orthogonal
        orth_dirs = [(-1,0),(1,0),(0,-1),(0,1)]
        for dr, dc in orth_dirs:
            for i in range(1,8):
                rr = r + dr*i
                cc = c + dc*i
                if not (0 <= rr <= 7 and 0 <= cc <= 7):
                    break
                p = self.board[rr][cc]
                if p == "--":
                    continue
                if p[0].lower() == attacker:
                    if p[1].upper() in ('R','Q'):
                        return True
                    else:
                        break
                else:
                    break

        # diagonal
        diag_dirs = [(-1,-1),(-1,1),(1,-1),(1,1)]
        for dr, dc in diag_dirs:
            for i in range(1,8):
                rr = r + dr*i
                cc = c + dc*i
                if not (0 <= rr <= 7 and 0 <= cc <= 7):
                    break
                p = self.board[rr][cc]
                if p == "--":
                    continue
                if p[0].lower() == attacker:
                    if p[1].upper() in ('B','Q'):
                        return True
                    else:
                        break
                else:
                    break

        # king adjacent squares
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if dr == 0 and dc == 0:
                    continue
                rr = r + dr
                cc = c + dc
                if 0 <= rr <= 7 and 0 <= cc <= 7:
                    p = self.board[rr][cc]
                    if p != "--" and p[0].lower() == attacker and p[1].upper() == 'K':
                        return True

        return False

    # ---------------- helpers for generating possible moves ----------------
    def get_all_possible_moves(self):
        """Return pseudo-legal moves for current side (no check filtering)."""
        moves = []
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece == "--":
                    continue
                color = piece[0].lower()
                if (self.whiteToMove and color != 'w') or (not self.whiteToMove and color != 'b'):
                    continue
                ptype = piece[1].upper()
                if ptype == 'P':
                    self.get_pawn_moves(r, c, moves)
                elif ptype == 'R':
                    self._slide_moves(r, c, [(-1,0),(1,0),(0,-1),(0,1)], moves)
                elif ptype == 'B':
                    self._slide_moves(r, c, [(-1,-1),(-1,1),(1,-1),(1,1)], moves)
                elif ptype == 'Q':
                    self._slide_moves(r, c, [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)], moves)
                elif ptype == 'K':
                    self.get_king_moves(r, c, moves)
                elif ptype == 'N':
                    self.get_knight_moves(r, c, moves)
        return moves

    def get_pawn_moves(self, r, c, moves):
        piece = self.board[r][c]
        color = piece[0].lower()
        direction = -1 if color == 'w' else 1
        startRow = 6 if color == 'w' else 1

        # forward one
        if 0 <= r + direction <= 7 and self.board[r + direction][c] == "--":
            moves.append(Move((r, c), (r + direction, c), self.board))
            # forward two from start
            if r == startRow and self.board[r + 2*direction][c] == "--":
                moves.append(Move((r, c), (r + 2*direction, c), self.board))

        # captures & en-passant
        for dc in (-1, 1):
            nc = c + dc
            nr = r + direction
            if 0 <= nc <= 7 and 0 <= nr <= 7:
                target = self.board[nr][nc]
                if target != "--" and target[0].lower() != color:
                    moves.append(Move((r, c), (nr, nc), self.board))
                elif (nr, nc) == self.enPassantPossible:
                    moves.append(Move((r, c), (nr, nc), self.board, isEnPassantMove=True))

    def _slide_moves(self, r, c, directions, moves):
        color = self.board[r][c][0].lower()
        for dr, dc in directions:
            for i in range(1,8):
                nr = r + dr*i
                nc = c + dc*i
                if not (0 <= nr <= 7 and 0 <= nc <= 7):
                    break
                target = self.board[nr][nc]
                if target == "--":
                    moves.append(Move((r,c),(nr,nc),self.board))
                else:
                    if target[0].lower() != color:
                        moves.append(Move((r,c),(nr,nc),self.board))
                    break

    def get_king_moves(self, r, c, moves):
        color = self.board[r][c][0].lower()
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if dr == 0 and dc == 0:
                    continue
                nr = r + dr
                nc = c + dc
                if 0 <= nr <= 7 and 0 <= nc <= 7:
                    target = self.board[nr][nc]
                    if target == "--" or target[0].lower() != color:
                        moves.append(Move((r,c),(nr,nc),self.board))

        # castling (ensure king and rook haven't moved, path empty, and not under attack)
        if color == 'w' and self.whiteToMove:
            # white king-side
            if self.currentCastlingRights.wks:
                if self.board[7][5] == "--" and self.board[7][6] == "--":
                    if (not self.square_under_attack(7,4,'b') and
                        not self.square_under_attack(7,5,'b') and
                        not self.square_under_attack(7,6,'b')):
                        moves.append(Move((7,4),(7,6),self.board,isCastleMove=True))
            # white queen-side
            if self.currentCastlingRights.wqs:
                if self.board[7][1] == "--" and self.board[7][2] == "--" and self.board[7][3] == "--":
                    if (not self.square_under_attack(7,4,'b') and
                        not self.square_under_attack(7,3,'b') and
                        not self.square_under_attack(7,2,'b')):
                        moves.append(Move((7,4),(7,2),self.board,isCastleMove=True))
        elif color == 'b' and not self.whiteToMove:
            # black king-side
            if self.currentCastlingRights.bks:
                if self.board[0][5] == "--" and self.board[0][6] == "--":
                    if (not self.square_under_attack(0,4,'w') and
                        not self.square_under_attack(0,5,'w') and
                        not self.square_under_attack(0,6,'w')):
                        moves.append(Move((0,4),(0,6),self.board,isCastleMove=True))
            # black queen-side
            if self.currentCastlingRights.bqs:
                if self.board[0][1] == "--" and self.board[0][2] == "--" and self.board[0][3] == "--":
                    if (not self.square_under_attack(0,4,'w') and
                        not self.square_under_attack(0,3,'w') and
                        not self.square_under_attack(0,2,'w')):
                        moves.append(Move((0,4),(0,2),self.board,isCastleMove=True))

    def get_knight_moves(self, r, c, moves):
        color = self.board[r][c][0].lower()
        knight_offsets = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        for dr, dc in knight_offsets:
            nr = r + dr
            nc = c + dc
            if 0 <= nr <= 7 and 0 <= nc <= 7:
                target = self.board[nr][nc]
                if target == "--" or target[0].lower() != color:
                    moves.append(Move((r,c),(nr,nc),self.board))
