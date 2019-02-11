import pygame as pg
import traceback
from math import pi, sin, cos, inf
from pytmx.util_pygame import load_pygame


W_WIDTH = 1024
W_HEIGHT = 768
FPS = 60
TWO_PI = pi * 2

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (50, 100, 20)
DARKGREEN = (24, 50, 10)
GREY = (100, 100, 100)

vec = pg.math.Vector2


def load_map(file):
    tiled_map = load_pygame('assets/{}.tmx'.format(file))
    # create empty surface based on tile map dimensions
    bg_image = pg.Surface((tiled_map.width * tiled_map.tilewidth,
                          tiled_map.height * tiled_map.tileheight))
    map_objects = tiled_map.get_layer_by_name('objects_1')
    # iterate through each tile layer and blit the corresponding tile
    for layer in tiled_map.layers:
        if hasattr(layer, 'data'):
            for x, y, image in layer.tiles():
                if image:
                    bg_image.blit(image, (x * tiled_map.tilewidth, 
                                          y * tiled_map.tileheight))
    return bg_image, map_objects


def construct_polyeder(center, n, size, rotation=0):
    # construct a hexagon from a given center and radius
    points = []
    for i in range(n):
        angle_deg = (360 / n) * i - rotation
        angle_rad = pi / 180 * angle_deg
        points.append(vec(center.x + size * cos(angle_rad),
                         center.y + size * sin(angle_rad)))
    return points


def vec_to_int(vec):
    return (int(vec.x), int(vec.y))


def rotate_point(point, center, angle):
    # rotate a point around the center by a given angle
    point -= center
    # rotate point around the origin
    original_x = point.x
    original_y = point.y
    point.x = original_x * cos(angle) - original_y * sin(angle)
    point.y = original_y * cos(angle) + original_x * sin(angle)
    # translate back to shape's center
    point += center


class Camera(object):
    def __init__(self, game, target):
        self.game = game
        self.offset = vec()
        self.target = target
        self.rect = self.game.screen_rect
        
    
    def update(self, dt):  
        w = self.game.screen_rect.w
        h = self.game.screen_rect.h
        self.offset.x = self.target.rect.centerx + w // 2 * -1
        self.offset.y = self.target.rect.centery + h // 2 * -1
        pg.display.set_caption(f'{self.target.rect.center}')
        

        # camera can't go over upper left borders
        self.offset.x = max(self.offset.x, 0)
        self.offset.y = max(self.offset.y, 0)
        # camera can't go over bottom right borders
        self.offset.x = min(self.offset.x, (self.game.map_rect.w - 
                                            self.game.screen_rect.w))
        self.offset.y = min(self.offset.y, (self.game.map_rect.h - 
                                            self.game.screen_rect.h))

    
    def apply_mouse(self, m_pos):
        return m_pos - self.offset
    

    def apply_pos(self, pos):
        return pos - self.offset


    def apply_rect(self, rect):
        return pg.Rect(rect.topleft - self.offset, rect.size)



class Game:
    def __init__(self):
        pg.init()
        self.screen = pg.display.set_mode((W_WIDTH, W_HEIGHT))
        self.screen_rect = self.screen.get_rect()
        self.clock = pg.time.Clock()
        self.running = True
        
        self.shapes = []
        self.particles = []
        self.car = Car(self)
        self.car.move_to((3105, 2260))
        self.car.rotate(pi / -2)
        
        self.map, self.map_objects = load_map('track_1')
        self.map_rect = self.map.get_rect()

        self.camera = Camera(self, self.car)
        
    def events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
    
    
    def update(self, dt):
        #pg.display.set_caption(f'FPS: {round(self.clock.get_fps(), 2)}')
                 
        self.camera.update(dt)
        
        for shape in self.shapes:
            shape.update(dt)
        for p in self.particles:
            p.update(dt)
       
        
    def draw(self):
        self.screen.fill(GREEN)
        self.screen.blit(self.map, self.camera.apply_pos(self.map_rect.topleft))
        for p in self.particles:
            p.draw(self.screen)
        for shape in self.shapes:
            shape.draw(self.screen)
        
        pg.display.update()
        
        
    def run(self):
        while self.running:
            delta_time = self.clock.tick(FPS) / 1000.0
            self.events()
            self.update(delta_time)
            self.draw()
        pg.quit()
        


