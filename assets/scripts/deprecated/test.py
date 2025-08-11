import pygame as pg
import math
import random

class Test:
    def __init__(self, game):
        self.game = game
        
        self.x = 0
        self.y = 700
        self.width = 50
        self.height = 50

        self.angle = 0
        self.speed = 2  
        self.gravity = 0.5
        self.velocity_y = 0

        self.image = pg.Surface((self.width, self.height), pg.SRCALPHA)
        self.image.fill((255, 0, 0))

    def collides_with_tile(self, x, y):
        for hitbox in self.game.map.tile_hitboxes:
            if hitbox.collidepoint(x, y):
                return True
        return False

    def move_towards_player(self, dx, dy):
        new_x = self.x + dx * self.speed
        new_y = self.y + dy * self.speed

        if not self.collides_with_tile(new_x, new_y):
            self.x = new_x
            self.y = new_y
            return True
        return False

    def check_floor(self):
        for hitbox in self.game.map.tile_hitboxes:
            if hitbox.collidepoint(self.x, self.y + self.height // 2):
                return True
        return False

    def path_finding(self):
        dx = self.game.player.x - self.x
        dy = self.game.player.y - self.y
        distance = math.hypot(dx, dy)

        if distance > 2:
            dx /= distance
            dy /= distance
            self.move_towards_player(dx, dy)

    def apply_gravity(self):
        if not self.check_floor():
            self.velocity_y += self.gravity
        else:
            self.velocity_y = 0
            self.y = (self.y // 32) * 32 + (self.height // 2)

    def render(self):
        rotated_image = pg.transform.rotate(self.image, self.angle)
        rect = rotated_image.get_rect(center=(self.x - self.game.player.cam_x, self.y - self.game.player.cam_y))
        self.game.screen.blit(rotated_image, rect.topleft)

    def update(self):
        if self.game.environment.menu == "play":
            self.apply_gravity()
            self.path_finding()
            self.y += self.velocity_y
            self.render()
