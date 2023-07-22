import ast
import math
import pygame
import os

global e_colorkey
e_colorkey = (255, 255, 255)


def set_global_colorkey(colorkey):
    global e_colorkey
    e_colorkey = colorkey


def load_txt(path):
    with open(path, 'r') as fp:
        return fp.read().splitlines()


def draw_txt(text, font, color, surface, x, y):
    textobj = font.render(text, 1, color)
    textrect = textobj.get_rect()
    textrect.topleft = (x, y)
    surface.blit(textobj, textrect)


def load_background_objs(path):
    background_objs_temp = load_txt(path)
    background_objs = []
    for i in background_objs_temp:
        temp = []
        i = i.split('/')
        for x in i:
            x = ast.literal_eval(x)
            temp.append(x)
        background_objs.append(temp)
    return background_objs


def apply_basic_forces(entity, movdir, frameRate, tile_rects, velocity, fcoeff):
    ent_movement = [0, 0]
    ent_movement[0] += entity.x_momentum
    moving_right = movdir[0]
    moving_left = movdir[1]
    if moving_right:
        if entity.flip_x:
            entity.flip_x = False
        entity.x_momentum = entity.x_momentum + velocity / frameRate if entity.x_momentum <= entity.MAX_X else entity.MAX_X
    if moving_left:
        if not entity.flip_x:
            entity.flip_x = True
        entity.x_momentum = entity.x_momentum - velocity / frameRate if entity.x_momentum >= -entity.MAX_X else -entity.MAX_X
    if moving_left == moving_right:
        if entity.x_momentum > 0:
            entity.x_momentum = entity.x_momentum - min(math.ceil(entity.x_momentum * fcoeff),
                                                        velocity / frameRate) if entity.x_momentum >= 0.01 else 0
        if entity.x_momentum < 0:
            entity.x_momentum = entity.x_momentum - max(-math.ceil(abs(entity.x_momentum) * fcoeff),
                                                        -velocity / frameRate) if entity.x_momentum <= -0.01 else 0
    ent_movement[1] += entity.y_momentum
    entity.y_momentum = entity.y_momentum + velocity / frameRate if entity.y_momentum <= entity.MAX_Y else entity.MAX_Y

    return ent_movement, entity.move(ent_movement, tile_rects)


# entity obj physics
class ObjectEnt:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def collision_test(self, tile_list):
        collision_list = []
        for tile in tile_list:
            if self.rect.colliderect(tile):
                collision_list.append(tile)
        return collision_list

    def move(self, movementarr, tiles, ramps=[]):
        collision_types = {"top": False, "bottom": False, "left": False, "right": False, "dat": []}
        self.rect.x += movementarr[0]
        collision_list = self.collision_test(tiles)
        for tile in collision_list:
            markers = [False, False, False, False]
            if movementarr[0] > 0:
                self.rect.right = tile.left
                collision_types['right'] = True
                markers[0] = True
            if movementarr[0] < 0:
                self.rect.left = tile.right
                collision_types['left'] = True
                markers[1] = True
            collision_types["dat"].append([tile, markers])
        self.rect.y += movementarr[1]
        collision_list = self.collision_test(tiles)
        for tile in collision_list:
            markers = [False, False, False, False]
            if movementarr[1] > 0:
                self.rect.bottom = tile.top
                collision_types['bottom'] = True
                markers[2] = True
            if movementarr[1] < 0:
                self.rect.top = tile.bottom
                collision_types['top'] = True
                markers[3] = True
            collision_types["dat"].append([tile, markers])
        self.x = self.rect.x
        self.y = self.rect.y
        return collision_types


def blit_center(surf, surf2, pos):
    x = int(surf2.get_width() / 2)
    y = int(surf2.get_height() / 2)
    surf.blit(surf2, (pos[0] - x, pos[1] - y))


