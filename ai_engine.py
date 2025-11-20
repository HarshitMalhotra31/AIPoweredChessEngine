# ai_engine.py
import math
import time
import random
import ChessEngine

# ---------------------- PIECE VALUES ----------------------
piece_values = {
    "K": 0, "Q": 9, "R": 5, "B": 3, "N": 3, "P": 1,
    "k": 0, "q": 9, "r": 5, "b": 3, "n": 3, "p": 1
}

# ---------------------- POSITIONAL TABLES ----------------------
pawn_table = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [5, 5, 5, 5, 5, 5, 5, 5],
    [1, 1, 2, 3, 3, 2, 1, 1],
    [0.5, 0.5, 1, 2.5, 2.5, 1, 0.5, 0.5],
    [0, 0, 0, 2, 2, 0, 0, 0],
    [0.5, -0.5, -1, 0, 0, -1, -0.5, 0.5],
    [0.5, 1, 1, -2, -2, 1, 1, 0.5],
    [0, 0, 0, 0, 0, 0, 0, 0]
]

piece_square_tables = {
    "P": pawn_table,
    "p": pawn_table[::-1],
}

# ---------------------- EVALUATION ----------------------
def evaluate_board(gs):
    """Improved evaluation: material + piece-square + mobility"""
    # Use the correct attribute names from your GameState
    if getattr(gs, "checkmate", False):
        return -9999 if gs.whiteToMove else 9999
    elif getattr(gs, "stalemate", False):
        return 0

    value = 0
    for r in range(8):
        for c in range(8):
            piece = gs.board[r][c]
            if piece == "--":
                continue
            color, symbol = piece[0], piece[1].upper()
            piece_value = piece_values.get(symbol, 0)
            sign = 1 if color == 'w' else -1

            value += sign * piece_value

            # Positional bonus
            if symbol in piece_square_tables:
                if color == 'w':
                    value += piece_square_tables[symbol][r][c] * sign
                else:
                    value -= piece_square_tables[symbol.lower()][r][c] * sign

    # Mobility bonus (more legal moves = better)
    # Save current turn, compute mobility for both sides safely
    current_turn = gs.whiteToMove
    # white mobility
    gs.whiteToMove = True
    white_moves = len(gs.get_valid_moves())
    # black mobility
    gs.whiteToMove = False
    black_moves = len(gs.get_valid_moves())
    # restore
    gs.whiteToMove = current_turn

    value += (white_moves - black_moves) * 0.1

    return value

# ---------------------- MOVE ORDERING ----------------------
def order_moves(gs, moves):
    def move_score(move):
        score = 0
        if move.pieceCaptured != "--":
            # reward captures by victim value minus attacker value
            victim = move.pieceCaptured[1].upper()
            attacker = move.pieceMoved[1].upper()
            score += (piece_values.get(victim, 0) - piece_values.get(attacker, 0)) * 10
        # prefer promotions if present (some Move implementations set isPawnPromotion)
        if getattr(move, 'isPawnPromotion', False):
            score += 800
        # small bonus for castling
        if getattr(move, 'isCastleMove', False):
            score += 50
        return score
    return sorted(moves, key=move_score, reverse=True)

# ---------------------- MINIMAX + ALPHA-BETA ----------------------
def minimax(gs, depth, alpha, beta, maximizing_player, start_time, time_limit):
    # time cutoff
    if (time.time() - start_time) > time_limit:
        return evaluate_board(gs), None

    if depth == 0 or gs.is_game_over():
        return evaluate_board(gs), None

    valid_moves = gs.get_valid_moves()
    if not valid_moves:
        return evaluate_board(gs), None

    # move ordering helps pruning
    valid_moves = order_moves(gs, valid_moves)

    best_move = None
    if maximizing_player:
        max_eval = -math.inf
        for move in valid_moves:
            gs.makeMove(move)
            eval_score, _ = minimax(gs, depth - 1, alpha, beta, False, start_time, time_limit)
            gs.undoMove()
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = math.inf
        for move in valid_moves:
            gs.makeMove(move)
            eval_score, _ = minimax(gs, depth - 1, alpha, beta, True, start_time, time_limit)
            gs.undoMove()
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = move
            beta = min(beta, eval_score)
            if beta <= alpha:
                break
        return min_eval, best_move

# ---------------------- FIND BEST MOVE ----------------------
def find_best_move(gs, level="intermediate"):
    lvl = (level or "intermediate").lower()
    if lvl == "beginner":
        depth, time_limit = 2, 1.5
    elif lvl == "intermediate":
        depth, time_limit = 3, 3.0
    elif lvl == "advanced":
        depth, time_limit = 4, 6.0
    else:
        depth, time_limit = 3, 3.0

    start_time = time.time()
    # We pass maximizing_player = not gs.whiteToMove because minimax expects
    maximizing = gs.whiteToMove
    _, best_move = minimax(gs, depth, -math.inf, math.inf, maximizing, start_time, time_limit)

    # Beginner randomness to simulate human blunders
    if lvl == "beginner" and best_move is not None:
        if random.random() < 0.25:
            candidates = gs.get_valid_moves()
            if candidates:
                return random.choice(candidates)

    # fallback: if no best_move found, pick any legal move
    if best_move is None:
        moves = gs.get_valid_moves()
        return random.choice(moves) if moves else None

    return best_move






