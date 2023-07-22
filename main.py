import pygame
import sys
import os
import math

from pygame.locals import *
from data.assets import *



class Piece:
    def __init__(self, ptype, color, x, y):
        self.type = ptype
        self.color = color
        self.image = None
        self.x = x
        self.y = y
        self.hold = ()
        self.pos = ()  # x, y
        self.rect = None
        self.drag = False
        self.scaled = None
        self.offset = [0, 0]
        self.moved = False

    def display(self, surface, scaled=False):
        if self.image is not None:
            if scaled:
                center_x = self.scaled.get_width() / 2
                center_y = self.scaled.get_height() / 2
                blit_center(surface, self.scaled, [int(self.rect.x) + center_x, int(self.rect.y) + center_y])
            else:
                center_x = self.image.get_width() / 2
                center_y = self.image.get_height() / 2
                blit_center(surface, self.image, [int(self.rect.x) + center_x, int(self.rect.y) + center_y])

    def load_image(self):
        self.image = pygame.image.load(f"data/chess_sprites/{self.type}_{self.color}.png").convert()
        self.image.set_colorkey(PIECE_COLORKEY)
        self.scaled = pygame.transform.scale(self.image, (24, 24))
        self.rect = pygame.Rect(self.x, self.y, 16, 16)

    def update(self):
        self.rect.x = self.x + self.offset[0]
        self.rect.y = self.y + self.offset[1]

    def set_hold(self):
        self.hold = (self.rect.x, self.rect.y)

    def get_board_pos(self, board_loc, init=False):
        if init:
            self.pos = (self.x - board_loc[0]) // SQUARE_SIZE, abs((self.y - board_loc[1]) // SQUARE_SIZE - 7)
            return self.pos
        return (self.x - board_loc[0]) // SQUARE_SIZE, (self.y - board_loc[1]) // SQUARE_SIZE

    def check_valid(self, pos, board):  # why did i implement it like this
        if self.color != board.turn:
            return False
        sign = 1 - 2 * (self.color == "black")
        pos = int(pos[0]), int(pos[1])
        self.pos = int(self.pos[0]), int(self.pos[1])
        movement_array = (int(pos[0] - self.pos[0]), int(pos[1] - self.pos[1]))  # fd, rd
        valid = False
        if movement_array == (0, 0):
            return None
        if movement_array in move_set[self.type]:
            target = board.grid[pos[1]][pos[0]]
            if target is not None and target.color == self.color:
                return False
            null = target is None
            match self.type:
                case "pawn":
                    passant = null and list(pos) == board.en_passant[0] and (movement_array[0] == 1 or movement_array[0] == -1)
                    if (not null and movement_array[0] != 0 and movement_array[1] * sign > 0) or passant:
                        if not passant:
                            board.piece_list.remove(target)
                        else:
                            board.piece_list.remove(board.en_passant[1])
                            board.grid[board.en_passant[1].pos[1]][board.en_passant[1].pos[0]] = None
                        board.grid[pos[1]][pos[0]] = board.grid[self.pos[1]][self.pos[0]]
                        board.grid[self.pos[1]][self.pos[0]] = None
                        board.full_move += 1
                        board.en_passant = ([], None)
                        self.pos = pos
                        self.moved = True
                        if pos[1] == 7 or pos[1] == 0:
                            self.type = board.promo
                            self.load_image()
                        return True
                    elif not null or movement_array[0] != 0:
                        return False
                    if not self.moved and movement_array[1] == 2 * sign:
                        if board.grid[pos[1] - 1 + 2 * (movement_array[1] < 0)][pos[0]] is None:
                            board.grid[pos[1]][pos[0]] = board.grid[self.pos[1]][self.pos[0]]
                            board.grid[self.pos[1]][self.pos[0]] = None
                            board.full_move += 1
                            self.pos = pos
                            self.moved = True
                            board.en_passant = ([self.pos[0], self.pos[1] - sign], self)
                            return True
                    if movement_array[1] == 1 * sign:
                        valid = True
                        if pos[1] == 7 or pos[1] == 0:
                            self.type = "queen"
                            self.load_image()  # now implement promotion here... bruh i think i need to implement UI
                case "knight":
                    if (movement_array[0] == 2 or movement_array[0] == -2) and (
                            movement_array[1] == 1 or movement_array[1] == -1):
                        valid = True
                    elif (movement_array[0] == 1 or movement_array[0] == -1) and (
                            movement_array[1] == 2 or movement_array[1] == -2):
                        valid = True
                case "bishop":
                    valid = True
                    rank_dir = 1 - 2 * (movement_array[1] < 0)
                    file_dir = 1 - 2 * (movement_array[0] < 0)
                    for i in range(self.pos[1] + rank_dir, pos[1] + rank_dir, rank_dir):
                        destination = board.grid[i][
                            self.pos[0] + i * rank_dir * file_dir - self.pos[1] * rank_dir * file_dir]
                        if destination is not None and destination != target:
                            valid = False
                case "rook":
                    valid = True
                    rank_dir = 1 - 2 * (movement_array[1] < 0) if movement_array[1] != 0 else 0
                    file_dir = 1 - 2 * (movement_array[0] < 0) if movement_array[0] != 0 else 0
                    if movement_array[1] == 0:
                        for i in range(self.pos[0] + file_dir, pos[0] + file_dir, file_dir):
                            destination = board.grid[self.pos[1]][i]
                            if destination is not None and destination != target:
                                valid = False
                    elif movement_array[0] == 0:
                        for i in range(self.pos[1] + rank_dir, pos[1] + rank_dir, rank_dir):
                            destination = board.grid[i][self.pos[0]]
                            if destination is not None and destination != target:
                                valid = False
                    if valid and not self.moved:
                        board.castle[self.color == "black"][self.pos[0] == 0] = False

            if valid:
                board.grid[pos[1]][pos[0]] = board.grid[self.pos[1]][self.pos[0]]
                board.grid[self.pos[1]][self.pos[0]] = None
                board.full_move += 1
                board.en_passant = ([], None)
                board.piece_list.remove(target) if not null else ...
                self.pos = pos
                self.moved = True
            return valid

        else:
            return False