class Entity:
    def __init__(self, x, y, width=0, height=0, ent_type=None):
        self.MAX_X = 3
        self.MAX_Y = 4
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.obj = None
        self.type = ent_type
        self.flip_x = False
        self.flip_y = False
        self.anims = {}
        self.anim_type = None
        self.anim_frame = None
        self.image = None
        self.offset = [0, 0]
        self.rotation = 0
        self.state = 0
        self.alpha = None
        self.y_momentum = 0
        self.x_momentum = 0
        self.color_key = (255, 255, 255)
        self.masks = {}

    def init_obj(self, width=0, height=0, custom=True):
        if not custom:
            width = self.width
            height = self.height
        self.obj = ObjectEnt(self.x, self.y, width, height)

    def move(self, movement, platforms, ramps=[]):
        collisions = self.obj.move(movement, platforms, ramps)
        self.x = self.obj.rect.x
        self.y = self.obj.rect.y
        return collisions

    def load_anims(self, path, frame_amt, frame_time, mask=False):
        name = path.split('/')[-1]
        frames = []
        mask_list = []
        for i in range(int(frame_amt)):
            image = pygame.image.load(f"{path}/{name}_{i}.png").convert()
            # make white transparent
            image.set_colorkey(self.color_key)
            if self.obj is None:  # if you want to load anims before the hitbox, assumes all frames have same dimensions
                self.width = image.get_width()
                self.height = image.get_height()
            if mask:
                masks = pygame.mask.from_surface(image)
                mask_list.append(masks)
            frames.append(image)
        self.masks[name] = mask_list
        self.anims[name] = [frames, frame_time]

    def run_anim(self, frame, tag=None, force=False):
        if tag is None:
            tag = self.anim_type
        elif force or self.anim_type != tag:
            self.state = 0
        self.anim_type = tag
        if frame % int(self.anims[tag][1][self.state]) == 0:
            self.state += 1
            if self.state >= len(self.anims[tag][0]):
                self.state = 0
        self.anim_frame = self.anims[tag][0][self.state]

    def display_outline(self, surface, scroll):
        mask_img = self.masks[self.anim_type][self.state].to_surface()
        mask_img = pygame.transform.flip(mask_img, self.flip_x, self.flip_y)
        mask_img.set_colorkey((0, 0, 0))
        center_x = mask_img.get_width() / 2
        center_y = mask_img.get_height() / 2
        blit_center(surface, mask_img, [int(self.x) - scroll[0] + self.offset[0] + center_x + 1,
                                        int(self.y) - scroll[1] + self.offset[1] + center_y])
        blit_center(surface, mask_img, [int(self.x) - scroll[0] + self.offset[0] + center_x - 1,
                                        int(self.y) - scroll[1] + self.offset[1] + center_y])
        blit_center(surface, mask_img, [int(self.x) - scroll[0] + self.offset[0] + center_x,
                                        int(self.y) - scroll[1] + self.offset[1] + center_y + 1])
        blit_center(surface, mask_img, [int(self.x) - scroll[0] + self.offset[0] + center_x,
                                        int(self.y) - scroll[1] + self.offset[1] + center_y - 1])

    def set_maxvel(self, velocities):
        self.MAX_X, self.MAX_Y = velocities[0], velocities[1]

    def set_colorkey(self, colorkey):
        self.color_key = colorkey

    def set_pos(self, x, y):
        self.x = x
        self.y = y
        self.obj.x = x
        self.obj.y = y
        self.obj.rect.x = x
        self.obj.rect.y = y

    def set_action(self, anim_type, force=False):
        if (self.anim_type == anim_type) and not force:
            pass
        else:
            self.anim_type = anim_type
            self.run_anim(0, anim_type, True)

    def set_offset(self, offset):
        self.offset = offset

    def set_flip_x(self, arg):
        self.flip_x = arg

    def set_flip_y(self, arg):
        self.flip_y = arg

    def get_center(self):
        x = self.x + int(self.size_x / 2)
        y = self.y + int(self.size_y / 2)
        return [x, y]

    def get_curr_img(self):
        return self.anim_frame

    def get_entity_angle(self, entity_2):  # angle to the other entity
        x1 = self.x + int(self.width / 2)
        y1 = self.y + int(self.height / 2)
        x2 = entity_2.x + int(entity_2.width / 2)
        y2 = entity_2.y + int(entity_2.width / 2)
        angle = math.atan((y2 - y1) / (x2 - x1))
        if x2 < x1:
            angle += math.pi
        return angle

    def display(self, surface, scroll):
        image_to_render = pygame.transform.flip(self.anim_frame, self.flip_x, self.flip_y).copy()
        if image_to_render is not None:
            center_x = image_to_render.get_width() / 2
            center_y = image_to_render.get_height() / 2
            image_to_render = pygame.transform.rotate(image_to_render, self.rotation)
            if self.alpha is not None:
                image_to_render.set_alpha(self.alpha)
            blit_center(surface, image_to_render, [int(self.x) - scroll[0] + self.offset[0] + center_x,
                                                   int(self.y) - scroll[1] + self.offset[1] + center_y])


def particle_file_sort(l):
    l2 = []
    for obj in l:
        l2.append(int(obj[:-4]))
    l2.sort()
    l3 = []
    for obj in l2:
        l3.append(str(obj) + '.png')
    return l3


global particle_images
particle_images = {}


def load_particle_images(path):
    global particle_images, e_colorkey
    file_list = os.listdir(path)
    for folder in file_list:
        try:
            img_list = os.listdir(path + '/' + folder)
            img_list = particle_file_sort(img_list)
            images = []
            for img in img_list:
                images.append(pygame.image.load(path + '/' + folder + '/' + img).convert())
            for img in images:
                img.set_colorkey(e_colorkey)
            particle_images[folder] = images.copy()
        except Exception:
            pass


class Particle(ObjectEnt):

    def __init__(self, x, y, particle_type, motion, decay_rate, start_frame, width, height, custom_color=None):
        super().__init__(x, y, width, height)
        self.x = x
        self.y = y
        self.type = particle_type
        self.motion = motion
        self.decay_rate = decay_rate
        self.color = custom_color
        self.frame = start_frame

    def draw(self, surface, scroll):
        global particle_images
        if self.frame > len(particle_images[self.type]) - 1:
            self.frame = len(particle_images[self.type]) - 1
        if self.color is None:
            blit_center(surface, particle_images[self.type][int(self.frame)], (self.x - scroll[0], self.y - scroll[1]))
        else:
            blit_center(surface, swap_color(particle_images[self.type][int(self.frame)], (255, 255, 255), self.color),
                        (self.x - scroll[0], self.y - scroll[1]))

    def update(self, frame):
        self.frame += self.decay_rate
        running = True
        if self.frame > len(particle_images[self.type]) - 1:
            running = False
        self.x += self.motion[0]
        self.y += self.motion[1]
        return running


class JumperObj:  # a jump arrow up, but probably can be repurposed for other stuff
    def __init__(self, loc, image):
        self.loc = loc
        self.image = image

    def render(self, surf, scroll):
        surf.blit(self.image, (self.loc[0] - scroll[0], self.loc[1] - scroll[1]))

    def get_rect(self):
        return pygame.Rect(self.loc[0], self.loc[1], 8, 9)

    def collision_test(self, rect):
        jumper_rect = self.get_rect()
        return jumper_rect.colliderect(rect)


def swap_color(img, old_c, new_c):
    global e_colorkey
    img.set_colorkey(old_c)
    surf = img.copy()
    surf.fill(new_c)
    surf.blit(img, (0, 0))
    surf.set_colorkey(e_colorkey)
    return surf
