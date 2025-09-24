import pygame as pg
import json
import random
import math
import os

class Entities:
    def __init__(self, game):
        self.game = game
        
        self.show_indicators = True
        self.sounds = {
            "hit": [
                {"sound": pg.mixer.Sound("assets/sounds/entity/21_orc_damage_1.wav"), "volume": 2},
                {"sound": pg.mixer.Sound("assets/sounds/entity/21_orc_damage_2.wav"), "volume": 2},
                {"sound": pg.mixer.Sound("assets/sounds/entity/21_orc_damage_3.wav"), "volume": 2}
            ]
        }
        
        random.seed(self.game.environment.seed)
        
        self.load_settings()

    def load_entity_info(self):
        with open('assets/settings/entities.json', 'r') as f:
            self.entity_info = json.load(f)

    def load_tilesheet(self, path, tile_width, tile_height):
        self.tilesheet = None
        self.item_sprites.clear()

        if not path or not os.path.exists(path):
            print(f"Tilesheet not found: {path}")
            return

        self.tilesheet = pg.image.load(path).convert_alpha()
        sheet_width, sheet_height = self.tilesheet.get_size()

        for row in range(sheet_height // tile_height):
            for col in range(sheet_width // tile_width):
                rect = pg.Rect(col * tile_width, row * tile_height, tile_width, tile_height)
                sprite = self.tilesheet.subsurface(rect).copy()
                key = (row, col)
                self.item_sprites[key] = sprite

    def load_settings(self):
        self.x = 0
        self.y = 0
        
        self.width = 0
        self.height = 0
        self.weight = 0
        
        self.health = 0
        
        self.vel_x = 0
        self.vel_y = 0
        
        self.tilesheet = None
        self.scale = self.game.environment.scale 
        
        self.entities = []
        self.entity_info = {}
        self.item_sprites = {}
        
        self.load_entity_info()

    def reset(self):
        self.entities.clear()

    def item(self, item_name):
        if item_name in self.entity_info["items"]:
            return self.entity_info["items"][item_name]
        return None

    def enemy(self, enemy_name):
        if enemy_name in self.entity_info["enemies"]:
            return self.entity_info["enemies"][enemy_name]
        return None

    def npc(self, npc_name):
        if npc_name in self.entity_info["npcs"]:
            return self.entity_info["npcs"][npc_name]
        return None

    def actor(self, actor_name):
        if actor_name in self.entity_info["actors"]:
            return self.entity_info["actors"][actor_name]
        return None
    
    def create_entity(self, entity_type, name, x, y):
        template_func = {
            "item": self.item,
            "enemy": self.enemy,
            "npc": self.npc,
            "actor": self.actor
        }.get(entity_type)
        
        if not template_func:
            raise ValueError(f"Invalid entity type: {entity_type}")
            
        template = template_func(name)
        if not template:
            raise ValueError(f"{entity_type} '{name}' not found in entity definitions")
        
        if template.get("tile_sheet"):
            self.load_tilesheet(template["tile_sheet"][0], template["tile_sheet"][1], template["tile_sheet"][2])
        
        index_key = tuple(template.get("index")) if isinstance(template.get("index"), list) else template.get("index")
        image = self.item_sprites.get(index_key, self.game.environment.missing_texture.copy())
        
        entity = {
            "entity_type": entity_type,
            "type": template.get("type"),
            "name": name,
            "x": x,
            "y": y,
            "width": template.get("width", 32),
            "height": template.get("height", 32),
            "hitbox_width": template.get("hitbox_width", template.get("width", image.get_width() if image else 32)),
            "hitbox_height": template.get("hitbox_height", template.get("height", image.get_height() if image else 32)),
            "hitbox_offset_x": template.get("hitbox_offset_x", 0),
            "hitbox_offset_y": template.get("hitbox_offset_y", 0),
            "weight": template.get("weight", 1),
            "image": image,
            "vel_x": 0,
            "vel_y": 0,
            "on_ground": False,
            "push_force": template.get("push_force", 20),
            "value": template.get("value", 0),
            "health": template.get("health", 100 if entity_type in ("npc", "enemy", "actor") else 0),
            "max_health": template.get("health", 100 if entity_type in ("npc", "enemy", "actor") else 0),
            "states": template.get("states", {}),
            "current_state": "idle",
            "animation_frame": 0,
            "animation_timer": 0,
            "animation_speed": template.get("animation_speed", 0.2),
            "flip_x": False,
            "flip_y": False
        }

        if entity["states"]:
            self.setup_entity_animations(entity)
            
        if entity_type == "item":
            entity.update({"quantity": template.get("quantity", 1)})
            
        elif entity_type in ("npc", "enemy"):
            entity.update({
                "behavior": template.get("behavior", "idle"),
                "move_speed": template.get("move_speed", 1),
                "jump_force": template.get("jump_force", 10),
                "aggro_range": template.get("aggro_range", 0),
                "attack_damage": template.get("attack_damage", 10),
                "ai_timer": 0,
                "ai_direction": 0,
                "damage_effect": 0
            })
            
            if entity_type == "enemy":
                entity.update({
                    "abilities": template.get("entity_abilities"),
                    "attack_timer": 0
                })
                
        elif entity_type == "actor":
            entity.update({
                "abilities": template.get("entity_abilities")
            })

        if "message" in template:
            entity["message"] = template["message"]

        self.entities.append(entity)
        
        return entity

    def setup_entity_animations(self, entity):
        entity["animation_frames"] = {}
        
        for state, state_data in entity["states"].items():
            frames = []
            start_row = state_data.get("start_row", 0)
            start_col = state_data.get("start_col", 0)
            frame_count = state_data.get("frames", 1)
            
            animation_speed = state_data.get("speed", entity.get("animation_speed", 0.2))
            
            for i in range(frame_count):
                row = start_row + (i // state_data.get("cols", frame_count))
                col = start_col + (i % state_data.get("cols", frame_count))
                key = (row, col)
                if key in self.item_sprites:
                    frames.append(self.item_sprites[key])
                    
                else:
                    print(f"Warning: Missing animation frame {key} for state {state}")
                    frames.append(entity["image"])
            
            entity["animation_frames"][state] = {
                "frames": frames,
                "speed": animation_speed
            }

    def update_entity(self, entity):
        for sound_group in self.sounds.values():
            if isinstance(sound_group, list):
                for sound_dict in sound_group:
                    sound = sound_dict["sound"]
                    volume = sound_dict["volume"]
                    sound.set_volume(self.game.environment.volume / 10 * volume)
                        
            elif isinstance(sound_group, dict):
                for sound_key, sound_dict in sound_group.items():
                    sound = sound_dict["sound"]
                    volume = sound_dict["volume"]
                    sound.set_volume(self.game.environment.volume / 10 * volume)

        if entity["entity_type"] in {"npc", "enemy"}:
            if entity["health"] <= 0:
                self.death_particles(entity)
                self.entities.remove(entity)
    
    def update_animation(self, entity):
        cam_x, cam_y = self.game.player.cam_x, self.game.player.cam_y
        screen_width, screen_height = self.game.screen_width, self.game.screen_height

        sprite_x = entity["x"] - cam_x - entity["width"] // 2
        sprite_y = entity["y"] - cam_y - entity["height"] // 2

        if sprite_x + entity["width"] >= 0 and sprite_x <= screen_width and sprite_y + entity["height"] >= 0 and sprite_y <= screen_height:
            if not entity.get("states"):
                return
                
            new_state = entity["current_state"]
            
            if entity["entity_type"] in {"npc", "enemy"}:
                if abs(entity["vel_x"]) > 0.1:
                    new_state = "walk"
                    
                elif entity.get("damage_effect", 0) > 0:
                    new_state = "hurt"
                    
                else:
                    new_state = "idle"
                
            if new_state != entity["current_state"] and new_state in entity["states"]:
                entity["current_state"] = new_state
                entity["animation_frame"] = 0
                entity["animation_timer"] = 0

            animation_data = entity.get("animation_frames", {}).get(entity["current_state"])
            if animation_data:
                frames = animation_data["frames"]
                speed = animation_data["speed"]

                entity["animation_timer"] += 1

                if "frame_duration" not in animation_data:
                    animation_data["frame_duration"] = (1 / speed) + random.uniform(0, 0.2)

                if entity["animation_timer"] >= animation_data["frame_duration"]:
                    entity["animation_timer"] = 0
                    entity["animation_frame"] = (entity["animation_frame"] + 1) % len(frames)

                entity["image"] = frames[entity["animation_frame"]]

                if entity["entity_type"] in ("npc", "enemy"):
                    ai_dir = entity.get("ai_direction", 0)
                    entity["flip_x"] = ai_dir < 0

    def spawn_hit_particles(self, entity, amount=5):
        for particles in range(amount):
            vel_x = random.uniform(-1.5, 1.5)  
            vel_y = random.uniform(-6.0, -6.5) 
            radius = random.randint(2, 4)

            #image_path = "assets/sprites/particles/blood.png"
            #particle_img = pg.image.load(image_path).convert_alpha()

            self.game.particles.generate(
                pos=(entity["x"], entity["y"]),
                velocity=(vel_x, vel_y),
                gravity=0.7,             
                friction=0.4,
                floor_behavior="bounce",   
                color=(255, 50, 50),
                radius=radius,
                lifespan=100,
                fade=True,
                image_size=(radius * 3, radius * 3),
            )
            
    def death_particles(self, entity, amount=13):
        for particles in range(amount):
            vel_x = random.uniform(-1.5, 1.5)
            vel_y = random.uniform(-2.0, -3.5)
            
            radius = random.randint(3, 6)
            
            image_path = f"assets/sprites/particles/smoke{random.choice([1, 2])}.png"
            smoke_img = pg.image.load(image_path).convert_alpha()
            
            self.game.particles.generate(
                pos=(entity["x"] + random.uniform(-2, 2), entity["y"] + random.uniform(-5, 5)),
                velocity=(vel_x, vel_y),
                gravity=0,
                radius=radius,
                lifespan=random.randint(40, 80),
                fade=True,
                image=smoke_img,
                image_size=(radius * 4, radius * 4),
            )

    def update_collision(self, entity):
        hitbox_width = entity.get("hitbox_width", entity["width"])
        hitbox_heigth = entity.get("hitbox_height", entity["height"])
        
        offset_x = entity.get("hitbox_offset_x", 0)
        offset_y = entity.get("hitbox_offset_y", 0)
        
        entity_hitbox = pg.Rect(
            entity["x"] - hitbox_width / 2 + offset_x,
            entity["y"] - hitbox_heigth / 2 + offset_y,
            hitbox_width,
            hitbox_heigth
        )
        
        ground_check = pg.Rect(
            entity_hitbox.left + 2,
            entity_hitbox.bottom - 2,
            entity_hitbox.width - 4,
            4
        )
        
        nearby_tiles = self.game.map.get_nearby_tiles(entity_hitbox, padding=5)
        entity["on_ground"] = False
        
        for tile_hitbox, tile_id in nearby_tiles:
            tile_attrs = self.game.map.tile_attributes.get(tile_id, {})
            swimmable = tile_attrs.get("swimmable", False)
            #damage = tile_attrs.get("damage", 0)
            
            if entity_hitbox.colliderect(tile_hitbox) or ground_check.colliderect(tile_hitbox):
                #if damage and entity["entity_type"] != "actor":
                    #entity["health"] -= damage
                    #entity["damage_effect"] = 1
                
                if swimmable:
                    continue
                    
                overlap_x = min(entity_hitbox.right - tile_hitbox.left, tile_hitbox.right - entity_hitbox.left)
                overlap_y = min(entity_hitbox.bottom - tile_hitbox.top, tile_hitbox.bottom - entity_hitbox.top)
                
                if overlap_x < overlap_y:
                    if entity_hitbox.centerx > tile_hitbox.centerx:
                        entity["x"] = tile_hitbox.right + hitbox_width / 2 - offset_x
                        
                    else:
                        entity["x"] = tile_hitbox.left - hitbox_width / 2 - offset_x
                        
                else:
                    if entity_hitbox.centery < tile_hitbox.centery:
                        entity["y"] = tile_hitbox.top - hitbox_heigth / 2 - offset_y
                        entity["vel_y"] = 0
                        entity["on_ground"] = True
                        
                    else:
                        entity["y"] = tile_hitbox.bottom + hitbox_heigth / 2 - offset_y
                        entity["vel_y"] = 0
        
        if entity["entity_type"] in {"enemy", "npc", "actor"}:
            if entity_hitbox.colliderect(self.game.player.attack_hitbox):
                for attack_id in self.game.player.active_melee_attack_ids:
                    if entity.get("last_hit_id") != attack_id:
                        if entity["entity_type"] in {"enemy", "npc"} and entity["health"] > 0:
                            entity["health"] -= self.game.player.weapon_info[self.game.player.equipped_weapon]["damage"]
                            entity["damage_effect"] = 1
                            self.spawn_hit_particles(entity)
                        
                        if entity.get("abilities") and "pushable" in entity["abilities"]:
                            direction = pg.Vector2(
                                entity["x"] - self.game.player.x,
                                entity["y"] - self.game.player.y
                            ).normalize()
                            
                            push_force = entity.get("push_force", 20) / max(entity["weight"], 0.1)
                            
                            entity["vel_x"] += direction.x * push_force
                            entity["vel_y"] += direction.y * push_force
                        
                        if entity["entity_type"] in {"enemy", "npc"}:
                            for sound in self.sounds["hit"]:
                                sound["sound"].stop()
                                
                            random.choice(self.sounds["hit"])["sound"].play()
                        
                        entity["last_hit_id"] = attack_id
            
            for attack_id in self.game.player.active_projectile_attack_ids:
                if (entity.get("last_hit_id") != attack_id and 
                    entity_hitbox.collidepoint(attack_id["x"], attack_id["y"])):
                    if entity["entity_type"] in {"enemy", "npc"} and entity["health"] > 0:
                        entity["health"] -= 10
                        entity["damage_effect"] = 1
                    
                    if entity.get("abilities") and "pushable" in entity["abilities"]:
                        direction = pg.Vector2(
                            entity["x"] - attack_id["x"],
                            entity["y"] - attack_id["y"]
                        ).normalize()
                        
                        push_force = attack_id.get("force", 20) / max(entity["weight"], 0.1)
                        
                        entity["vel_x"] += direction.x * push_force
                        entity["vel_y"] += direction.y * push_force
                    
                    if entity["entity_type"] in {"enemy", "npc"}:
                        for sound in self.sounds["hit"]:
                            sound["sound"].stop()
                            
                        random.choice(self.sounds["hit"])["sound"].play()
                    
                    entity["last_hit_id"] = attack_id

    def apply_gravity(self, entity):
        if not self.is_on_ground(entity):
            step = round(max(1, entity["vel_y"]))
            for _ in range(step):
                entity["y"] += 1
                if self.is_on_ground(entity): 
                    entity["vel_y"] = 0
                    break
            
            entity["vel_y"] += self.game.environment.gravity * entity["weight"]
            
            if entity["vel_y"] > self.game.environment.max_fall_speed:
                entity["vel_y"] = self.game.environment.max_fall_speed 

    def apply_horizontal_movement(self, entity):
        entity["x"] += entity["vel_x"]

        if entity.get("on_ground", False): 
            friction = 0.8 # temporary friction value

            if abs(entity["vel_x"]) > 0.1:
                entity["vel_x"] *= friction 
                
                if abs(entity["vel_x"]) < 0.1:  
                    entity["vel_x"] = 0

    def is_on_ground(self, entity):
        hitbox_w = entity.get("hitbox_width", entity["width"])
        hitbox_h = entity.get("hitbox_height", entity["height"])
        offset_x = entity.get("hitbox_offset_x", 0)
        offset_y = entity.get("hitbox_offset_y", 0)
        
        ground_check = pg.Rect(
            entity["x"] - hitbox_w/2 + offset_x + 2,
            entity["y"] + hitbox_h/2 + offset_y - 2,
            hitbox_w - 4,
            4
        )
        
        nearby_tiles = self.game.map.get_nearby_tiles(ground_check, padding=5)
        
        for tile_hitbox, tile_id in nearby_tiles:
            if ground_check.colliderect(tile_hitbox):
                tile_attrs = self.game.map.tile_attributes.get(tile_id, {})
                if not tile_attrs.get("swimmable", False):
                    entity["y"] = tile_hitbox.top - hitbox_h/2 - offset_y
                    entity["vel_y"] = 0
                    entity["on_ground"] = True
                    return True
                
                else:
                    entity["vel_y"] *= 0.8
                    entity["on_ground"] = True
        
        entity["on_ground"] = False
        return False
        
    def health_bar(self, entity):
        if entity["health"] <= 0 or entity["health"] == entity["max_health"]:
            return

        if not hasattr(self, "health_font"):
            self.health_font = pg.font.Font(self.game.environment.fonts["fantasy"], 13)

        health_percentage = entity["health"] / entity["max_health"]
        bar_width, bar_height = entity["width"], 5
        cam_x, cam_y = self.game.player.cam_x, self.game.player.cam_y

        bar_x = int(entity["x"] - cam_x - bar_width // 2)
        bar_y = int(entity["y"] - cam_y - entity["height"] // 2 - 10)

        if "last_health" not in entity or entity["last_health"] != entity["health"] or "health_text" not in entity:
            entity["last_health"] = entity["health"]
            entity["health_text"] = self.health_font.render(f"{int(entity['health'])}/{int(entity['max_health'])}", True, (255, 255, 255))

        text_surface = entity["health_text"]
        text_rect = text_surface.get_rect(center=(bar_x + bar_width // 2, bar_y - 6))
        self.game.screen.blit(text_surface, text_rect)

        pg.draw.rect(self.game.screen, (255, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        pg.draw.rect(self.game.screen, (0, 255, 0), (bar_x, bar_y, bar_width * health_percentage, bar_height))

    def entity_indicators(self, entity):
        if not self.show_indicators:
            return
        
        if not hasattr(self, "arrow_surface"):
            self.arrow_surface = pg.Surface((20, 20), pg.SRCALPHA)
            pg.draw.polygon(self.arrow_surface, (255, 0, 0), [(7, 14), (0, 0), (14, 0)])

            self.arrow_scales = {}
            for s in [0.9, 1.0, 1.1]:
                width, height = self.arrow_surface.get_size()
                self.arrow_scales[round(s, 1)] = pg.transform.scale(self.arrow_surface, (int(width * s), int(height * s)))

        if not hasattr(self, "bubble_surface"):
            bubble_width, bubble_height = 18, 14
            self.bubble_surface = pg.Surface((bubble_width, bubble_height + 6), pg.SRCALPHA)

            pg.draw.ellipse(self.bubble_surface, (255, 255, 255), (0, 0, bubble_width, bubble_height))
            pg.draw.ellipse(self.bubble_surface, (200, 200, 200), (0, 0, bubble_width, bubble_height), 1)

            tail_points = [(bubble_width // 2 - 3, bubble_height - 1), (bubble_width // 2 + 3, bubble_height - 1), (bubble_width // 2, bubble_height + 5)]
            pg.draw.polygon(self.bubble_surface, (255, 255, 255), tail_points)
            pg.draw.polygon(self.bubble_surface, (200, 200, 200), tail_points, 1)

            for x in (6, 9, 12):
                pg.draw.circle(self.bubble_surface, (100, 100, 100), (x, 6), 1)

            self.bubble_scales = {}
            for s in [0.9, 1.0, 1.1]:
                width, height = self.bubble_surface.get_size()
                self.bubble_scales[round(s, 1)] = pg.transform.scale(self.bubble_surface, (int(width * s), int(height * s)))

        dx = entity["x"] - self.game.player.x
        dy = entity["y"] - self.game.player.y
        distance_sq = dx * dx + dy * dy

        indicator_radius = self.game.player.interact_radius.width * 2
        indicator_radius_sq = indicator_radius * indicator_radius

        if distance_sq <= indicator_radius_sq:
            distance = math.sqrt(distance_sq)
            cam_x, cam_y = self.game.player.cam_x, self.game.player.cam_y
            screen_x = entity["x"] - cam_x
            screen_y = entity["y"] - cam_y - entity["height"] - 20

            max_opacity, min_opacity = 255, 50
            fade_start = indicator_radius * 0.6

            if distance <= fade_start:
                opacity = max_opacity
                
            elif distance <= indicator_radius:
                fade_range = indicator_radius - fade_start
                fade_progress = (distance - fade_start) / fade_range
                opacity = max_opacity - fade_progress * (max_opacity - min_opacity)
                
            else:
                opacity = min_opacity

            time = pg.time.get_ticks() / 250
            scale = round(1.0 + 0.1 * math.sin(time), 1)

            if entity["entity_type"] == "enemy":
                arrow = self.arrow_scales.get(scale, self.arrow_surface)
                arrow.set_alpha(int(opacity))
                self.game.screen.blit(arrow, (screen_x - arrow.get_width() // 2, screen_y - arrow.get_height() // 2))
                
            elif entity["entity_type"] == "npc":
                bubble = self.bubble_scales.get(scale, self.bubble_surface)
                bubble.set_alpha(int(opacity))
                self.game.screen.blit(bubble, (screen_x - bubble.get_width() // 2, screen_y - bubble.get_height() - 6))

    def render(self, entity):
        cam_x, cam_y = self.game.player.cam_x, self.game.player.cam_y
        screen_width, screen_height = self.game.screen_width, self.game.screen_height

        if entity["image"]:
            sprite_x = entity["x"] - cam_x - entity["width"] // 2
            sprite_y = entity["y"] - cam_y - entity["height"] // 2

            if sprite_x + entity["width"] >= 0 and sprite_x <= screen_width and sprite_y + entity["height"] >= 0 and sprite_y <= screen_height:
                if entity.get("damage_effect", 0) > 0:
                    tinted_image = entity["image"].copy()
                    tinted_image.fill((255, 0, 0), special_flags=pg.BLEND_ADD)

                    entity["damage_effect"] -= 0.05
                    if entity["damage_effect"] < 0:
                        entity["damage_effect"] = 0
                        
                else:
                    tinted_image = entity["image"]

                scaled_image = pg.transform.scale(tinted_image, (entity["width"], entity["height"]))

                if entity["entity_type"] in {"npc"}:
                    self.health_bar(entity)
                    if entity["x"] > self.game.player.x:
                        scaled_image = pg.transform.flip(scaled_image, True, False)
                
                elif entity["entity_type"] in {"enemy"}:
                    self.health_bar(entity)
                    if "last_dir" not in entity:
                        entity["last_dir"] = 1
                    
                    if entity["vel_x"] > 0:
                        entity["last_dir"] = 1
                        
                    elif entity["vel_x"] < 0:
                        entity["last_dir"] = -1
                    
                    if entity["last_dir"] == -1:
                        scaled_image = pg.transform.flip(scaled_image, True, False)

                self.game.screen.blit(scaled_image, (sprite_x, sprite_y))

    def mouse_interact(self, entity):
        mouse_x, mouse_y = pg.mouse.get_pos()
        mouse_world_x = mouse_x + self.game.player.cam_x
        mouse_world_y = mouse_y + self.game.player.cam_y
        
        hitbox_w = entity.get("hitbox_width", entity["width"])
        hitbox_h = entity.get("hitbox_height", entity["height"])
        
        entity_hitbox = pg.Rect(
            entity["x"] - hitbox_w / 2, 
            entity["y"] - hitbox_h / 2, 
            hitbox_w, 
            hitbox_h
        )
        
        hovering = entity_hitbox.collidepoint(mouse_world_x, mouse_world_y)
        mouse_pressed = pg.mouse.get_pressed()[0]
        
        if not hasattr(self, "dragged_entity"):
            if hovering and mouse_pressed:
                self.dragged_entity = entity
                self.drag_offset_x = entity["x"] - mouse_world_x
                self.drag_offset_y = entity["y"] - mouse_world_y

        if hasattr(self, "dragged_entity") and self.dragged_entity == entity:
            if mouse_pressed and entity in self.entities:
                entity["on_ground"] = False
                entity["vel_x"] = 0
                entity["vel_y"] = 0
                entity["x"] = mouse_world_x + self.drag_offset_x
                entity["y"] = mouse_world_y + self.drag_offset_y
                
            else:
                del self.dragged_entity 
    
    def show_hitboxes(self, entity):
        if not self.game.debugging:
            return
        
        cam_x, cam_y = self.game.player.cam_x, self.game.player.cam_y
        hitbox_w = entity.get("hitbox_width", entity["width"])
        hitbox_h = entity.get("hitbox_height", entity["height"])
        offset_x = entity.get("hitbox_offset_x", 0)
        offset_y = entity.get("hitbox_offset_y", 0)
        
        hitbox_rect = pg.Rect(
            entity["x"] - hitbox_w/2 + offset_x - cam_x,
            entity["y"] - hitbox_h/2 + offset_y - cam_y,
            hitbox_w,
            hitbox_h
        )
        
        if entity["entity_type"] == "enemy":
            color = (255, 0, 0)
            
        elif entity["entity_type"] == "npc":
            color = (0, 255, 0)
            
        elif entity["entity_type"] == "item":
            color = (0, 0, 255)
            
        elif entity["entity_type"] == "actor":
            color = (255, 255, 0)
            
        else:
            color = (255, 255, 255)
        
        fill_surface = pg.Surface((hitbox_w, hitbox_h), pg.SRCALPHA)
        fill_surface.fill((*color, 50))
        self.game.screen.blit(fill_surface, (hitbox_rect.x, hitbox_rect.y))
        
        pg.draw.rect(self.game.screen, color, hitbox_rect, 2)
        
        center_x = entity["x"] + offset_x - cam_x
        center_y = entity["y"] + offset_y - cam_y
        
        pg.draw.circle(self.game.screen, color, (int(center_x), int(center_y)), 3)
        
        if offset_x != 0 or offset_y != 0:
            original_center = (entity["x"] - cam_x, entity["y"] - cam_y)
            offset_center = (center_x, center_y)
            pg.draw.line(self.game.screen, (255, 255, 0), original_center, offset_center, 2)
        
        if entity["entity_type"] in ["enemy"]:
            aggro_range = entity.get("aggro_range", 300)
            
            detection_surface = pg.Surface((aggro_range*2, aggro_range*2), pg.SRCALPHA)
            pg.draw.circle(
                detection_surface, 
                (255, 165, 0, 30),
                (aggro_range, aggro_range), 
                aggro_range
            )
            
            self.game.screen.blit(
                detection_surface,
                (entity["x"] - aggro_range - cam_x, entity["y"] - aggro_range - cam_y)
            )
            
            player_center = (self.game.player.x - cam_x, self.game.player.y - cam_y)
            entity_center = (entity["x"] - cam_x, entity["y"] - cam_y)
            distance = math.sqrt((player_center[0]-entity_center[0])**2 + (player_center[1]-entity_center[1])**2)
            
            if distance <= aggro_range:
                pg.draw.line(
                    self.game.screen, 
                    (255, 0, 255),
                    entity_center, 
                    player_center, 
                    2
                )
                            
    def update(self):
        for entity in self.entities[:]:
            if entity["entity_type"] in ["npc", "enemy"]:
                self.game.ai.update_ai(entity)
            self.update_collision(entity)
            self.apply_gravity(entity)
            self.apply_horizontal_movement(entity)
            self.update_animation(entity)
            self.update_entity(entity)
            self.render(entity)
            self.mouse_interact(entity)
            self.show_hitboxes(entity)
            self.entity_indicators(entity)