class Board:
    def __init__(self, image, x, y):
        self.image = image
        self.x = x
        self.y = y
        self.turn = None
        self.castle = [[False, False], [False, False]]
        self.half_move = 0
        self.full_move = 0
        self.en_passant = [[], []]
        self.piece_list = []
        self.grid = [[None for _ in range(8)] for i in range(8)]
        self.promo = "queen"


# 3d3d3d
SQUARE_SIZE = 16
PIECE_COLORKEY = (255, 232, 232)

pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 512)  # freq, size, mono/stereo, buffer
pygame.mixer.set_num_channels(64)

frame_rate = 60
WINDOW_SIZE = (1920, 1080)
DISPLAY_SIZE = (320, 180)
MONITOR_SIZE = (pygame.display.Info().current_w, pygame.display.Info().current_h)

move_set = {
    "pawn": ((0, 1), (1, 1), (-1, 1), (0, 2), (0, -1), (1, -1), (-1, -1), (0, -2)),
    "knight": ((2, 1), (2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2), (-2, 1), (-2, -1)),
    "bishop": (
        (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (1, -1), (2, -2), (3, -3), (4, -4), (5, -5), (6, -6),
        (7, -7), (-1, 1), (-2, 2), (-3, 3), (-4, 4), (-5, 5), (-6, 6), (-7, 7), (-1, -1), (-2, -2), (-3, -3), (-4, -4),
        (-5, -5), (-6, -6), (-7, -7)),
    "rook": ((1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (-1, 0), (-2, 0), (-3, 0), (-4, 0), (-5, 0), (-6, 0), (-7, 0),
             (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, -1), (0, -2), (0, -3), (0, -4), (0, -5), (0, -6), (0, -7)),
    "king": ((1, 1), (1, 0), (1, -1), (0, 1), (0, -1), (-1, 1), (-1, 0), (-1, -1), (2, 0), (-2, 0))
}
move_set["queen"] = tuple(list(move_set["bishop"]) + list(move_set["rook"]))


def read_fen(fen, board):  # default fen: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
    parts = fen.split()
    board_state = parts[0].split('/')
    rank = 7
    file = 0
    for row in board_state:
        for c in row:
            if c.isnumeric():
                file += int(c)
                continue
            x = board.x + file * SQUARE_SIZE
            y = board.y + (7 - rank) * SQUARE_SIZE
            match c:
                case 'p':
                    init_piece = Piece('pawn', 'black', x, y)
                    init_piece.load_image()
                case 'n':
                    init_piece = Piece('knight', 'black', x, y)
                    init_piece.load_image()
                case 'b':
                    init_piece = Piece('bishop', 'black', x, y)
                    init_piece.load_image()
                case 'r':
                    init_piece = Piece('rook', 'black', x, y)
                    init_piece.load_image()
                case 'q':
                    init_piece = Piece('queen', 'black', x, y)
                    init_piece.load_image()
                case 'k':
                    init_piece = Piece('king', 'black', x, y)
                    init_piece.load_image()
                case 'P':
                    init_piece = Piece('pawn', 'white', x, y)
                    init_piece.load_image()
                case 'N':
                    init_piece = Piece('knight', 'white', x, y)
                    init_piece.load_image()
                case 'B':
                    init_piece = Piece('bishop', 'white', x, y)
                    init_piece.load_image()
                case 'R':
                    init_piece = Piece('rook', 'white', x, y)
                    init_piece.load_image()
                case 'Q':
                    init_piece = Piece('queen', 'white', x, y)
                    init_piece.load_image()
                case 'K':
                    init_piece = Piece('king', 'white', x, y)
                    init_piece.load_image()
                case _:
                    init_piece = None
            board.grid[rank][file] = init_piece
            board.piece_list.append(init_piece) if init_piece is not None else ...
            file += 1
        rank -= 1
        file = 0
    match parts[1][0]:
        case 'w':
            board.turn = 'white'
        case 'b':
            board.turn = 'black'

    board.castle[0][0] = ('K' in parts[2])
    board.castle[0][1] = ('Q' in parts[2])
    board.castle[1][0] = ('k' in parts[2])
    board.castle[1][1] = ('q' in parts[2])

    if parts[3][0] != '-':
        board.en_passant = [ord(parts[3][0]) - ord('a'), int(parts[3][1]) - 1]

    board.half_move = int(parts[4][0])
    board.full_move = int(parts[5][0])


pygame.display.set_mode(DISPLAY_SIZE, 0, 32)
pygame.display.set_caption("PyChess")
clock = pygame.time.Clock()
display = pygame.Surface(DISPLAY_SIZE)
screen = pygame.display.set_mode(WINDOW_SIZE, 0, 32)
board_loc = [(DISPLAY_SIZE[0] - 128) // 2, (DISPLAY_SIZE[1] - 128) // 2]
board = Board(pygame.image.load("data/chess_sprites/board.png").convert(), (DISPLAY_SIZE[0] - 128) // 2, (DISPLAY_SIZE[1] - 128) // 2)

clicked_piece = None
drag = False

hover_square = pygame.Surface((16, 16))
hover_square.fill((255, 0, 0))
hover_square.set_alpha(128)
hover_square_loc = None

og_square = pygame.Surface((16, 16))
og_square.fill((0, 0, 255))
og_square.set_alpha(128)
og_square_loc = None

full_screen = False
running = True

read_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", board)

while running:
    display.fill((50, 50, 50))
    mx, my = pygame.mouse.get_pos()
    mx = mx * (DISPLAY_SIZE[0] / WINDOW_SIZE[0])
    my = my * (DISPLAY_SIZE[1] / WINDOW_SIZE[1])
    mouse_rect = pygame.Rect(mx, my, 1, 1)
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type == MOUSEBUTTONDOWN:
            if event.button == 1:
                for piece in board.piece_list:
                    if piece.rect.colliderect(mouse_rect) and piece.color == board.turn:
                        centre_x = piece.rect.x + 8
                        centre_y = piece.rect.y + 8
                        piece.set_hold()
                        piece.get_board_pos(board_loc, init=True)
                        og_square_loc = piece.hold
                        piece.offset = [piece.rect.x - 4 - centre_x, piece.rect.y - 4 - centre_y]
                        piece.x = mx
                        piece.y = my
                        piece.drag = True
                        drag = True
                        piece.update()
                        clicked_piece = piece
        if event.type == MOUSEBUTTONUP:
            if event.button == 1 and drag:
                px = (mx - board.x) // 16
                py = (my - board.y) // 16
                valid = clicked_piece.check_valid([px, abs(py - 7)], board)
                if valid or valid is None:
                    drag = False
                    clicked_piece.drag = False
                    clicked_piece.offset = [0, 0]
                    clicked_piece.x = board.x + px * 16
                    clicked_piece.y = board.y + py * 16
                    clicked_piece.update()
                    clicked_piece = None
                    if valid is not None:
                        if board.turn == 'white':
                            board.turn = 'black'
                        else:
                            board.turn = 'white'
                elif not valid:
                    drag = False
                    clicked_piece.drag = False
                    clicked_piece.offset = [0, 0]
                    clicked_piece.x = og_square_loc[0]
                    clicked_piece.y = og_square_loc[1]
                    hover_square_loc = None
                    clicked_piece.update()
                    clicked_piece = None

        if event.type == MOUSEMOTION and drag:
            clicked_piece.x = mx
            clicked_piece.y = my
            hover_square_loc = (int(board.x + ((mx - board.x) // 16) * 16), int(board.y + ((my - board.y) // 16) * 16))
            clicked_piece.update()

    display.blit(board.image, (board.x, board.y))
    if og_square_loc is not None:
        display.blit(og_square, og_square_loc)
    if hover_square_loc is not None and hover_square_loc != og_square_loc:
        display.blit(hover_square, hover_square_loc)
    for piece in board.piece_list:
        piece.display(display, scaled=piece.drag)

    pygame.draw.rect(display, (255, 255, 255), mouse_rect)
    scaled_display = pygame.transform.scale(display, WINDOW_SIZE)
    screen.blit(scaled_display, (0, 0))
    pygame.display.update()
    clock.tick(frame_rate)
