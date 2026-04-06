import pygame as pg
import random


class ProjectileSystem:
    def __init__(self, game):
        self.game = game
        
        self.projectiles = []

    def spawn(self, **kwargs):
        projectile = {
            "x":          kwargs["x"],
            "y":          kwargs["y"],
            "width":      kwargs.get("width", 10),
            "height":     kwargs.get("height", 10),
            "vel_x":      kwargs.get("vel_x", 0),
            "vel_y":      kwargs.get("vel_y", 0),
            "lifetime":   kwargs.get("lifetime", 30),
            "damage":     kwargs.get("damage", 0),
            "push_force": kwargs.get("push_force", 0),
            "gravity":    kwargs.get("gravity", 0),
            "image":      kwargs.get("image", None),
            "scale":      kwargs.get("scale", 1.0),
            "piercing":   kwargs.get("piercing", False),
            "owner":      kwargs.get("owner", "player"),
            "follow":     kwargs.get("follow", None),
            "hit_ids":    set(),
            "alive":      True,
        }
        self.projectiles.append(projectile)
        return projectile

    def get_rect(self, projectile):
        width = projectile["width"] * projectile["scale"]
        height = projectile["height"] * projectile["scale"]
        return pg.Rect(
            projectile["x"] - width / 2,
            projectile["y"] - height / 2,
            width,
            height,
        )

    def hits_wall(self, rect):
        for tile_hitbox, tile_id in self.game.map.get_nearby_tiles(rect, padding=2):
            tile_attrs = self.game.map.tile_attributes.get(tile_id, {})
            if not tile_attrs.get("swimmable", False) and rect.colliderect(tile_hitbox):
                return True
            
        return False

    def check_entity_hits(self, projectile, rect):
        if projectile["owner"] == "player":
            for entity in self.game.entities.entities:
                if entity["entity_type"] not in {"enemy", "npc", "actor"}:
                    continue

                entity_id = id(entity)
                if entity_id in projectile["hit_ids"]:
                    continue

                hitbox_width = entity.get("hitbox_width", entity["width"])
                hitbox_height = entity.get("hitbox_height", entity["height"])
                offset_x = entity.get("hitbox_offset_x", 0)
                offset_y = entity.get("hitbox_offset_y", 0)
                entity_rect = pg.Rect(
                    entity["x"] - hitbox_width / 2 + offset_x,
                    entity["y"] - hitbox_height / 2 + offset_y,
                    hitbox_width,
                    hitbox_height,
                )

                if not rect.colliderect(entity_rect):
                    continue

                if entity["entity_type"] in {"enemy", "npc"} and entity["health"] > 0:
                    entity["health"] -= projectile["damage"]
                    entity["damage_effect"] = 1
                    
                    self.game.player.shake_camera(intensity=3.2, duration=25)
                    self.game.entities.spawn_hit_particles(entity)

                    for sound in self.game.entities.sounds["hit"]:
                        sound["sound"].stop()
                        
                    random.choice(self.game.entities.sounds["hit"])["sound"].play()

                if entity.get("abilities") and "pushable" in entity["abilities"]:
                    if self.game.player.direction == "right":
                        direction = pg.Vector2(1, -0.2)
                        
                    else:
                        direction = pg.Vector2(-1, -0.2)
                    
                    direction = direction.normalize()
                    
                    push_force = projectile.get("push_force", 20) / max(entity.get("weight", 1), 0.1)
                    
                    entity["vel_x"] = direction.x * push_force
                    entity["vel_y"] = direction.y * push_force
                    
                    entity["knockback_timer"] = 10
                    
                    if entity["entity_type"] == "enemy":
                        if entity["x"] > self.game.player.x:
                            entity["force_facing"] = "left"
                            
                        else:
                            entity["force_facing"] = "right"

                projectile["hit_ids"].add(entity_id)

                if not projectile["piercing"]:
                    projectile["alive"] = False
                    break

        else:
            player_id = id(self.game.player)
            if player_id not in projectile["hit_ids"] and rect.colliderect(self.game.player.hitbox):
                self.game.player.take_damage(projectile["damage"])
                projectile["hit_ids"].add(player_id)
                
                if not projectile["piercing"]:
                    projectile["alive"] = False

    def update(self):
        for projectile in self.projectiles:
            if not projectile["alive"]:
                continue

            if projectile["follow"] is not None:
                new_x, new_y = projectile["follow"]()
                projectile["x"] = new_x
                projectile["y"] = new_y
                
            else:
                projectile["vel_y"] += projectile["gravity"]
                projectile["x"] += projectile["vel_x"]
                projectile["y"] += projectile["vel_y"]

            projectile["lifetime"] -= 1

            if projectile["lifetime"] <= 0:
                projectile["alive"] = False
                continue

            rect = self.get_rect(projectile)

            if projectile["follow"] is None and self.hits_wall(rect):
                projectile["alive"] = False
                continue

            self.check_entity_hits(projectile, rect)

        self.projectiles = [projectile for projectile in self.projectiles if projectile["alive"]]
        self.render()

    def render(self):
        cam_x = self.game.player.cam_x
        cam_y = self.game.player.cam_y

        for projectile in self.projectiles:
            if not projectile["alive"]:
                continue

            rect = self.get_rect(projectile)
            screen_x = rect.x - cam_x
            screen_y = rect.y - cam_y

            if projectile["image"] is not None:
                image = projectile["image"]
                if projectile["scale"] != 1.0:
                    new_width = int(image.get_width() * projectile["scale"])
                    new_height = int(image.get_height() * projectile["scale"])
                    image = pg.transform.scale(image, (new_width, new_height))
                    
                self.game.screen.blit(image, (screen_x, screen_y))
            
            if self.game.debugging:
                pg.draw.rect(self.game.screen, (255, 80, 80), (screen_x, screen_y, rect.width, rect.height))
