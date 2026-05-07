import pygame as pg
import os
import json
import math
import random

class Foreground:
    def __init__(self, game):
        self.game = game
        self.enable_foreground = False
        
        self.load_settings()

    def load_settings(self):
        self.cam_x = 0
        self.cam_y = 0
        
        self.layers = []
        self.screen_effects = []

    def add_screen_effect(self, effect_type, intensity=1.0, duration=30, color=None):
        effect = {
            "type": effect_type,
            "intensity": intensity,
            "duration": duration,
            "timer": duration,
            "color": color or (255, 0, 0)
        }
        
        match effect_type:
            case "hurt":
                effect["color"] = (255, 50, 50)
            
            case "flash":
                effect["color"] = (255, 255, 255)
            
            case "darken":
                effect["color"] = (0, 0, 0)
            
        self.screen_effects.append(effect)

    def update_screen_effects(self):
        for effect in self.screen_effects[:]:
            effect["timer"] -= 1
            effect["current_intensity"] = effect["intensity"] * (effect["timer"] / effect["duration"])
            
            if effect["timer"] <= 0:
                self.screen_effects.remove(effect)

    def render_screen_effects(self):
        if not self.screen_effects:
            return
        
        for effect in self.screen_effects:
            effect_type = effect["type"]
            intensity = effect["current_intensity"]
            color = effect["color"]
            
            if effect_type in ["hurt", "flash", "darken"]:
                alpha = int(255 * intensity)
                overlay = pg.Surface((self.game.screen_width, self.game.screen_height))
                overlay.fill(color)
                overlay.set_alpha(alpha)
                self.game.screen.blit(overlay, (0, 0))

    def load(self, map_path):
        print("Foreground reset")
        self.load_settings()

        foreground_file = os.path.join(map_path, "foreground.json")
        if not os.path.exists(foreground_file):
            print(f"Foreground file does not exist: {foreground_file}")
            return

        try:
            with open(foreground_file, "r") as file:
                fg_attributes = json.load(file)

                for fg_id, fg_data in fg_attributes.items():
                    layer_type = fg_data.get("type", "world")

                    image_surface = None
                    image_path = fg_data.get("image", "")
                    width, height = 0, 0

                    if image_path and os.path.exists(image_path):
                        image_surface = pg.image.load(image_path).convert_alpha()
                        original_width, original_height = image_surface.get_size()
                        width = fg_data.get("width", original_width)
                        height = fg_data.get("height", original_height)
                        if (width, height) != (original_width, original_height):
                            image_surface = pg.transform.scale(image_surface, (width, height))
                            
                    else:
                        print(f"Image file not found: {image_path}")

                    layer = {
                        "type": layer_type,
                        "x": fg_data.get("x", 0),
                        "y": fg_data.get("y", 0),
                        "width": width,
                        "height": height,
                        "layer": fg_data.get("layer", 1),
                        "image": image_surface
                    }

                    if layer_type == "overlay":
                        layer.update({
                            "scroll_x": fg_data.get("scroll_speed_x", 0),
                            "scroll_y": fg_data.get("scroll_speed_y", 0),
                            "repeat_directions": fg_data.get("repeat_directions", []),
                            "move_directions": fg_data.get("move_directions", []),
                            "opacity": fg_data.get("opacity", 1.0),
                            "bob_amount": fg_data.get("bob_amount", 8),
                            "bob_speed": fg_data.get("bob_speed", 1.0),
                            "offset_x": 0,
                            "offset_y": 0,
                            "time": 0,
                            "bob_offset": 0
                        })

                    elif layer_type == "scroll_overlay":
                        layer.update({
                            "scroll_x": fg_data.get("scroll_speed_x", 0),
                            "scroll_y": fg_data.get("scroll_speed_y", 0),
                            "repeat_directions": fg_data.get("repeat_directions", []),
                            "move_directions": fg_data.get("move_directions", []),
                            "opacity": fg_data.get("opacity", 1.0),
                            "bob_amount": fg_data.get("bob_amount", 8),
                            "bob_speed": fg_data.get("bob_speed", 1.0),
                            "offset_x": 0,
                            "offset_y": 0,
                            "time": 0,
                            "bob_offset": 0,
                            "camera_scroll_factor": fg_data.get("camera_scroll_factor", 0.5)
                        })

                    elif layer_type == "world":
                        count = fg_data.get("count", 5)
                        radius = fg_data.get("radius", 50)
                        particles = []
                        for particle_index in range(count):
                            particle_x = fg_data["x"] + random.uniform(-radius, radius)
                            particle_y = fg_data["y"] + random.uniform(-radius, radius)
                            particles.append({
                                "x": particle_x,
                                "y": particle_y,
                                "angle": random.uniform(0, math.pi * 2),
                                "speed": random.uniform(0.2, 0.6),
                                "glow": random.uniform(0.4, 1.0)
                            })

                        layer.update({
                            "effect": fg_data.get("effect", ""),
                            "count": count,
                            "radius": radius,
                            "glow_strength": fg_data.get("glow_strength", 0.5),
                            "particles": particles
                        })

                    self.layers.append(layer)

                self.layers.sort(key=lambda foreground_layer: foreground_layer["layer"])

        except Exception as error:
            print(f"Failed to load foreground info: {error}")

    def update_camera(self):
        if not getattr(self.game.player, "settings_loaded", False):
            self.cam_x = 0
            self.cam_y = 0
            return
        
        self.cam_x = self.game.player.cam_x
        self.cam_y = self.game.player.cam_y

    def update_layers(self):
        current_time = self.game.environment.current_time * 0.001
        
        for foreground_layer in self.layers:
            if foreground_layer["type"] == "overlay":
                foreground_layer["time"] = current_time
                foreground_layer["offset_x"] += foreground_layer["scroll_x"]
                foreground_layer["offset_y"] += foreground_layer["scroll_y"]

                if foreground_layer["bob_amount"] > 0:
                    foreground_layer["bob_offset"] = math.sin(foreground_layer["time"] * foreground_layer["bob_speed"]) * foreground_layer["bob_amount"]
                    
                else:
                    foreground_layer["bob_offset"] = 0

                move_x = foreground_layer["scroll_x"]
                move_y = foreground_layer["scroll_y"]
                move_directions = foreground_layer.get("move_directions", [])

                if "left" in move_directions:
                    foreground_layer["x"] -= move_x
                    
                if "right" in move_directions:
                    foreground_layer["x"] += move_x
                    
                if "up" in move_directions:
                    foreground_layer["y"] -= move_y
                    
                if "down" in move_directions:
                    foreground_layer["y"] += move_y

                if "horizontal" in foreground_layer["repeat_directions"]:
                    foreground_layer["offset_x"] %= foreground_layer["width"]
                    
                if "vertical" in foreground_layer["repeat_directions"]:
                    foreground_layer["offset_y"] %= foreground_layer["height"]

            elif foreground_layer["type"] == "scroll_overlay":
                foreground_layer["time"] = current_time
                
                foreground_layer["offset_x"] += foreground_layer["scroll_x"]
                foreground_layer["offset_y"] += foreground_layer["scroll_y"]

                if foreground_layer["bob_amount"] > 0:
                    foreground_layer["bob_offset"] = math.sin(foreground_layer["time"] * foreground_layer["bob_speed"]) * foreground_layer["bob_amount"]
                    
                else:
                    foreground_layer["bob_offset"] = 0

                move_x = foreground_layer["scroll_x"]
                move_y = foreground_layer["scroll_y"]
                move_directions = foreground_layer.get("move_directions", [])

                if "left" in move_directions:
                    foreground_layer["x"] -= move_x
                    
                if "right" in move_directions:
                    foreground_layer["x"] += move_x
                    
                if "up" in move_directions:
                    foreground_layer["y"] -= move_y
                    
                if "down" in move_directions:
                    foreground_layer["y"] += move_y

                if "horizontal" in foreground_layer["repeat_directions"]:
                    foreground_layer["offset_x"] %= foreground_layer["width"]
                    
                if "vertical" in foreground_layer["repeat_directions"]:
                    foreground_layer["offset_y"] %= foreground_layer["height"]

            elif foreground_layer["type"] == "world":
                for particle in foreground_layer["particles"]:
                    particle["angle"] += (random.random() - 0.5) * 0.05
                    particle["x"] += math.cos(particle["angle"]) * particle["speed"]
                    particle["y"] += math.sin(particle["angle"]) * particle["speed"]

    def render_overlay(self, foreground_layer):
        image = foreground_layer["image"]
        if not image:
            return

        width, height = foreground_layer["width"], foreground_layer["height"]

        alpha_image = image.copy()
        alpha_image.set_alpha(int(foreground_layer["opacity"] * 255))

        repeat_horizontal = "horizontal" in foreground_layer["repeat_directions"]
        repeat_vertical = "vertical" in foreground_layer["repeat_directions"]

        if repeat_horizontal:
            start_x = -int(foreground_layer["offset_x"]) % width - width
            
        else:
            start_x = int(foreground_layer["x"] - self.cam_x)

        if repeat_vertical:
            start_y = -int(foreground_layer["offset_y"]) % height - height
            
        else:
            start_y = int(foreground_layer["y"] + foreground_layer["bob_offset"] - self.cam_y)

        if repeat_horizontal:
            tiles_x = (self.game.screen_width // width) + 3
        
        else:
            tiles_x = 1

        if repeat_vertical:
            tiles_y = (self.game.screen_height // height) + 3
            
        else:
            tiles_y = 1

        for tile_x in range(tiles_x):
            for tile_y in range(tiles_y):
                draw_x = start_x + tile_x * width
                
                if repeat_vertical:
                    draw_y = start_y + tile_y * height + int(foreground_layer["bob_offset"])
                    
                else:
                    draw_y = start_y + tile_y * height
                
                if (draw_x + width > 0 and draw_x < self.game.screen_width and draw_y + height > 0 and draw_y < self.game.screen_height):
                    self.game.screen.blit(alpha_image, (draw_x, draw_y))

    def render_scroll_overlay(self, foreground_layer):
        image = foreground_layer["image"]
        if not image:
            return

        width, height = foreground_layer["width"], foreground_layer["height"]
        camera_scroll_factor = foreground_layer.get("camera_scroll_factor", 0.5)

        alpha_image = image.copy()
        alpha_image.set_alpha(int(foreground_layer["opacity"] * 255))

        repeat_horizontal = "horizontal" in foreground_layer["repeat_directions"]
        repeat_vertical = "vertical" in foreground_layer["repeat_directions"]

        camera_offset_x = int(self.cam_x * camera_scroll_factor)
        camera_offset_y = int(self.cam_y * camera_scroll_factor)

        if repeat_horizontal:
            start_x = -int(foreground_layer["offset_x"] + camera_offset_x) % width - width
            
        else:
            start_x = int(foreground_layer["x"] + camera_offset_x)

        if repeat_vertical:
            start_y = -int(foreground_layer["offset_y"] + camera_offset_y) % height - height
            
        else:
            start_y = int(foreground_layer["y"] + foreground_layer["bob_offset"] + camera_offset_y)

        if repeat_horizontal:
            tiles_x = (self.game.screen_width // width) + 3
            
        else:
            tiles_x = 1

        if repeat_vertical:
            tiles_y = (self.game.screen_height // height) + 3
            
        else:
            tiles_y = 1

        for tile_x in range(tiles_x):
            for tile_y in range(tiles_y):
                draw_x = start_x + tile_x * width
                if repeat_vertical:
                    draw_y = start_y + tile_y * height + int(foreground_layer["bob_offset"])
                    
                else:
                    draw_y = start_y + tile_y * height
                
                if (draw_x + width > 0 and draw_x < self.game.screen_width and 
                    draw_y + height > 0 and draw_y < self.game.screen_height):
                    self.game.screen.blit(alpha_image, (draw_x, draw_y))

    def render_world_effect(self, foreground_layer):
        image = foreground_layer["image"]
        if not image:
            return

        for particle in foreground_layer["particles"]:
            render_x = int(particle["x"] - self.cam_x)
            render_y = int(particle["y"] - self.cam_y)

            glow = 150 + int(105 * math.sin(self.game.environment.current_time * 0.002 + particle["x"]))
            glow_image = image.copy()
            glow_image.fill((glow, glow, glow, 0), special_flags=pg.BLEND_RGBA_ADD)

            self.game.screen.blit(glow_image, (render_x, render_y))

    def render_foreground_layers(self):
        for foreground_layer in self.layers:
            if not foreground_layer["image"]:
                continue
            
            match foreground_layer["type"]:
                case "overlay":
                    self.render_overlay(foreground_layer)
                
                case "scroll_overlay":
                    self.render_scroll_overlay(foreground_layer)
                
                case"world":
                    self.render_world_effect(foreground_layer)

    def update(self):
        self.update_camera()
        self.update_screen_effects()
        
        if self.enable_foreground:
            self.update_layers()
            self.render_foreground_layers()
        
        self.render_screen_effects()