class Shape:
    '''
    This class constructs a polygon from any number of given vectors
    '''
    def __init__(self, game, points, static=False):
        self.game = game
        self.game.shapes.append(self)
        self.points = points
        self.center = self.find_center()
        self.overlap = False
        self.static = static       
        self.edges = [Line(self.points[i], self.points[i + 1]) 
                      for i in range(-1, len(self.points) - 1)]
        self.diagonals = [Line(self.center, p) for p in self.points]       
        self.rect = self.construct_rect()
        
    
    def update(self, dt):                  
        # construct edges and diagonals based on the new coordinates
        self.edges = [Line(self.points[i], self.points[i + 1]) 
                      for i in range(-1, len(self.points) - 1)]
        self.diagonals = [Line(self.center, p) for p in self.points]
        self.rect = self.construct_rect()
        
        for shape in self.game.shapes:
            # check for collisions with the other shapes
            if shape != self and self.rect.colliderect(shape.rect):
                if self.shape_overlap(shape):
                    self.overlap = True
                    shape.overlap = True
    
    
    def rotate(self, angle):
        # rotate the edges around the shape's center
        for point in self.points:
            # translate the center to the origin
            rotate_point(point, self.center, angle)
    
    
    def draw(self, screen):
        if self.overlap: 
            color = RED
        else:
            color = WHITE
        # draw the shape of the polygon
        pg.draw.polygon(screen, color, 
                        [self.game.camera.apply_pos(x) for x in self.points], 2)
        # draw the center point of the shape
        x = int(self.game.camera.apply_pos(self.center)[0])
        y = int(self.game.camera.apply_pos(self.center)[1])
        pg.draw.circle(screen, RED, (x, y), 4)
        '''
        # for debugging
        for diag in self.diagonals:
            diag.draw(screen, color)
        for edge in self.edges:
            edge.draw(screen, color)
        '''
        pg.draw.rect(screen, WHITE, self.game.camera.apply_rect(self.rect), 1)
        # reset the overlap flag after all collisions are checked
        self.overlap = False
        
        
    def find_center(self):
        # calculate geometric center (centroid) as mean of all points
        # https://en.wikipedia.org/wiki/Centroid
        p_sum = vec()
        for p in self.points:
            p_sum += p
        return p_sum / len(self.points)
    
    
    def construct_rect(self):
        min_x = inf
        max_x = -inf
        min_y = inf
        max_y = -inf
        
        for point in self.points:
            min_x = min(min_x, point.x)
            max_x = max(max_x, point.x)
            min_y = min(min_y, point.y)
            max_y = max(max_y, point.y)
            
        width = max_x - min_x
        height = max_y - min_y
        return pg.Rect((min_x, min_y), (width, height))
    
    
    def move(self, amount):
        # move all points of this shape by a given vector
        self.center += amount
        for point in self.points:
                point += amount
    
    
    def move_to(self, position):
        # move the center to a given position and change all points accordingly
        # just a convenience function, could possibly be refactored
        old_center = self.center
        self.center = position
        amount = position - old_center
        for point in self.points:
                point += amount
                
    
    def shape_overlap(self, other):
        # https://github.com/OneLoneCoder/olcPixelGameEngine/blob/master/OneLoneCoder_PGE_PolygonCollisions1.cpp
        # check if the diagonals of this shape overlap any of the edges of 
        # the other shape. If true, move this shape's points by the
        # displacement vector that gets modified by the intersects_line function
        for diag in self.diagonals:
            for edge in other.edges:
                displacement = vec()
                if diag.intersects_line(edge, displacement):
                    self.move(displacement)
                    if not other.static:
                        other.move(displacement * -1)
                    return True
        return False
        


