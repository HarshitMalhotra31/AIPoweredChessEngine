import pygame as p
import sys
import time
import ChessEngine
from ai_engine import find_best_move
import chess_db as db
import random
import copy

# ---------------------- GLOBAL SETTINGS ----------------------
WIDTH = 768
HEIGHT = 512
BOARD_SIZE = 512
PANEL_WIDTH = WIDTH - BOARD_SIZE
DIMENSION = 8
SQ_SIZE = BOARD_SIZE // DIMENSION
MAX_FPS = 60
IMAGES = {}

# Colors & animation
LIGHT_COLOR = p.Color(240, 217, 181)
DARK_COLOR = p.Color(181, 136, 99)
HIGHLIGHT_COLOR = p.Color(0, 170, 255)
LAST_MOVE_COLOR = p.Color(200, 200, 80)
LEGAL_MOVE_COLOR = p.Color(100, 255, 100)
ANIMATION_SPEED = 8

# flip board flag (if True, UI is flipped so player sees black at bottom)
flip_board = False

# DB init
db.init_db()

# ------------------ Image loader ------------------
def load_images():
    pieces = ["wp", "wr", "wn", "wb", "wq", "wk",
              "bp", "br", "bn", "bb", "bq", "bk"]
    for piece in pieces:
        IMAGES[piece] = p.transform.smoothscale(
            p.image.load(f"images/{piece}.png").convert_alpha(), (SQ_SIZE, SQ_SIZE)
        )

# ------------------ Helpers for flipping ------------------
def display_coords_from_board(r, c):
    """Convert game board coords (r,c) to screen/display coords (r_disp, c_disp) respecting flip_board."""
    if not flip_board:
        return r, c
    return 7 - r, 7 - c

def board_coords_from_mouse(x, y):
    """Convert mouse (pixel) coords to game board coords (r,c), taking flip into account."""
    col = x // SQ_SIZE
    row = y // SQ_SIZE
    # clamp range
    if col < 0: col = 0
    if col > 7: col = 7
    if row < 0: row = 0
    if row > 7: row = 7
    if not flip_board:
        return row, col
    return 7 - row, 7 - col

def display_rect_for_square(r, c):
    """Return pygame.Rect for drawing a square at board coords (r,c) on screen respecting flip."""
    dr, dc = display_coords_from_board(r, c)
    return p.Rect(dc * SQ_SIZE, dr * SQ_SIZE, SQ_SIZE, SQ_SIZE)

def pixel_center_of_square(r, c):
    """Return center pixel of display location for board square (r,c)."""
    dr, dc = display_coords_from_board(r, c)
    return (dc * SQ_SIZE + SQ_SIZE//2, dr * SQ_SIZE + SQ_SIZE//2)

# ------------------ Modern UI: Menu, Color & Difficulty pickers, Scoreboard ------------------
def draw_menu(screen, hover_idx=-1):
    screen.fill((12, 16, 22))
    title_font = p.font.SysFont("Arial", 56, True)
    opt_font = p.font.SysFont("Arial", 28, True)
    small = p.font.SysFont("Arial", 16)

    title = title_font.render("AI CHESS ENGINE", True, p.Color("white"))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 48))

    # cards
    options = ["Player vs Player", "Player vs AI", "Scorecard / Leaderboard", "Quit"]
    card_w, card_h = 420, 64
    start_y = 160
    gap = 22

    buttons = []
    for i, txt in enumerate(options):
        x = WIDTH//2 - card_w//2
        y = start_y + i*(card_h + gap)
        hovered = (i == hover_idx)
        # card bg
        bg_col = (26,28,36) if not hovered else (0,140,200)
        p.draw.rect(screen, bg_col, (x, y, card_w, card_h), border_radius=12)
        # subtle border
        p.draw.rect(screen, (60,60,70), (x, y, card_w, card_h), 2, border_radius=12)
        # text
        lbl = opt_font.render(txt, True, p.Color("white"))
        screen.blit(lbl, (x + 22, y + card_h//2 - lbl.get_height()//2))
        buttons.append((x, y, card_w, card_h))
    hint = small.render("Click a card to choose — Mouse & Keyboard supported (Esc to quit)", True, (180,180,185))
    screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 40))
    return buttons

