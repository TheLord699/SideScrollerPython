import pygame as pg
import numpy as np
import random
import json
import math
import os

from helper_methods import load_json

class Player:
    def __init__(self, game):
        self.game = game
           
        self.load_settings()
        
    def load_settings(self):
        self.x = 0 * self.game.environment.scale  / 3
        self.y = 900 * self.game.environment.scale  / 3
        self.vel_x = 0
        self.vel_y = 0
        self.speed = 5 # 5
        self.dash_speed = 100 # 100
        self.weight = 1 # 1
        self.jump_strength = 10 # 10
        self.friction = 0

        self.cam_x = self.x - self.game.screen_width / 2
        self.cam_y = self.y - self.game.screen_height / 1.5
        self.camera_smoothing_factor = 0.1
        self.free_cam = False

        self.scale_factor = self.game.environment.scale 
        self.hitbox_width = 5 * self.scale_factor
        self.hitbox_height = 15 * self.scale_factor
        self.attack_hitbox_width = 17 * self.scale_factor
        self.attack_hitbox_height = 15 * self.scale_factor
        self.hitbox = pg.Rect(self.x, self.y, self.hitbox_width, self.hitbox_height)
        self.interact_radius = pg.Rect(self.x, self.y, self.hitbox_width, self.hitbox_height)
        self.attack_hitbox = pg.Rect(0, 0, self.attack_hitbox_width, self.attack_hitbox_height)
        self.blocked_horizontally = False

        self.attack_timeout = 30
        self.attack_sequence = 1
        self.attack_timer = 0
        
        self.max_inventory_slots = 15
        self.inventory = {}
        self.rendered_inventory_ui_elements = []
        self.inventory_x_offset = self.game.screen_width / 2.5
        self.inventory_y_offset = self.game.screen_height / 2.5
        self.items_per_row = 5
        self.item_spacing = 40
        self.selected_slot = None
        self.inventory_changed = False
        self.inventory_cooldown = 0
        
        # will remove melee attacks soon and replace with "projectile" based attack, the melee attacks will still visually be melee but will be internally handled as projectiles
        self.active_projectile_ids = []
        self.active_melee_ids = []
        self.current_attack_id = 0
            
        self.max_health = 3
        self.current_health = self.max_health
        self.health_per_row = 10
        self.health_spacing = 35
        self.invinsibility_duration = 900 # 600
        self.last_damage_time = -self.invinsibility_duration * 2 
        
        self.pickup_tags = []
        self.max_tags = 3
            
        self.last_step_time = 0 
        self.step_interval = 300
        self.actual_horizontal_movement = False
        
        self.in_dialogue = False
        self.dialogue_index = 0
        self.dialogue_with = None
            
        self.current_state = "idle"
        self.direction = "right"
        self.current_frame = 0
        self.animation_timer = 0
        self.weapon_info = load_json(os.path.join("assets", "settings", "weapon_data.json"))
        self.equipped_weapon = "basic_sword"
        # will load settings from json instead of hard coding dictionaries
        self.state_frames = {
            "idle": {"frames": 6, "speed": 0.15},
            "walking": {"frames": 8, "speed": 0.2},
            "attacking1": {"frames": 6}, # Gonna need to change when weapon system fully implemented
            "attacking2": {"frames": 6},
            "jump": {"frames": 3, "speed": 0.15},
            "hurt": {"frames": 4, "speed": 0.10}, # 0.10
            "death": {"frames": 4, "speed": 0.15},
        }
        self.frames = {state: [] for state in self.state_frames}
        
        self.sounds = {
            "jump": [
                {"sound": pg.mixer.Sound("assets/sounds/player/movement/12_human_jump_2.wav"), "volume": 2.0}
            ],
            "attack": [
                {"sound": pg.mixer.Sound("assets/sounds/player/attack/swing1.wav"), "volume": 2.0},
                {"sound": pg.mixer.Sound("assets/sounds/player/attack/swing2.wav"), "volume": 2.0}
            ],
            "land": [
                {"sound": pg.mixer.Sound("assets/sounds/player/movement/13_human_jump_land_1.wav"), "volume": 2.0},
                {"sound": pg.mixer.Sound("assets/sounds/player/movement/13_human_jump_land_2.wav"), "volume": 2.0}
            ],
            "inventory": {
                "open": {"sound": pg.mixer.Sound("assets/sounds/player/interact/01_chest_open_1.wav"), "volume": 2.0},
                "close": {"sound": pg.mixer.Sound("assets/sounds/player/interact/02_chest_close_1.wav"), "volume": 2.0}
            },
            "pickup": [
                {"sound": pg.mixer.Sound("assets/sounds/player/interact/04_sack_open_1.wav"), "volume": 2.0},
                {"sound": pg.mixer.Sound("assets/sounds/player/interact/04_sack_open_2.wav"), "volume": 2.0},
                {"sound": pg.mixer.Sound("assets/sounds/player/interact/04_sack_open_3.wav"), "volume": 2.0}
            ],
            "walking": [
                {"sound": pg.mixer.Sound("assets/sounds/player/movement/16_human_walk_stone_1.wav"), "volume": 2.0},
                {"sound": pg.mixer.Sound("assets/sounds/player/movement/16_human_walk_stone_2.wav"), "volume": 2.0},
                {"sound": pg.mixer.Sound("assets/sounds/player/movement/16_human_walk_stone_3.wav"), "volume": 2.0}
            ],
            "talking": [
                {"sound": pg.mixer.Sound("assets/sounds/entity/npc/talking_0.wav"), "volume": 2.0},
                {"sound": pg.mixer.Sound("assets/sounds/entity/npc/talking_2.wav"), "volume": 2.0},
                {"sound": pg.mixer.Sound("assets/sounds/entity/npc/talking_3.wav"), "volume": 2.0}
            ],
            "consume": [
                {"sound": pg.mixer.Sound("assets/sounds/player/interact/consume.wav"), "volume": 2.0}
            ],
            "hit": [
                {"sound": pg.mixer.Sound("assets/sounds/entity/21_orc_damage_1.wav"), "volume": 2.0},
                {"sound": pg.mixer.Sound("assets/sounds/entity/21_orc_damage_2.wav"), "volume": 2.0},
                {"sound": pg.mixer.Sound("assets/sounds/entity/21_orc_damage_3.wav"), "volume": 2.0}
            ],
            "dash": [
                {"sound": pg.mixer.Sound("assets/sounds/player/movement/15_human_dash_1.wav"), "volume": 2.0},
                {"sound": pg.mixer.Sound("assets/sounds/player/movement/15_human_dash_2.wav"), "volume": 2.0}
            ]
        }
        
        self.attacking = False
        self.on_ground = False
        self.in_inventory = False
        self.just_closed_dialogue = False
        
        random.seed(self.game.environment.seed)
        
        self.item_info = load_json(os.path.join("assets", "settings", "entities.json"))
        
        self.load_frames()

    def load_frames(self):
        self.frames = {}
        self.flipped_frames = {}
        
        self.sheet_width = 100
        self.sheet_height = 100
        
        for state, settings in self.state_frames.items():
            self.frames[state] = []
            self.flipped_frames[state] = []
            
            sheet_path = f"assets/sprites/player/{state}_animation.png"
            try:
                sheet = pg.image.load(sheet_path).convert_alpha()
                
            except:
                print(f"Failed to load sprite sheet: {sheet_path}")
                continue
                
            scaled_width = self.sheet_width * self.scale_factor
            scaled_height = self.sheet_height * self.scale_factor
            
            for frame_index in range(settings["frames"]):
                frame_rect = pg.Rect(
                    frame_index * self.sheet_width,
                    0,
                    self.sheet_width,
                    self.sheet_height
                )
                
                frame_image = pg.Surface(frame_rect.size, pg.SRCALPHA).convert_alpha()
                frame_image.blit(sheet, (0, 0), frame_rect)
                frame_image = pg.transform.scale(frame_image, (scaled_width, scaled_height))
                
                flipped_image = pg.transform.flip(frame_image, True, False)
                
                self.frames[state].append(frame_image)
                self.flipped_frames[state].append(flipped_image)

    def update_state(self):     
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

        self.current_health = math.floor(self.current_health * 2) / 2  
        self.current_health = min(self.current_health, self.max_health)

        self.x += self.vel_x
        self.y += self.vel_y
        
        self.attack_timer += 1
        
        if self.current_health < 0:
            self.current_health = 0
        
        if self.vel_y >= self.game.environment.max_fall_speed:
            self.vel_y = self.game.environment.max_fall_speed

        if self.attack_timer > self.attack_timeout:
            self.attack_sequence = 1
        
        if self.current_state in {"death"} or getattr(self, "sliding", False):   
            if self.friction <= 0 and self.on_ground:
                self.friction = 0.3
                         
            self.vel_x -= self.friction * (1 if self.vel_x > 0 else -1 if self.vel_x < 0 else 0)
                    
            if abs(self.vel_x) < 0.5:
                self.vel_x = 0
            
        if self.actual_horizontal_movement and self.on_ground and not self.current_state in {"death"}:
            if self.game.environment.current_time - self.last_step_time > self.step_interval:
                walking_sound = random.choice(self.sounds["walking"])
                walking_sound["sound"].play()
                self.last_step_time = self.game.environment.current_time
                
                flip_offset = 14 if self.direction == "right" else 0

                for amount in range(5): # 5
                    base_vel_x = random.uniform(0, 0.5)
                    if self.direction == "right":
                        vel_x = -base_vel_x
                        
                    elif self.direction == "left":
                        vel_x = base_vel_x
                        
                    else:
                        vel_x = random.uniform(-0.5, 0.5)

                    vel_y = random.uniform(-0.5, -0.1)
                    radius = random.randint(2, 4)
                    image_path = f"assets/sprites/particles/smoke{random.choice([1, 2])}.png"
                    smoke_img = pg.image.load(image_path).convert_alpha()

                    self.game.particles.generate(
                        pos=(self.x + self.hitbox_width / 2 - flip_offset + random.uniform(-10, 10), self.y + self.hitbox_height / 2 + random.uniform(0, 5)),
                        velocity=(vel_x, vel_y),
                        color=(255, 255, 255),
                        radius=radius,
                        lifespan=30,
                        fade=True,
                        image=smoke_img,
                        image_size=(radius*2, radius*2)
                    )

    def take_damage(self, damage):
        if self.current_state == "death":
            return
        
        if self.game.environment.current_time - self.last_damage_time >= self.invinsibility_duration:
            self.current_health -= damage
            self.last_damage_time = self.game.environment.current_time
            
            if self.current_health < 0.5:
                self.death()
                hurt_sound = random.choice(self.sounds["hit"])
                hurt_sound["sound"].play()
                
            else:
                self.current_state = "hurt"
                self.current_frame = 0
                self.animation_timer = 0
                self.attacking = False
                self.attack_sequence = (self.attack_sequence % 2) + 1
                self.active_melee_ids.clear()
                hurt_sound = random.choice(self.sounds["hit"])
                hurt_sound["sound"].play()
                    
    def death(self):
        self.current_state = "death"
        self.current_frame = 0
        self.attacking = False
        self.in_inventory = False
        self.in_dialogue = False
        self.dialogue_with = None
        self.game.ui.remove_ui_element("dialogue_boarder")
        self.game.ui.remove_ui_element("dialogue_name")
        self.game.environment.menu = "death"
    
    def render_health(self):
        previous_health = getattr(self, "previous_health", self.current_health)

        if previous_health != self.current_health:
            for health in range(self.max_health):
                row = health // self.health_per_row
                col = health % self.health_per_row

                self.game.ui.remove_ui_element(health)

        for heart in range(self.max_health):
            row = heart // self.health_per_row
            col = heart % self.health_per_row

            x_position = self.inventory_x_offset + col * self.health_spacing - 300
            y_position = self.inventory_y_offset + row * self.health_spacing - 220
            
            if heart + 1 <= self.current_health:
                image_path = [0, 0]
                
            elif heart + 1 - self.current_health == 0.5:
                image_path = [0, 1]
                
            else:
                image_path = [0, 2]

            self.game.ui.create_ui(
                sprite_sheet_path="hearts", image_id=image_path,
                sprite_width=32, sprite_height=32, 
                x=x_position, y=y_position, 
                centered=True, width=60, height=60, 
                alpha=True, 
                element_id=heart,
                render_order=1
            )
        
        self.previous_health = self.current_health

    def add_item_to_inventory(self, item):
        item_name = item["name"]
        item_type = item["type"]
        item_value = item["value"]
        item_quantity = item["quantity"]

        for index, inventory_item in self.inventory.items():
            if (inventory_item["name"] == item_name and inventory_item["type"] == item_type and inventory_item["value"] == item_value):
                inventory_item["quantity"] += item_quantity
                return

        for index in range(self.max_inventory_slots):
            if index not in self.inventory:
                self.inventory[index] = item
                return
            
    def render_item_mouse(self):
        if not self.in_inventory or self.selected_slot is None or self.selected_slot not in self.inventory:
            if hasattr(self, "mouse_item") and self.mouse_item:
                self.game.ui.remove_ui_element(self.mouse_item)
                
            return
        
        item = self.inventory[self.selected_slot]
        item_name = item["name"]
        item_index = self.item_info["items"][item_name]["index"]

        item_element_id = f"item:{item_name}"
        if item_element_id in self.rendered_inventory_ui_elements:
            self.game.ui.remove_ui_element(item_element_id)
            self.rendered_inventory_ui_elements.remove(item_element_id)

        if hasattr(self, "mouse_item") and self.mouse_item:
            self.game.ui.remove_ui_element(self.mouse_item)

        mouse_x, mouse_y = pg.mouse.get_pos()
        self.mouse_item = f"mouse_{item_name}"
        
        self.game.ui.create_ui(
            sprite_sheet_path="item_sheet", image_id=item_index,
            x=mouse_x, y=mouse_y,
            sprite_width=16, sprite_height=16,
            centered=True, width=30, height=30,
            alpha=True,
            element_id=self.mouse_item,
            render_order=1
        )
        
    def add_pickup_tag(self, item_name):
        if len(self.pickup_tags) >= self.max_tags:
            self.remove_oldest_tag()
        
        element_id = f"pickup_tag_{len(self.pickup_tags)}_{pg.time.get_ticks()}"
        text_id = f"pickup_text_{len(self.pickup_tags)}_{pg.time.get_ticks()}"
        
        screen_width = self.game.screen.get_width()
        x_pos = screen_width - 100
        y_pos = 20
        
        self.game.ui.create_ui(
            sprite_sheet_path="item_sheet",
            image_id=self.item_info["items"][item_name]["index"],
            x=x_pos,
            y=y_pos,
            sprite_width=16,
            sprite_height=16,
            width=30,
            height=30,
            element_id=element_id,
            render_order=2
        )
        
        self.game.ui.create_ui(
            x=x_pos + 50,
            y=y_pos + 15,
            font_size=10,
            font=self.game.environment.fonts["fantasy"],
            element_id=text_id,
            render_order=2,
            label=item_name
        )
        
        self.pickup_tags.insert(0, {
            "name": item_name,
            "element_id": element_id,
            "text_id": text_id,
            "creation_time": self.game.environment.current_time
        })
        
        self.update_tag_positions()

    def update_pickup_tags(self):
        if not self.pickup_tags:
            return
        
        current_time = self.game.environment.current_time
        expired_tags = [tag for tag in self.pickup_tags if current_time - tag["creation_time"] >= 3000]
        
        for tag in expired_tags:
            self.pickup_tags.remove(tag)
            self.game.ui.remove_ui_element(tag["element_id"])
            self.game.ui.remove_ui_element(tag["text_id"])
        
        if expired_tags:
            self.update_tag_positions()

    def remove_oldest_tag(self):
        if self.pickup_tags:
            oldest = self.pickup_tags.pop()
            self.game.ui.remove_ui_element(oldest["element_id"])
            self.game.ui.remove_ui_element(oldest["text_id"])

    def update_tag_positions(self):
        screen_width = self.game.screen.get_width()
        x_pos = screen_width - 100
        start_y = 20
        
        for tag in self.pickup_tags:
            self.game.ui.remove_ui_element(tag["element_id"])
            self.game.ui.remove_ui_element(tag["text_id"])
        
        for index, tag in enumerate(self.pickup_tags):
            y_pos = start_y + index * 35
            
            self.game.ui.create_ui(
                sprite_sheet_path="item_sheet",
                image_id=self.item_info["items"][tag["name"]]["index"],
                x=x_pos,
                y=y_pos,
                sprite_width=16,
                sprite_height=16,
                width=30,
                height=30,
                element_id=tag["element_id"],
                render_order=2
            )
            
            self.game.ui.create_ui(
                x=x_pos + 50,
                y=y_pos + 15,
                font_size=10,
                font=self.game.environment.fonts["fantasy"],
                element_id=tag["text_id"],
                render_order=2,
                label=tag["name"]
            )
                    
    def render_item_info(self, id): # doesnt update amount in real time
        if hasattr(self, "last_rendered_item") and self.last_rendered_item:
            self.game.ui.remove_ui_element(self.last_rendered_item)
            self.game.ui.remove_ui_element("item_info")
            
        if self.selected_slot is not None:
            self.game.ui.create_ui(
                sprite_sheet_path="item_sheet", image_id=self.item_info["items"][self.inventory[id]["name"]]["index"],
                x=self.game.screen_width / 5, y=self.game.screen_height / 2.2, sprite_width=16, sprite_height=16, 
                centered=True, width=60, height=60,
                alpha=True,
                element_id=self.inventory[id]["name"],
                render_order=0
            )
            
            self.game.ui.create_ui(
                x=self.game.screen_width / 6, y=self.game.screen_height / 2,
                centered=True, width=60, height=60,
                element_id="item_info",
                render_order=1, font=self.game.environment.fonts["fantasy"],
                label=f"{self.inventory[id]["name"]} x{self.inventory[id]["quantity"]} Value:{self.inventory[id]["value"]}"
            )
            self.rendered_inventory_ui_elements.append(self.inventory[id]["name"])
            self.rendered_inventory_ui_elements.append("item_info")
        
            self.last_rendered_item = self.inventory[id]["name"]
        
    def refresh_inventory(self):
        if self.inventory_changed:
            for element_id in self.rendered_inventory_ui_elements:
                self.game.ui.remove_ui_element(element_id)
                
            self.rendered_inventory_ui_elements.clear()
            self.inventory_changed = False
        
        for slot in range(self.max_inventory_slots):
            row = slot // self.items_per_row
            col = slot % self.items_per_row

            x_position = self.inventory_x_offset + col * self.item_spacing
            y_position = self.inventory_y_offset + row * self.item_spacing

            slot_element_id = f"slot:{slot}" 
            
            self.game.ui.create_ui(
                sprite_sheet_path="ui_sheet", image_id=[34, 3],
                x=x_position, y=y_position, sprite_width=32, sprite_height=32, 
                centered=True, width=35, height=35,
                alpha=True, is_button=True,
                element_id=slot_element_id,
                scale_multiplier=1,
                callback=lambda id=slot: (self.on_inventory_click(id), self.render_item_info(id) if id in self.inventory else None),
                render_order=1
                )

            self.rendered_inventory_ui_elements.append(slot_element_id)
    
    def render_inventory(self):
        if self.in_inventory:
            self.refresh_inventory()

            for item_slot, item in self.inventory.items():
                row = item_slot // self.items_per_row
                col = item_slot % self.items_per_row

                x_position = self.inventory_x_offset + col * self.item_spacing
                y_position = self.inventory_y_offset + row * self.item_spacing 

                item_element_id = f"item:{item["name"]}"
                self.game.ui.create_ui(
                    image_id=self.item_info["items"][item["name"]]["index"], 
                    sprite_sheet_path="item_sheet",
                    sprite_width=16, sprite_height=16, 
                    x=x_position, y=y_position, 
                    centered=True, width=20, height=20, 
                    alpha=True, is_button=True, 
                    scale_multiplier=1, 
                    element_id=item_element_id,
                    is_hold=False,
                    render_order=1
                )

                self.rendered_inventory_ui_elements.append(item_element_id)
                
        else:
            for element_id in self.rendered_inventory_ui_elements:
                self.game.ui.remove_ui_element(element_id)
                
            self.rendered_inventory_ui_elements.clear()
            self.selected_slot = None
        
            if hasattr(self, "last_rendered_item") and self.last_rendered_item:
                self.last_rendered_item = None

    def on_inventory_click(self, slot):
        if self.selected_slot is None and slot in self.inventory and (self.game.environment.current_time - self.inventory_cooldown >= 150):
            self.selected_slot = slot
            self.render_item_info(slot)
            
        elif self.selected_slot == slot and (self.game.environment.current_time - self.inventory_cooldown >= 150):
            self.selected_slot = None
            self.render_inventory() 
            self.inventory_cooldown = self.game.environment.current_time  
            
            drop_sound = random.choice(self.sounds["pickup"])
            drop_sound["sound"].play()
            
        elif self.selected_slot is not None and slot != self.selected_slot and (self.game.environment.current_time - self.inventory_cooldown >= 150):
            if slot in self.inventory:
                self.inventory[self.selected_slot], self.inventory[slot] = self.inventory[slot], self.inventory[self.selected_slot]
                
            else:
                self.inventory[slot] = self.inventory.pop(self.selected_slot)
            
            drop_sound = random.choice(self.sounds["pickup"])
            drop_sound["sound"].play()

            self.refresh_inventory()
            self.selected_slot = None  
            self.inventory_changed = True
            self.inventory_cooldown = self.game.environment.current_time
    
    # probably shit way of handling hitboxes/updates
    def hitbox_set(self):
        self.hitbox = pg.Rect(
            self.x - self.hitbox_width / 2,
            self.y - self.hitbox_height / 2,
            self.hitbox_width,
            self.hitbox_height
        )
    
    def interact_hitbox(self):
        self.interact_radius = pg.Rect(
            self.x - self.hitbox_width / 2 - 50,  
            self.y - self.hitbox_height / 2 - 50, 
            self.hitbox_width + 100,  
            self.hitbox_height + 100  
        )
        
    def render_dialogue(self):
        if self.in_dialogue and self.dialogue_with:
            messages = self.dialogue_with.get("message", [])

            if self.dialogue_index >= len(messages):
                self.in_dialogue = False
                self.dialogue_with = None
                self.just_closed_dialogue = True

                self.game.ui.remove_ui_element("dialogue_boarder")
                self.game.ui.remove_ui_element("dialogue_name")

                for sound in self.sounds["talking"]:
                    sound["sound"].stop()
                    
            else:
                message_text = messages[self.dialogue_index]

                self.game.ui.create_ui(
                    sprite_sheet_path="ui_sheet", 
                    image_id=[33, 0],
                    x=self.game.screen_width / 2, 
                    y=self.game.screen_height / 1.15,
                    sprite_width=95, 
                    sprite_height=32,
                    centered=True, 
                    width=300, 
                    height=150,
                    alpha=True, 
                    is_button=False,
                    element_id="dialogue_boarder",
                    scale_multiplier=1,
                    label=message_text,
                    font_size=20,
                    font=self.game.environment.fonts["fantasy"],
                    render_order=0,
                    is_dialogue=True,
                    typing_speed=25
                )

                self.game.ui.create_ui(
                    sprite_sheet_path="ui_sheet",
                    x=self.game.screen_width / 5, 
                    y=self.game.screen_height / 1.5,
                    sprite_width=95, 
                    sprite_height=32,
                    centered=True, 
                    width=300, 
                    height=150,
                    alpha=True, 
                    is_button=False,
                    element_id="dialogue_name",
                    font_size=15,
                    scale_multiplier=1,
                    label=self.dialogue_with.get("name", "???"),
                    font=self.game.environment.fonts["fantasy"],
                    render_order=1
                )
                self.dialogue_just_opened = False

    def interact_with_entity(self):
        for entity in self.game.entities.entities:
            if entity["entity_type"] == "item":
                entity_hitbox = pg.Rect(entity["x"] - entity["width"] / 2, entity["y"] - entity["height"] / 2, entity["width"], entity["height"])

                if self.interact_radius.colliderect(entity_hitbox):
                    if len(self.inventory) < self.max_inventory_slots:
                        self.add_item_to_inventory({**entity})
                        self.add_pickup_tag(entity["name"])
                        
                        self.game.entities.entities.remove(entity)
                        
                        for sound in self.sounds["pickup"]:
                            sound["sound"].stop()
                        
                        pickup_sound = random.choice(self.sounds["pickup"])
                        pickup_sound["sound"].play()
            
            if entity["entity_type"] == "npc":
                if not self.on_ground:
                    return
                
                entity_hitbox = pg.Rect(entity["x"] - entity["width"] / 2, entity["y"] - entity["height"] / 2, entity["width"], entity["height"])
                
                if self.interact_radius.colliderect(entity_hitbox):
                    if entity["message"]:
                        if self.just_closed_dialogue:
                            return
                        
                        self.dialogue_with = entity
                        self.dialogue_index = 0
                        self.dialogue_just_opened = True
                        self.in_dialogue = True

                        if entity["x"] < self.x:
                            self.direction = "left"
                        
                        else: 
                            self.direction = "right"

                        for sound in self.sounds["talking"]:
                            sound["sound"].stop()

                        talk_sound = random.choice(self.sounds["talking"])
                        talk_sound["sound"].play()
    
    def drop_item(self):
        if self.selected_slot is None or self.selected_slot not in self.inventory: 
            return
            
        item_to_drop = self.inventory[self.selected_slot]
        
        if item_to_drop["quantity"] > 1:
            item_to_drop["quantity"] -= 1
        
        else:
            del self.inventory[self.selected_slot]
        
        self.game.entities.create_entity("item", item_to_drop["name"], self.x, self.y)
        
        self.refresh_inventory()
        self.selected_slot = None
        self.inventory_changed = True
        
        drop_sound = random.choice(self.sounds["pickup"])
        drop_sound["sound"].play()
    
    def consume_item(self):
        if self.selected_slot is None or self.selected_slot not in self.inventory or self.inventory[self.selected_slot]["type"] != "consumable":
            return
    
        item_to_consume = self.inventory[self.selected_slot]
        self.current_health += item_to_consume["health"]
        
        if item_to_consume["quantity"] > 1:
            item_to_consume["quantity"] -= 1
        
        else:
            del self.inventory[self.selected_slot]
        
        self.refresh_inventory()
        self.selected_slot = None
        self.inventory_changed = True
        
        consume_sound = random.choice(self.sounds["consume"])
        consume_sound["sound"].play()

    def jump(self):
        self.vel_y = -self.jump_strength
        jump_sound = random.choice(self.sounds["jump"])
        jump_sound["sound"].play()
        
        flip_offset = 11 if self.direction == "right" else 0
        
        for amount in range(7): # 7
            vel_x = random.uniform(-1.0, 1.0)  
            vel_y = random.uniform(-1.0, -0.3)  

            radius = random.randint(2, 4)
            image_path = f"assets/sprites/particles/smoke{random.choice([1, 2])}.png"
            smoke_img = pg.image.load(image_path).convert_alpha()

            pos_x = self.x + self.hitbox_width / 2 + random.uniform(-15, 15) - flip_offset
            pos_y = self.y + self.hitbox_height / 2 + random.uniform(0, 7)

            self.game.particles.generate(
                pos=(pos_x, pos_y),
                velocity=(vel_x, vel_y),
                color=(255, 255, 255),
                radius=radius,
                lifespan=60,
                fade=True,
                image=smoke_img,
                image_size=(radius * 2, radius * 2)
            )
            
    def update_collision(self):
        self.hitbox_set()
        
        horizontal_collisions = []
        vertical_collisions = []

        self.blocked_horizontally = False

        nearby_tiles = self.game.map.get_nearby_tiles(self.hitbox)
        
        for tile_hitbox, tile_id in nearby_tiles:
            tile_attributes = self.game.map.tile_attributes.get(tile_id, {})

            swimmable = tile_attributes.get("swimmable", False)
            damage = tile_attributes.get("damage", 0)

            if self.hitbox.colliderect(tile_hitbox):
                overlap_x = min(self.hitbox.right - tile_hitbox.left, tile_hitbox.right - self.hitbox.left)
                overlap_y = min(self.hitbox.bottom - tile_hitbox.top, tile_hitbox.bottom - self.hitbox.top)

                if overlap_x < overlap_y:
                    horizontal_collisions.append((tile_hitbox, overlap_x, swimmable, damage))
                    
                else:
                    vertical_collisions.append((tile_hitbox, overlap_y, swimmable, damage))

        if horizontal_collisions:
            tile_hitbox, overlap_x, swimmable, damage = max(horizontal_collisions, key=lambda t: t[1])
            if not swimmable:
                self.blocked_horizontally = True 
                
                if damage > 0:
                    self.take_damage(damage)
                    
                if self.hitbox.centerx < tile_hitbox.centerx:
                    self.x -= overlap_x
                    
                else:
                    self.x += overlap_x
                    
                self.vel_x = 0
                self.hitbox_set()

        if vertical_collisions:
            tile_hitbox, overlap_y, swimmable, damage = max(vertical_collisions, key=lambda t: t[1])
            if not swimmable:
                if damage > 0:
                    self.take_damage(damage)
                    
                if self.hitbox.centery < tile_hitbox.centery:
                    self.y -= overlap_y
                    
                else:
                    self.y += overlap_y
                    self.vel_y += 1 # will set 0 when I fix head collisions
                    
                self.hitbox_set()

        self.actual_horizontal_movement = not self.blocked_horizontally and self.vel_x != 0
        self.hitbox_set()

    def handle_gravity(self):
        self.on_ground = False
        self.vel_y += self.game.environment.gravity * self.weight
        self.hitbox_set()

        bottom_middle_x = self.hitbox.centerx
        bottom_middle_y = self.hitbox.bottom

        nearby_tiles = self.game.map.get_nearby_tiles(self.hitbox)
        
        for tile_hitbox, tile_id in nearby_tiles:
            if tile_hitbox.collidepoint(bottom_middle_x, bottom_middle_y):
                tile_attributes = self.game.map.tile_attributes.get(tile_id, {})

                swimmable = tile_attributes.get("swimmable", False)
                slippy = tile_attributes.get("slippy", False)
                friction = tile_attributes.get("friction", 0)
                damage = tile_attributes.get("damage", 0)

                if swimmable:
                    self.vel_y *= 0.8  # temp fix for swimming
                    self.on_ground = True
                    continue

                if slippy:
                    self.friction = friction
                    self.sliding = True
                    
                else:
                    self.friction = 0
                    self.sliding = False

                if damage > 0:
                    self.take_damage(damage)

                if self.vel_y >= 1.5:
                    self.y = tile_hitbox.top - self.hitbox.height / 2
                    self.vel_y = 0
                    self.on_ground = True
                    break

    def animate(self):
        previous_state = self.current_state
        
        if self.current_state == "death":
            frame_delay = int(1 / self.state_frames["death"]["speed"])
            self.animation_timer += 1

            if self.current_frame < len(self.frames["death"]) - 1:
                if self.animation_timer >= frame_delay:
                    self.animation_timer = 0
                    self.current_frame += 1
            return

        if self.current_state == "hurt":
            frame_delay = int(1 / self.state_frames["hurt"]["speed"])
            self.animation_timer += 1

            if self.animation_timer >= frame_delay:
                self.animation_timer = 0
                self.current_frame += 1
                
                if self.current_frame >= len(self.frames["hurt"]):
                    self.current_state = "idle"
                    self.current_frame = 0
            return
        
        if self.attacking:
            self.current_state = f"attacking{self.attack_sequence}"
            
        elif self.vel_x != 0:
            self.current_state = "walking"
            
        else:
            self.current_state = "idle"

        if self.current_state != previous_state:
            self.current_frame = 0
            self.animation_timer = 0
        
        self.advance_frame()

    def advance_frame(self):
        if self.current_state.startswith("attacking"):
            if self.equipped_weapon not in self.weapon_info: # this is dumb(maybe should make current weapon speed part of current state speed?)
                self.attacking = False
                return
                
            weapon_data = self.weapon_info[self.equipped_weapon]
            frame_delay = int(1 / weapon_data["speed"])
            
        else:
            frame_delay = int(1 / self.state_frames[self.current_state]["speed"])
            
        self.animation_timer += 1

        if self.animation_timer < frame_delay:
            return

        self.animation_timer = 0
        self.current_frame = (self.current_frame + 1) % len(self.frames[self.current_state])

        if self.current_state.startswith("attacking") and self.current_frame == len(self.frames[self.current_state]) - 1:
            self.attacking = False
            
            max_sequence = weapon_data.get("sequence", 1)
            self.attack_sequence = (self.attack_sequence % max_sequence) + 1
            
            self.active_melee_ids.clear()

    def handle_controls(self):
        keys = pg.key.get_pressed()
        mouse_buttons = pg.mouse.get_pressed()
        self.joystick = self.game.environment.joystick

        controller = {}
        if self.joystick:
            controller = {
                "left_x": self.joystick.get_axis(0) if abs(self.joystick.get_axis(0)) > 0.1 else 0,
                "left_y": self.joystick.get_axis(1) if abs(self.joystick.get_axis(1)) > 0.1 else 0,
                "A": self.joystick.get_button(0),
                "B": self.joystick.get_button(1),
                "X": self.joystick.get_button(2),
                "Y": self.joystick.get_button(3),
                "LB": self.joystick.get_button(4),
                "RB": self.joystick.get_button(5),
                "back": self.joystick.get_button(6),
                "start": self.joystick.get_button(7)
            }

            if self.joystick.get_numhats() > 0:
                controller["dpad"] = self.joystick.get_hat(0)
                
            else:
                controller["dpad"] = (0, 0)

        if self.current_state == "death":
            return

        if self.in_inventory:
            self.handle_inventory_controls(keys, controller)
            
        else:
            self.handle_normal_controls(keys, mouse_buttons, controller)

        self.handle_events(controller)

    def handle_inventory_controls(self, keys, controller):
        if not getattr(self, "sliding", False):
            self.vel_x = 0
            
        if keys[pg.K_q] or (self.joystick and controller.get("X")):
            self.drop_item()
        
        if keys[pg.K_e] or (self.joystick and controller.get("A")):
            self.consume_item()

    def handle_normal_controls(self, keys, mouse_buttons, controller):
        if self.in_dialogue:
            self.vel_x = 0
            return

        self.handle_movement(keys, controller)
        self.handle_actions(keys, mouse_buttons, controller)

    def handle_movement(self, keys, controller):
        left_input = keys[pg.K_a] or (self.joystick and controller.get("left_x") < -0.5)
        right_input = keys[pg.K_d] or (self.joystick and controller.get("left_x") > 0.5)
        
        if getattr(self, "sliding", False):
            if left_input and not right_input and not self.blocked_horizontally:
                self.vel_x = -self.speed
                self.direction = "left"
                
            elif right_input and not left_input and not self.blocked_horizontally:
                self.vel_x = self.speed
                self.direction = "right"
                
        else:
            if left_input and right_input:
                self.vel_x = 0
                
            elif left_input and not self.blocked_horizontally:
                self.vel_x = -self.speed
                self.direction = "left"
                
            elif right_input and not self.blocked_horizontally:
                self.vel_x = self.speed
                self.direction = "right"
                
            else:
                self.vel_x = 0

    def handle_actions(self, keys, mouse_buttons, controller):
        jump_input = keys[pg.K_w] or (self.joystick and controller.get("A"))
        if jump_input and self.on_ground:
            self.jump()
        
        interact_input = keys[pg.K_e] or (self.joystick and controller.get("Y"))
        if interact_input:
            self.interact_with_entity()
        
        attack_input = keys[pg.K_SPACE] or (self.joystick and controller.get("B"))
        if attack_input and self.current_state != "hurt":
            self.start_attack()
        
        if mouse_buttons[0] and self.current_state != "hurt":
            # self.shoot_ray((self.x - self.cam_x, self.y - self.cam_y), pg.mouse.get_pos())
            pass
        
        pause_input = keys[pg.K_ESCAPE] or (self.joystick and controller.get("start"))
        if pause_input:
            pass

    def handle_events(self, controller):
        for event in self.game.events:
            match event.type:
                case pg.KEYDOWN | pg.JOYBUTTONDOWN:
                    self.handle_button_down(event, controller)
                    
                case pg.KEYUP | pg.JOYBUTTONUP:
                    self.handle_button_up(event)

    def handle_button_down(self, event, controller):
        button_pressed = event.type == pg.JOYBUTTONDOWN
        button = event.button if button_pressed else None
        
        if self.in_dialogue:
            self.handle_dialogue_input(event, button_pressed, button)
            
        else:
            self.handle_gameplay_input(event, button_pressed, button)

    def handle_dialogue_input(self, event, button_pressed, button):
        if (event.type == pg.KEYDOWN and event.key == pg.K_e) or (button_pressed and button == 3):
            if not self.dialogue_just_opened:
                self.game.ui.remove_ui_element("dialogue_boarder")
                self.dialogue_index += 1

                for sound in self.sounds["talking"]:
                    sound["sound"].stop()

                talk_sound = random.choice(self.sounds["talking"])
                talk_sound["sound"].play()
                
            else:
                self.dialogue_just_opened = False

    def handle_gameplay_input(self, event, button_pressed, button):
        if (event.type == pg.KEYDOWN and event.key == pg.K_i) or (button_pressed and button == 6):
            self.in_inventory = not self.in_inventory
            
            if self.in_inventory:
                self.sounds["inventory"]["open"]["sound"].play()
                
            else:
                self.sounds["inventory"]["close"]["sound"].play()
        
        if (event.type == pg.KEYDOWN and event.key == pg.K_LSHIFT) or (button_pressed and button == 4):
            if not self.in_inventory:
                self.dash()

    def handle_button_up(self, event):
        if ((event.type == pg.KEYUP and event.key == pg.K_e) or (event.type == pg.JOYBUTTONUP and event.button == 3)):
            if self.just_closed_dialogue:
                self.just_closed_dialogue = False
        
    def dash_visuals(self, start_x, distance):
        if distance == 0:
            return

        dash_dir = 1 if self.direction == "right" else -1
        num_ghosts = 4 # 8
        step_size = distance / num_ghosts

        for i in range(num_ghosts):
            ghost_x = start_x + (step_size * i * dash_dir)
            ghost_y = self.y - 5

            current_frame_image = self.frames[self.current_state][self.current_frame]

            if self.direction == "left":
                current_frame_image = pg.transform.flip(current_frame_image, True, False)

            white_image = current_frame_image.copy()

            white_surface = pg.Surface(white_image.get_size(), pg.SRCALPHA)
            white_surface.fill((255, 255, 255, 255))
            white_image.blit(white_surface, (0, 0), special_flags=pg.BLEND_MULT)

            opacity = int(255 * ((i + 1) / num_ghosts))
            white_image.fill((255, 255, 255, opacity), special_flags=pg.BLEND_RGBA_MULT)

            flip_offset = 14 if self.direction == "right" else 0
            #screen_x = ghost_x + self.hitbox_width / 2 - flip_offset - self.cam_x
            #screen_y = ghost_y + self.hitbox_height / 8 - self.cam_y

            lifespan = 15 + (num_ghosts - i - 1) * 2

            self.game.particles.generate(
                pos=(ghost_x + self.hitbox_width / 2 - flip_offset, ghost_y + self.hitbox_height / 8),
                velocity=(0, 0),
                color=(255, 255, 255),
                radius=(self.hitbox_width, self.hitbox_height),
                lifespan=lifespan,
                fade=True,
                image=white_image,
                image_size=white_image.get_size()
            )

    def dash(self):
        current_time = pg.time.get_ticks()
        if hasattr(self, "last_dash_time") and current_time - self.last_dash_time < 500:
            return

        dash_dir = 1 if self.direction == "right" else -1
        dash_distance = self.dash_speed

        steps = 20
        step_size = dash_distance / steps

        start_x = self.x
        final_x = self.x
        blocked = False

        for segment in range(1, steps + 1):
            test_x = self.x + (step_size * segment * dash_dir)

            temp_hitbox = pg.Rect(
                test_x - self.hitbox_width / 2,
                self.y - self.hitbox_height / 2,
                self.hitbox_width,
                self.hitbox_height
            )

            for tile in self.game.map.tile_hitboxes:
                if temp_hitbox.colliderect(tile):
                    blocked = True
                    break

            if blocked:
                break

            final_x = test_x

        distance_traveled = abs(final_x - start_x)

        if distance_traveled > 0:
            self.x = final_x
            self.last_dash_time = current_time

            self.dash_visuals(start_x, distance_traveled)

            dash_sound = random.choice(self.sounds["dash"])
            dash_sound["sound"].play()

    def start_attack(self): # will make all attacks projectile based using projectile func
        if self.attacking or self.equipped_weapon not in self.weapon_info:
            return
            
        self.attacking = True
        self.current_frame = 0
        self.attack_timer = 0

        new_attack_id = self.current_attack_id
        self.active_melee_ids.append(new_attack_id)
        self.current_attack_id += 1

        attack_sound = random.choice(self.sounds["attack"])
        attack_sound["sound"].play()
            
    def update_projectiles(self): # not in use currently
        self.active_projectile_ids = [id for id in self.active_projectile_ids if not self.is_projectile_done(id)]

    def update_attack_hitbox(self):
        if not self.attacking:
            return
        
        if self.direction == "right":
            self.attack_hitbox.centerx = self.hitbox.right + self.attack_hitbox_width // 2
            
        else:
            self.attack_hitbox.centerx = self.hitbox.left - self.attack_hitbox_width // 2
            
        self.attack_hitbox.centery = self.hitbox.centery

    def render(self):
        self.flip_offset = {'left': 1.4, 'right': 0} # weird temp fix
        self.foot_alignment = 3
        
        if (self.current_state not in self.frames or 
            not self.frames[self.current_state] or
            (self.game.environment.current_time - self.last_damage_time < self.invinsibility_duration and 
            not self.current_state == "death" and (pg.time.get_ticks() // 100) % 2 == 0)):
            return

        frame_idx = min(self.current_frame, len(self.frames[self.current_state]) - 1)
        
        if hasattr(self, "flipped_frames"):
            image = (self.flipped_frames[self.current_state][frame_idx] if self.direction == "left" else self.frames[self.current_state][frame_idx])
            
        else:
            image = self.frames[self.current_state][frame_idx]
            if self.direction == "left":
                image = pg.transform.flip(image, True, False)

        img_w, img_h = image.get_size()
        cam_x, cam_y = self.cam_x, self.cam_y
        hb_cx, hb_cy = self.hitbox.centerx, self.hitbox.centery
        
        sprite_x = hb_cx - cam_x - img_w // 2 + self.flip_offset[self.direction]
        sprite_y = hb_cy - cam_y + self.foot_alignment - img_h // 2

        self.game.screen.blit(image, (sprite_x, sprite_y))

    def update_camera(self):
        # can change the target here
        if self.free_cam:
            return
        
        target_cam_x = self.x - self.game.screen_width / 2
        target_cam_y = self.y - self.game.screen_height / 1.5 # 1.5

        self.cam_x += (target_cam_x - self.cam_x) * self.camera_smoothing_factor
        self.cam_y += (target_cam_y - self.cam_y) * self.camera_smoothing_factor
        
        self.cam_x = max(min(self.cam_x, target_cam_x + self.game.screen_width / 4), target_cam_x - self.game.screen_width / 4)
        self.cam_y = max(min(self.cam_y, target_cam_y + self.game.screen_height / 4), target_cam_y - self.game.screen_height / 7)

    def render_hitboxes(self):
        if not self.game.debugging:
            return

        interact_color = (0, 0, 255, 50)
        interact_surface = pg.Surface((self.interact_radius.width, self.interact_radius.height), pg.SRCALPHA)
        interact_surface.fill(interact_color)
        self.game.screen.blit(
            interact_surface,
            (
                self.interact_radius.centerx - self.cam_x - self.interact_radius.width // 2,
                self.interact_radius.centery - self.cam_y - self.interact_radius.height // 2
            )
        )

        if self.attacking:
            hitbox_color = (255, 0, 0, 100)
            hitbox_surface = pg.Surface((self.attack_hitbox_width, self.attack_hitbox_height), pg.SRCALPHA)
            hitbox_surface.fill(hitbox_color)
            self.game.screen.blit(
                hitbox_surface,
                (self.attack_hitbox.x - self.cam_x, self.attack_hitbox.y - self.cam_y)
            )

        hitbox_color = (0, 255, 0, 100)
        hitbox_surface = pg.Surface((self.hitbox_width, self.hitbox_height), pg.SRCALPHA)
        hitbox_surface.fill(hitbox_color)
        self.game.screen.blit(
            hitbox_surface,
            (self.hitbox.x - self.cam_x, self.hitbox.y - self.cam_y)
        )
    
    def shoot_ray(self, origin, destination, color=(255, 255, 0), thickness=2):
        origin = np.array(origin, dtype=float)
        destination = np.array(destination, dtype=float)

        direction = destination - origin
        length = np.linalg.norm(direction)
        if length == 0:
            return

        direction /= length

        ray_length = 1000
        end_point = origin + direction * ray_length

        pg.draw.line(self.game.screen, color, origin, end_point, thickness)
        self.ray_jump(direction)
    
    def ray_jump(self, direction):
        force_magnitude = 15
        
        direction_length = np.linalg.norm(direction)
        if direction_length == 0:
            return
            
        normalized_direction = direction / direction_length
        
        self.x -= normalized_direction[0] * force_magnitude
        self.y -= normalized_direction[1] * force_magnitude
    
    def handle_free_cam(self):
        if not self.free_cam:
            return
        
        keys = pg.key.get_pressed()
        speed = 10
        
        if keys[pg.K_UP]:
            self.cam_y -= speed
            
        if keys[pg.K_DOWN]:
            self.cam_y += speed
            
        if keys[pg.K_LEFT]:
            self.cam_x -= speed
            
        if keys[pg.K_RIGHT]:
            self.cam_x += speed

    def update(self):
        if self.game.environment.menu in {"play", "death", "pause"}:
            if not hasattr(self, "settings_loaded") or not self.settings_loaded:
                self.load_settings()
                self.settings_loaded = True 
            
            self.update_camera()
            if not self.game.memory_debugger.show_memory_info:
                self.handle_controls()
                
            self.update_state()
            self.handle_gravity()
            self.update_collision()
            #self.update_projectiles()
            self.interact_hitbox()
            self.animate()
            self.update_attack_hitbox()
            self.render_inventory()
            self.update_pickup_tags()
            self.render_item_mouse()
            self.render_health()
            self.render_dialogue()
            self.render()
            self.render_hitboxes()
            self.handle_free_cam()
            
        else:
            if hasattr(self, "settings_loaded"):
                del self.settings_loaded