class Car(Shape):
    def __init__(self, game):
        points = [vec(64, 0), vec(64, 32), vec(0, 32), vec(0, 0)]
        super().__init__(game, points)
        
        # adjust center to simulate steering with front axis
        self.center.x += 20
        
        self.image_orig = pg.image.load('assets/Cars/car_red_1.png').convert_alpha()
        self.image_orig = pg.transform.rotate(self.image_orig, 270)
        self.image_orig = pg.transform.scale(self.image_orig, self.rect.size)
        self.image = self.image_orig.copy()
        
        self.particle_timer = 0
             
        self.acc = vec()
        self.vel = vec()
        self.friction = 0.98
        self.rotation = 0
        self.speed = 15
        
        self.steer_sensitivity = 8 # the higher the more sensitive
        
    
    def rotate(self, angle):
        super().rotate(angle) 
        self.rotation += angle
        # rotate the images accordingly
        self.image = pg.transform.rotate(self.image_orig, 
                                         self.rotation * -360 / TWO_PI)
    
    
    def update(self, dt):
        keys = pg.key.get_pressed()
        rot = keys[pg.K_d] - keys[pg.K_a]
        # backwards is only half the speed
        move = keys[pg.K_w] - (keys[pg.K_s] * 0.5)
            
        # rotate
        angle = pi * rot * dt * (self.vel.length() / self.steer_sensitivity)
        self.rotate(angle)
        # move
        self.acc.x += move * dt * self.speed
        angle_deg = self.rotation * 360 / TWO_PI
        self.acc = self.acc.rotate(angle_deg)
        self.vel += self.acc
        self.vel *= self.friction
        self.move(self.vel)
        self.acc *= 0
        
        self.particle_timer += dt
        if self.particle_timer >= 0.01 and self.vel.length() > 0.5:
            self.particle_timer = 0
            p1 = self.points[2] + 0.3 * (self.center - self.points[2])
            p2 = self.points[3] + 0.3 * (self.center - self.points[3])
            Particle(self.game, (10, 10), p1, BLACK)
            Particle(self.game, (10, 10), p2, BLACK)
        
        super().update(dt)
    
    
    def draw(self, screen):
        screen.blit(self.image, self.game.camera.apply_pos(self.rect.topleft))
        #super().draw(screen)



class Line:
    '''
    custom Line class that represents a line with a start and end vector
    and provides a method for intersection checking
    '''
    def __init__(self, start, end):
        self.start = vec(start)
        self.end = vec(end)
    
    
    def draw(self, screen, color=WHITE, width=1):
        pg.draw.line(screen, color, self.start, self.end, width)
        
        
    def intersects_line(self, other, displacement):
        # http://www.jeffreythompson.org/collision-detection/line-rect.php
        # check if two Line objects intersect
        # if true, change the displacement vector by the distance between
        # this line's end and the intersection
        denA = ((other.end.y - other.start.y) * (self.end.x - self.start.x) - 
                (other.end.x - other.start.x) * (self.end.y - self.start.y))
        denB = ((other.end.y - other.start.y) * (self.end.x - self.start.x) - 
                (other.end.x - other.start.x) * (self.end.y - self.start.y))
        if denA == 0 or denB == 0:
            return False
        else:
            numA = ((other.end.x - other.start.x) * (self.start.y - other.start.y) - 
                    (other.end.y - other.start.y) * (self.start.x - other.start.x))
            numB = ((self.end.x - self.start.x) * (self.start.y - other.start.y) - 
                    (self.end.y - self.start.y) * (self.start.x - other.start.x))
            uA = numA / denA
            uB = numB / denB
            if (uA >= 0 and uA <= 1 and uB >= 0 and uB <= 1):
                displacement.x -= (1.0 - uA) * (self.end.x - self.start.x)
                displacement.y -= (1.0 - uA) * (self.end.y - self.start.y)
                return True
            else:
                return False


class Particle:
    def __init__(self, game, size, position, color):
        self.game = game
        self.game.particles.append(self)
        self.position = position
        self.color = color
        self.image = pg.Surface(size)
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.center = self.position
        self.alpha = 20
    
    
    def update(self, dt):
        self.alpha -= dt * 0.5
        if self.alpha <= 0:
            self.game.particles.remove(self)
            return
        self.image.set_alpha(self.alpha)
    
        
    def draw(self, screen):
        screen.blit(self.image, self.game.camera.apply_rect(self.rect))
    
    
if __name__ == '__main__':
    try:
        g = Game()
        #mymap = load_pygame('assets/{}.tmx'.format('track_1'))
        g.run()
    except:
        traceback.print_exc()
        pg.quit()