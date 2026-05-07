import pygame as pg
import math
import random

class Camera:
    def __init__(self, game):
        self.game = game

        self.x = 0
        self.y = 0
        
        self.smoothing_factor = 0.1
        self.free_cam = False
        self.screen_shake_timer = 0
        
        self.shake_intensity = 0
        self.shake_duration = 1

    def load_settings(self, player_x, player_y):
        self.x = player_x - self.game.screen_width / 2
        self.y = player_y - self.game.screen_height / 1.5
        
        self.smoothing_factor = 0.1
        self.free_cam = False
        self.screen_shake_timer = 0

    def shake(self, intensity, duration):
        self.shake_intensity = intensity
        self.shake_duration = duration
        self.screen_shake_timer = duration

    def update_shake(self):
        if self.screen_shake_timer > 0:
            decay = self.screen_shake_timer / self.shake_duration

            current_intensity = self.shake_intensity * decay

            time = self.game.environment.current_time / 100
            angle_x = time * 15
            angle_y = time * 13

            offset_x = math.sin(angle_x) * current_intensity
            offset_y = math.sin(angle_y) * current_intensity

            offset_x += (random.random() - 0.5) * current_intensity * 0.5
            offset_y += (random.random() - 0.5) * current_intensity * 0.5

            self.screen_shake_timer -= 1

            return (offset_x, offset_y)

        return (0, 0)

    def update(self):
        if self.free_cam:
            return

        player = self.game.player

        if player.enable_cam_mouse:
            mouse_dist_from_player_x = (pg.mouse.get_pos()[0] + self.x) - player.x
            mouse_dist_from_player_y = (pg.mouse.get_pos()[1] + self.y) - player.y

            target_cam_x = player.x - self.game.screen_width / 2 + mouse_dist_from_player_x * 0.1
            target_cam_y = player.y - self.game.screen_height / 1.5 + mouse_dist_from_player_y * 0.1

        else:
            target_cam_x = player.x - self.game.screen_width / 2
            target_cam_y = player.y - self.game.screen_height / 1.5

        base_cam_x = self.x + (target_cam_x - self.x) * self.smoothing_factor
        base_cam_y = self.y + (target_cam_y - self.y) * self.smoothing_factor

        base_cam_x = max(min(base_cam_x, target_cam_x + self.game.screen_width / 4), target_cam_x - self.game.screen_width / 4)
        base_cam_y = max(min(base_cam_y, target_cam_y + self.game.screen_height / 4), target_cam_y - self.game.screen_height / 7)

        shake_offset_x, shake_offset_y = self.update_shake()
        self.x = base_cam_x + shake_offset_x
        self.y = base_cam_y + shake_offset_y

    def handle_free_cam(self):
        if not self.free_cam:
            return

        keys = pg.key.get_pressed()
        speed = 10

        if keys[pg.K_UP]:
            self.y -= speed

        if keys[pg.K_DOWN]:
            self.y += speed

        if keys[pg.K_LEFT]:
            self.x -= speed

        if keys[pg.K_RIGHT]:
            self.x += speed