def menu_loop(screen):
    clock = p.time.Clock()
    while True:
        mx, my = p.mouse.get_pos()
        clicked = False
        for e in p.event.get():
            if e.type == p.QUIT:
                p.quit(); sys.exit()
            if e.type == p.KEYDOWN:
                if e.key == p.K_ESCAPE:
                    p.quit(); sys.exit()
                if e.key == p.K_1:
                    return "1"
                if e.key == p.K_2:
                    return "2"
                if e.key == p.K_3:
                    return "3"
                if e.key == p.K_4:
                    return "4"
            if e.type == p.MOUSEBUTTONDOWN:
                clicked = True

        buttons = draw_menu(screen)
        hover = -1
        for i, (x, y, w, h) in enumerate(buttons):
            if x <= mx <= x+w and y <= my <= y+h:
                hover = i
                # hover micro-glow
                glow = p.Surface((w, h), p.SRCALPHA)
                glow.fill((0,170,255,30))
                screen.blit(glow, (x, y))
                if clicked:
                    return str(i+1)
        # redraw with hover index to update styles
        if hover != -1:
            draw_menu(screen, hover)
        p.display.flip()
        clock.tick(60)

# Color choice UI (card style)
def choose_color_ui(screen):
    clock = p.time.Clock()
    font = p.font.SysFont("Arial", 36, True)
    small = p.font.SysFont("Arial", 18)
    options = ["Play as White ", "Play as Black"]
    btn_w, btn_h = 520, 68
    while True:
        mx, my = p.mouse.get_pos(); clicked=False
        for e in p.event.get():
            if e.type == p.QUIT:
                p.quit(); sys.exit()
            if e.type == p.KEYDOWN and e.key == p.K_ESCAPE:
                p.quit(); sys.exit()
            if e.type == p.MOUSEBUTTONDOWN:
                clicked = True

        screen.fill((10,12,18))
        title = font.render("Choose Your Color", True, p.Color("white"))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 48))
        start_y = 160; gap=28
        hover = -1
        for i, txt in enumerate(options):
            x = WIDTH//2 - btn_w//2
            y = start_y + i*(btn_h+gap)
            rect = p.Rect(x,y,btn_w,btn_h)
            if rect.collidepoint(mx,my):
                p.draw.rect(screen, (0,140,200), rect, border_radius=12)
                hover = i
                if clicked:
                    # return "2" if choose black (so ai_plays_white = True)
                    return "2" if i==1 else "1"
            else:
                p.draw.rect(screen, (30,34,42), rect, border_radius=12)
            txt_s = p.font.SysFont("Arial", 22).render(txt, True, p.Color("white"))
            screen.blit(txt_s, (x+22, y + btn_h//2 - txt_s.get_height()//2))
        hint = small.render("Click a card to select. (Esc to quit)", True, (170,170,170))
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT-40))
        p.display.flip(); clock.tick(60)

