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

                    if layer_type == "screen_overlay":
                        layer.update({
                            "scroll_x": fg_data.get("scroll_speed_x", 0),
                            "scroll_y": fg_data.get("scroll_speed_y", 0),
                            "loop": fg_data.get("loop", True),
                            "opacity": fg_data.get("opacity", 1.0),
                            "bob_amount": fg_data.get("bob_amount", 8),
                            "bob_speed": fg_data.get("bob_speed", 1.0),
                            "offset_x": 0,
                            "offset_y": 0,
                            "time": 0,
                            "bob_offset": 0
                        })

                    elif layer_type == "world":
                        count = fg_data.get("count", 5)
                        radius = fg_data.get("radius", 50)
                        particles = []
                        for _ in range(count):
                            px = fg_data["x"] + random.uniform(-radius, radius)
                            py = fg_data["y"] + random.uniform(-radius, radius)
                            particles.append({
                                "x": px,
                                "y": py,
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

                self.layers.sort(key=lambda fg: fg["layer"])

        except Exception as e:
            print(f"Failed to load foreground info: {e}")

    def update_camera(self):
        if hasattr(self.game, "player"):
            self.cam_x = self.game.player.cam_x
            self.cam_y = self.game.player.cam_y

    def update_layers(self):
        dt = self.game.dt if hasattr(self.game, "dt") else 1
        current_time = pg.time.get_ticks() * 0.001

        for fg in self.layers:
            if fg["type"] == "screen_overlay":
                fg["time"] += dt
                fg["offset_x"] += fg["scroll_x"] * dt
                fg["offset_y"] += fg["scroll_y"] * dt

                if fg["loop"]:
                    fg["offset_x"] %= fg["width"]
                    fg["offset_y"] %= fg["height"]

                if fg["bob_amount"] > 0:
                    fg["bob_offset"] = math.sin(fg["time"] * fg["bob_speed"]) * fg["bob_amount"]
        
                else:
                    fg["bob_offset"] = 0

            elif fg["type"] == "world":
                for p in fg["particles"]:
                    p["angle"] += (random.random() - 0.5) * 0.05
                    p["x"] += math.cos(p["angle"]) * p["speed"]
                    p["y"] += math.sin(p["angle"]) * p["speed"]

    def render(self):
        for fg in self.layers:
            if not fg["image"]:
                continue

            if fg["type"] == "screen_overlay":
                self.render_screen_overlay(fg)

            elif fg["type"] == "world":
                self.render_world_effect(fg)

    def render_screen_overlay(self, fg):
        image = fg["image"]
        if not image:
            return

        width, height = fg["width"], fg["height"]
        offset_x, offset_y = fg["offset_x"], fg["offset_y"]
        fog_y = fg["y"] + fg["bob_offset"]

        # Apply opacity
        alpha_image = image.copy()
        alpha_value = int(fg["opacity"] * 255)
        alpha_image.set_alpha(alpha_value)

        # Wrap offsets precisely
        if fg["loop"]:
            offset_x = math.fmod(offset_x, width)
            offset_y = math.fmod(offset_y, height)

        start_x = -offset_x
        start_y = -offset_y

        tiles_x = self.game.screen_width // width + 2
        tiles_y = self.game.screen_height // height + 2

        for x in range(tiles_x):
            for y in range(tiles_y):
                draw_x = int(start_x + x * width)
                draw_y = int(start_y + y * height + fog_y)
                self.game.screen.blit(alpha_image, (draw_x, draw_y))

    def render_world_effect(self, fg):
        image = fg["image"]
        if not image:
            return

        for p in fg["particles"]:
            render_x = p["x"] - self.cam_x
            render_y = p["y"] - self.cam_y

            glow = 150 + int(105 * math.sin(pg.time.get_ticks() * 0.002 + p["x"]))
            glow_image = image.copy()
            glow_image.fill((glow, glow, glow, 0), special_flags=pg.BLEND_RGBA_ADD)

            self.game.screen.blit(glow_image, (render_x, render_y))

    def update(self):
        if not self.enable_foreground:
            return

        self.update_camera()
        self.update_layers()
        self.render()
