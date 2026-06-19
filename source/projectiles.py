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
        "knockback_direction_x", "get_facing_direction", "cached_image",
        "cached_rotation", "cached_flip",
        "rect", "scaled_image", "scale_key", "visual_size_cache"
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

        self.rect = pg.Rect(0, 0, 0, 0)
        self.scaled_image = None
        self.scale_key = None
        self.visual_size_cache = (0, 0)

    def reset(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.alive = True
        self.embedded = False
        self.hit_ids.clear()
        self.cached_image = None
        self.cached_rotation = -999
        self.cached_flip = False
        self.scaled_image = None
        self.scale_key = None
        self.visual_size_cache = (0, 0)

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
        self.scaled_cache_keys = []
        self.scaled_cache_max = 128

        self.swimmable_tile_ids = {
            tile_id for tile_id, attrs in self.game.map.tile_attributes.items()
            if attrs.get("swimmable", False)
        }
        self.swimmable_dirty = False

    def invalidate_swimmable_cache(self):
        self.swimmable_dirty = True

    def refresh_swimmable_cache(self):
        self.swimmable_tile_ids = {
            tile_id for tile_id, attrs in self.game.map.tile_attributes.items()
            if attrs.get("swimmable", False)
        }

        self.swimmable_dirty = False

    def cache_scaled_image(self, key, image):
        if len(self.scaled_cache) >= self.scaled_cache_max:
            oldest_key = self.scaled_cache_keys.pop(0)
            self.scaled_cache.pop(oldest_key, None)

        self.scaled_cache[key] = image
        self.scaled_cache_keys.append(key)

    def spawn(self, **kwargs):
        projectile = self.pool.pop() if self.pool else Projectile()
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
        projectile.scaled_image = None
        projectile.scale_key = None
        projectile.visual_size_cache = (0, 0)

        last_index = len(self.projectiles) - 1
        if index != last_index:
            self.projectiles[index] = self.projectiles[last_index]

        self.projectiles.pop()
        self.pool.append(projectile)

    def get_rect(self, projectile):
        width = projectile.width * projectile.scale
        height = projectile.height * projectile.scale
        rect = projectile.rect
        rect.x = projectile.x - width * 0.5
        rect.y = projectile.y - height * 0.5
        rect.width = width
        rect.height = height
        return rect

    def visual_size(self, projectile):
        scale = projectile.scale
        image = projectile.image
        cache_image_id = id(image) if image else None

        if projectile.visual_size_cache != (0, 0) and projectile.scale_key == (scale, cache_image_id):
            return projectile.visual_size_cache

        if image:
            iw, ih = image.get_size()
            width = max(projectile.width * scale, iw * scale)
            height = max(projectile.height * scale, ih * scale)
            
        else:
            width = projectile.width * scale
            height = projectile.height * scale

        projectile.visual_size_cache = (width, height)
        projectile.scale_key = (scale, cache_image_id)
        return width, height

    def hits_wall(self, rect):
        for tile_hitbox, tile_id in self.game.map.get_nearby_tiles(rect, padding=2):
            attributes = self.game.map.tile_attributes.get(tile_id, {})
            if not attributes.get("swimmable", False) and rect.colliderect(tile_hitbox):
                return True
            
        return False

    def in_fluid(self, projectile, rect):
        if not projectile.fluid_drag:
            return False
        
        swimmable = self.swimmable_tile_ids
        for tile_hitbox, tile_id in self.game.map.get_nearby_tiles(rect, padding=2):
            if tile_id in swimmable and rect.colliderect(tile_hitbox):
                return True
            
        return False

    def _make_update_bounds(self, camera_x, camera_y, screen_width, screen_height):
        half_w = screen_width // 2
        half_h = screen_height // 2
        
        return pg.Rect(
            camera_x - half_w,
            camera_y - half_h,
            screen_width + half_w * 2,
            screen_height + half_h * 2,
        )

    def is_offscreen(self, projectile, screen_rect):
        visual_width, visual_height = self.visual_size(projectile)
        vr = pg.Rect(
            projectile.x - visual_width * 0.5 + projectile.image_offset_x,
            projectile.y - visual_height * 0.5 + projectile.image_offset_y,
            visual_width,
            visual_height,
        )
        
        return not vr.colliderect(screen_rect)

    def should_update(self, projectile, update_bounds):
        return update_bounds.collidepoint(projectile.x, projectile.y)

    def should_render(self, projectile, render_bounds):
        visual_width, visual_height = self.visual_size(projectile)
        vr = pg.Rect(
            projectile.x - visual_width * 0.5 + projectile.image_offset_x,
            projectile.y - visual_height * 0.5 + projectile.image_offset_y,
            visual_width,
            visual_height,
        )
        return vr.colliderect(render_bounds)

    def update_rotation(self, projectile):
        if not projectile.rotate_to_velocity:
            return
        
        vx, vy = projectile.vel_x, projectile.vel_y
        if abs(vx) > 0.1 or abs(vy) > 0.1:
            projectile.rotation = math.degrees(math.atan2(vy, vx)) + projectile.rotation_offset

    def check_entity_hits(self, projectile, rect):
        if projectile.embedded:
            return

        if projectile.owner == "player":
            entities = self.game.entities
            player = self.game.player
            hit_sounds = entities.sounds.get("hit", [])

            for entity in entities.entities[:]: 
                etype = entity.get("entity_type")
                if etype not in ("enemy", "npc", "actor") or not entity.get("projectile_target", False):
                    continue

                entity_id = id(entity)
                if entity_id in projectile.hit_ids:
                    continue

                hitbox_width = entity.get("hitbox_width", entity["width"])
                hitbox_height = entity.get("hitbox_height", entity["height"])
                offset_x = entity.get("hitbox_offset_x", 0)
                offset_y = entity.get("hitbox_offset_y", 0)

                entity_rect = pg.Rect(
                    entity["x"] - hitbox_width * 0.5 + offset_x,
                    entity["y"] - hitbox_height * 0.5 + offset_y,
                    hitbox_width,
                    hitbox_height,
                )

                if not rect.colliderect(entity_rect):
                    continue

                if etype in ("enemy", "npc") and entity.get("health", 0) > 0:
                    entity["health"] -= projectile.damage
                    entity["damage_effect"] = 1
                    
                    self.game.camera.shake(intensity=4.4, duration=25)
                    entities.spawn_hit_particles(entity)
                    
                    for sound_data in hit_sounds:
                        sound_data["sound"].stop()
                        
                    if hit_sounds:
                        random.choice(hit_sounds)["sound"].play()

                if entity.get("abilities") and "pushable" in entity["abilities"]:
                    if projectile.is_melee:
                        if projectile.get_facing_direction:
                            direction_sign = projectile.get_facing_direction()
                            
                        elif projectile.melee_direction is not None:
                            direction_sign = projectile.melee_direction
                            
                        else:
                            direction_sign = 1 if entity["x"] > player.x else -1
                            
                    else:
                        if projectile.knockback_direction_x is not None:
                            direction_sign = projectile.knockback_direction_x
                            
                        else:
                            direction_sign = 1 if projectile.vel_x >= 0 else -1

                    push_force = projectile.push_force / max(entity.get("weight", 1), 0.1)
                    entities.apply_knockback(entity, direction_sign, push_force)

                projectile.hit_ids.add(entity_id)

                if not projectile.piercing:
                    projectile.alive = False
                    return

        else:
            player = self.game.player
            player_id = id(player)
            
            if player_id not in projectile.hit_ids and rect.colliderect(player.hitbox):
                if projectile.is_melee and projectile.melee_direction is not None:
                    direction_sign = projectile.melee_direction
                    
                elif projectile.knockback_direction_x is not None:
                    direction_sign = projectile.knockback_direction_x
                    
                else:
                    direction_sign = 1 if projectile.vel_x >= 0 else -1

                if projectile.push_force:
                    player.vel_x = direction_sign * projectile.push_force

                player.take_damage(projectile.damage)
                projectile.hit_ids.add(player_id)

                if not projectile.piercing:
                    projectile.alive = False

    def update(self):
        if self.swimmable_dirty:
            self.refresh_swimmable_cache()

        game = self.game
        
        camera = game.camera
        camera_x = camera.x
        camera_y = camera.y
        
        screen_width = game.screen_width
        screen_height = game.screen_height
        vigorous = game.game_context.vigorous_optimizations

        update_bounds = self._make_update_bounds(camera_x, camera_y, screen_width, screen_height)
        screen_rect = pg.Rect(camera_x, camera_y, screen_width, screen_height)

        projectiles = self.projectiles
        projectile_index = 0

        while projectile_index < len(projectiles):
            projectile = projectiles[projectile_index]

            if not projectile.alive:
                self.release(projectile, projectile_index)
                continue

            rect = self.get_rect(projectile)

            if projectile.follow is not None:
                projectile.x, projectile.y = projectile.follow()
                rect = self.get_rect(projectile)

            elif projectile.embedded:
                if projectile.lifetime <= 0:
                    self.release(projectile, projectile_index)
                    continue

            else:
                if self.in_fluid(projectile, rect):
                    drag = projectile.fluid_drag_mult
                    projectile.vel_x *= drag
                    projectile.vel_y *= drag

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
                if vigorous:
                    if self.is_offscreen(projectile, screen_rect) and not self.should_update(projectile, update_bounds):
                        self.release(projectile, projectile_index)
                        continue
                    
                else:
                    if not self.should_update(projectile, update_bounds):
                        self.release(projectile, projectile_index)
                        continue

                if self.hits_wall(rect):
                    if projectile.embed_on_wall:
                        step_x = projectile.vel_x * 0.25
                        step_y = projectile.vel_y * 0.25
                        for _ in range(4):
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

            if not projectile.alive:
                self.release(projectile, projectile_index)
                continue

            projectile_index += 1

        self.render()

    def render(self):
        game = self.game
        
        debugging = game.debugging
        screen = game.screen
        
        camera_x = game.camera.x
        camera_y = game.camera.y
        scaled_cache = self.scaled_cache

        half_w = game.screen_width // 2
        half_h = game.screen_height // 2
        render_bounds = pg.Rect(
            camera_x - half_w,
            camera_y - half_h,
            game.screen_width + half_w * 2,
            game.screen_height + half_h * 2,
        )

        for projectile in self.projectiles:
            if not projectile.alive:
                continue

            rect = projectile.rect

            if debugging:
                debug_color = (255, 80, 80) if projectile.owner == "player" else (255, 140, 0)
                fill_surface = pg.Surface((max(1, rect.width), max(1, rect.height)), pg.SRCALPHA)
                fill_surface.fill((*debug_color, 120))
                screen.blit(fill_surface, (rect.x - camera_x, rect.y - camera_y))
                
                pg.draw.rect(screen, debug_color, (rect.x - camera_x, rect.y - camera_y, rect.width, rect.height), 2)
                pg.draw.circle(screen, debug_color, (int(rect.centerx - camera_x), int(rect.centery - camera_y)), 4)

            if not self.should_render(projectile, render_bounds):
                continue

            image = projectile.image
            if image is None:
                continue

            scale = projectile.scale
            cache_key = (id(image), scale)
            if cache_key in scaled_cache:
                image = scaled_cache[cache_key]
                
            elif scale != 1.0:
                new_w = int(image.get_width() * scale)
                new_h = int(image.get_height() * scale)
                image = pg.transform.scale(image, (new_w, new_h))
                self.cache_scaled_image(cache_key, image)

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
                            image = pg.transform.rotate(pg.transform.flip(image, True, False), -rotation)
                            
                        else:
                            image = pg.transform.rotate(image, -rotation)
                            
                        projectile.cached_image = image
                        projectile.cached_rotation = rotation
                        projectile.cached_flip = should_flip

                    hitbox_cx = rect.centerx - camera_x
                    hitbox_cy = rect.centery - camera_y
                    rotated_rect = image.get_rect(center=(hitbox_cx, hitbox_cy))
                    
                    rotated_rect.x += projectile.image_offset_x
                    rotated_rect.y += projectile.image_offset_y
                    screen.blit(image, rotated_rect)

                    if debugging:
                        pg.draw.circle(screen, (255, 0, 0), (int(hitbox_cx), int(hitbox_cy)), 4)
                        pg.draw.circle(screen, (0, 255, 0), (int(rotated_rect.centerx), int(rotated_rect.centery)), 3)
                        debug_color = (255, 80, 80) if projectile.owner == "player" else (255, 140, 0)
                        pg.draw.rect(screen, debug_color, (rect.x - camera_x, rect.y - camera_y, rect.width, rect.height), 2)

                    continue

                else:
                    if should_flip:
                        image = pg.transform.flip(image, True, False)
                        
            else:
                if should_flip:
                    image = pg.transform.flip(image, True, False)

            hitbox_cx = rect.centerx - camera_x
            hitbox_cy = rect.centery - camera_y
            
            image_rect = image.get_rect(center=(hitbox_cx, hitbox_cy))
            image_rect.x += projectile.image_offset_x
            image_rect.y += projectile.image_offset_y
            
            screen.blit(image, image_rect)

            if debugging:
                pg.draw.circle(screen, (255, 0, 0), (int(hitbox_cx), int(hitbox_cy)), 4)
                pg.draw.circle(screen, (0, 255, 0), (int(image_rect.centerx), int(image_rect.centery)), 3)

            if debugging and projectile.rotate_to_velocity and not projectile.embedded:
                cx = rect.centerx - camera_x
                cy = rect.centery - camera_y
                
                angle_rad = math.radians(projectile.rotation)
                if projectile.vel_x < 0:
                    angle_rad = -angle_rad
                    
                end_x = cx + math.cos(angle_rad) * 20
                end_y = cy + math.sin(angle_rad) * 20
                pg.draw.line(screen, (255, 255, 0), (cx, cy), (end_x, end_y), 2)
                pg.draw.circle(screen, (255, 255, 0), (int(cx), int(cy)), 3)