# Difficulty choice UI (card style)
def choose_difficulty_ui(screen):
    clock = p.time.Clock()
    title_font = p.font.SysFont("Arial", 36, True)
    opt_font = p.font.SysFont("Arial", 20)
    opts = [("Beginner", "Easy "), ("Intermediate", "Balanced"), ("Advanced", "Stronger, deeper")]
    btn_w, btn_h = 480, 60
    while True:
        mx, my = p.mouse.get_pos(); clicked=False
        for e in p.event.get():
            if e.type == p.QUIT:
                p.quit(); sys.exit()
            if e.type == p.MOUSEBUTTONDOWN:
                clicked = True
            if e.type == p.KEYDOWN and e.key == p.K_ESCAPE:
                p.quit(); sys.exit()

        screen.fill((8,10,14))
        title = title_font.render("Choose Difficulty", True, p.Color("white"))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 40))
        start_y = 140; gap = 20
        for i, (t,s) in enumerate(opts):
            x = WIDTH//2 - btn_w//2
            y = start_y + i*(btn_h+gap)
            rect = p.Rect(x,y,btn_w,btn_h)
            if rect.collidepoint(mx,my):
                p.draw.rect(screen, (0,130,200), rect, border_radius=10)
                if clicked:
                    return ["beginner","intermediate","advanced"][i]
            else:
                p.draw.rect(screen, (28,30,36), rect, border_radius=10)
            lbl = opt_font.render(f"{t} — {s}", True, p.Color("white"))
            screen.blit(lbl, (x+18, y + btn_h//2 - lbl.get_height()//2))
        p.display.flip(); clock.tick(60)

# Scoreboard / Leaderboard screen
def show_scoreboard(screen):
    font = p.font.SysFont("Arial", 26, True)
    small = p.font.SysFont("Arial", 18)
    clock = p.time.Clock()
    players = db.list_players(limit=50)
    while True:
        for e in p.event.get():
            if e.type == p.QUIT:
                p.quit(); sys.exit()
            if e.type == p.KEYDOWN or e.type == p.MOUSEBUTTONDOWN:
                # any key / click returns to menu
                return
        screen.fill((6,8,12))
        title = font.render("Scorecard — Leaderboard (Top by wins)", True, p.Color("white"))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 18))
        y = 70
        header = small.render(f"{ 'Rank':<6}{'Name':<22}{'W':>4}{'L':>5}{'D':>5}{'Total':>7}{'Win%':>8}", True, p.Color("lightgray"))
        screen.blit(header, (48, y)); y += 28
        rank = 1
        for row in players:
            total = row["wins"] + row["losses"] + row["draws"]
            win_pct = (row["wins"]/total*100.0) if total>0 else 0.0
            line = small.render(f"{rank:<6}{row['name']:<22}{row['wins']:>4}{row['losses']:>5}{row['draws']:>5}{total:>7}{win_pct:>7.1f}%", True, p.Color("lightgray"))
            screen.blit(line, (48,y)); y += 22; rank += 1
            if y > HEIGHT - 40:
                break
        foot = small.render("Press any key or click to return", True, p.Color("gray"))
        screen.blit(foot, (WIDTH//2 - foot.get_width()//2, HEIGHT - 36))
        p.display.flip(); clock.tick(60)

# ------------------ SAN utilities ------------------
def square_name(r, c):
    return ChessEngine.Move.colsToFiles[c] + ChessEngine.Move.rowsToRanks[r]

def is_capture(move):
    return (move.pieceCaptured != "--") or move.isEnPassantMove

def find_other_movers(gs, move):
    others = []
    typ = move.pieceMoved[1].upper()
    color = move.pieceMoved[0]
    for r in range(8):
        for c in range(8):
            if (r, c) == (move.startRow, move.startCol):
                continue
            pce = gs.board[r][c]
            if pce != "--" and pce[0] == color and pce[1].upper() == typ:
                pmoves = []
                pieceType = pce[1].upper()
                if pieceType == 'P':
                    gs.get_pawn_moves(r, c, pmoves)
                elif pieceType == 'R':
                    gs._slide_moves(r, c, [(-1,0),(1,0),(0,-1),(0,1)], pmoves)
                elif pieceType == 'B':
                    gs._slide_moves(r, c, [(-1,-1),(-1,1),(1,-1),(1,1)], pmoves)
                elif pieceType == 'Q':
                    gs._slide_moves(r, c, [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)], pmoves)
                elif pieceType == 'N':
                    gs.get_knight_moves(r, c, pmoves)
                elif pieceType == 'K':
                    gs.get_king_moves(r, c, pmoves)
                for m in pmoves:
                    if m.endRow == move.endRow and m.endCol == move.endCol:
                        others.append((r,c))
                        break
    return others

def move_to_san(move, gs_before):
    # Castling
    if move.isCastleMove:
        san = "O-O" if move.endCol == 6 else "O-O-O"
    else:
        piece = move.pieceMoved
        piece_letter = '' if piece[1].lower() == 'p' else piece[1].upper()
        capture = is_capture(move)
        dest = square_name(move.endRow, move.endCol)
        promotion = ''
        if move.promotionChoice:
            promotion = '=' + move.promotionChoice.upper()
        else:
            if piece[1].lower() == 'p' and (move.endRow == 0 or move.endRow == 7):
                promotion = '=Q'  # default

        if piece_letter == '':
            if capture:
                san = ChessEngine.Move.colsToFiles[move.startCol] + 'x' + dest
            else:
                san = dest
            san += promotion
        else:
            others = find_other_movers(gs_before, move)
            disamb = ''
            if others:
                file_conflict = any(o[1] != move.startCol for o in others)
                rank_conflict = any(o[0] != move.startRow for o in others)
                if file_conflict and not rank_conflict:
                    disamb = ChessEngine.Move.colsToFiles[move.startCol]
                elif rank_conflict and not file_conflict:
                    disamb = ChessEngine.Move.rowsToRanks[move.startRow]
                else:
                    disamb = ChessEngine.Move.colsToFiles[move.startCol] + ChessEngine.Move.rowsToRanks[move.startRow]
            san = piece_letter + disamb + ('x' if capture else '') + dest + promotion

    # Append '+' or '#' for check / mate
    gs_copy = copy.deepcopy(gs_before)
    gs_copy.makeMove(move)
    status = gs_copy.get_game_status()
    if status == "checkmate":
        san += '#'
    elif status == "check":
        san += '+'
    return san

# ------------------ Drawing helpers (flipped-aware) ------------------
def draw_board(screen):
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            dr, dc = display_coords_from_board(r, c)
            color = LIGHT_COLOR if (r + c) % 2 == 0 else DARK_COLOR
            p.draw.rect(screen, color, p.Rect(dc * SQ_SIZE, dr * SQ_SIZE, SQ_SIZE, SQ_SIZE))

def draw_last_move(screen, move):
    if not move:
        return
    s = p.Surface((SQ_SIZE, SQ_SIZE))
    s.set_alpha(120)
    s.fill(LAST_MOVE_COLOR)
    sr, sc = display_coords_from_board(move.startRow, move.startCol)
    er, ec = display_coords_from_board(move.endRow, move.endCol)
    screen.blit(s, (sc * SQ_SIZE, sr * SQ_SIZE))
    screen.blit(s, (ec * SQ_SIZE, er * SQ_SIZE))

def highlight_square(screen, sq):
    if not sq:
        return
    r, c = sq
    dr, dc = display_coords_from_board(r, c)
    s = p.Surface((SQ_SIZE, SQ_SIZE))
    s.set_alpha(120)
    s.fill(HIGHLIGHT_COLOR)
    screen.blit(s, (dc * SQ_SIZE, dr * SQ_SIZE))

def draw_legal_moves(screen, moves):
    dot_radius = max(6, SQ_SIZE // 8)
    for r, c in moves:
        cx, cy = pixel_center_of_square(r, c)
        p.draw.circle(screen, LEGAL_MOVE_COLOR, (cx, cy), dot_radius)

def draw_pieces(screen, board, animate_move=None):
    if animate_move:
        move, progress = animate_move
    else:
        move = None
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            piece = board[r][c]
            if piece != "--":
                if move and (r, c) == (move.startRow, move.startCol):
                    continue
                key = piece.lower()
                if key in IMAGES:
                    dr, dc = display_coords_from_board(r, c)
                    screen.blit(IMAGES[key], p.Rect(dc * SQ_SIZE, dr * SQ_SIZE, SQ_SIZE, SQ_SIZE))
    if move:
        sr, sc = move.startRow, move.startCol
        er, ec = move.endRow, move.endCol
        start_disp_r, start_disp_c = display_coords_from_board(sr, sc)
        end_disp_r, end_disp_c = display_coords_from_board(er, ec)
        start_pix = (start_disp_c * SQ_SIZE, start_disp_r * SQ_SIZE)
        end_pix = (end_disp_c * SQ_SIZE, end_disp_r * SQ_SIZE)
        cur_x = start_pix[0] + (end_pix[0] - start_pix[0]) * progress
        cur_y = start_pix[1] + (end_pix[1] - start_pix[1]) * progress
        key = move.pieceMoved.lower()
        if key in IMAGES:
            screen.blit(IMAGES[key], p.Rect(int(cur_x), int(cur_y), SQ_SIZE, SQ_SIZE))

# ------------------  UI ------------------
def get_panel_layout():
    panel_rect = p.Rect(BOARD_SIZE, 0, PANEL_WIDTH, HEIGHT)
    # header area
    header_rect = p.Rect(BOARD_SIZE + 10, 8, PANEL_WIDTH - 20, 28)
    # flip button (circular) top center
    cx = BOARD_SIZE + PANEL_WIDTH // 2
    cy = 64
    flip_radius = 20
    # move log box
    log_rect = p.Rect(BOARD_SIZE + 10, 100, PANEL_WIDTH - 20, 260)
    # controls area (buttons stacked) bottom
    btn_w = PANEL_WIDTH - 40
    btn_h = 34
    btn_x = BOARD_SIZE + 20
    btn_y = HEIGHT - 150
    undo_rect = p.Rect(btn_x, btn_y, btn_w, btn_h)
    restart_rect = p.Rect(btn_x, btn_y + 44, btn_w, btn_h)
    toggle_rect = p.Rect(btn_x, btn_y + 88, btn_w, btn_h)
    return {
        'panel': panel_rect,
        'header': header_rect,
        'flip_center': (cx, cy),
        'flip_radius': flip_radius,
        'log': log_rect,
        'undo': undo_rect,
        'restart': restart_rect,
        'toggle': toggle_rect
    }


def draw_panel(screen, san_moves, move_log_shown, font, flip_btn_hover=False):
    L = get_panel_layout()
    # panel background
    p.draw.rect(screen, p.Color(30, 30, 30), L['panel'])

    # header
    title = font.render("Move Log (SAN)", True, p.Color("white"))
    screen.blit(title, (L['header'].x, L['header'].y))

    # flip button (circular) - smaller and centered
    circle_color = (50, 50, 60) if not flip_btn_hover else (0, 140, 200)
    p.draw.circle(screen, circle_color, L['flip_center'], L['flip_radius'])
    p.draw.circle(screen, (100,100,110), L['flip_center'], L['flip_radius'], 2)
    try:
        emoji_font = p.font.SysFont("Segoe UI Emoji", 22)
    except:
        emoji_font = p.font.SysFont("Arial", 22)
    emoji_s = emoji_font.render("♻️", True, p.Color("white"))
    screen.blit(emoji_s, (L['flip_center'][0] - emoji_s.get_width()//2, L['flip_center'][1] - emoji_s.get_height()//2))
    lbl = font.render("Flip (F)", True, p.Color("lightgray"))
    screen.blit(lbl, (L['flip_center'][0] - lbl.get_width()//2, L['flip_center'][1] + L['flip_radius'] + 6))

    # ---------------------Move log box------------
    p.draw.rect(screen, (22,24,28), L['log'], border_radius=8)
    p.draw.rect(screen, (60,60,70), L['log'], 2, border_radius=8)

    # Render SAN moves inside the log box with padding
    pad_x = 8
    pad_y = 8
    line_h = 20
    sx = L['log'].x + pad_x
    sy = L['log'].y + pad_y
    # show last N moves that fit
    max_lines = (L['log'].h - pad_y*2)//line_h
    to_show = []
    # combine into numbered pairs
    pairs = []
    for i in range(0, len(san_moves), 2):
        move_no = i//2 + 1
        w = san_moves[i] if i < len(san_moves) else ""
        b = san_moves[i+1] if (i+1) < len(san_moves) else ""
        pairs.append(f"{move_no}. {w}  {b}")
    if not move_log_shown:
        # show only last few
        pairs = pairs[-(max_lines):]
    # render
    small = p.font.SysFont("Arial", 16)
    y = sy
    for line in pairs:
        txt = small.render(line, True, p.Color("lightgray"))
        screen.blit(txt, (sx, y)); y += line_h
        if y > L['log'].y + L['log'].h - pad_y:
            break

    # Controls (stacked buttons) - clean card style
    for text, rect in [("Undo (Z)", L['undo']), ("Restart (R)", L['restart']), ("Toggle Log (M)", L['toggle'])]:
        p.draw.rect(screen, p.Color(60, 60, 60), rect, border_radius=8)
        p.draw.rect(screen, p.Color(90, 90, 100), rect, 2, border_radius=8)
        btn_font = p.font.SysFont("Arial", 16)
        txt = btn_font.render(text, True, p.Color("white"))
        screen.blit(txt, (rect.x + 12, rect.y + (rect.h - txt.get_height())//2))

# show game over overlay
def show_game_over(screen, result, gs):
    font = p.font.SysFont("Arial", 36, True)
    if result == "checkmate":
        winner = "Black" if gs.whiteToMove else "White"
        text = font.render(f"Checkmate! {winner} wins!", True, p.Color("red"))
    elif result == "stalemate":
        text = font.render("Stalemate!", True, p.Color("red"))
    else:
        return
    s = p.Surface((BOARD_SIZE, BOARD_SIZE))
    s.set_alpha(220)
    s.fill(p.Color(0, 0, 0))
    screen.blit(s, (0, 0))
    screen.blit(text, (BOARD_SIZE//2 - text.get_width()//2, BOARD_SIZE//2 - text.get_height()//2))
    p.display.flip()
    p.time.wait(2000)

# ---------- text input modal (same as before) ----------
def get_text_input(screen, prompt="Enter name:", font=None, max_len=20):
    if font is None:
        font = p.font.SysFont("Arial", 24)
    clock = p.time.Clock()
    text = ""
    while True:
        for e in p.event.get():
            if e.type == p.QUIT:
                p.quit(); sys.exit()
            elif e.type == p.KEYDOWN:
                if e.key == p.K_RETURN:
                    if text.strip():
                        return text.strip()
                elif e.key == p.K_BACKSPACE:
                    text = text[:-1]
                else:
                    if len(text) < max_len and e.unicode.isprintable():
                        text += e.unicode
        s = p.Surface((WIDTH, HEIGHT))
        s.set_alpha(200)
        s.fill(p.Color(0,0,0))
        screen.blit(s, (0,0))
        prompt_s = font.render(prompt, True, p.Color("white"))
        screen.blit(prompt_s, (WIDTH//2 - prompt_s.get_width()//2, HEIGHT//2 - 60))
        input_box = p.Rect(WIDTH//2 - 200, HEIGHT//2 - 20, 400, 40)
        p.draw.rect(screen, p.Color(255,255,255), input_box, 2)
        txt_s = font.render(text, True, p.Color("white"))
        screen.blit(txt_s, (input_box.x + 10, input_box.y + 6))
        hint = font.render("Press Enter to confirm", True, p.Color("gray"))
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT//2 + 30))
        p.display.flip()
        clock.tick(30)

# ---------- stats screen (same as earlier) ----------
def show_stats_screen(screen, player_name, font):
    stats = db.get_player_stats(player_name)
    recent = db.get_recent_games_for_player(player_name, limit=10)
    running = True
    clock = p.time.Clock()
    while running:
        for e in p.event.get():
            if e.type == p.QUIT:
                p.quit(); sys.exit()
            elif e.type == p.KEYDOWN or e.type == p.MOUSEBUTTONDOWN:
                running = False
        s = p.Surface((WIDTH, HEIGHT))
        s.set_alpha(220)
        s.fill((10, 10, 10))
        screen.blit(s, (0, 0))
        title_font = p.font.SysFont("Arial", 30, True)
        title = title_font.render("Player Stats", True, p.Color("white"))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 20))
        small = p.font.SysFont("Arial", 20)
        y = 80
        lines = [
            f"Name: {stats['name']}",
            f"Wins: {stats['wins']}",
            f"Losses: {stats['losses']}",
            f"Draws: {stats['draws']}",
            f"Total games: {stats['total']}",
            f"Win rate: {stats['win_rate']:.1f} %"
        ]
        for line in lines:
            tx = small.render(line, True, p.Color("lightgray"))
            screen.blit(tx, (WIDTH//2 - 150, y)); y += 28
        sub = p.font.SysFont("Arial", 22, True)
        sub_t = sub.render("Recent games:", True, p.Color("white"))
        screen.blit(sub_t, (WIDTH//2 - 150, y + 10)); y += 40
        for g in recent:
            created = g["created_at"][:19].replace("T", " ")
            text = f"{created} | {g['opponent_type']} | {g['result']} | depth={g['ai_depth']} | {g['moves'][:60]}"
            tx = small.render(text, True, p.Color("lightgray"))
            screen.blit(tx, (WIDTH//2 - 350, y)); y += 20
            if y > HEIGHT - 40:
                break
        hint = small.render("Press any key or click to return", True, p.Color("gray"))
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 40))
        p.display.flip()
        clock.tick(30)

# ---------------------- MAIN ----------------------
def main():
    global flip_board
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    p.display.set_caption("Chess (levels + SAN + DB) - Clean UI")
    clock = p.time.Clock()
    load_images()

    # modern menu
    font = p.font.SysFont("Arial", 18)
    big_font = p.font.SysFont("Arial", 48, True)

    mode = menu_loop(screen)

    # Map mode choices to game setup
    if mode == "1":
        player_vs_ai = False
        ai_plays_white = False
        player_name = None
        opponent_name = None
        ai_level = "intermediate"
        # ask both names (PvP)
        p1 = get_text_input(screen, prompt="Player 1 name (White):", font=font)
        db.get_or_create_player(p1)
        p2 = get_text_input(screen, prompt="Player 2 name (Black):", font=font)
        db.get_or_create_player(p2)
        player_name = p1; opponent_name = p2

    elif mode == "2":
        player_vs_ai = True
        ai_plays_white = False
        player_name = None
        opponent_name = None
        # modern color / difficulty flow
        color_choice = choose_color_ui(screen)  # "1" => play as white, "2" => play as black
        ai_plays_white = True if color_choice == "2" else False
        # Auto flip board so player always sits at bottom
        flip_board = True if ai_plays_white else False
        ai_level = choose_difficulty_ui(screen)  # returns "beginner"/"intermediate"/"advanced"
        player_name = get_text_input(screen, prompt="Enter your name:", font=font)
        db.get_or_create_player(player_name)
        db.set_setting("ai_level", ai_level)

    elif mode == "3":
        # Scorecard -> then return to menu for a choice
        show_scoreboard(screen)
        mode = menu_loop(screen)
        # rerun mapping (simple approach: only handle PvP or PvAI after scoreboard)
        if mode == "1":
            player_vs_ai = False
            ai_plays_white = False
            player_name = None
            opponent_name = None
            ai_level = "intermediate"
            p1 = get_text_input(screen, prompt="Player 1 name (White):", font=font)
            db.get_or_create_player(p1)
            p2 = get_text_input(screen, prompt="Player 2 name (Black):", font=font)
            db.get_or_create_player(p2)
            player_name = p1; opponent_name = p2
        elif mode == "2":
            player_vs_ai = True
            ai_plays_white = False
            player_name = None
            opponent_name = None
            color_choice = choose_color_ui(screen)
            ai_plays_white = True if color_choice == "2" else False
            flip_board = True if ai_plays_white else False
            ai_level = choose_difficulty_ui(screen)
            player_name = get_text_input(screen, prompt="Enter your name:", font=font)
            db.get_or_create_player(player_name)
            db.set_setting("ai_level", ai_level)
        else:
            p.quit(); sys.exit()

    else:
        p.quit(); sys.exit()

    # ---------- Game setup ----------
    gs = ChessEngine.GameState()
    valid_moves = gs.getValidMoves()
    move_made = False
    selected_sq = ()
    player_clicks = []
    running = True
    move_log_shown = True
    last_move = None
    animate = None
    san_moves = []  # list of SAN strings (alternating white, black)

    while running:
        human_turn = (not player_vs_ai) or (gs.whiteToMove != ai_plays_white)

        for e in p.event.get():
            if e.type == p.QUIT:
                running = False; p.quit(); sys.exit()

            # keyboard shortcuts
            elif e.type == p.KEYDOWN:
                if e.key == p.K_f:
                    flip_board = not flip_board
                elif e.key == p.K_z:
                    gs.undoMove()
                    if san_moves:
                        san_moves.pop()
                    last_move = gs.moveLog[-1] if gs.moveLog else None
                    move_made = True
                elif e.key == p.K_r:
                    gs = ChessEngine.GameState()
                    valid_moves = gs.getValidMoves(); selected_sq = (); player_clicks = []
                    move_made = False; last_move = None; san_moves = []
                elif e.key == p.K_m:
                    move_log_shown = not move_log_shown

            # mouse input (only when it's human's turn and not animating)
            elif e.type == p.MOUSEBUTTONDOWN and human_turn and animate is None:
                x, y = p.mouse.get_pos()
                layout = get_panel_layout()
                if x >= BOARD_SIZE:
                    # Click on panel controls
                    if layout['undo'].collidepoint(x, y):
                        gs.undoMove()
                        if san_moves:
                            san_moves.pop()
                        last_move = gs.moveLog[-1] if gs.moveLog else None
                        move_made = True
                    elif layout['restart'].collidepoint(x, y):
                        gs = ChessEngine.GameState()
                        valid_moves = gs.getValidMoves()
                        selected_sq = (); player_clicks = []
                        move_made = False; last_move = None; san_moves = []
                    elif layout['toggle'].collidepoint(x, y):
                        move_log_shown = not move_log_shown
                    elif (x - layout['flip_center'][0]) ** 2 + (y - layout['flip_center'][1]) ** 2 <= layout['flip_radius'] ** 2:
                        flip_board = not flip_board
                    elif layout['header'].collidepoint(x, y):
                        # header click shows stats if name exists
                        if player_name:
                            show_stats_screen(screen, player_name, font)
                else:
                    # Click on board. Convert mouse pixel to board coords (game coords)
                    row, col = board_coords_from_mouse(x, y)
                    if selected_sq == (row, col):
                        selected_sq = (); player_clicks = []
                    else:
                        selected_sq = (row, col); player_clicks.append(selected_sq)
                    if len(player_clicks) == 2:
                        move = ChessEngine.Move(player_clicks[0], player_clicks[1], gs.board)
                        for valid in valid_moves:
                            if move == valid:
                                # compute SAN before making move
                                san = move_to_san(valid, gs)
                                san_moves.append(san)
                                animate = (valid, 0.0)
                                gs.makeMove(valid)
                                last_move = valid
                                move_made = True
                                selected_sq = (); player_clicks = []
                                break
                        if not move_made:
                            player_clicks = [selected_sq]

        # --- AI move ---
        if player_vs_ai and not human_turn and not gs.checkmate and not gs.stalemate and animate is None:
            ai_move = find_best_move(gs, level=ai_level)
            if ai_move is None:
                valid_moves = gs.getValidMoves()
                if valid_moves:
                    ai_move = random.choice(valid_moves)
            if ai_move:
                san = move_to_san(ai_move, gs)
                san_moves.append(san)
                animate = (ai_move, 0.0)
                gs.makeMove(ai_move)
                last_move = ai_move
                move_made = True

        # handle animation
        if animate:
            move_obj, progress = animate
            progress += ANIMATION_SPEED * clock.get_time() / 1000.0
            if progress >= 1.0:
                animate = None; progress = 1.0
            else:
                animate = (move_obj, progress)

        if move_made:
            valid_moves = gs.getValidMoves()
            move_made = False

        # ---- render ----
        draw_board(screen)
        draw_last_move(screen, last_move)
        highlight_square(screen, selected_sq)
        if selected_sq:
            legal = [(m.endRow, m.endCol) for m in valid_moves if m.startRow == selected_sq[0] and m.startCol == selected_sq[1]]
            draw_legal_moves(screen, legal)
        draw_pieces(screen, gs.board, animate_move=animate)

        # compute whether flip button is hovered
        mx, my = p.mouse.get_pos()
        layout = get_panel_layout()
        flip_hover = ((mx - layout['flip_center'][0]) ** 2 + (my - layout['flip_center'][1]) ** 2 <= layout['flip_radius'] ** 2) and (BOARD_SIZE <= mx <= WIDTH)
        draw_panel(screen, san_moves, move_log_shown, font, flip_btn_hover=flip_hover)

        # small header
        hdr_font = p.font.SysFont("Arial", 16, True)
        hdr_text = f"Player: {player_name or 'N/A'}"
        if player_vs_ai:
            hdr_text += f" | Opponent: AI ({ai_level})"
        else:
            hdr_text += f" | Opponent: {opponent_name or 'Human'}"
        hdr = hdr_font.render(hdr_text, True, p.Color("white"))
        screen.blit(hdr, (BOARD_SIZE + 10, 8))

        # ----- game over check -----
        status = gs.get_game_status()
        if status == "checkmate":
            show_game_over(screen, "checkmate", gs)
            winner_color = "White" if not gs.whiteToMove else "Black"

            if player_vs_ai:
                # Human perspective
                human_is_white = not ai_plays_white
                human_won = (winner_color == "White" and human_is_white) or (winner_color == "Black" and not human_is_white)

                # ensure AI player exists
                db.get_or_create_player("AI")
                if human_won:
                    db.record_game(player_name, "AI", "AI", "win", ' '.join(san_moves), ai_depth=0)
                    db.record_game("AI", "Human", player_name, "loss", ' '.join(san_moves), ai_depth=0)
                else:
                    db.record_game(player_name, "AI", "AI", "loss", ' '.join(san_moves), ai_depth=0)
                    db.record_game("AI", "Human", player_name, "win", ' '.join(san_moves), ai_depth=0)

            else:
                # PvP — update BOTH players
                white_player = player_name
                black_player = opponent_name

                if winner_color == "White":
                    db.record_game(white_player, "Human", black_player, "win", ' '.join(san_moves))
                    db.record_game(black_player, "Human", white_player, "loss", ' '.join(san_moves))
                else:
                    db.record_game(white_player, "Human", black_player, "loss", ' '.join(san_moves))
                    db.record_game(black_player, "Human", white_player, "win", ' '.join(san_moves))

            running = False

        elif status == "stalemate":
            show_game_over(screen, "stalemate", gs)

            if player_vs_ai:
                db.get_or_create_player("AI")
                db.record_game(player_name, "AI", "AI", "draw", ' '.join(san_moves), ai_depth=0)
                db.record_game("AI", "Human", player_name, "draw", ' '.join(san_moves), ai_depth=0)
            else:
                white_player = player_name
                black_player = opponent_name
                db.record_game(white_player, "Human", black_player, "draw", ' '.join(san_moves))
                db.record_game(black_player, "Human", white_player, "draw", ' '.join(san_moves))

            running = False

        p.display.flip()
        clock.tick(MAX_FPS)

    p.quit()

if __name__ == "__main__":
    main()
