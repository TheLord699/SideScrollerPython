import pygame as pg
import numpy as np
import random
import math
import os

from helper_methods import load_json

class Player:
    def __init__(self, game):
        self.game = game
        
        self.enable_cam_mouse = False
        
        self.smoke_images = { # Ik this is super specific but i dont want to write an image manager
            1: pg.image.load("assets/sprites/particles/smoke1.png").convert_alpha(),
            2: pg.image.load("assets/sprites/particles/smoke2.png").convert_alpha(),
        }
                   
    def load_settings(self):
        self.x = self.game.environment.player_spawn_x
        self.y = self.game.environment.player_spawn_y
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
        self.screen_shake_timer = 0

        self.scale_factor = self.game.environment.scale
        self.hitbox_width = 5 * self.scale_factor
        self.hitbox_height = 15 * self.scale_factor
        self.hitbox = pg.Rect(self.x, self.y, self.hitbox_width, self.hitbox_height)
        self.interact_radius = pg.Rect(self.x, self.y, self.hitbox_width, self.hitbox_height)
        self.blocked_horizontally = False

        self.attack_timeout = 30
        self.attack_sequence = 1
        self.attack_timer = 0
        self.current_attack_projectile = None

        self.max_inventory_slots = 15
        self.rendered_inventory_ui_elements = []
        self.inventory_x_offset = self.game.screen_width / 2.5
        self.inventory_y_offset = self.game.screen_height / 2.5
        self.items_per_row = 5
        self.item_spacing = 40
        self.selected_slot = None
        self.inventory_changed = False
        self.inventory_cooldown = 0
        self.inventory = {}

        self.max_health = 3
        self.current_health = self.max_health
        self.health_per_row = 10
        self.health_spacing = 35
        self.invinsibility_duration = 900
        self.last_damage_time = -self.invinsibility_duration * 2

        self.pickup_tags = []
        self.max_tags = 3

        self.last_step_time = 0
        self.step_interval = 300
        self.actual_horizontal_movement = False

        self.in_dialogue = False
        self.dialogue_index = 0
        self.dialogue_with = None

        self.in_map = False
        self.map_scale_factor = 5
        self.map_offset_x = 0
        self.map_offset_y = 0
        self.map_dragging = False

        self.fall_time = 0
        self.max_fall_time = 500

        self.coyote_time = 8
        self.coyote_timer = 0
        
        self.last_volume = None

        self.current_state = "idle"
        self.direction = "right"
        self.current_frame = 0
        self.animation_timer = 0
        self.weapon_info = load_json(os.path.join("assets", "settings", "weapon_data.json"))
        self.weapon_inventory = ["basic_sword", "basic_bow"] # temporary, will be replaced with actual inventory system
        self.equipped_weapon = "basic_sword"
        self.loaded_weapons = set()
        self.state_frames = {
            "idle": {"frames": 6, "speed": 0.15},
            "walking": {"frames": 8, "speed": 0.2},
            "jump": {"frames": 3, "speed": 0.15},
            "hurt": {"frames": 4, "speed": 0.10},
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
            ],
            "bow_draw": [
                {"sound": pg.mixer.Sound("assets/sounds/player/attack/bow_draw.wav"), "volume": 2.0}
            ],
            "bow_shoot": [
                {"sound": pg.mixer.Sound("assets/sounds/player/attack/bow_shoot.wav"), "volume": 2.0}
            ]
        }

        self.charging = False
        self.charge_timer = 0
        self.charge_sound_played = False
        self.proj_image_cache = {}

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

    def load_weapon_animations(self):
        weapons_to_load = [w for w in self.weapon_inventory if w in self.weapon_info and w not in self.loaded_weapons]
        unloaded = self.loaded_weapons - set(self.weapon_inventory)
                
        if not weapons_to_load and not unloaded:
            return

        for weapon in weapons_to_load:
            weapon_data = self.weapon_info[weapon]
            first_sequence_state = f"attacking{weapon}1"

            if first_sequence_state in self.frames and self.frames[first_sequence_state]:
                self.loaded_weapons.add(weapon)
                continue

            for sequence in range(1, weapon_data.get("sequence", 1) + 1):
                state_name = f"attacking{weapon}{sequence}"
                frames_count = weapon_data["frames"][sequence - 1]

                self.frames[state_name] = []
                self.flipped_frames[state_name] = []

                sheet_paths = [
                    f"assets/sprites/player/weapons/attacking_{weapon}{sequence}.png",
                    f"assets/sprites/player/weapons/{weapon}_attack{sequence}.png",
                    f"assets/sprites/player/weapons/{weapon}{sequence}.png"
                ]

                sheet = None
                for sheet_path in sheet_paths:
                    try:
                        sheet = pg.image.load(sheet_path).convert_alpha()
                        break

                    except:
                        continue

                if sheet is None:
                    fallback_paths = [
                        f"assets/sprites/player/attacking_animation.png",
                        f"assets/sprites/player/attacking{sequence}_animation.png"
                    ]

                    for fallback_path in fallback_paths:
                        try:
                            sheet = pg.image.load(fallback_path).convert_alpha()
                            print(f"Using fallback animation: {fallback_path}")
                            break

                        except:
                            continue

                if sheet is None:
                    print(f"Failed to load any animation for {state_name}")
                    continue

                scaled_width = self.sheet_width * self.scale_factor
                scaled_height = self.sheet_height * self.scale_factor

                for frame_index in range(frames_count):
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

                    self.frames[state_name].append(frame_image)
                    self.flipped_frames[state_name].append(flipped_image)

            self.loaded_weapons.add(weapon)

        for weapon in unloaded:
            for sequence in range(1, self.weapon_info.get(weapon, {}).get("sequence", 1) + 1):
                state_name = f"attacking{weapon}{sequence}"
                if state_name in self.frames:
                    del self.frames[state_name]
                    
                if state_name in self.flipped_frames:
                    del self.flipped_frames[state_name]
                    
            self.loaded_weapons.remove(weapon)

    def update_state(self):
        if self.last_volume != self.game.environment.volume:
            self.last_volume = self.game.environment.volume
            for sound_group in self.sounds.values():
                if isinstance(sound_group, list):
                    for sound_dict in sound_group:
                        sound_dict["sound"].set_volume(self.game.environment.volume / 10 * sound_dict["volume"])
                        
                elif isinstance(sound_group, dict):
                    for sound_dict in sound_group.values():
                        sound_dict["sound"].set_volume(self.game.environment.volume / 10 * sound_dict["volume"])

        self.current_health = math.floor(self.current_health * 2) / 2
        self.current_health = min(self.current_health, self.max_health)

        self.x += self.vel_x
        self.y += self.vel_y

        self.attack_timer += 1

        if self.current_health < 0:
            self.current_health = 0
                
        if not self.equipped_weapon in self.weapon_inventory:
            self.equipped_weapon = ""

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

                for amount in range(5):
                    base_vel_x = random.uniform(0, 0.5)
                    if self.direction == "right":
                        vel_x = -base_vel_x

                    elif self.direction == "left":
                        vel_x = base_vel_x

                    else:
                        vel_x = random.uniform(-0.5, 0.5)

                    vel_y = random.uniform(-0.5, -0.1)
                    radius = random.randint(2, 4)

                    smoke_img = self.smoke_images[random.choice([1, 2])]

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
            self.knockback_timer = 12 

            self.game.foreground.add_screen_effect("hurt", intensity=0.7, duration=20)

            self.shake_camera(intensity=8, duration=25)
            self.cancel_charge()

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
                self.current_attack_projectile = None
                hurt_sound = random.choice(self.sounds["hit"])
                hurt_sound["sound"].play()

    def death(self):
        self.current_state = "death"
        self.current_frame = 0
        self.attacking = False
        self.in_inventory = False
        self.in_dialogue = False
        self.in_map = False
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
                render_order=-15
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
        screen_width = self.game.screen.get_width()
        x_pos = screen_width - 100

        if len(self.pickup_tags) >= self.max_tags:
            oldest = self.pickup_tags.pop(0)
            self.game.ui.remove_ui_element(oldest["element_id"])
            self.game.ui.remove_ui_element(oldest["text_id"])
            self.reposition_tags(x_pos)

        index = len(self.pickup_tags)
        creation_time = self.game.environment.current_time
        element_id = f"pickup_tag_{creation_time}_{index}"
        text_id = f"pickup_text_{creation_time}_{index}"

        self.game.ui.create_ui(
            sprite_sheet_path="item_sheet",
            image_id=self.item_info["items"][item_name]["index"],
            x=x_pos, y=20 + index * 35,
            sprite_width=16, sprite_height=16,
            width=30, height=30,
            element_id=element_id,
            render_order=2
        )

        self.game.ui.create_ui(
            x=x_pos + 50, y=20 + index * 35 + 15,
            font_size=10,
            font=self.game.environment.fonts["fantasy"],
            element_id=text_id,
            render_order=2,
            label=item_name
        )

        self.pickup_tags.append({
            "name": item_name,
            "element_id": element_id,
            "text_id": text_id,
            "creation_time": creation_time
        })

    def reposition_tags(self, x_pos=None):
        if x_pos is None:
            x_pos = self.game.screen.get_width() - 100

        for slot, tag in enumerate(self.pickup_tags):
            self.game.ui.remove_ui_element(tag["element_id"])
            self.game.ui.remove_ui_element(tag["text_id"])

            tag["element_id"] = f"pickup_tag_{tag['creation_time']}_{slot}"
            tag["text_id"] = f"pickup_text_{tag['creation_time']}_{slot}"

            self.game.ui.create_ui(
                sprite_sheet_path="item_sheet",
                image_id=self.item_info["items"][tag["name"]]["index"],
                x=x_pos, y=20 + slot * 35,
                sprite_width=16, sprite_height=16,
                width=30, height=30,
                element_id=tag["element_id"],
                render_order=2
            )

            self.game.ui.create_ui(
                x=x_pos + 50, y=20 + slot * 35 + 15,
                font_size=10,
                font=self.game.environment.fonts["fantasy"],
                element_id=tag["text_id"],
                render_order=2,
                label=tag["name"]
            )

    def update_pickup_tags(self):
        if not self.pickup_tags:
            return

        current_time = self.game.environment.current_time
        expired = [tag for tag in self.pickup_tags if current_time - tag["creation_time"] >= 3000]

        if not expired:
            return

        for tag in expired:
            self.game.ui.remove_ui_element(tag["element_id"])
            self.game.ui.remove_ui_element(tag["text_id"])

        expired_ids = {id(tag) for tag in expired}
        self.pickup_tags = [tag for tag in self.pickup_tags if id(tag) not in expired_ids]

        self.reposition_tags()

    def render_item_info(self, id):
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
        for entity in list(self.game.entities.entities):
            if entity["entity_type"] == "item":
                entity_hitbox = pg.Rect(
                    entity["x"] - entity["width"] / 2,
                    entity["y"] - entity["height"] / 2,
                    entity["width"],
                    entity["height"]
                )

                if self.interact_radius.colliderect(entity_hitbox):
                    if len(self.inventory) < self.max_inventory_slots:
                        self.add_item_to_inventory({**entity})
                        self.add_pickup_tag(entity["name"])
                        self.game.entities.entities.remove(entity)

                        for sound in self.sounds["pickup"]:
                            sound["sound"].stop()

                        pickup_sound = random.choice(self.sounds["pickup"])
                        pickup_sound["sound"].play()

            elif entity["entity_type"] == "npc":
                if not self.on_ground:
                    continue

                entity_hitbox = pg.Rect(
                    entity["x"] - entity["width"] / 2,
                    entity["y"] - entity["height"] / 2,
                    entity["width"],
                    entity["height"]
                )

                if self.interact_radius.colliderect(entity_hitbox):
                    if entity["message"]:
                        if self.just_closed_dialogue:
                            return

                        self.dialogue_with = entity
                        self.dialogue_index = 0
                        self.dialogue_just_opened = True
                        self.in_dialogue = True

                        self.direction = "left" if entity["x"] < self.x else "right"

                        for sound in self.sounds["talking"]:
                            sound["sound"].stop()

                        talk_sound = random.choice(self.sounds["talking"])
                        talk_sound["sound"].play()
            
            elif entity["entity_type"] == "actor":
                if entity.get("interactable", True) and (entity.get("interaction") == "scripted" or entity.get("script")):
                    entity_hitbox = pg.Rect(
                        entity["x"] - entity["width"] / 2,
                        entity["y"] - entity["height"] / 2,
                        entity["width"],
                        entity["height"]
                    )
                    if self.interact_radius.colliderect(entity_hitbox):
                        self.game.ai.interact_with_actor(entity)
                        break

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
        self.coyote_timer = 0
        self.vel_y = -self.jump_strength
        jump_sound = random.choice(self.sounds["jump"])
        jump_sound["sound"].play()

        flip_offset = 11 if self.direction == "right" else 0

        for amount in range(7):
            vel_x = random.uniform(-1.0, 1.0)
            vel_y = random.uniform(-1.0, -0.3)

            radius = random.randint(2, 4)
            smoke_img = self.smoke_images[random.choice([1, 2])]

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
                    self.vel_y += 1
                    
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
                    self.vel_y *= 0.8
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
        
        if self.on_ground or self.vel_y < 0:
            if self.on_ground:
                self.coyote_timer = self.coyote_time
                
            self.fall_time = 0
            
        else:
            if self.coyote_timer > 0:
                self.coyote_timer -= 1
            
            if self.fall_time < self.max_fall_time:
                self.fall_time += 1
    
    def update_fall_shake(self):
        if not self.on_ground and self.fall_time > 150:
            normalized = min(1.0, (self.fall_time - 150) / (self.max_fall_time - 150))
            shake_intensity = (normalized ** 2) * 4
            
            if self.vel_y > 3:
                self.shake_camera(intensity=shake_intensity, duration=2)
            
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
            self.current_state = f"attacking{self.equipped_weapon}{self.attack_sequence}"
            
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
            weapon_data = self.weapon_info.get(self.equipped_weapon)
            if not weapon_data:
                self.attacking = False
                return

            if self.charging:
                return

            frame_delay = int(1 / weapon_data["speed"])
            frames_for_attack = weapon_data["frames"][self.attack_sequence - 1]

        else:
            frame_delay = int(1 / self.state_frames[self.current_state]["speed"])
            frames_for_attack = self.state_frames[self.current_state]["frames"]

        self.animation_timer += 1
        if self.animation_timer < frame_delay:
            return

        self.animation_timer = 0
        self.current_frame = (self.current_frame + 1) % frames_for_attack

        if self.current_state.startswith("attacking"):
            weapon_data = self.weapon_info.get(self.equipped_weapon, {})
            is_ranged = weapon_data.get("type") in ("ranged", "instant_ranged")
            if not is_ranged and self.current_frame == frames_for_attack - 1:
                self.attacking = False
                max_sequence = weapon_data.get("sequence", 1)
                self.attack_sequence = (self.attack_sequence % max_sequence) + 1
                self.current_attack_projectile = None

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

        if hasattr(self, "knockback_timer") and self.knockback_timer > 0:
            self.knockback_timer -= 1
            
            if self.in_inventory:
                self.handle_inventory_controls(keys, controller, in_knockback=True)
                
            else:
                self.handle_normal_controls(keys, mouse_buttons, controller, in_knockback=True)
                
        else:
            if self.in_inventory:
                self.handle_inventory_controls(keys, controller, in_knockback=False)
                
            else:
                self.handle_normal_controls(keys, mouse_buttons, controller, in_knockback=False)

        if self.in_map:
            self.handle_map_controls(mouse_buttons)

        self.handle_events(controller)

    def handle_inventory_controls(self, keys, controller, in_knockback=False):
        if not in_knockback:
            if not getattr(self, "sliding", False):
                self.vel_x = 0
                #self.vel_y = 0

        if keys[pg.K_q] or (self.joystick and controller.get("X")):
            self.drop_item()

        if keys[pg.K_e] or (self.joystick and controller.get("A")):
            self.consume_item()
        
    def handle_normal_controls(self, keys, mouse_buttons, controller, in_knockback=False):
        if self.in_dialogue:
            self.vel_x = 0
            return

        if in_knockback:
            jump_input = keys[pg.K_w] or (self.joystick and controller.get("A"))
            if jump_input and self.coyote_timer > 0:
                self.jump()
            
            interact_input = keys[pg.K_e] or (self.joystick and controller.get("Y"))
            if interact_input and not self.in_map:
                self.interact_with_entity()
            
            attack_input = keys[pg.K_SPACE] or (self.joystick and controller.get("B"))
            if self.current_state != "hurt":
                self.handle_weapon_input(attack_input)
                
            return

        self.handle_movement(keys, controller)
        self.handle_actions(keys, mouse_buttons, controller)

    def handle_movement(self, keys, controller):
        if getattr(self, "knockback_timer", 0) > 0:
            self.knockback_timer -= 1
            return 
    
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
        if jump_input and self.coyote_timer > 0:
            self.jump()

        interact_input = keys[pg.K_e] or (self.joystick and controller.get("Y"))
        if interact_input and not self.in_map:
            self.interact_with_entity()

        attack_input = keys[pg.K_SPACE] or (self.joystick and controller.get("B"))
        if self.current_state != "hurt":
            self.handle_weapon_input(attack_input)

        pause_input = keys[pg.K_ESCAPE] or (self.joystick and controller.get("start"))
        if pause_input:
            pass

        self.handle_weapon_switching(keys, controller)

    def handle_weapon_switching(self, keys, controller):
        key_to_index = {
            pg.K_1: 0, pg.K_2: 1, pg.K_3: 2, pg.K_4: 3, pg.K_5: 4,
            pg.K_6: 5, pg.K_7: 6, pg.K_8: 7, pg.K_9: 8
        }
        
        for key, index in key_to_index.items():
            if keys[key] and index < len(self.weapon_inventory):
                weapon_to_equip = self.weapon_inventory[index]
                
                if weapon_to_equip != self.equipped_weapon:
                    self.equip_weapon(weapon_to_equip)
                    break
        
        if self.joystick and controller:
            dpad = controller.get("dpad", (0, 0))
            
            if dpad[0] < 0:
                current_index = self.weapon_inventory.index(self.equipped_weapon) if self.equipped_weapon in self.weapon_inventory else 0
                new_index = (current_index - 1) % len(self.weapon_inventory)
                self.equip_weapon(self.weapon_inventory[new_index])
                
            elif dpad[0] > 0:
                current_index = self.weapon_inventory.index(self.equipped_weapon) if self.equipped_weapon in self.weapon_inventory else 0
                new_index = (current_index + 1) % len(self.weapon_inventory)
                self.equip_weapon(self.weapon_inventory[new_index])

    def handle_weapon_input(self, attack_held):
        if self.current_state in ("hurt", "death"):
            return
            
        weapon_data = self.weapon_info.get(self.equipped_weapon, {})
        weapon_type = weapon_data.get("type", "melee")

        if weapon_type in ("ranged", "instant_ranged"):
            self.handle_ranged_input(attack_held, weapon_data)
            
        elif attack_held:
            self.handle_melee_input(weapon_data)

    def handle_ranged_input(self, attack_held, weapon_data):
        is_instant = weapon_data.get("type") == "instant_ranged"
        draw_start = weapon_data.get("draw_start_frame", 0 if is_instant else 4)
        
        full_frame = weapon_data.get("full_draw_frame", 2 if is_instant else 6)
        full_ticks = weapon_data.get("full_draw_ticks", 1 if is_instant else 18)
        
        min_vel_mult = weapon_data.get("min_vel_mult", 1.0 if is_instant else 0.4)
        
        charge_key = weapon_data.get("charge_sound", "bow_draw")
        shoot_key = weapon_data.get("shoot_sound", "bow_shoot")

        if attack_held:
            if not self.attacking:
                self.attacking = True
                self.current_frame = 0
                self.attack_timer = 0
                self.charging = False
                self.charge_timer = 0
                self.charge_sound_played = False

            if self.current_frame >= draw_start:
                self.charge_timer = min(self.charge_timer + 1, full_ticks)
                t = self.charge_timer / full_ticks
                self.current_frame = min(draw_start + int(t * (full_frame - draw_start)), full_frame)
                self.charging = True

                if not self.charge_sound_played:
                    for s in self.sounds.get(charge_key, []):
                        s["sound"].play()
                    self.charge_sound_played = True

                if is_instant:
                    self.fire_projectile(weapon_data, charge=1.0, min_vel_mult=min_vel_mult)
                    for s in self.sounds.get(shoot_key, []):
                        s["sound"].play()
                    self.cancel_charge()

        else:
            if self.attacking and self.charging:
                charge = min(1.0, self.charge_timer / max(full_ticks, 1))
                self.fire_projectile(weapon_data, charge=charge, min_vel_mult=min_vel_mult)
                for s in self.sounds.get(shoot_key, []):
                    s["sound"].play()

            self.cancel_charge()

    def cancel_charge(self):
        if self.charging:
            charge_key = self.weapon_info.get(self.equipped_weapon, {}).get("charge_sound", "bow_draw")
            for s in self.sounds.get(charge_key, []):
                s["sound"].stop()

        self.charging = False
        self.charge_timer = 0
        self.charge_sound_played = False
        self.attacking = False
        self.attack_timer = 0

    def fire_projectile(self, weapon_data, charge=1.0, min_vel_mult=0.4):
        proj_data = weapon_data.get("projectile", {})
        facing = 1 if self.direction == "right" else -1

        vel_mult = min_vel_mult + (1.0 - min_vel_mult) * charge
        proj_vel_x = facing * proj_data.get("vel_x", 20) * vel_mult
        proj_vel_y = proj_data.get("vel_y", 0)
        
        base_damage = weapon_data.get("damage", 20)
        min_damage_mult = weapon_data.get("min_damage_mult", 0.3)
        damage = base_damage * (min_damage_mult + (1.0 - min_damage_mult) * charge)
        
        base_push_force = proj_data.get("push_force", 30)
        min_push_mult = proj_data.get("min_push_force_mult", 0.3)
        push_force = base_push_force * (min_push_mult + (1.0 - min_push_mult) * charge)
        
        off_x = weapon_data.get("spawn_offset_x", 25)
        if isinstance(off_x, list):
            off_x = off_x[0] if facing == -1 else off_x[1]
        
        off_y = weapon_data.get("spawn_offset_y", -8)
        if isinstance(off_y, list):
            off_y = off_y[0] if facing == -1 else off_y[1]

        img = self.load_projectile_image(self.equipped_weapon)
        if img and facing == -1:
            img = pg.transform.flip(img, True, False)

        img_off_x = weapon_data.get("image_offset_x", -30 if facing == 1 else -10)
        if isinstance(img_off_x, list):
            img_off_x = img_off_x[0] if facing == -1 else img_off_x[1]
        
        img_off_y = weapon_data.get("image_offset_y", -20)
        if isinstance(img_off_y, list):
            img_off_y = img_off_y[0] if facing == -1 else img_off_y[1]

        self.game.projectiles_system.spawn(
            x=self.x + facing * off_x,
            y=self.y + off_y,
            width=proj_data.get("width", 6),
            height=proj_data.get("height", 6),
            vel_x=proj_vel_x,
            vel_y=proj_vel_y,
            lifetime=proj_data.get("lifetime", 90),
            damage=damage,
            push_force=push_force,
            gravity=proj_data.get("gravity", 0.2),
            piercing=proj_data.get("piercing", False),
            embed_on_wall=proj_data.get("embed_on_wall", False),
            fluid_drag=proj_data.get("fluid_drag", False),
            fluid_drag_mult=proj_data.get("fluid_drag_mult", 0.85),
            image=img,
            image_offset_x=img_off_x,
            image_offset_y=img_off_y,
            owner="player",
            is_melee=False,
            knockback_direction_x=facing,
            rotate_to_velocity=proj_data.get("rotate_to_velocity", False),
            rotation_offset=proj_data.get("rotation_offset", 0)
        )

    def load_projectile_image(self, weapon_name):
        if weapon_name in self.proj_image_cache:
            return self.proj_image_cache[weapon_name]

        path = self.weapon_info.get(weapon_name, {}).get("projectile", {}).get("image")
        img = None
        if path:
            try:
                img = pg.image.load(path).convert_alpha()
                
            except Exception as e:
                print(f"Could not load projectile image '{path}': {e}")

        self.proj_image_cache[weapon_name] = img
        return img

    def handle_melee_input(self, weapon_data):
        if self.attacking or self.equipped_weapon not in self.weapon_info:
            return

        self.attacking = True
        self.current_frame = 0
        self.attack_timer = 0

        self.attack_start_direction = 1 if self.direction == "right" else -1
        offset_x = weapon_data.get("spawn_offset_x", 30)
        if isinstance(offset_x, list):
            offset_x = offset_x[0] if self.attack_start_direction == -1 else offset_x[1]
        
        offset_y = weapon_data.get("spawn_offset_y", 0)
        if isinstance(offset_y, list):
            offset_y = offset_y[0] if self.attack_start_direction == -1 else offset_y[1]

        def make_follow(player, off_x, off_y):
            def follow():
                current_facing = 1 if player.direction == "right" else -1
                return player.x + current_facing * off_x, player.y + off_y
            
            return follow

        follow_func = make_follow(self, offset_x, offset_y)

        self.current_attack_projectile = self.game.projectiles_system.spawn(
            x=self.x + self.attack_start_direction * offset_x,
            y=self.y + offset_y,
            width=weapon_data.get("hitbox_width", 34),
            height=weapon_data.get("hitbox_height", 30),
            vel_x=0,
            vel_y=0,
            lifetime=weapon_data.get("lifetime", 15),
            damage=weapon_data.get("damage", 10),
            push_force=weapon_data.get("push_force", 70),
            gravity=0,
            piercing=weapon_data.get("piercing", False),
            follow=follow_func,
            owner="player",
            is_melee=True,
            get_facing_direction=lambda: 1 if self.direction == "right" else -1,
        )

        attack_sound = random.choice(self.sounds["attack"])
        attack_sound["sound"].play()

    def equip_weapon(self, weapon_name):
        self.cancel_charge()
        
        if hasattr(self, "current_attack_projectile") and self.current_attack_projectile:
            if self.current_attack_projectile in self.game.projectiles_system.projectiles:
                self.current_attack_projectile.lifetime = 0
        
        self.equipped_weapon = weapon_name
        self.attacking = False
        self.current_frame = 0
        self.attack_timer = 0
        self.attack_sequence = 1
        self.current_attack_projectile = None
        
        if hasattr(self, "attack_facing_direction"):
            delattr(self, "attack_facing_direction")

    def handle_map_controls(self, mouse_buttons):
        mouse_pos = pg.mouse.get_pos()

        for event in self.game.events:
            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.map_dragging = True
                    self.drag_start_pos = mouse_pos
                    self.drag_start_offset = (self.map_offset_x, self.map_offset_y)

                if event.button == 4:
                    mouse_world_x = (mouse_pos[0] - self.game.screen_width // 2 - self.map_offset_x) / self.map_scale_factor
                    mouse_world_y = (mouse_pos[1] - self.game.screen_height // 2 - self.map_offset_y) / self.map_scale_factor

                    self.map_scale_factor = min(int(self.map_scale_factor) + 1, 10)

                    self.map_offset_x = mouse_pos[0] - self.game.screen_width // 2 - mouse_world_x * self.map_scale_factor
                    self.map_offset_y = mouse_pos[1] - self.game.screen_height // 2 - mouse_world_y * self.map_scale_factor

                elif event.button == 5:
                    mouse_world_x = (mouse_pos[0] - self.game.screen_width // 2 - self.map_offset_x) / self.map_scale_factor
                    mouse_world_y = (mouse_pos[1] - self.game.screen_height // 2 - self.map_offset_y) / self.map_scale_factor

                    self.map_scale_factor = max(int(self.map_scale_factor) - 1, 1)

                    self.map_offset_x = mouse_pos[0] - self.game.screen_width // 2 - mouse_world_x * self.map_scale_factor
                    self.map_offset_y = mouse_pos[1] - self.game.screen_height // 2 - mouse_world_y * self.map_scale_factor

            elif event.type == pg.MOUSEBUTTONUP:
                if event.button == 1:
                    self.map_dragging = False

            elif event.type == pg.MOUSEMOTION:
                if self.map_dragging:
                    dx = mouse_pos[0] - self.drag_start_pos[0]
                    dy = mouse_pos[1] - self.drag_start_pos[1]
                    self.map_offset_x = self.drag_start_offset[0] + dx
                    self.map_offset_y = self.drag_start_offset[1] + dy

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
            if not self.in_map:
                self.in_inventory = not self.in_inventory

                if self.in_inventory:
                    self.sounds["inventory"]["open"]["sound"].play()

                else:
                    self.sounds["inventory"]["close"]["sound"].play()

        if (event.type == pg.KEYDOWN and event.key == pg.K_t) or (button_pressed and button == 5):
            if not self.in_inventory:
                self.in_map = not self.in_map

                if self.in_map:
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
        num_ghosts = 4
        step_size = distance / num_ghosts

        for ghost in range(num_ghosts):
            ghost_x = start_x + (step_size * ghost * dash_dir)
            ghost_y = self.y - 5

            current_frame_image = self.frames[self.current_state][self.current_frame]

            if self.direction == "left":
                current_frame_image = pg.transform.flip(current_frame_image, True, False)

            white_image = current_frame_image.copy()

            white_surface = pg.Surface(white_image.get_size(), pg.SRCALPHA)
            white_surface.fill((255, 255, 255, 255))
            white_image.blit(white_surface, (0, 0), special_flags=pg.BLEND_MULT)

            opacity = int(255 * ((ghost + 1) / num_ghosts))
            white_image.fill((255, 255, 255, opacity), special_flags=pg.BLEND_RGBA_MULT)

            flip_offset = 14 if self.direction == "right" else 0

            bonus = 1 if ghost == num_ghosts - 1 else 0
            lifespan = 15 + ghost * 2 + bonus

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
        current_time = self.game.environment.current_time

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

            nearby_tiles = self.game.map.get_nearby_tiles(temp_hitbox)
            
            for tile_hitbox, tile_id in nearby_tiles:
                tile_attributes = self.game.map.tile_attributes.get(tile_id, {})
                swimmable = tile_attributes.get("swimmable", False)
                
                if temp_hitbox.colliderect(tile_hitbox) and not swimmable:
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

    def render_charge_bar(self):
        if not self.game.environment.show_indicators:
            return
        
        if not self.charging or self.equipped_weapon not in self.weapon_info:
            return
        
        weapon_data = self.weapon_info[self.equipped_weapon]
        if weapon_data.get("type") not in ("ranged", "instant_ranged"):
            return
        
        full_ticks = weapon_data.get("full_draw_ticks", 18)
        charge_percent = min(1.0, self.charge_timer / max(full_ticks, 1))
        
        bar_width = 30
        bar_height = 4
        filled_width = int(bar_width * charge_percent)
        
        bar_x = self.hitbox.centerx - self.cam_x - bar_width // 2
        bar_y = self.hitbox.y - self.cam_y - 12
        
        pg.draw.rect(self.game.screen, (50, 50, 50, 180), (bar_x, bar_y, bar_width, bar_height))
        
        if charge_percent > 0:
            if charge_percent < 0.6:
                color = (200, 255, 0)
                
            else:
                color = (0, 255, 0)
                
            pg.draw.rect(self.game.screen, color, (bar_x, bar_y, filled_width, bar_height))

    def render(self):
        self.flip_offset = {"left": 1.4, "right": 0}
        self.foot_alignment = 3
        
        if (self.current_state not in self.frames or
            not self.frames[self.current_state] or
            (self.game.environment.current_time - self.last_damage_time < self.invinsibility_duration and
            not self.current_state == "death" and (self.game.environment.current_time // 100) % 2 == 0)):
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
        
        self.render_charge_bar()
        self.game.screen.blit(image, (sprite_x, sprite_y))
        
    def shake_camera(self, intensity, duration):
        self.shake_intensity = intensity
        self.shake_duration = duration
        self.screen_shake_timer = duration

    def update_camera_shake(self):
        if self.screen_shake_timer > 0:
            decay = self.screen_shake_timer / self.shake_duration
            
            current_intensity = self.shake_intensity * decay
            
            time = self.game.environment.current_time / 100
            angle_x = time * 15
            angle_y = time * 13
            
            offset_x = math.sin(angle_x) * current_intensity
            offset_y = math.sin(angle_y) * current_intensity
            
            offset_x += (random.random() - 0.5) * current_intensity * 0.5
            offset_y += (random.random() - 0.5) * current_intensity * 0.5
            
            self.screen_shake_timer -= 1
            
            return (offset_x, offset_y)

        return (0, 0)

    def update_camera(self):
        if self.free_cam:
            return
        
        if self.enable_cam_mouse:
            mouse_dist_from_player_x = (pg.mouse.get_pos()[0] + self.cam_x) - self.x
            mouse_dist_from_player_y = (pg.mouse.get_pos()[1] + self.cam_y) - self.y
        
            target_cam_x = self.x - self.game.screen_width / 2 + mouse_dist_from_player_x * 0.1
            target_cam_y = self.y - self.game.screen_height / 1.5 + mouse_dist_from_player_y * 0.1
        
        else:
            target_cam_x = self.x - self.game.screen_width / 2
            target_cam_y = self.y - self.game.screen_height / 1.5

        base_cam_x = self.cam_x + (target_cam_x - self.cam_x) * self.camera_smoothing_factor
        base_cam_y = self.cam_y + (target_cam_y - self.cam_y) * self.camera_smoothing_factor

        base_cam_x = max(min(base_cam_x, target_cam_x + self.game.screen_width / 4), target_cam_x - self.game.screen_width / 4)
        base_cam_y = max(min(base_cam_y, target_cam_y + self.game.screen_height / 4), target_cam_y - self.game.screen_height / 7)

        shake_offset_x, shake_offset_y = self.update_camera_shake()
        self.cam_x = base_cam_x + shake_offset_x
        self.cam_y = base_cam_y + shake_offset_y

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

        hitbox_color = (0, 255, 0, 100)
        hitbox_surface = pg.Surface((self.hitbox_width, self.hitbox_height), pg.SRCALPHA)
        hitbox_surface.fill(hitbox_color)
        self.game.screen.blit(
            hitbox_surface,
            (self.hitbox.x - self.cam_x, self.hitbox.y - self.cam_y)
        )
    
    def render_map(self):
        if not self.in_map:
            self.game.ui.remove_ui_element("map_bg")
            self.map_surface = None
            return

        if not hasattr(self, "map_surface") or self.map_surface is None:
            self.map_surface = pg.Surface((self.game.screen_width, self.game.screen_height), pg.SRCALPHA)
        
        self.map_surface.fill((0, 0, 0, 0))
        
        overlay_surface = pg.Surface((self.game.screen_width, self.game.screen_height), pg.SRCALPHA)
        overlay_surface.fill((0, 0, 0, 150))
        self.map_surface.blit(overlay_surface, (0, 0))
        
        tile_pixel_size = max(1, int(self.map_scale_factor))
        center_pixel_x = self.game.screen_width // 2 + self.map_offset_x
        center_pixel_y = self.game.screen_height // 2 + self.map_offset_y
        
        visible_margin = 50
        min_pixel_x = -visible_margin
        max_pixel_x = self.game.screen_width + visible_margin
        min_pixel_y = -visible_margin
        max_pixel_y = self.game.screen_height + visible_margin
        
        map_tiles = self.game.map.tiles
        cached_tiles = getattr(self, "cached_tile_surfaces", {})
        
        sorted_tiles = sorted(map_tiles, key=lambda tile: tile.get("layer", 0))
        
        for current_tile in sorted_tiles:
            tile_pixel_x = center_pixel_x + current_tile.get("x", 0) * tile_pixel_size
            tile_pixel_y = center_pixel_y + current_tile.get("y", 0) * tile_pixel_size
            
            if not (min_pixel_x <= tile_pixel_x <= max_pixel_x and min_pixel_y <= tile_pixel_y <= max_pixel_y):
                continue
            
            cache_key = (current_tile.get("tilesheet", 0), current_tile.get("id"), current_tile.get("direction", 0), tile_pixel_size)
            
            if cache_key not in cached_tiles:
                tile_surface = self.get_tile_surface(current_tile, tile_pixel_size)
                if tile_surface:
                    cached_tiles[cache_key] = tile_surface
                    
                else:
                    continue
            
            tile_surface = cached_tiles[cache_key]
            
            tile_rect = tile_surface.get_rect(center=(tile_pixel_x, tile_pixel_y))
            self.map_surface.blit(tile_surface, tile_rect)
        
        map_bg_element = None
        
        for element in self.game.ui.ui_elements:
            if element.get("id") == "map_bg":
                map_bg_element = element
                break
        
        if map_bg_element:
            map_bg_element["original_image"] = self.map_surface
            map_bg_element["image"] = self.map_surface
            
        else:
            map_bg_element = {
                "id": "map_bg",
                "original_image": self.map_surface,
                "image": self.map_surface,
                "rect": self.map_surface.get_rect(topleft=(0, 0)),
                "render_order": -10,
                "alpha": True,
                "is_button": False
            }
            self.game.ui.ui_elements.append(map_bg_element)
        
        if len(cached_tiles) > 1000:
            self.cached_tile_surfaces = {}

    def create_map_tile(self, tile_data, tile_index, element_id, center_pixel_x, center_pixel_y, tile_pixel_size):
        tile_surface = self.get_tile_surface(tile_data, tile_pixel_size)
        if not tile_surface:
            return

        tile_pixel_x = center_pixel_x + tile_data.get("x", 0) * tile_pixel_size
        tile_pixel_y = center_pixel_y + tile_data.get("y", 0) * tile_pixel_size

        new_tile_element = {
            "id": element_id,
            "original_image": tile_surface,
            "image": tile_surface.copy(),
            "rect": tile_surface.get_rect(center=(tile_pixel_x, tile_pixel_y)),
            "render_order": 3 + tile_data.get("layer", 0),
            "alpha": True,
            "is_button": False,
            "centered": True,
            "x": tile_pixel_x,
            "y": tile_pixel_y,
            "width": tile_pixel_size,
            "height": tile_pixel_size,
            "direction": tile_data.get("direction", 0),
            "layer": tile_data.get("layer", 0)
        }

        self.game.ui.ui_elements.append(new_tile_element)

    def update_map_tile(self, element_data, tile_data, center_pixel_x, center_pixel_y, tile_pixel_size):
        tile_pixel_x = center_pixel_x + tile_data.get("x", 0) * tile_pixel_size
        tile_pixel_y = center_pixel_y + tile_data.get("y", 0) * tile_pixel_size

        current_element_width = element_data.get("width")
        current_element_height = element_data.get("height")
        current_element_direction = element_data.get("direction", 0)
        tile_direction = tile_data.get("direction", 0)

        if (element_data.get("x") != tile_pixel_x or
                element_data.get("y") != tile_pixel_y or
                current_element_width != tile_pixel_size or
                current_element_height != tile_pixel_size or
                current_element_direction != tile_direction):

            tile_surface = self.get_tile_surface(tile_data, tile_pixel_size)
            if tile_surface:
                element_data["original_image"] = tile_surface
                element_data["image"] = tile_surface.copy()

            element_data["x"] = tile_pixel_x
            element_data["y"] = tile_pixel_y
            element_data["width"] = tile_pixel_size
            element_data["height"] = tile_pixel_size
            element_data["direction"] = tile_direction
            element_data["layer"] = tile_data.get("layer", 0)
            element_data["rect"] = element_data["original_image"].get_rect(center=(tile_pixel_x, tile_pixel_y))

    def get_tile_surface(self, tile_data, tile_pixel_size):
        sheet_index = tile_data.get("tilesheet", 0)
        if sheet_index >= len(self.game.map.all_tile_surfaces):
            return None

        tilesheet = self.game.map.all_tile_surfaces[sheet_index]
        tile_id = tile_data.get("id")
        if tile_id is None or tile_id >= len(tilesheet["surfaces"]):
            return None

        tile_image = tilesheet["surfaces"][tile_id]
        tile_direction = tile_data.get("direction", 0)

        if tile_direction:
            tile_image = pg.transform.rotate(tile_image, tile_direction)

        if tile_image.get_size() != (tile_pixel_size, tile_pixel_size):
            tile_image = pg.transform.scale(tile_image, (tile_pixel_size, tile_pixel_size))
        
        return tile_image

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
            self.update_fall_shake()
            self.handle_gravity()
            self.update_collision()
            self.interact_hitbox()
            self.animate()
            self.render_inventory()
            self.render_map()
            self.update_pickup_tags()
            self.render_item_mouse()
            self.render_health()
            self.render_dialogue()
            self.render()
            self.render_hitboxes()
            self.handle_free_cam()
            self.load_weapon_animations()

        else:
            if hasattr(self, "settings_loaded"):
                del self.settings_loaded
