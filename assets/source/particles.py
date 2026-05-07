import pygame as pg

from collections import deque

class Particles:
    def __init__(self, game):
        self.game = game
        
        self.particles = deque(maxlen=game.environment.max_particles)
        self.pool = []
        
        self.enable_particles = True
        self.max_particles = game.environment.max_particles
        
        self.surface_cache = {}
        
        self.precreate_common_surfaces()
        self.update_tile_hitboxes()

    def update_tile_hitboxes(self):
        if hasattr(self.game.map, "tile_hitboxes"):
            self.tile_hitboxes = [[rect.x, rect.y, rect.width, rect.height] for rect in self.game.map.tile_hitboxes]
            
        else:
            self.tile_hitboxes = []

    def precreate_common_surfaces(self):
        common_radii = [2, 3, 4, 5, 6, 7, 8, 10, 12, 15]
        
        common_colors = [
            (255, 50, 50),
            (255, 0, 0),
            (100, 100, 100),
            (150, 150, 150),
            (255, 215, 0),
            (255, 255, 255),
            (0, 255, 0),
            (0, 100, 255),
        ]
        
        for radius in common_radii:
            for color in common_colors:
                cache_key = (radius, color[0], color[1], color[2])
                if cache_key not in self.surface_cache:
                    surf = pg.Surface((radius * 2, radius * 2), pg.SRCALPHA)
                    pg.draw.rect(surf, color, surf.get_rect())
                    self.surface_cache[cache_key] = surf

    def get_cached_surface(self, radius, color, alpha=None):
        cache_key = (radius, color[0], color[1], color[2])
        
        if cache_key not in self.surface_cache:
            surf = pg.Surface((radius * 2, radius * 2), pg.SRCALPHA)
            pg.draw.rect(surf, color, surf.get_rect())
            self.surface_cache[cache_key] = surf
        
        if alpha is not None and alpha < 255:
            cached = self.surface_cache[cache_key]
            copy = cached.copy()
            copy.set_alpha(alpha)
            return copy
        
        return self.surface_cache[cache_key]

    def get_particle_from_pool(self):
        if self.pool:
            particle = self.pool.pop()
            particle.clear()
            return particle
        
        return {}

    def recycle_particle(self, particle):
        if len(self.pool) < self.max_particles * 2:
            self.pool.append(particle)

    def find_valid_spawn_position(self, pos, radius):
        x, y = pos
        particle_rect = pg.Rect(x - radius, y - radius, radius * 2, radius * 2)

        if not hasattr(self.game.map, "get_nearby_tiles"):
            return pos
            
        nearby_tiles = self.game.map.get_nearby_tiles(particle_rect)
        
        for tile_hitbox, tile_id in nearby_tiles:
            if particle_rect.colliderect(tile_hitbox):
                max_search = 100
                
                for offset in range(1, max_search):
                    new_y = y - offset
                    test_rect = pg.Rect(x - radius, new_y - radius, radius * 2, radius * 2)
                    
                    valid = True
                    for test_hitbox, _ in nearby_tiles:
                        if test_rect.colliderect(test_hitbox):
                            valid = False
                            break
                    
                    if valid:
                        return (x, new_y)
                
                return pos
            
        return pos

    def handle_tile_collisions(self, particle):
        radius = particle["radius"]
        pos = particle["pos"]
        vel = particle["vel"]

        rect = pg.Rect(
            pos.x - radius,
            pos.y - radius,
            radius * 2,
            radius * 2
        )

        if not hasattr(self.game.map, "get_nearby_tiles"):
            pos += vel
            return
            
        nearby_tiles = self.game.map.get_nearby_tiles(rect)
        
        particle["on_ground"] = False

        # horizontal movement
        pos.x += vel.x
        rect.x = pos.x - radius

        for tile_hitbox, _ in nearby_tiles:
            if rect.colliderect(tile_hitbox):
                if vel.x > 0:
                    pos.x = tile_hitbox.left - radius
                    
                elif vel.x < 0:
                    pos.x = tile_hitbox.right + radius
                    
                vel.x = 0
                rect.x = pos.x - radius

        # vertical movement
        pos.y += vel.y
        rect.y = pos.y - radius

        for tile_hitbox, _ in nearby_tiles:
            if rect.colliderect(tile_hitbox):
                if vel.y > 0:
                    pos.y = tile_hitbox.top - radius
                    particle["on_ground"] = True
                    
                    if particle["floor_behavior"] == "bounce":
                        vel.y *= -0.6
                        if abs(vel.y) < 0.5:
                            vel.y = 0
                        
                    else:
                        vel.y = 0
                        
                elif vel.y < 0:
                    pos.y = tile_hitbox.bottom + radius
                    vel.y = 0
                    
                rect.y = pos.y - radius

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
            img = particle["image"]
            if particle["fade"]:
                alpha = max(0, 255 * (1 - particle["age"] / particle["lifespan"]))
                img = img.copy()
                img.set_alpha(alpha)
            surface.blit(img, screen_pos)
            
            return
        
        if particle["fade"]:
            alpha = max(0, 255 * (1 - particle["age"] / particle["lifespan"]))
            cached = self.get_cached_surface(particle["radius"], particle["color"], alpha)
            surface.blit(cached, screen_pos)
            
        else:
            cached = self.get_cached_surface(particle["radius"], particle["color"], None)
            surface.blit(cached, screen_pos)

    def generate(self, pos, velocity, color=(255, 255, 255), radius=5, lifespan=30,
                 image=None, image_size=None, fade=False, gravity=0.0,
                 floor_behavior=None, friction=None):
        if not self.enable_particles:
            return
        
        if floor_behavior:
            pos = self.find_valid_spawn_position(pos, radius)

        particle = self.get_particle_from_pool()
        
        particle["pos"] = pg.Vector2(pos)
        particle["vel"] = pg.Vector2(velocity)
        particle["color"] = color
        particle["radius"] = radius
        particle["lifespan"] = lifespan
        particle["age"] = 0
        particle["image"] = None
        particle["rect"] = None
        particle["fade"] = fade
        particle["gravity"] = gravity
        particle["friction"] = friction
        particle["floor_behavior"] = floor_behavior
        particle["on_ground"] = False

        if image:
            if image_size:
                image = pg.transform.scale(image, image_size)
                
            particle["image"] = image
            particle["rect"] = image.get_rect(center=pos)
            
        else:
            particle["rect"] = pg.Rect(pos[0] - radius, pos[1] - radius, radius * 2, radius * 2)

        self.particles.append(particle)

    def update_physics_batch(self):
        if not self.particles:
            return
        
        for particle in list(self.particles):
            particle["vel"].y += particle["gravity"]
            
            if particle.get("on_ground", False) and particle.get("friction"):
                particle["vel"].x *= (1 - particle["friction"])
                
                if abs(particle["vel"].x) < 0.1:
                    particle["vel"].x = 0
            
            if particle["floor_behavior"]:
                self.handle_tile_collisions(particle)
                
            else:
                particle["pos"] += particle["vel"]
            
            particle["age"] += 1
            
            if particle["image"]:
                particle["rect"].center = particle["pos"]
                
            else:
                particle["rect"].topleft = (particle["pos"].x - particle["radius"], particle["pos"].y - particle["radius"])

    def update(self):
        if not self.particles:
            return
        
        self.update_physics_batch()
        
        for particle in list(self.particles):
            if particle["age"] >= particle["lifespan"]:
                self.recycle_particle(particle)
                
            else:
                self.render_particle(self.game.screen, particle)
        
        self.particles = deque([p for p in self.particles if p["age"] < p["lifespan"]], maxlen=self.max_particles)

    def clear(self):     
        for particle in self.particles:
            self.recycle_particle(particle)
                
        del self.surface_cache
        self.particles.clear()
    
    def set_max_particles(self, max_particles):
        self.max_particles = max_particles
        self.particles = deque(list(self.particles)[:max_particles], maxlen=max_particles)
    
    def get_particle_count(self):
        return len(self.particles)
    
    def get_pool_size(self):
        return len(self.pool)