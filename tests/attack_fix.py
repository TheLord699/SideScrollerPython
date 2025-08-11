import pygame as pg
import random
import json
import math
import os

class Player:
    def __init__(self, game):
        self.game = game
           
        self.load_settings()
        
    def load_settings(self):
        self.x = 0
        self.y = 900
        self.vel_x = 0
        self.vel_y = 0
        self.speed = 5 # 5
        self.dash_speed = 100 # 100
        self.weight = 1 # 1
        self.jump_strength = 10
        self.friction = 0

        self.cam_x = self.x - self.game.screen_width / 2
        self.cam_y = self.y - self.game.screen_height / 1.5
        self.camera_speed = 10
        self.camera_smoothing_factor = 0.1
        self.camera_unlock_duration = 2
        self.camera_unlock_time = 0

        self.sheet_width = 100
        self.sheet_height = 100
        self.scale_factor = self.game.environment.scale 
        self.hitbox_width = 5 * self.scale_factor
        self.hitbox_height = 15 * self.scale_factor
        self.attack_hitbox_width = 17 * self.scale_factor
        self.attack_hitbox_height = 15 * self.scale_factor
        self.attack_hitbox_offset = 5
        self.hitbox = pg.Rect(self.x, self.y, self.hitbox_width, self.hitbox_height)
        self.interact_radius = pg.Rect(self.x, self.y, self.hitbox_width, self.hitbox_height)
        self.attack_hitbox = pg.Rect(0, 0, self.attack_hitbox_width, self.attack_hitbox_height)

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
        
        # will remove melee attacks soon and replace with projectile based attack
        self.active_projectile_attack_ids = []
        self.active_melee_attack_ids = []
        self.current_attack_id = 0
            
        self.max_health = 3
        self.current_health = self.max_health
        self.health_per_row = 10
        self.health_spacing = 35
        
        self.last_step_time = 0 
        self.step_interval = 300
        self.actual_horizontal_movement = False
        
        self.in_dialogue = False
        self.dialougue_index = 0
        self.dialogue_with = None
        
        self.frame_delay = 5
        self.states = ["idle", "walking", "attacking1", "attacking2", "attacking3", "hurt", "death"]
        self.current_state = "idle"
        self.direction = "right"
        self.frames = {state: [] for state in self.states}
        self.current_frame = 0
        self.animation_timer = 0
        self.frame_count = 0
        # will load settings from json instead of hard coding dictionaries
        self.state_frames = {
            "idle": {"frames": 6, "speed": 0.15},
            "walking": {"frames": 8, "speed": 0.2},
            "attacking1": {"frames": 6, "speed": 0.2},
            "attacking2": {"frames": 6, "speed": 0.2},
            "hurt": {"frames": 4, "speed": 0.2},
            "death": {"frames": 4, "speed": 0.2},
        }
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
            ]
        }

        self.sprite_sheet = None
        self.attacking = False
        self.on_ground = False
        self.in_inventory = False
        self.just_closed_dialogue = False
        
        random.seed(self.game.environment.seed)
        
        with open(os.path.join("assets", "settings", "entities.json"), "r") as file:
            self.item_info = json.load(file)
        
        self.load_frames()

    def load_frames(self):
        sprite_sheets = {} 
        
        for state, num_frames in self.state_frames.items():
            if state not in sprite_sheets:  
                sprite_sheets[state] = pg.image.load(f"assets/sprites/player/{state}_animation.png").convert_alpha()
                
            sheet = sprite_sheets[state]
            for frame in range(num_frames["frames"]):
                image = self.get_image(sheet, frame, self.sheet_width, self.sheet_height, self.sheet_width * self.scale_factor, self.sheet_height * self.scale_factor, (0, 0, 0))
                self.frames[state].append(image)

    def get_image(self, sheet, frame, width, height, new_w, new_h, color):
        image = pg.Surface((width, height), pg.SRCALPHA).convert_alpha()
        image.blit(sheet, (0, 0), ((frame * width), 0, width, height))
        image = pg.transform.scale(image, (new_w, new_h))
        image.set_colorkey(color)
        return image

    def checks(self):     
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
        
        if self.current_health < 0.5 and not self.current_state in {"death"}:
            self.death()
        
        if self.current_state in {"death"} or getattr(self, "sliding", False):   
            if self.friction <= 0:
                if self.on_ground:
                    self.friction = 0.3
                         
            if self.vel_x > 0:
                self.vel_x -= self.friction
            
            if self.vel_x < 0:
                self.vel_x += self.friction
            
            if self.vel_x < 0.5 and self.vel_x > 0:
                self.vel_x = 0
            
            if self.vel_x < -0.5 and self.vel_x > 0:
                self.vel_x = 0
            
        if self.actual_horizontal_movement and self.on_ground and not self.current_state in {"death"}:
            if self.game.environment.current_time - self.last_step_time > self.step_interval:
                walking_sound = random.choice(self.sounds["walking"])
                walking_sound["sound"].play()
                self.last_step_time = self.game.environment.current_time
                
    def death(self):
        self.current_state = "death"
        self.current_frame = 0
        self.frame_count = 0
        self.attacking = False
        self.in_inventory = False
        self.in_dialogue = False
        self.dialogue_with = None
        self.game.ui.remove_ui_element("dialogue_boarder")
        self.game.ui.remove_ui_element("dialogue_name")
        self.game.environment.menu = "death"
    
    def render_health(self):
        previous_health = getattr(self, 'previous_health', self.current_health)

        if not previous_health == self.current_health:
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
                image_path = "heart_0_0"
                
            elif heart + 1 - self.current_health == 0.5:
                image_path = "heart_0_1"
                
            else:
                image_path = "heart_0_2"

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
    
    def render_item_info(self, id): # doesnt update amount in real time
        if hasattr(self, "last_rendered_item") and self.last_rendered_item:
            self.game.ui.remove_ui_element(self.last_rendered_item)
            self.game.ui.remove_ui_element("item_info")
            
        if not self.selected_slot == None:
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
                sprite_sheet_path="ui_sheet", image_id="item_34_3",
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
            
        elif self.selected_slot is not None and not slot == self.selected_slot and (self.game.environment.current_time - self.inventory_cooldown >= 150):
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
    
    # probably shit way of handling hitboxes
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
        if self.in_dialogue:
            if self.dialougue_index > len(self.dialogue_with["message"]) - 1:
                self.in_dialogue = False
                self.dialogue_with = None
                self.just_closed_dialogue = True

                self.game.ui.remove_ui_element("dialogue_boarder")
                self.game.ui.remove_ui_element("dialogue_name")

                for sound in self.sounds["talking"]:
                    sound["sound"].stop()

            else:    
                self.game.ui.create_ui(
                    sprite_sheet_path="ui_sheet", image_id="item_33_0",
                    x=self.game.screen_width / 2, y=self.game.screen_height / 1.15, sprite_width=95, sprite_height=32, 
                    centered=True, width=300, height=150,
                    alpha=True, is_button=False,
                    element_id="dialogue_boarder",
                    scale_multiplier=1,
                    label=self.dialogue_with["message"][self.dialougue_index],
                    font=self.game.environment.fonts["fantasy"],
                    render_order=0
                )
                self.game.ui.create_ui(
                    sprite_sheet_path="ui_sheet",
                    x=self.game.screen_width / 5, y=self.game.screen_height / 1.5, sprite_width=95, sprite_height=32, 
                    centered=True, width=300, height=150,
                    alpha=True, is_button=False,
                    element_id="dialogue_name",
                    scale_multiplier=1,
                    label=self.dialogue_with["name"],
                    font=self.game.environment.fonts["fantasy"],
                    render_order=1
                )
                
    def interact_with_entity(self):
        for entity in self.game.entities.entities:
            if entity["entity_type"] == "item":
                entity_hitbox = pg.Rect(entity["x"] - entity["width"] / 2, entity["y"] - entity["height"] / 2, entity["width"], entity["height"])

                if self.interact_radius.colliderect(entity_hitbox):
                    if len(self.inventory) < self.max_inventory_slots:
                        self.add_item_to_inventory({**entity})
                        
                        self.game.entities.entities.remove(entity)
                        
                        for sound in self.sounds["pickup"]:
                            sound["sound"].stop()
                        
                        pickup_sound = random.choice(self.sounds["pickup"])
                        pickup_sound["sound"].play()
            
            if entity["entity_type"] == "npc":
                entity_hitbox = pg.Rect(entity["x"] - entity["width"] / 2, entity["y"] - entity["height"] / 2, entity["width"], entity["height"])
                
                if self.interact_radius.colliderect(entity_hitbox):
                    if entity["message"]:
                        if self.just_closed_dialogue:
                            return

                        self.in_dialogue = True
                        self.dialougue_index = 0
                        self.dialogue_with = entity
                        
                        if entity["x"] < self.x:
                            self.direction = "left"
                        
                        else: 
                            self.direction = "right"

                        for sound in self.sounds["talking"]:
                            sound["sound"].stop()

                        talk_sound = random.choice(self.sounds["talking"])
                        talk_sound["sound"].play()
    
    def drop_item(self):
        if self.selected_slot is not None and self.selected_slot in self.inventory:
            item_to_drop = self.inventory[self.selected_slot]
            
            if item_to_drop["quantity"] > 1:
                item_to_drop["quantity"] -= 1
            
            else:
                del self.inventory[self.selected_slot]
            
            self.game.entities.create_item(item_to_drop["name"], self.x, self.y)
            
            self.refresh_inventory()
            self.selected_slot = None
            self.inventory_changed = True
            
            drop_sound = random.choice(self.sounds["pickup"])
            drop_sound["sound"].play()
    
    def consume_item(self):
        if self.selected_slot is not None and self.selected_slot in self.inventory and self.inventory[self.selected_slot]["type"] == "consumable":
            item_to_consume = self.inventory[self.selected_slot]
            
            if item_to_consume["quantity"] > 1:
                self.current_health += item_to_consume["health"]
                item_to_consume["quantity"] -= 1
            
            else:
                self.current_health += item_to_consume["health"]
                del self.inventory[self.selected_slot]
            
            self.refresh_inventory()
            self.selected_slot = None
            self.inventory_changed = True
            
            consume_sound = random.choice(self.sounds["consume"])
            consume_sound["sound"].play()
            
    def update_collision(self):
        self.hitbox_set()
        horizontal_collisions = []
        vertical_collisions = []

        self.blocked_horizontally = False

        for index, tile_hitbox in enumerate(self.game.map.tile_hitboxes):
            tile_id = self.game.map.tile_id[index]
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
                    self.current_health -= damage
                    
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
                    self.current_health -= damage
                    
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

        for index, tile_hitbox in enumerate(self.game.map.tile_hitboxes):
            if tile_hitbox.collidepoint(bottom_middle_x, bottom_middle_y):
                tile_id = self.game.map.tile_id[index]
                tile_attributes = self.game.map.tile_attributes.get(tile_id, {})

                swimmable = tile_attributes.get("swimmable", False)
                slippy = tile_attributes.get("slippy", False)
                friction = tile_attributes.get("friction", 0)
                damage = tile_attributes.get("damage", 0)

                if swimmable:
                    self.vel_y *= 0.3 # temp fix for swimming
                    continue

                if slippy:
                    self.friction = friction
                    self.sliding = True
                
                else:
                    self.friction = 0
                    self.sliding = False

                if damage > 0:
                    self.current_health -= damage

                if self.vel_y >= 1.5:
                    self.y = tile_hitbox.top - self.hitbox.height / 2
                    self.vel_y = 0
                    self.on_ground = True

    def animate(self):
        previous_state = self.current_state

        # Set the attack state on the first frame if attacking is triggered
        if self.attacking:
            self.current_state = f"attacking{self.attack_sequence}"
            self.attacking = False  # Immediately unset attacking to avoid loops

        elif self.current_state.startswith("attacking"):
            # Continue the attack animation until it completes
            pass
        
        elif self.current_state != "death":
            # Movement and idle logic
            if self.vel_x != 0:
                self.current_state = "walking"
            else:
                self.current_state = "idle"

        # Lock the death animation at the last frame
        if self.current_state == "death" and self.current_frame == len(self.frames[self.current_state]) - 1:
            self.current_frame = len(self.frames[self.current_state]) - 1
            self.animation_timer = 0

        # Reset animation frame if the state changed
        if self.current_state != previous_state:
            self.current_frame = 0
            self.animation_timer = 0

        # Frame timing
        frame_delay = int(1 / self.state_frames[self.current_state]["speed"])
        self.animation_timer += 1

        # Frame advancement logic
        if self.animation_timer >= frame_delay:
            self.animation_timer = 0
            self.current_frame += 1

            # Handle the end of an attack sequence
            if self.current_state.startswith("attacking"):
                if self.current_frame >= len(self.frames[self.current_state]):
                    # Reset attack sequence and return to idle
                    self.current_frame = 0
                    self.attack_sequence = (self.attack_sequence % 2) + 1
                    self.active_melee_attack_ids.clear()
                    self.current_state = "idle"
                else:
                    # Stay in the current attack state until the sequence completes
                    self.current_frame %= len(self.frames[self.current_state])


    def handle_controls(self):
        keys = pg.key.get_pressed()

        if not self.current_state == "death":
            if self.in_inventory:
                if not getattr(self, "sliding", False):
                    self.vel_x = 0
                    
                if keys[pg.K_q]:
                    self.drop_item()
                
                if keys[pg.K_e]:
                    self.consume_item()

            else:
                if not self.in_dialogue:
                    if getattr(self, "sliding", False):
                        if keys[pg.K_a] and not keys[pg.K_d]:
                            if not self.blocked_horizontally:
                                self.vel_x = -self.speed 
                                self.direction = "left"
                            
                        elif keys[pg.K_d] and not keys[pg.K_a]:
                            if not self.blocked_horizontally:
                                self.vel_x = self.speed 
                                self.direction = "right"
                            
                    else:
                        if keys[pg.K_a] and keys[pg.K_d]:
                            self.vel_x = 0  
                            
                        elif keys[pg.K_a]:
                            if not self.blocked_horizontally:
                                self.vel_x = -self.speed
                                self.direction = "left"
                            
                        elif keys[pg.K_d]:
                            if not self.blocked_horizontally:
                                self.vel_x = self.speed 
                                self.direction = "right"
                            
                        else:
                            self.vel_x = 0

                    if keys[pg.K_w] and self.on_ground:
                        self.vel_y = -self.jump_strength
                        jump_sound = random.choice(self.sounds["jump"])
                        jump_sound["sound"].play()
                        
                    if keys[pg.K_e]:
                        self.interact_with_entity()

                    if keys[pg.K_SPACE]:
                        self.start_attack()
                    
                    if keys[pg.K_ESCAPE]:
                        self.game.environment.menu = "pause"
                
                else:
                    self.vel_x = 0

            for event in self.game.events:
                if event.type == pg.KEYDOWN: 
                    if not self.in_dialogue:
                        if event.key == pg.K_i: 
                            self.in_inventory = not self.in_inventory
                            
                            if self.in_inventory:
                                inventory_open_sound = self.sounds["inventory"]["open"]
                                inventory_open_sound["sound"].play()
                                
                            else:
                                inventory_close_sound = self.sounds["inventory"]["close"]
                                inventory_close_sound["sound"].play()
                        
                        if event.key == pg.K_LSHIFT:
                            if not self.in_inventory:
                                self.dash()
                        
                    else:
                        if event.key == pg.K_e:
                            self.game.ui.remove_ui_element("dialogue_boarder")
                            self.dialougue_index += 1

                            for sound in self.sounds["talking"]:
                                sound["sound"].stop()

                            talk_sound = random.choice(self.sounds["talking"])
                            talk_sound["sound"].play()
                    
                elif event.type == pg.KEYUP:
                    if event.key == pg.K_e and self.just_closed_dialogue:
                            self.just_closed_dialogue = False
    
    def dash(self):
        # need to add collisison detection to prevent dash into wall
        if not hasattr(self, "dash_cooldown") or self.game.environment.current_time - self.dash_cooldown >= 500:
            if self.direction == "right":
                self.vel_x = self.dash_speed
                
            else:
                self.vel_x = -self.dash_speed
            
            dash_sound = random.choice(self.sounds["jump"])
            dash_sound["sound"].play()
            
            self.dash_cooldown = self.game.environment.current_time
                    
    def start_attack(self): # will make all attacks projectile based using projectile func
        if not self.current_state.startswith("attacking"):
            self.attacking = True
            self.current_frame = 0
            self.attack_timer = 0

            new_attack_id = self.current_attack_id
            self.active_melee_attack_ids.append(new_attack_id)
            self.current_attack_id += 1

            attack_sound = random.choice(self.sounds["attack"])
            attack_sound["sound"].play()
            
    def update_projectiles(self):
        self.active_projectile_attack_ids = [id for id in self.active_projectile_attack_ids if not self.is_projectile_done(id)]

    def update_attack_hitbox(self):
        if self.attacking:
            if self.direction == "right":
                self.attack_hitbox.centerx = self.hitbox.right + self.attack_hitbox_width // 2
                
            else:
                self.attack_hitbox.centerx = self.hitbox.left - self.attack_hitbox_width // 2
                
            self.attack_hitbox.centery = self.hitbox.centery

    def render(self):
        if self.current_state not in self.frames or len(self.frames[self.current_state]) == 0:
            return
        
        if self.current_frame >= len(self.frames[self.current_state]):
            self.current_frame = len(self.frames[self.current_state]) - 1
    
        image = self.frames[self.current_state][self.current_frame]
        
        if self.direction == "left":
            image = pg.transform.flip(image, True, False)
            
        flip_offset = 0.6 if self.direction == "left" else 0 # pls dont crucify me 
        
        sprite_x = self.hitbox.centerx - self.cam_x - image.get_width() // 2 + flip_offset
        sprite_y = self.hitbox.centery - self.cam_y + 3 - image.get_height() // 2 # 3 cuz feet visually not touching ground
        
        self.game.screen.blit(image, (sprite_x, sprite_y))

    def update_camera(self):
        # can change the target here
        target_cam_x = self.x - self.game.screen_width / 2
        target_cam_y = self.y - self.game.screen_height / 1.5 # 1.5

        self.cam_x += (target_cam_x - self.cam_x) * self.camera_smoothing_factor
        self.cam_y += (target_cam_y - self.cam_y) * self.camera_smoothing_factor
        
        self.cam_x = max(min(self.cam_x, target_cam_x + self.game.screen_width / 4), target_cam_x - self.game.screen_width / 4)
        self.cam_y = max(min(self.cam_y, target_cam_y + self.game.screen_height / 4), target_cam_y - self.game.screen_height / 4)

    def render_hitboxes(self):
        if self.attacking:
            hitbox_color = (255, 0, 0, 100)  
            hitbox_surface = pg.Surface((self.attack_hitbox_width, self.attack_hitbox_height), pg.SRCALPHA)
            hitbox_surface.fill(hitbox_color)
            self.game.screen.blit(hitbox_surface, (self.attack_hitbox.x - self.cam_x, self.attack_hitbox.y - self.cam_y))
        
        hitbox_color = (0, 255, 0, 100)
        hitbox_surface = pg.Surface((self.hitbox_width, self.hitbox_height), pg.SRCALPHA)
        hitbox_surface.fill(hitbox_color)
        self.game.screen.blit(hitbox_surface, (self.hitbox.x - self.cam_x, self.hitbox.y - self.cam_y))

    def update(self):
        if self.game.environment.menu in {"play", "death", "pause"}:
            if not hasattr(self, "settings_loaded") or not self.settings_loaded:
                self.load_settings()
                self.settings_loaded = True 
            
            self.update_camera()
            self.handle_controls()
            self.checks()
            self.handle_gravity()
            self.update_collision()
            #self.update_projectiles()
            self.interact_hitbox()
            self.animate()
            self.update_attack_hitbox()
            self.render_inventory()
            self.render_health()
            self.render_dialogue()
            self.render()
            #self.render_hitboxes()
            
        else:
            if hasattr(self, "settings_loaded"):
                del self.settings_loaded
        
            
