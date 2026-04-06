import pygame as pg
import random
import math
import importlib.util
import os
import sys

class AISystem:
    def __init__(self, game):
        self.game = game

        self.behaviors = {
            "idle": self.ai_idle,
            "wander": self.ai_wander,
            "aggressive": self.ai_aggressive,
            "friendly": self.ai_friendly,
        }

        self.script_cache = {}

        random.seed(self.game.environment.seed)

    def load_script(self, script_path):
        if script_path in self.script_cache:
            return self.script_cache[script_path]

        abs_path = os.path.abspath(script_path)
        if not os.path.isfile(abs_path):
            print(f"[AI] Script not found: {abs_path}")
            self.script_cache[script_path] = None
            return None

        module_name = f"ai_script_{os.path.splitext(os.path.basename(abs_path))[0]}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, abs_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            self.script_cache[script_path] = module
            print(f"[AI] Loaded script: {script_path}")
            return module
        
        except Exception as exc:
            print(f"[AI] Failed to load script '{script_path}': {exc}")
            self.script_cache[script_path] = None
            return None

    def check_wall_collision(self, entity):
        hitbox_w = entity.get("hitbox_width", entity["width"])
        hitbox_h = entity.get("hitbox_height", entity["height"])
        
        offset_x = entity.get("hitbox_offset_x", 0)
        offset_y = entity.get("hitbox_offset_y", 0)

        sensor_offset = 5
        direction = entity.get("ai_direction", 0)
        sensor_rect = pg.Rect(
            entity["x"] - hitbox_w / 2 + offset_x + (sensor_offset if direction > 0 else -sensor_offset),
            entity["y"] - hitbox_h / 2 + offset_y,
            hitbox_w,
            hitbox_h,
        )

        for tile_hitbox, tile_id in self.game.map.get_nearby_tiles(sensor_rect, padding=5):
            tile_attrs = self.game.map.tile_attributes.get(tile_id, {})
            if not tile_attrs.get("swimmable", False) and sensor_rect.colliderect(tile_hitbox):
                return True
            
        return False

    def check_floor_ahead(self, entity):
        hitbox_w = entity.get("hitbox_width", entity["width"])
        direction = entity.get("ai_direction", 0)

        if direction == 0:
            return True

        check_x = entity["x"] + (hitbox_w / 2 + 16) * direction
        check_y = entity["y"] + entity["height"] // 2 + 16
        sensor_rect = pg.Rect(check_x - 2, check_y - 2, 4, 4)

        for tile_rect, tile_id in self.game.map.get_nearby_tiles(sensor_rect, padding=0):
            tile_attrs = self.game.map.tile_attributes.get(tile_id, {})
            if not tile_attrs.get("swimmable", False):
                return True
            
        return False

    def ai_idle(self, entity):
        if entity.get("knockback_timer", 0) <= 0:
            entity["vel_x"] = 0

    def ai_wander(self, entity):
        if entity.get("knockback_timer", 0) > 0:
            return
            
        if "ai_timer" not in entity:
            self.reset_wander_timer(entity)

        if entity["ai_direction"] != 0 and not self.check_floor_ahead(entity):
            entity["ai_direction"] *= -1
            self.reset_wander_timer(entity)

        if entity["ai_direction"] != 0 and self.check_wall_collision(entity):
            entity["ai_direction"] *= -1
            self.reset_wander_timer(entity)

        entity["ai_timer"] -= 1
        if entity["ai_timer"] <= 0:
            self.reset_wander_timer(entity)

        entity["vel_x"] = entity.get("move_speed", 1) * entity["ai_direction"]

        if random.random() < 0.01 and entity.get("on_ground", False):
            entity["vel_y"] = -entity.get("jump_force", 10)

    def ai_aggressive(self, entity):
        if entity.get("knockback_timer", 0) > 0:
            return
            
        player = self.game.player

        if player.current_health <= 0:
            self.ai_wander(entity)
            return

        dx = player.x - entity["x"]
        dy = player.y - entity["y"]
        distance = math.hypot(dx, dy)

        aggro_range = entity.get("aggro_range", 300)
        stop_distance = entity.get("stop_distance", 50)

        if distance < aggro_range:
            if distance > stop_distance:
                new_dir = 1 if dx > 0 else -1

                if (
                    "ai_direction" not in entity
                    or new_dir != entity["ai_direction"]
                    or self.check_wall_collision(entity)
                    or not self.check_floor_ahead(entity)
                ):
                    entity["ai_direction"] = new_dir

                if self.check_floor_ahead(entity):
                    entity["vel_x"] = entity["ai_direction"] * entity.get("move_speed", 1) * 1.5
                    
                else:
                    entity["vel_x"] = 0
                    
            else:
                entity["vel_x"] = 0

            if dy < -50 and entity.get("on_ground", False):
                entity["vel_y"] = -entity.get("jump_force", 10)

            if distance < stop_distance:
                self.ai_attack(entity)
                
        else:
            self.ai_wander(entity)

    def ai_friendly(self, entity):
        if entity.get("knockback_timer", 0) > 0:
            return
            
        player = self.game.player
        dx = player.x - entity["x"]
        distance = abs(dx)

        if distance > 100:
            new_dir = 1 if dx > 0 else -1

            if (
                "ai_direction" not in entity
                or new_dir != entity["ai_direction"]
                or self.check_wall_collision(entity)
                or not self.check_floor_ahead(entity)
            ):
                entity["ai_direction"] = new_dir

            if self.check_floor_ahead(entity):
                entity["vel_x"] = entity["ai_direction"] * entity.get("move_speed", 1)
                
            else:
                entity["vel_x"] = 0
                
        else:
            entity["vel_x"] = 0

    def reset_wander_timer(self, entity):
        entity["ai_timer"] = random.randint(60, 180)
        entity["ai_direction"] = random.choice([-1, 0, 1])

    def ai_attack(self, entity):
        if "attack_timer" not in entity:
            entity["attack_timer"] = 0

        if entity["attack_timer"] <= 0:
            entity["attack_timer"] = 30
            direction = entity.get("ai_direction", 1)
            hitbox_width = 30
            hitbox_height = 30
            attack_dist = 20

            attack_rect = pg.Rect(
                entity["x"] + attack_dist * direction - hitbox_width // 2,
                entity["y"] - 10 - hitbox_height // 2,
                hitbox_width,
                hitbox_height,
            )

            if attack_rect.colliderect(self.game.player.hitbox):
                self.game.player.take_damage(entity.get("attack_damage", 10))
                
        else:
            entity["attack_timer"] -= 1

    def update_ai(self, entity):
        if entity.get("knockback_timer", 0) > 0:
            entity["knockback_timer"] -= 1
            return
            
        if entity.get("force_facing"):
            del entity["force_facing"]
            
        cam_x = self.game.player.cam_x
        cam_y = self.game.player.cam_y

        if not (cam_x <= entity["x"] <= cam_x + self.game.screen_width and cam_y <= entity["y"] <= cam_y + self.game.screen_height):
            return

        script_path = entity.get("script")
        if script_path:
            module = self.load_script(script_path)
            
            if module is not None and hasattr(module, "update"):
                try:
                    module.update(entity, self)
                    
                except Exception as exc:
                    print(f"[AI] Error in script '{script_path}': {exc}")
                    
                return

        behavior = entity.get("behavior")
        if behavior and behavior in self.behaviors:
            self.behaviors[behavior](entity)