import pygame as pg
import random
import math

class AISystem:
    def __init__(self, game):
        self.game = game
        
        self.behaviors = {
            "idle": self.ai_idle,
            "wander": self.ai_wander,
            "aggressive": self.ai_aggressive,
            "friendly": self.ai_friendly
        }
        
        random.seed(self.game.environment.seed)
    
    def check_wall_collision(self, entity):
        hitbox_w = entity.get("hitbox_width", entity["width"])
        hitbox_h = entity.get("hitbox_height", entity["height"])
        
        offset_x = entity.get("hitbox_offset_x", 0)
        offset_y = entity.get("hitbox_offset_y", 0)
        
        sensor_offset = 5
        sensor_rect = pg.Rect(
            entity["x"] - hitbox_w/2 + offset_x + (sensor_offset if entity.get("ai_direction", 0) > 0 else -sensor_offset),
            entity["y"] - hitbox_h/2 + offset_y,
            hitbox_w,
            hitbox_h
        )
        
        nearby_tiles = self.game.map.get_nearby_tiles(sensor_rect, padding=5)
        
        for tile_hitbox, tile_id in nearby_tiles:
            tile_attrs = self.game.map.tile_attributes.get(tile_id, {})
            if not tile_attrs.get("swimmable", False) and sensor_rect.colliderect(tile_hitbox):
                return True
            
        return False
    
    def ai_idle(self, entity):
        entity["vel_x"] = 0
    
    def ai_wander(self, entity):
        if "ai_timer" not in entity:
            self.reset_wander_timer(entity)
        
        if entity["ai_direction"] != 0:
            if self.check_wall_collision(entity):
                entity["ai_direction"] *= -1
                self.reset_wander_timer(entity)
        
        entity["ai_timer"] -= 1
        if entity["ai_timer"] <= 0:
            self.reset_wander_timer(entity)
        
        entity["vel_x"] = entity.get("move_speed", 1) * entity["ai_direction"]
        
        if random.random() < 0.01 and entity.get("on_ground", False):
            entity["vel_y"] = -entity.get("jump_force", 10)
    
    def reset_wander_timer(self, entity):
        entity["ai_timer"] = random.randint(60, 180)
        entity["ai_direction"] = random.choice([-1, 0, 1])

    def ai_aggressive(self, entity):
        player = self.game.player
        dx = player.x - entity["x"]
        dy = player.y - entity["y"]
        
        distance_sq = dx*dx + dy*dy
        
        aggro_range = entity.get("aggro_range", 300)
        
        if distance_sq < aggro_range*aggro_range:
            new_dir = 1 if dx > 0 else -1
            
            if ("ai_direction" not in entity or 
                new_dir != entity["ai_direction"] or 
                self.check_wall_collision(entity)):
                entity["ai_direction"] = new_dir
            
            move_speed = entity.get("move_speed", 1) * 1.5
            entity["vel_x"] = entity["ai_direction"] * move_speed
            
            if dy < -50 and entity.get("on_ground", False):
                entity["vel_y"] = -entity.get("jump_force", 10)
                
            if distance_sq < 50*50:
                self.ai_attack(entity)
                
        else:
            self.ai_wander(entity)
            
    def ai_friendly(self, entity):
        player = self.game.player
        dx = player.x - entity["x"]
        distance = abs(dx)
        
        if distance > 100:
            new_dir = 1 if dx > 0 else -1
            
            if ("ai_direction" not in entity or 
                new_dir != entity["ai_direction"] or 
                self.check_wall_collision(entity)):
                entity["ai_direction"] = new_dir
            
            entity["vel_x"] = entity["ai_direction"] * entity.get("move_speed", 1)
            
        else:
            entity["vel_x"] = 0

    def ai_attack(self, entity):
        if "attack_timer" not in entity:
            entity["attack_timer"] = 0

        if entity["attack_timer"] <= 0:
            entity["attack_timer"] = 30
            direction = entity.get("ai_direction", 1)
            
            hitbox_width = 30
            hitbox_height = 30
            attack_distance = 20
            
            attack_x = entity["x"] + (attack_distance * direction)
            attack_y = entity["y"] - 10
            
            attack_rect = pg.Rect(
                attack_x - hitbox_width // 2,
                attack_y - hitbox_height // 2,
                hitbox_width,
                hitbox_height
            )

            if hasattr(self.game, "debug") and self.game.debug:
                pg.draw.rect(self.game.screen, (255, 0, 255), attack_rect, 1)
                pg.draw.line(
                    self.game.screen, (255, 0, 255),
                    (entity["x"] - self.game.player.cam_x, entity["y"] - self.game.player.cam_y),
                    (attack_x - self.game.player.cam_x, attack_y - self.game.player.cam_y),
                    1
                )

            if attack_rect.colliderect(self.game.player.hitbox):
                self.game.player.take_damage(entity.get("attack_damage", 10))
                
        else:
            entity["attack_timer"] -= 1
        
    def update_ai(self, entity):
        screen_width = self.game.screen.get_width()
        screen_height = self.game.screen.get_height()
        
        if (self.game.player.cam_x <= entity["x"] <= self.game.player.cam_x + screen_width and self.game.player.cam_y <= entity["y"] <= self.game.player.cam_y + screen_height):
            if "behavior" in entity:
                behavior = entity["behavior"]
                if behavior in self.behaviors:
                    self.behaviors[behavior](entity)