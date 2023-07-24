import pygame
import sys
import os
import math

from pygame.locals import *
from data.assets import *


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
        self.kings = {}
        self.check = [False, None]
        self.grid = [[None for _ in range(8)] for i in range(8)]
        self.grid_cache = None
        self.cache = self.grid, self.piece_list, self.castle
        self.promo = "queen"


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
            self.pos = int((self.x - board_loc[0]) // SQUARE_SIZE), int(abs((self.y - board_loc[1]) // SQUARE_SIZE - 7))
            return self.pos
        return int((self.x - board_loc[0]) // SQUARE_SIZE), int(abs((self.y - board_loc[1]) // SQUARE_SIZE - 7))

    def check_valid(self, pos, board, checking=False, king=None):  # why did i implement it like this
        ret = {
            "valid": False,
            "passant": False,
            "target": None,
            "promo": False,
            "castle": None
        }
        if self.color != board.turn and not checking:
            return ret

        sign = 1 - 2 * (self.color == "black")
        movement_array = (int(pos[0] - self.pos[0]), int(pos[1] - self.pos[1]))  # fd, rd

        if movement_array in move_set[self.type]:
            ret["target"] = board.grid[pos[1]][pos[0]] if not checking else king
            if ret["target"] is not None and ret["target"].color == self.color:
                return ret
            null = ret["target"] is None
            match self.type:
                case "pawn":
                    ret["passant"] = null and list(pos) == board.en_passant[0] and (
                            movement_array[0] == 1 or movement_array[0] == -1)
                    if (not null and movement_array[0] != 0 and movement_array[1] * sign > 0) or ret["passant"]:
                        ret["valid"] = True
                        if not checking:
                            if pos[1] == 7 or pos[1] == 0:
                                ret["promo"] = True

                    elif not null or movement_array[0] != 0:
                        return ret

                    if not self.moved and movement_array[1] == 2 * sign:
                        if board.grid[pos[1] - 1 + 2 * (movement_array[1] < 0)][pos[0]] is None:
                            board.en_passant = ([self.pos[0], self.pos[1] + sign], self)
                            ret["valid"] = True

                    if movement_array[1] == 1 * sign:
                        ret["valid"] = True
                        if pos[1] == 7 or pos[1] == 0:
                            ret["promo"] = True  # now implement promotion... bruh i think i need to implement UI

                case "knight":
                    if (movement_array[0] == 2 or movement_array[0] == -2) and (
                            movement_array[1] == 1 or movement_array[1] == -1):
                        ret["valid"] = True
                    elif (movement_array[0] == 1 or movement_array[0] == -1) and (
                            movement_array[1] == 2 or movement_array[1] == -2):
                        ret["valid"] = True

                case "bishop":
                    ret["valid"] = True
                    rank_dir = 1 - 2 * (movement_array[1] < 0)
                    file_dir = 1 - 2 * (movement_array[0] < 0)
                    for i in range(self.pos[1] + rank_dir, pos[1] + rank_dir, rank_dir):
                        destination = board.grid[i][
                            self.pos[0] + i * rank_dir * file_dir - self.pos[1] * rank_dir * file_dir]
                        if destination is not None:
                            if ret["target"] is not None:
                                if destination.pos != ret["target"].pos:
                                    ret["valid"] = False
                            else:
                                ret["valid"] = False

                case "rook":
                    ret["valid"] = True
                    rank_dir = 1 - 2 * (movement_array[1] < 0) if movement_array[1] != 0 else 0
                    file_dir = 1 - 2 * (movement_array[0] < 0) if movement_array[0] != 0 else 0
                    if movement_array[1] == 0:
                        for i in range(self.pos[0] + file_dir, pos[0] + file_dir, file_dir):
                            destination = board.grid[self.pos[1]][i]
                            if destination is not None:
                                if ret["target"] is not None:
                                    if destination.pos != ret["target"].pos:
                                        ret["valid"] = False
                                else:
                                    ret["valid"] = False
                    elif movement_array[0] == 0:
                        for i in range(self.pos[1] + rank_dir, pos[1] + rank_dir, rank_dir):
                            destination = board.grid[i][self.pos[0]]
                            if destination is not None:
                                if ret["target"] is not None:
                                    if destination.pos != ret["target"].pos:
                                        ret["valid"] = False
                                else:
                                    ret["valid"] = False
                    if ret["valid"] and not self.moved and not checking:
                        board.castle[self.color == "black"][self.pos[0] == 0] = False

                case "queen":
                    ret["valid"] = True
                    if movement_array in move_set["bishop"]:
                        rank_dir = 1 - 2 * (movement_array[1] < 0)
                        file_dir = 1 - 2 * (movement_array[0] < 0)
                        for i in range(self.pos[1] + rank_dir, pos[1] + rank_dir, rank_dir):
                            destination = board.grid[i][
                                self.pos[0] + i * rank_dir * file_dir - self.pos[1] * rank_dir * file_dir]
                            if destination is not None:
                                if ret["target"] is not None:
                                    if destination.pos != ret["target"].pos:
                                        ret["valid"] = False
                                else:
                                    ret["valid"] = False
                    elif movement_array in move_set["rook"]:
                        rank_dir = 1 - 2 * (movement_array[1] < 0) if movement_array[1] != 0 else 0
                        file_dir = 1 - 2 * (movement_array[0] < 0) if movement_array[0] != 0 else 0
                        if movement_array[1] == 0:
                            for i in range(self.pos[0] + file_dir, pos[0] + file_dir, file_dir):
                                destination = board.grid[self.pos[1]][i]
                                if destination is not None:
                                    if ret["target"] is not None:
                                        if destination.pos != ret["target"].pos:
                                            ret["valid"] = False
                                    else:
                                        ret["valid"] = False
                        elif movement_array[0] == 0:
                            for i in range(self.pos[1] + rank_dir, pos[1] + rank_dir, rank_dir):
                                destination = board.grid[i][self.pos[0]]
                                if destination is not None:
                                    if ret["target"] is not None:
                                        if destination.pos != ret["target"].pos:
                                            ret["valid"] = False
                                    else:
                                        ret["valid"] = False

                case "king":
                    if movement_array[0] == 2 and board.castle[self.color == "black"][0]:
                        if check_king(board, self, pos, ret["target"]) and check_king(board, self, [pos[0] - 1, pos[1]],
                                                                                      ret["target"]):
                            ret["valid"] = True
                            if not checking:
                                ret["castle"] = "left"
                                board.castle[self.color == "black"] = [False, False]
                    elif movement_array[0] == -2 and board.castle[self.color == "black"][1]:
                        if check_king(board, self, pos, ret["target"]) and check_king(board, self, [pos[0] + 1, pos[1]],
                                                                                      ret["target"]) and \
                                board.grid[pos[1]][pos[0] - 1] is None:
                            ret["valid"] = True
                            if not checking:
                                ret["castle"] = "right"
                                board.castle[self.color == "black"] = [False, False]
                    elif movement_array[0] != 2 and movement_array[0] != -2:
                        if check_king(board, self, pos, ret["target"]):
                            board.castle[self.color == "black"] = [False, False]
                            ret["valid"] = True

            return ret
        else:
            return ret


def check_check(board, piece, king_pos=None, checking=False, king=None):
    result = piece.check_valid(king_pos, board, checking=True, king=king)
    if result["valid"]:
        board.check = [True, piece] if not checking else board.check
        return True
    return False


def check_king(board, king, pos, target):
    cache = king.pos
    for piece in board.piece_list:
        if piece.color != king.color and piece != target:
            movement_arr = pos[0] - piece.pos[0], pos[1] - piece.pos[1]
            if movement_arr in move_set[piece.type]:
                if piece.type == "king":
                    return False
                king.pos = pos
                if check_check(board, piece, king_pos=pos, checking=True, king=king):
                    king.pos = cache
                    return False
    king.pos = cache
    return True


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
                    board.kings['black'] = init_piece
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
                    board.kings['white'] = init_piece
                case _:
                    init_piece = None
            init_piece.get_board_pos(board_loc, init=True)
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
    "rook": (
        (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (-1, 0), (-2, 0), (-3, 0), (-4, 0), (-5, 0), (-6, 0),
        (-7, 0),
        (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, -1), (0, -2), (0, -3), (0, -4), (0, -5), (0, -6),
        (0, -7)),
    "king": ((1, 1), (1, 0), (1, -1), (0, 1), (0, -1), (-1, 1), (-1, 0), (-1, -1), (2, 0), (-2, 0))
}
move_set["queen"] = tuple(list(move_set["bishop"]) + list(move_set["rook"]))

pygame.display.set_mode(DISPLAY_SIZE, 0, 32)
pygame.display.set_caption("PyChess")
clock = pygame.time.Clock()
display = pygame.Surface(DISPLAY_SIZE)
screen = pygame.display.set_mode(WINDOW_SIZE, 0, 32)
board_loc = [(DISPLAY_SIZE[0] - 128) // 2, (DISPLAY_SIZE[1] - 128) // 2]
board = Board(pygame.image.load("data/chess_sprites/board.png").convert(), (DISPLAY_SIZE[0] - 128) // 2,
              (DISPLAY_SIZE[1] - 128) // 2)

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
                pos = (int(px), int(abs(py - 7)))
                result = clicked_piece.check_valid(pos, board)
                if result["valid"]:
                    board.cache = board.grid.copy(), board.piece_list.copy(), tuple(board.en_passant)
                    board.grid[pos[1]][pos[0]] = board.grid[clicked_piece.pos[1]][clicked_piece.pos[0]]
                    board.grid[clicked_piece.pos[1]][clicked_piece.pos[0]] = None

                    if result["castle"] is not None:
                        if result["castle"] == "right":
                            rock = board.grid[pos[1]][0]
                            rock.pos = (pos[0] + 1, pos[1])
                            rock.x = board.x + px * 16 + 16
                            rock.y = board.y + py * 16
                            rock.update()
                            rock = None
                            board.grid[pos[1]][pos[0] + 1] = board.grid[pos[1]][0]
                            board.grid[pos[1]][0] = None
                        elif result["castle"] == "left":
                            rock = board.grid[pos[1]][7]
                            rock.pos = (pos[0] - 1, pos[1])
                            rock.x = board.x + px * 16 - 16
                            rock.y = board.y + py * 16
                            rock.update()
                            rock = None
                            board.grid[pos[1]][pos[0] - 1] = board.grid[pos[1]][7]
                            board.grid[pos[1]][7] = None

                    elif result["passant"]:
                        board.piece_list.remove(board.en_passant[1])
                        board.grid[board.en_passant[1].pos[1]][board.en_passant[1].pos[0]] = None

                    if not check_king(board, board.kings[board.turn], board.kings[board.turn].pos, target=None) and clicked_piece.type != "king":
                            board.grid = board.cache[0]
                            board.piece_list = board.cache[1]
                            board.en_passant = board.cache[2]
                            drag = False
                            clicked_piece.drag = False
                            clicked_piece.offset = [0, 0]
                            clicked_piece.x = og_square_loc[0]
                            clicked_piece.y = og_square_loc[1]
                            hover_square_loc = None
                            clicked_piece.update()
                            clicked_piece = None

                    else:
                        if result["target"] is not None:
                            if result["target"].type == "rook":
                                match result["target"].pos:
                                    case (0, 0):
                                        board.castle[0][1] = False
                                    case (0, 7):
                                        board.castle[0][0] = False
                                    case (7, 0):
                                        board.castle[1][1] = False
                                    case (7, 7):
                                        board.castle[1][0] = False
                            board.piece_list.remove(result["target"])

                        if result["promo"]:
                            clicked_piece.type = board.promo
                            clicked_piece.load_image()

                        clicked_piece.pos = pos
                        clicked_piece.moved = True
                        board.full_move += 1

                        if board.turn == 'white':
                            board.turn = 'black'
                        else:
                            board.turn = 'white'

                        if board.en_passant[1] != clicked_piece:
                            board.en_passant = ([], None)

                        drag = False
                        clicked_piece.drag = False
                        clicked_piece.offset = [0, 0]
                        clicked_piece.x = board.x + px * 16
                        clicked_piece.y = board.y + py * 16
                        clicked_piece.update()
                        clicked_piece = None

                else:
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
