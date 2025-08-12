import pygame as pg
import random
import numpy as np

class Particles:
    def __init__(self, game):
        self.game = game
        self.particles = []
        self.pool = []
        
        self.max_particles = game.environment.max_particles

        self.tile_hitboxes_np = np.array([[rect.x, rect.y, rect.width, rect.height] for rect in self.game.map.tile_hitboxes]) if hasattr(self.game.map, "tile_hitboxes") else np.empty((0, 4))

    def get_particle_from_pool(self):
        return self.pool.pop() if self.pool else {}

    def recycle_particle(self, p):
        self.pool.append(p)

    def generate(self, pos, velocity, color=(255, 255, 255), radius=5, lifespan=30, image=None, image_size=None, fade=False, gravity=0.0, floor_behavior=None, friction=None):
        if floor_behavior:
            pos = self.find_valid_spawn_position(pos, radius)

        p = self.get_particle_from_pool()
        p.update({
            "pos": pg.Vector2(pos),
            "vel": pg.Vector2(velocity),
            "color": color,
            "radius": radius,
            "lifespan": lifespan,
            "age": 0,
            "image": None,
            "rect": None,
            "fade": fade,
            "gravity": gravity,
            "friction": friction,
            "floor_behavior": floor_behavior,
        })

        if image:
            if image_size:
                image = pg.transform.scale(image, image_size)
                
            p["image"] = image
            p["rect"] = image.get_rect(center=pos)
            
        else:
            p["rect"] = pg.Rect(pos[0] - radius, pos[1] - radius, radius * 2, radius * 2)

        self.particles.append(p)

    def find_valid_spawn_position(self, pos, radius):
        x, y = pos
        particle_rect = pg.Rect(x - radius, y - radius, radius * 2, radius * 2)

        nearby_tiles = self.game.map.get_nearby_tiles(particle_rect)
        
        for tile_hitbox, tile_id in nearby_tiles:
            if particle_rect.colliderect(tile_hitbox):
                max_search = 100
                hitboxes = self.tile_hitboxes_np

                for offset in range(1, max_search):
                    new_y = y + offset
                    tx, ty, tw, th = x - radius, new_y - radius, radius * 2, radius * 2
                    x_overlap = (hitboxes[:, 0] < tx + tw) & (hitboxes[:, 0] + hitboxes[:, 2] > tx)
                    y_overlap = (hitboxes[:, 1] < ty + th) & (hitboxes[:, 1] + hitboxes[:, 3] > ty)
                    if not np.any(x_overlap & y_overlap):
                        return (x, new_y)

                return pos
            
        return pos
    
    def enforce_max(self):
        excess = len(self.particles) - self.max_particles
        if excess > 0:
            oldest_indices = sorted(range(len(self.particles)), key=lambda i: self.particles[i]["age"], reverse=True)

            for i in oldest_indices[:excess]:
                self.recycle_particle(self.particles[i])

            self.particles = [p for j, p in enumerate(self.particles) if j not in set(oldest_indices[:excess])]

    def handle_floor_collision(self, p):
        tile_size = self.game.map.tile_dimension * self.game.map.map_scale

        bottom = p["pos"].y + p["radius"]
        left = p["pos"].x - p["radius"]
        right = p["pos"].x + p["radius"]

        particle_rect = pg.Rect(left, bottom, right - left, 1)

        nearby_tiles = self.game.map.get_nearby_tiles(particle_rect)

        for tile_hitbox, tile_id in nearby_tiles:
            tile_top = tile_hitbox.y
            tile_left = tile_hitbox.x
            tile_right = tile_hitbox.x + tile_hitbox.width

            if (right > tile_left and left < tile_right and bottom >= tile_top and p["vel"].y > 0):
                p["pos"].y = tile_top - p["radius"]

                if p["floor_behavior"] == "bounce":
                    p["vel"].y *= -0.6
                    
                    if abs(p["vel"].y) < 0.5:
                        p["vel"].y = 0

                elif p["floor_behavior"] == "stop":
                    p["vel"].y = 0

                if p["friction"] is not None and p["friction"] > 0:
                    if abs(p["vel"].x) < 0.1:
                        p["vel"].x = 0
                        
                    else:
                        p["vel"].x *= (1 - p["friction"])
                return

    def render_particle(self, surface, p):
        screen_width, screen_height = self.game.screen_width, self.game.screen_height
        cam_x, cam_y = self.game.player.cam_x, self.game.player.cam_y

        screen_x = p["rect"].x - cam_x
        screen_y = p["rect"].y - cam_y
        w, h = p["rect"].width, p["rect"].height

        if screen_x + w < 0 or screen_x > screen_width or screen_y + h < 0 or screen_y > screen_height:
            return

        if self.game.environment.menu not in {"play", "death", "pause"}:
            return

        screen_pos = (screen_x, screen_y)

        if p["image"]:
            img = p["image"].copy()
            if p["fade"]:
                alpha = max(0, 255 * (1 - p["age"] / p["lifespan"]))
                img.set_alpha(alpha)
            surface.blit(img, screen_pos)
            
        else:
            if p["fade"]:
                alpha = max(0, 255 * (1 - p["age"] / p["lifespan"]))
                color = (*p["color"][:3], int(alpha))
                surf = pg.Surface((p["radius"] * 2, p["radius"] * 2), pg.SRCALPHA)
                pg.draw.rect(surf, color, surf.get_rect())
                surface.blit(surf, screen_pos)
                
            else:
                pg.draw.rect(surface, p["color"], pg.Rect(screen_pos[0], screen_pos[1], p["radius"] * 2, p["radius"] * 2))

    def update(self):
        if not self.particles:
            return

        self.enforce_max()

        n = len(self.particles)
        positions = np.array([p["pos"] for p in self.particles], dtype=np.float32)
        velocities = np.array([p["vel"] for p in self.particles], dtype=np.float32)
        gravities = np.array([p["gravity"] for p in self.particles], dtype=np.float32)
        ages = np.array([p["age"] for p in self.particles], dtype=np.int32)
        lifespans = np.array([p["lifespan"] for p in self.particles], dtype=np.int32)

        velocities[:, 1] += gravities
        positions += velocities
        ages += 1

        for i, p in enumerate(self.particles):
            p["pos"].x, p["pos"].y = positions[i]
            p["vel"].x, p["vel"].y = velocities[i]
            p["age"] = int(ages[i])

            if p["floor_behavior"]:
                self.handle_floor_collision(p)

            if p["image"]:
                p["rect"].center = p["pos"]
                
            else:
                p["rect"].topleft = (p["pos"].x - p["radius"], p["pos"].y - p["radius"])

        alive_particles = []
        for p in self.particles:
            if p["age"] >= p["lifespan"]:
                self.recycle_particle(p)
                
            else:
                alive_particles.append(p)
                self.render_particle(self.game.screen, p)
                
        self.particles = alive_particles