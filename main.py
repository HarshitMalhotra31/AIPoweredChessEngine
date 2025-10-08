# main.py

import pygame as p
import sys
import ChessEngine

# ---------------------- GLOBAL SETTINGS ----------------------
WIDTH = HEIGHT = 512
DIMENSION = 8
SQ_SIZE = HEIGHT // DIMENSION
MAX_FPS = 15

IMAGES = {}

# ---------------------- LOAD PIECE IMAGES ----------------------
def load_images():
    pieces = ["wP", "wR", "wN", "wB", "wQ", "wK",
              "bP", "bR", "bN", "bB", "bQ", "bK"]
    for piece in pieces:
        IMAGES[piece] = p.transform.scale(
            p.image.load(f"images/{piece}.png"), (SQ_SIZE, SQ_SIZE))

# ---------------------- DRAW FUNCTIONS ----------------------
def draw_board(screen):
    colors = [p.Color("white"), p.Color("gray")]
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            p.draw.rect(screen, colors[(r+c)%2], p.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))

def draw_pieces(screen, board):
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            piece = board[r][c]
            if piece != "--":
                screen.blit(IMAGES[piece], p.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))

def show_game_over(screen, result):
    font = p.font.SysFont("Arial", 48)
    if result == "checkmate":
        winner = "Black" if gs.whiteToMove else "White"
        text = font.render(f"Checkmate! {winner} wins!", True, p.Color("red"))
    elif result == "stalemate":
        text = font.render("Stalemate!", True, p.Color("red"))
    screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - text.get_height()//2))
    p.display.flip()
    p.time.wait(3000)

# ---------------------- MAIN LOOP ----------------------
def main():
    global gs
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    gs = ChessEngine.GameState()
    load_images()

    selectedSq = ()
    playerClicks = []

    running = True
    while running:
        draw_board(screen)
        draw_pieces(screen, gs.board)

        # Check for checkmate/stalemate
        result = gs.checkmate_or_stalemate()
        if result:
            show_game_over(screen, result)
            running = False

        for e in p.event.get():
            if e.type == p.QUIT:
                running = False
                p.quit()
                sys.exit()
            elif e.type == p.MOUSEBUTTONDOWN:
                pos = p.mouse.get_pos()
                col = pos[0] // SQ_SIZE
                row = pos[1] // SQ_SIZE
                if selectedSq == (row, col):
                    selectedSq = ()
                    playerClicks = []
                else:
                    selectedSq = (row, col)
                    playerClicks.append(selectedSq)

                if len(playerClicks) == 2:
                    move = ChessEngine.GameState.Move(playerClicks[0], playerClicks[1], gs.board)
                    if move in gs.get_valid_moves():
                        gs.make_move(move)
                        selectedSq = ()
                        playerClicks = []
                    else:
                        playerClicks = [selectedSq]

            elif e.type == p.KEYDOWN:
                if e.key == p.K_z:  # Undo
                    gs.undo_move()
                elif e.key == p.K_y:  # Redo
                    gs.redo_move()

        clock.tick(MAX_FPS)
        p.display.flip()

if __name__ == "__main__":
    main()





