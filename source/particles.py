import pygame as pg
import random
import numpy as np

class Particles:
    def __init__(self, game):
        self.game = game
        self.particles = []
        self.pool = []
        
        self.enable_particles = True
        
        self.max_particles = game.environment.max_particles

        self.tile_hitboxes = np.array([[rect.x, rect.y, rect.width, rect.height] for rect in self.game.map.tile_hitboxes]) if hasattr(self.game.map, "tile_hitboxes") else np.empty((0, 4))

    def get_particle_from_pool(self):
        return self.pool.pop() if self.pool else {}

    def recycle_particle(self, particle):
        self.pool.append(particle)

    def generate(self, pos, velocity, color=(255, 255, 255), radius=5, lifespan=30, image=None, image_size=None, fade=False, gravity=0.0, floor_behavior=None, friction=None, rotate=False):
        if not self.enable_particles:
            return
            
        if floor_behavior:
            pos = self.find_valid_spawn_position(pos, radius)

        particle = self.get_particle_from_pool()
        particle.update({
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
            "rotate": rotate,
        })

        if image:
            if image_size:
                image = pg.transform.scale(image, image_size)
                
            particle["image"] = image
            particle["rect"] = image.get_rect(center=pos)
            
        else:
            particle["rect"] = pg.Rect(pos[0] - radius, pos[1] - radius, radius * 2, radius * 2)

        self.particles.append(particle)

    def find_valid_spawn_position(self, pos, radius):
        x, y = pos
        particle_rect = pg.Rect(x - radius, y - radius, radius * 2, radius * 2)

        nearby_tiles = self.game.map.get_nearby_tiles(particle_rect)
        
        for tile_hitbox, tile_id in nearby_tiles:
            if particle_rect.colliderect(tile_hitbox):
                max_search = 100
                hitboxes = self.tile_hitboxes

                if hitboxes.ndim != 2 or hitboxes.shape[1] != 4:
                    return pos

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
        
        if excess <= 0:
            return

        oldest_indices = sorted(range(len(self.particles)), key=lambda i: self.particles[i]["age"], reverse=True)[:excess]

        for i in oldest_indices:
            self.recycle_particle(self.particles[i])

        oldest_set = set(oldest_indices)
        self.particles = [p for j, p in enumerate(self.particles) if j not in oldest_set]

    def handle_floor_collision(self, particle):
        tile_size = self.game.map.tile_dimension * self.game.map.map_scale

        bottom = particle["pos"].y + particle["radius"]
        left = particle["pos"].x - particle["radius"]
        right = particle["pos"].x + particle["radius"]

        particle_rect = pg.Rect(left, bottom, right - left, 1)

        nearby_tiles = self.game.map.get_nearby_tiles(particle_rect)

        for tile_hitbox, tile_id in nearby_tiles:
            tile_top = tile_hitbox.y
            tile_left = tile_hitbox.x
            tile_right = tile_hitbox.x + tile_hitbox.width

            if (right > tile_left and left < tile_right and bottom >= tile_top and particle["vel"].y > 0):
                particle["pos"].y = tile_top - particle["radius"]

                if particle["floor_behavior"] == "bounce":
                    particle["vel"].y *= -0.6

                    if abs(particle["vel"].y) < 0.5:
                        particle["vel"].y = 0

                elif particle["floor_behavior"] == "stop":
                    particle["vel"].y = 0

                if particle["friction"] is not None and particle["friction"] > 0:
                    if abs(particle["vel"].x) < 0.1:
                        particle["vel"].x = 0
                        
                    else:
                        particle["vel"].x *= (1 - particle["friction"])
                        
                return

    def render_particle(self, surface, particle):
        screen_width, screen_height = self.game.screen_width, self.game.screen_height
        cam_x, cam_y = self.game.player.cam_x, self.game.player.cam_y

        screen_x = particle["rect"].x - cam_x
        screen_y = particle["rect"].y - cam_y
        w, h = particle["rect"].width, particle["rect"].height

        if screen_x + w < 0 or screen_x > screen_width or screen_y + h < 0 or screen_y > screen_height:
            return

        if self.game.environment.menu not in {"play", "death", "pause"}:
            return

        screen_pos = (screen_x, screen_y)

        if particle["image"]:
            img = particle["image"].copy()
            if particle["fade"]:
                alpha = max(0, 255 * (1 - particle["age"] / particle["lifespan"]))
                img.set_alpha(alpha)

            if particle["rotate"]:
                rotation = random.choice(["left", "right"])
                rotation_amount = random.randint(-10, 10)
                if rotation == "right":
                    img = pg.transform.rotate(img, rotation_amount)
                
            surface.blit(img, screen_pos)
            
        else:
            if particle["fade"]:
                alpha = max(0, 255 * (1 - particle["age"] / particle["lifespan"]))
                color = (*particle["color"][:3], int(alpha))
                surf = pg.Surface((particle["radius"] * 2, particle["radius"] * 2), pg.SRCALPHA)
                pg.draw.rect(surf, color, surf.get_rect())
                surface.blit(surf, screen_pos)
                
            else:
                pg.draw.rect(surface, particle["color"], pg.Rect(screen_pos[0], screen_pos[1], particle["radius"] * 2, particle["radius"] * 2))

    def update(self):
        if not self.particles:
            return

        self.enforce_max()

        n = len(self.particles)
        positions = np.array([particle["pos"] for particle in self.particles], dtype=np.float32)
        velocities = np.array([particle["vel"] for particle in self.particles], dtype=np.float32)
        gravities = np.array([particle["gravity"] for particle in self.particles], dtype=np.float32)
        ages = np.array([particle["age"] for particle in self.particles], dtype=np.int32)
        lifespans = np.array([particle["lifespan"] for particle in self.particles], dtype=np.int32)

        velocities[:, 1] += gravities
        positions += velocities
        ages += 1

        for i, particle in enumerate(self.particles):
            particle["pos"].x, particle["pos"].y = positions[i]
            particle["vel"].x, particle["vel"].y = velocities[i]
            particle["age"] = int(ages[i])

            if particle["floor_behavior"]:
                self.handle_floor_collision(particle)

            if particle["image"]:
                particle["rect"].center = particle["pos"]
                
            else:
                particle["rect"].topleft = (particle["pos"].x - particle["radius"], particle["pos"].y - particle["radius"])

        alive_particles = []
        
        for particle in self.particles:
            if particle["age"] >= particle["lifespan"]:
                self.recycle_particle(particle)
                
            else:
                alive_particles.append(particle)
                self.render_particle(self.game.screen, particle)
                
        self.particles = alive_particles
