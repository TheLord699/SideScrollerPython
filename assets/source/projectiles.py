import pygame as pg
import random


class ProjectileSystem:
    def __init__(self, game):
        self.game = game
        
        self.projectiles = []

    def spawn(self, **kwargs):
        projectile = {
            "x": kwargs["x"],
            "y": kwargs["y"],
            "width": kwargs.get("width", 10),
            "height": kwargs.get("height", 10),
            "vel_x": kwargs.get("vel_x", 0),
            "vel_y": kwargs.get("vel_y", 0),
            "lifetime": kwargs.get("lifetime", 30),
            "damage": kwargs.get("damage", 0),
            "push_force": kwargs.get("push_force", 0),
            "gravity": kwargs.get("gravity", 0),
            "image": kwargs.get("image", None),
            "image_offset_x": kwargs.get("image_offset_x", 0),
            "image_offset_y": kwargs.get("image_offset_y", 0),
            "scale": kwargs.get("scale", 1.0),
            "piercing": kwargs.get("piercing", False),
            "owner": kwargs.get("owner", "player"),
            "follow": kwargs.get("follow", None),
            "embed_on_wall": kwargs.get("embed_on_wall", False),
            "fluid_drag": kwargs.get("fluid_drag", False),
            "fluid_drag_mult": kwargs.get("fluid_drag_mult", 0.85),
            "embedded": False,
            "hit_ids": set(),
            "alive": True,
        }
        self.projectiles.append(projectile)
        return projectile

    def get_rect(self, projectile):
        w = projectile["width"]  * projectile["scale"]
        h = projectile["height"] * projectile["scale"]
        
        return pg.Rect(projectile["x"] - w / 2, projectile["y"] - h / 2, w, h)

    def visual_size(self, projectile):
        img = projectile.get("image")
        sc = projectile["scale"]
        
        if img:
            iw, ih = img.get_size()
            return max(projectile["width"] * sc, iw * sc), max(projectile["height"] * sc, ih * sc)
        
        return projectile["width"] * sc, projectile["height"] * sc

    def hits_wall(self, rect):
        for tile_hitbox, tile_id in self.game.map.get_nearby_tiles(rect, padding=2):
            attrs = self.game.map.tile_attributes.get(tile_id, {})
            if not attrs.get("swimmable", False) and rect.colliderect(tile_hitbox):
                return True
            
        return False

    def in_fluid(self, projectile, rect):
        if not projectile["fluid_drag"]:
            return False
        
        for tile_hitbox, tile_id in self.game.map.get_nearby_tiles(rect, padding=2):
            attrs = self.game.map.tile_attributes.get(tile_id, {})
            if attrs.get("swimmable", False) and rect.colliderect(tile_hitbox):
                return True
            
        return False

    def is_offscreen(self, projectile):
        cam_x = self.game.player.cam_x
        cam_y = self.game.player.cam_y
        
        sw = self.game.screen_width
        sh = self.game.screen_height
        
        vis_w, vis_h = self.visual_size(projectile)
        off_x = projectile.get("image_offset_x", 0)
        off_y = projectile.get("image_offset_y", 0)
        
        vis_rect    = pg.Rect(projectile["x"] - vis_w/2 + off_x, projectile["y"] - vis_h/2 + off_y, vis_w, vis_h)
        screen_rect = pg.Rect(cam_x, cam_y, sw, sh)
        
        return not vis_rect.colliderect(screen_rect)

    def check_entity_hits(self, projectile, rect):
        if projectile["owner"] == "player":
            for entity in self.game.entities.entities:
                if entity["entity_type"] not in {"enemy", "npc", "actor"}:
                    continue

                entity_id = id(entity)
                if entity_id in projectile["hit_ids"]:
                    continue

                hw = entity.get("hitbox_width", entity["width"])
                hh = entity.get("hitbox_height", entity["height"])
                
                ox = entity.get("hitbox_offset_x", 0)
                oy = entity.get("hitbox_offset_y", 0)
                e_rect = pg.Rect(entity["x"] - hw/2 + ox, entity["y"] - hh/2 + oy, hw, hh)

                if not rect.colliderect(e_rect):
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
                    is_melee = projectile.get("follow") is not None
                    if is_melee:
                        dir_sign = 1 if entity["x"] > self.game.player.x else -1
                        
                    else:
                        dir_sign = 1 if projectile["vel_x"] >= 0 else -1

                    push = projectile.get("push_force", 20) / max(entity.get("weight", 1), 0.1)
                    entity["vel_x"] = dir_sign * push
                    entity["vel_y"] = -abs(push) * 0.2
                    
                    entity["knockback_timer"] = 10
                    entity["force_facing"] = "left" if dir_sign > 0 else "right"

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

            elif projectile["embedded"]:
                projectile["lifetime"] -= 1
                if projectile["lifetime"] <= 0:
                    projectile["alive"] = False
                    
                continue

            else:
                rect = self.get_rect(projectile)

                if self.in_fluid(projectile, rect):
                    d = projectile["fluid_drag_mult"]
                    projectile["vel_x"] *= d
                    projectile["vel_y"] *= d

                projectile["vel_y"] += projectile["gravity"]
                projectile["x"] += projectile["vel_x"]
                projectile["y"] += projectile["vel_y"]

            projectile["lifetime"] -= 1
            if projectile["lifetime"] <= 0:
                projectile["alive"] = False
                continue

            rect = self.get_rect(projectile)

            if projectile["follow"] is None and not projectile["embedded"]:
                if self.is_offscreen(projectile):
                    projectile["alive"] = False
                    continue

                if self.hits_wall(rect):
                    if projectile["embed_on_wall"]:
                        projectile["embedded"] = True
                        projectile["vel_x"]    = 0
                        projectile["vel_y"]    = 0
                        
                    else:
                        projectile["alive"] = False
                        
                    continue

            self.check_entity_hits(projectile, rect)

        self.projectiles = [p for p in self.projectiles if p["alive"]]
        self.render()

    def render(self):
        cam_x = self.game.player.cam_x
        cam_y = self.game.player.cam_y
        
        sw = self.game.screen_width
        sh = self.game.screen_height
        
        screen_rect = pg.Rect(cam_x, cam_y, sw, sh)

        for projectile in self.projectiles:
            if not projectile["alive"]:
                continue

            vis_w, vis_h = self.visual_size(projectile)
            off_x = projectile.get("image_offset_x", 0)
            off_y = projectile.get("image_offset_y", 0)
            vis_rect = pg.Rect(projectile["x"] - vis_w/2 + off_x, projectile["y"] - vis_h/2 + off_y, vis_w, vis_h)
            if not vis_rect.colliderect(screen_rect):
                continue

            rect = self.get_rect(projectile)
            screen_x = rect.x - cam_x + off_x
            screen_y = rect.y - cam_y + off_y

            if projectile["image"] is not None:
                image = projectile["image"]
                if projectile["scale"] != 1.0:
                    nw = int(image.get_width()  * projectile["scale"])
                    nh = int(image.get_height() * projectile["scale"])
                    
                    image = pg.transform.scale(image, (nw, nh))
                    
                self.game.screen.blit(image, (screen_x, screen_y))

            if self.game.debugging:
                pg.draw.rect(self.game.screen, (255, 80, 80), (rect.x - cam_x, rect.y - cam_y, rect.width, rect.height))