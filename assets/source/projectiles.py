import pygame as pg
import math
import random

class Projectile:
    __slots__ = (
        "x", "y", "width", "height", "vel_x", "vel_y", "lifetime",
        "damage", "push_force", "gravity", "image", "image_offset_x", 
        "image_offset_y", "scale", "piercing", "owner", "follow",
        "embed_on_wall", "fluid_drag", "fluid_drag_mult", "rotate_to_velocity",
        "rotation_offset", "rotation", "facing_direction", "flipped",
        "embedded", "hit_ids", "alive", "is_melee", "melee_direction",
        "knockback_direction_x", "get_facing_direction", "cached_image", "cached_rotation", "cached_flip"
    )

    def __init__(self):
        self.x = self.y = 0
        self.width = self.height = 10
        self.vel_x = self.vel_y = 0
        
        self.lifetime = 30
        self.damage = 0
        self.push_force = 0
        self.gravity = 0
        
        self.image = None
        self.image_offset_x = self.image_offset_y = 0
        self.scale = 1.0
        
        self.piercing = False
        self.owner = "player"
        self.follow = None
        self.embed_on_wall = False
        self.fluid_drag = False
        self.fluid_drag_mult = 0.85
        self.rotate_to_velocity = False
        self.rotation_offset = 0
        self.rotation = 0
        self.facing_direction = 1
        self.flipped = False
        self.embedded = False
        self.hit_ids = set()
        
        self.alive = False
        self.is_melee = False
        self.melee_direction = None
        self.knockback_direction_x = None
        self.get_facing_direction = None
        self.cached_image = None
        self.cached_rotation = -999
        self.cached_flip = False

    def reset(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
            
        self.alive = True
        self.embedded = False
        self.hit_ids.clear()
        self.cached_image = None
        self.cached_rotation = -999
        self.cached_flip = False
        
        if "flipped" not in kwargs:
            self.flipped = False
            
        if "rotation" not in kwargs:
            self.rotation = 0

class ProjectileSystem:
    def __init__(self, game, pool_size=200):
        self.game = game
        self.pool = [Projectile() for _ in range(pool_size)]
        self.projectiles = []
        self.scaled_cache = {}

    def spawn(self, **kwargs):
        if self.pool:
            projectile = self.pool.pop()
            projectile.reset(**kwargs)
            
        else:
            projectile = Projectile()
            projectile.reset(**kwargs)
            
        self.projectiles.append(projectile)
        
        return projectile

    def release(self, projectile, index):
        projectile.alive = False
        projectile.hit_ids.clear()
        
        projectile.follow = None
        projectile.image = None
        
        projectile.get_facing_direction = None
        projectile.cached_image = None
        
        last_index = len(self.projectiles) - 1
        if index != last_index:
            self.projectiles[index] = self.projectiles[last_index]
            
        self.projectiles.pop()
        self.pool.append(projectile)

    def get_rect(self, projectile):
        width = projectile.width * projectile.scale
        height = projectile.height * projectile.scale
        
        return pg.Rect(projectile.x - width / 2, projectile.y - height / 2, width, height)

    def visual_size(self, projectile):
        image = projectile.image
        scale = projectile.scale
        if image:
            image_width, image_height = image.get_size()
            return max(projectile.width * scale, image_width * scale), max(projectile.height * scale, image_height * scale)
        
        return projectile.width * scale, projectile.height * scale

    def hits_wall(self, rect):
        for tile_hitbox, tile_id in self.game.map.get_nearby_tiles(rect, padding=2):
            attributes = self.game.map.tile_attributes.get(tile_id, {})
            
            if not attributes.get("swimmable", False) and rect.colliderect(tile_hitbox):
                return True
            
        return False

    def in_fluid(self, projectile, rect):
        if not projectile.fluid_drag:
            return False
        
        for tile_hitbox, tile_id in self.game.map.get_nearby_tiles(rect, padding=2):
            attributes = self.game.map.tile_attributes.get(tile_id, {})
            if attributes.get("swimmable", False) and rect.colliderect(tile_hitbox):
                
                return True
        return False

    def is_offscreen(self, projectile):
        camera_x = self.game.player.cam_x
        camera_y = self.game.player.cam_y
        
        screen_width = self.game.screen_width
        screen_height = self.game.screen_height
        visual_width, visual_height = self.visual_size(projectile)
        
        offset_x = projectile.image_offset_x
        offset_y = projectile.image_offset_y
        
        visual_rect = pg.Rect(projectile.x - visual_width/2 + offset_x, projectile.y - visual_height/2 + offset_y, visual_width, visual_height)
        
        screen_rect = pg.Rect(camera_x, camera_y, screen_width, screen_height)
        return not visual_rect.colliderect(screen_rect)

    def should_update(self, projectile):
        camera_x = self.game.player.cam_x
        camera_y = self.game.player.cam_y
        
        screen_width = self.game.screen_width
        screen_height = self.game.screen_height
        
        half_width = screen_width // 2
        half_height = screen_height // 2
        
        update_bounds = pg.Rect(camera_x - half_width, camera_y - half_height, screen_width + (half_width * 2), screen_height + (half_height * 2))
        
        return update_bounds.collidepoint(projectile.x, projectile.y)

    def should_render(self, projectile):
        camera_x = self.game.player.cam_x
        camera_y = self.game.player.cam_y
        
        screen_width = self.game.screen_width
        screen_height = self.game.screen_height
        
        half_width = screen_width // 2
        half_height = screen_height // 2
        
        render_bounds = pg.Rect(camera_x - half_width, camera_y - half_height, screen_width + (half_width * 2), screen_height + (half_height * 2))
        visual_width, visual_height = self.visual_size(projectile)
        
        offset_x = projectile.image_offset_x
        offset_y = projectile.image_offset_y
        
        visual_rect = pg.Rect(projectile.x - visual_width/2 + offset_x, projectile.y - visual_height/2 + offset_y, visual_width, visual_height)
        
        return visual_rect.colliderect(render_bounds)

    def update_rotation(self, projectile):
        if not projectile.rotate_to_velocity:
            return
        
        if abs(projectile.vel_x) > 0.1 or abs(projectile.vel_y) > 0.1:
            angle_rad = math.atan2(projectile.vel_y, projectile.vel_x)
            projectile.rotation = math.degrees(angle_rad) + projectile.rotation_offset

    def check_entity_hits(self, projectile, rect):
        if projectile.embedded:
            return
            
        if projectile.owner == "player":
            for entity in self.game.entities.entities:
                if entity["entity_type"] not in {"enemy", "npc", "actor"}:
                    continue
                
                entity_id = id(entity)
                if entity_id in projectile.hit_ids:
                    continue
                
                hitbox_width = entity.get("hitbox_width", entity["width"])
                hitbox_height = entity.get("hitbox_height", entity["height"])
                
                offset_x = entity.get("hitbox_offset_x", 0)
                offset_y = entity.get("hitbox_offset_y", 0)
                
                entity_rect = pg.Rect(entity["x"] - hitbox_width/2 + offset_x, entity["y"] - hitbox_height/2 + offset_y, hitbox_width, hitbox_height)
                
                if not rect.colliderect(entity_rect):
                    continue
                
                if entity["entity_type"] in {"enemy", "npc"} and entity["health"] > 0:
                    entity["health"] -= projectile.damage
                    entity["damage_effect"] = 1
                    self.game.player.shake_camera(intensity=4.4, duration=25) # 3.2
                    self.game.entities.spawn_hit_particles(entity)
                    for sound_data in self.game.entities.sounds["hit"]:
                        sound_data["sound"].stop()
                        
                    random.choice(self.game.entities.sounds["hit"])["sound"].play()
                    
                if entity.get("abilities") and "pushable" in entity["abilities"]:
                    if projectile.is_melee:
                        if projectile.get_facing_direction:
                            direction_sign = projectile.get_facing_direction()
                            
                        elif projectile.melee_direction is not None:
                            direction_sign = projectile.melee_direction
                            
                        else:
                            direction_sign = 1 if entity["x"] > self.game.player.x else -1
                            
                    else:
                        if projectile.knockback_direction_x is not None:
                            direction_sign = projectile.knockback_direction_x
                            
                        else:
                            direction_sign = 1 if projectile.vel_x >= 0 else -1
                            
                    push_force = projectile.push_force / max(entity.get("weight", 1), 0.1)
                    self.game.entities.apply_knockback(entity, direction_sign, push_force)
                                    
                if not projectile.piercing:
                    projectile.alive = False
                    return
                
                projectile.hit_ids.add(entity_id)
                
        else:
            player_id = id(self.game.player)
            if player_id not in projectile.hit_ids and rect.colliderect(self.game.player.hitbox):
                if projectile.is_melee and projectile.melee_direction is not None:
                    direction_sign = projectile.melee_direction
                    
                elif projectile.knockback_direction_x is not None:
                    direction_sign = projectile.knockback_direction_x
                    
                else:
                    direction_sign = 1 if projectile.vel_x >= 0 else -1

                if projectile.push_force:
                    self.game.player.vel_x = direction_sign * projectile.push_force
                    if self.game.player.vel_y >= 0:
                        self.game.player.vel_y = -abs(projectile.push_force) * 0.1
                        
                    else:
                        self.game.player.vel_y += -abs(projectile.push_force) * 0.05

                self.game.player.take_damage(projectile.damage)
                projectile.hit_ids.add(player_id)

                if not projectile.piercing:
                    projectile.alive = False

    def update(self):
        projectile_index = 0
        while projectile_index < len(self.projectiles):
            projectile = self.projectiles[projectile_index]

            if not projectile.alive:
                self.release(projectile, projectile_index)
                continue

            rect = self.get_rect(projectile)

            if projectile.follow is not None:
                new_position = projectile.follow()
                projectile.x, projectile.y = new_position
                rect = self.get_rect(projectile)

            elif projectile.embedded:
                projectile.lifetime -= 1
                if projectile.lifetime <= 0:
                    self.release(projectile, projectile_index)
                    continue

            else:
                if self.in_fluid(projectile, rect):
                    drag_multiplier = projectile.fluid_drag_mult
                    projectile.vel_x *= drag_multiplier
                    projectile.vel_y *= drag_multiplier

                projectile.vel_y += projectile.gravity
                projectile.x += projectile.vel_x
                projectile.y += projectile.vel_y

                self.update_rotation(projectile)
                rect = self.get_rect(projectile)

            projectile.lifetime -= 1
            if projectile.lifetime <= 0:
                self.release(projectile, projectile_index)
                continue

            if projectile.follow is None and not projectile.embedded:
                if self.game.environment.vigorous_optimizations:
                    if self.is_offscreen(projectile):
                        if self.should_update(projectile):
                            self.release(projectile, projectile_index)
                            continue
                    
                else:
                    if not self.should_update(projectile):
                        self.release(projectile, projectile_index)
                        continue

                if self.hits_wall(rect):
                    if projectile.embed_on_wall:
                        step_x = projectile.vel_x * 0.25
                        step_y = projectile.vel_y * 0.25
                        
                        for backup_step in range(4):
                            projectile.x -= step_x
                            projectile.y -= step_y
                            rect = self.get_rect(projectile)
                            if not self.hits_wall(rect):
                                break

                        projectile.flipped = projectile.vel_x < 0
                        projectile.embedded = True
                        projectile.vel_x = 0
                        projectile.vel_y = 0

                    else:
                        self.release(projectile, projectile_index)
                        continue

            self.check_entity_hits(projectile, rect)
            projectile_index += 1

        self.render()

    def render(self):
        debugging = self.game.debugging
        
        for projectile in self.projectiles:
            if not projectile.alive:
                continue

            camera_x = self.game.player.cam_x
            camera_y = self.game.player.cam_y
            rect = self.get_rect(projectile)

            if debugging:
                debug_color = (255, 80, 80) if projectile.owner == "player" else (255, 140, 0)
                fill_surface = pg.Surface((max(1, rect.width), max(1, rect.height)), pg.SRCALPHA)
                fill_surface.fill((*debug_color, 120))
                self.game.screen.blit(fill_surface, (rect.x - camera_x, rect.y - camera_y))
                pg.draw.rect(self.game.screen, debug_color, (rect.x - camera_x, rect.y - camera_y, rect.width, rect.height), 2)
                pg.draw.circle(self.game.screen, debug_color, (int(rect.centerx - camera_x), int(rect.centery - camera_y)), 4)

            if not self.should_render(projectile):
                continue

            if projectile.image is not None:
                image = projectile.image
                
                cache_key = (id(image), projectile.scale)
                if cache_key in self.scaled_cache:
                    image = self.scaled_cache[cache_key]
                    
                elif projectile.scale != 1.0:
                    new_width = int(image.get_width() * projectile.scale)
                    new_height = int(image.get_height() * projectile.scale)
                    image = pg.transform.scale(image, (new_width, new_height))
                    self.scaled_cache[cache_key] = image
                    
                if projectile.embedded:
                    should_flip = projectile.flipped
                    
                else:
                    should_flip = projectile.vel_x < 0
                    projectile.flipped = should_flip
                    
                if projectile.rotate_to_velocity:
                    rotation = projectile.rotation
                    if rotation != 0:
                        if (projectile.cached_image is not None and 
                            projectile.cached_rotation == rotation and 
                            projectile.cached_flip == should_flip):
                            image = projectile.cached_image
                            
                        else:
                            if should_flip:
                                flipped_image = pg.transform.flip(image, True, False)
                                rotated_image = pg.transform.rotate(flipped_image, -rotation)
                                
                            else:
                                rotated_image = pg.transform.rotate(image, -rotation)
                                
                            projectile.cached_image = rotated_image
                            projectile.cached_rotation = rotation
                            projectile.cached_flip = should_flip
                            image = rotated_image
                            
                        hitbox_center_x = rect.centerx - camera_x
                        hitbox_center_y = rect.centery - camera_y
                        rotated_rect = image.get_rect(center=(hitbox_center_x, hitbox_center_y))
                        rotated_rect.x += projectile.image_offset_x
                        rotated_rect.y += projectile.image_offset_y
                        self.game.screen.blit(image, rotated_rect)
                        
                        if debugging:
                            pg.draw.circle(self.game.screen, (255, 0, 0), (int(hitbox_center_x), int(hitbox_center_y)), 4)
                            pg.draw.circle(self.game.screen, (0, 255, 0), (int(rotated_rect.centerx), int(rotated_rect.centery)), 3)
                            debug_color = (255, 80, 80) if projectile.owner == "player" else (255, 140, 0)
                            pg.draw.rect(self.game.screen, debug_color, (rect.x - camera_x, rect.y - camera_y, rect.width, rect.height), 2)
                            
                        continue
                    
                    else:
                        if should_flip:
                            image = pg.transform.flip(image, True, False)
                            
                else:
                    if should_flip:
                        image = pg.transform.flip(image, True, False)
                        
                hitbox_center_x = rect.centerx - camera_x
                hitbox_center_y = rect.centery - camera_y
                
                image_rect = image.get_rect(center=(hitbox_center_x, hitbox_center_y))
                
                image_rect.x += projectile.image_offset_x
                image_rect.y += projectile.image_offset_y
                
                self.game.screen.blit(image, image_rect)
                
                if debugging:
                    pg.draw.circle(self.game.screen, (255, 0, 0), (int(hitbox_center_x), int(hitbox_center_y)), 4)
                    pg.draw.circle(self.game.screen, (0, 255, 0), (int(image_rect.centerx), int(image_rect.centery)), 3)

            if debugging and projectile.rotate_to_velocity and not projectile.embedded:
                    center_x = rect.centerx - camera_x
                    center_y = rect.centery - camera_y
                    angle_rad = math.radians(projectile.rotation)
                    if projectile.vel_x < 0:
                        angle_rad = -angle_rad
                        
                    line_length = 20
                    end_x = center_x + math.cos(angle_rad) * line_length
                    end_y = center_y + math.sin(angle_rad) * line_length
                    
                    pg.draw.line(self.game.screen, (255, 255, 0), (center_x, center_y), (end_x, end_y), 2)
                    pg.draw.circle(self.game.screen, (255, 255, 0), (int(center_x), int(center_y)), 3)