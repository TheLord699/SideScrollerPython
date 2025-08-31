import pygame as pg
import random
import math

class Soldier:
    def __init__(self, game):
        self.game = game
        
        self.load_settings()
        
    def load_settings(self):
        self.x = 0
        self.y = 900
        self.vel_x = 0
        self.vel_y = 0
        self.speed = 5 # 5
        self.gravity = 0.5 # 0.5
        self.jump_strength = -10
        self.friction = 0

        self.cam_x = self.x - self.game.screen_width / 2
        self.cam_y = self.y - self.game.screen_height / 1.5
        self.camera_speed = 10
        self.camera_smoothing_factor = 0.1
        self.camera_unlock_duration = 2
        self.camera_unlock_time = 0

        self.sheet_width = 100
        self.sheet_height = 100
        self.scale_factor = 3
        self.hitbox_width = 15 * self.scale_factor
        self.hitbox_height = 15 * self.scale_factor
        self.attack_hitbox_width = 30 * self.scale_factor
        self.attack_hitbox_height = 15 * self.scale_factor
        self.attack_hitbox_offset = 5
        self.hitbox = pg.Rect(self.x, self.y, self.hitbox_width, self.hitbox_height)
        self.attack_hitbox = pg.Rect(0, 0, self.attack_hitbox_width, self.attack_hitbox_height)

        self.attack_timeout = 30
        self.attack_sequence = 1
        self.attack_timer = 0
        
        self.max_inventory_slots = 10
        self.inventory = {}
        self.rendered_inventory_ui_elements = []
        self.inventory_x_offset = self.game.screen_width / 2.5
        self.inventory_y_offset = self.game.screen_height / 2.5
        self.items_per_row = 5
        self.item_spacing = 40
        self.selected_slot = None
        self.inventory_changed = False
        self.inventory_cooldown = 0
            
        self.max_health = 3
        self.current_health = self.max_health
        self.health_per_row = 10
        self.health_spacing = 35
        
        self.frame_delay = 5
        self.states = ["idle", "walking", "attacking1", "attacking2", "attacking3", "hurt", "death"]
        self.current_state = "idle"
        self.direction = "right"
        self.frames = {state: [] for state in self.states}
        self.current_frame = 0
        self.frame_count = 0
        self.state_frames = {
            "idle": 6,
            "walking": 8,
            "attacking1": 6,
            "attacking2": 6,
            "attacking3": 6,
            "hurt": 4,
            "death": 4
        }

        self.sprite_sheet = None
        self.attacking = False
        self.on_ground = False
        self.in_inventory = False
        
        self.load_frames()

    def load_frames(self):
        sprite_sheets = {} 
        for state, num_frames in self.state_frames.items():
            if state not in sprite_sheets:  
                sprite_sheets[state] = pg.image.load(f"assets/sprites/Soldier/{state}_animation.png").convert_alpha()
                
            sheet = sprite_sheets[state]
            for frame in range(num_frames):
                image = self.get_image(sheet, frame, self.sheet_width, self.sheet_height, self.sheet_width * self.scale_factor, self.sheet_height * self.scale_factor, (0, 0, 0))
                self.frames[state].append(image)

    def get_image(self, sheet, frame, width, height, new_w, new_h, color):
        image = pg.Surface((width, height), pg.SRCALPHA).convert_alpha()
        image.blit(sheet, (0, 0), ((frame * width), 0, width, height))
        image = pg.transform.scale(image, (new_w, new_h))
        image.set_colorkey(color)
        return image

    def checks(self):
        self.current_time = pg.time.get_ticks()
        
        self.current_health = math.floor(self.current_health * 2) / 2  
        self.current_health = min(self.current_health, self.max_health)

        self.x += self.vel_x
        self.y += self.vel_y
        
        self.attack_timer += 1

        if self.attack_timer > self.attack_timeout:
            self.attack_sequence = 1
        
        if self.current_health < 0.5 and not self.current_state in {"death"}:
            self.death()
        
        if self.current_state in {"death"} or getattr(self, "sliding", False):   
            if self.friction <= 0:
                self.friction = 0.05
                         
            if self.vel_x > 0:
                self.vel_x -= self.friction
            
            if self.vel_x < 0:
                self.vel_x += self.friction
            
            if self.vel_x < 0.5 and self.vel_x > 0:
                self.vel_x = 0
            
            if self.vel_x < -0.5 and self.vel_x > 0:
                self.vel_x = 0
        
    def death(self):
        self.current_state = "death"
        self.current_frame = 0
        self.frame_count = 0
        self.attacking = False
        self.in_inventory = False
    
    def render_health(self):
        previous_health = getattr(self, 'previous_health', self.current_health)

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
                image_path = "assets/sprites/ui/health/full.png"
                
            elif heart + 1 - self.current_health == 0.5:
                image_path = "assets/sprites/ui/health/half.png"
                
            else:
                image_path = "assets/sprites/ui/health/empty.png"

            self.game.ui.create_ui(
                image_path=image_path, 
                x=x_position, y=y_position, 
                centered=True, width=25, height=25, 
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
            if (inventory_item["name"] == item_name and
                inventory_item["type"] == item_type and
                inventory_item["value"] == item_value):
                inventory_item["quantity"] += item_quantity
                return

        for index in range(self.max_inventory_slots):
            if index not in self.inventory:
                self.inventory[index] = {
                    "name": item_name,
                    "quantity": item_quantity,
                    "type": item_type,
                    "value": item_value
                }
                return
    
    def render_item_info(self, id): # doesnt update amount in real time
        if hasattr(self, "last_rendered_item") and self.last_rendered_item:
            self.game.ui.remove_ui_element(self.last_rendered_item)
            self.game.ui.remove_ui_element("item_info")
            
        if not self.selected_slot == None:
            self.game.ui.create_ui(
                image_path=f"assets/sprites/ui/items/{self.inventory[id]["name"]}.png",
                x=150, y=250,
                centered=True, width=60, height=60,
                alpha=True,
                element_id=self.inventory[id]["name"],
                render_order=0
            )
            self.game.ui.create_ui(
                x=120, y=270,
                centered=True, width=60, height=60,
                element_id="item_info",
                render_order=1,
                label=f"{self.inventory[id]["name"]} x{self.inventory[id]["quantity"]}"
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
                image_path=f"assets/sprites/ui/slot.png", 
                x=x_position, y=y_position, 
                centered=True, width=30, height=30, 
                alpha=False, is_button=True, 
                element_id=slot_element_id,
                scale_multiplier=1, 
                callback=lambda id=slot: (self.on_inventory_click(id), self.render_item_info(id) if id in self.inventory else None),
                is_hold=False,
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

                item_element_id = f"item:{item['name']}"
                self.game.ui.create_ui(
                    image_path=f"assets/sprites/ui/items/{item['name']}.png", 
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
        if self.selected_slot is None and slot in self.inventory and (self.current_time - self.inventory_cooldown >= 150):
            self.selected_slot = slot
            self.render_item_info(slot)
            
        elif self.selected_slot == slot and (self.current_time - self.inventory_cooldown >= 150):
            self.selected_slot = None
            self.render_inventory() 
            self.inventory_cooldown = self.current_time  
            
        elif self.selected_slot is not None and slot != self.selected_slot and (self.current_time - self.inventory_cooldown >= 150):
            if slot in self.inventory:
                self.inventory[self.selected_slot], self.inventory[slot] = self.inventory[slot], self.inventory[self.selected_slot]
                
            else:
                self.inventory[slot] = self.inventory.pop(self.selected_slot)

            self.refresh_inventory()
            self.selected_slot = None  
            self.inventory_changed = True
            self.inventory_cooldown = self.current_time
    
    def hitbox_set(self):
        self.hitbox = pg.Rect(
            self.x - self.hitbox_width / 2,
            self.y - self.hitbox_height / 2,
            self.hitbox_width,
            self.hitbox_height
        )
        
    def update_collision(self):
        self.hitbox_set()

        # Iterate over all tiles to check for collisions
        for index, tile_hitbox in enumerate(self.game.map.tile_hitboxes):
            tile_id = self.game.map.tile_id[index]
            tile_attributes = self.game.map.tile_attributes.get(tile_id, {})

            swimmable = tile_attributes.get("swimmable", False)
            slippy = tile_attributes.get("slippy", False)
            friction = tile_attributes.get("friction", 0)
            damage = tile_attributes.get("damage", 0)

            step = max(1, min(5, int(abs(self.vel_y) / 2)))  # Adjusts step size dynamically

            # Check vertical collisions (gravity)
            for i in range(0, int(abs(self.vel_y)) + 1, step):
                test_y = self.y + math.copysign(i, self.vel_y)
                test_hitbox = pg.Rect(self.hitbox.x, test_y, self.hitbox_width, self.hitbox_height / 2)

                if test_hitbox.colliderect(tile_hitbox):
                    if swimmable:
                        self.vel_y *= 0.3  # Slow down fall speed in water
                    elif slippy:
                        self.friction = friction
                        self.sliding = True

                    if damage > 0:
                        self.current_health -= damage

                    # Adjust the player's position to be just above the tile (ground level)
                    if self.vel_y > 0 and not swimmable:
                        self.y = tile_hitbox.top - self.hitbox.height / 2  # Precise ground level
                        self.vel_y = 0
                        self.on_ground = True

                        if not slippy:
                            self.sliding = False
                        return  # Stop moving further if we've hit the ground

            # Check horizontal collisions (walking into walls)
            if self.hitbox.colliderect(tile_hitbox):
                overlap_x = min(self.hitbox.right - tile_hitbox.left, tile_hitbox.right - self.hitbox.left)
                overlap_y = min(self.hitbox.bottom - tile_hitbox.top, tile_hitbox.bottom - self.hitbox.top)

                if overlap_x < overlap_y:  # Horizontal collision (left-right)
                    if swimmable:
                        continue  # Skip if the tile is swimmable, let the player "swim" through

                    # Move the player horizontally, pushing them out of the tile
                    if self.hitbox.centerx < tile_hitbox.centerx:
                        self.x -= overlap_x  # Moving left
                    else:
                        self.x += overlap_x  # Moving right

                    self.hitbox_set()  # Update the hitbox after moving
                    self.vel_x = 0  # Stop horizontal velocity to prevent sliding

                else:  # Vertical collision (up-down)
                    if self.hitbox.centery < tile_hitbox.centery:
                        # Player is colliding with the bottom of the tile (falling)
                        pass
                    else:
                        # Player is colliding with the top of the tile (hitting the ceiling)
                        self.y += overlap_y  # Move the player down (but not up!)
                        self.vel_y = 0  # Stop downward velocity

        # Reset movement flags
        self.hitbox_set()


    def animate(self):
        previous_state = self.current_state

        if not self.current_state == "death":
            if self.attacking:
                self.current_state = f"attacking{self.attack_sequence}"

            elif self.vel_x != 0:
                self.current_state = "walking"

            else:
                self.current_state = "idle"

        if self.current_state == "death":
            if self.current_frame == len(self.frames[self.current_state]) - 1:
                self.current_frame = len(self.frames[self.current_state]) - 1
                self.frame_count = 0

        if self.current_state != previous_state:
            self.current_frame = 0
            self.frame_count = 0
            
        self.frame_count += 1
        if self.frame_count >= self.frame_delay:
            self.frame_count = 0
            self.current_frame = (self.current_frame + 1) % len(self.frames[self.current_state])

        if self.current_state.startswith("attacking") and self.current_frame == len(self.frames[self.current_state]) - 1:
            self.attacking = False
            self.attack_sequence = (self.attack_sequence % 2) + 1

    def handle_gravity(self):
        self.on_ground = False
        self.vel_y += self.gravity 

        max_fall_speed = 20
        self.vel_y = min(self.vel_y, max_fall_speed)

    def handle_controls(self):
        keys = pg.key.get_pressed()

        if not self.current_state in {"death"}:
            if not self.in_inventory:
                if getattr(self, "sliding", False):
                        if keys[pg.K_a]:
                            self.vel_x = -self.speed 
                            self.direction = "left"
                            
                        elif keys[pg.K_d]:
                            self.vel_x = self.speed 
                            self.direction = "right"
                    
                else:
                    self.vel_x = -self.speed if keys[pg.K_a] else self.speed if keys[pg.K_d] else 0
                    self.direction = "left" if keys[pg.K_a] else "right" if keys[pg.K_d] else self.direction

                if keys[pg.K_w] and self.on_ground:
                    self.vel_y = self.jump_strength

                if keys[pg.K_SPACE]:
                    self.start_attack()
            
            elif not getattr(self, "sliding", False):
                self.vel_x = 0
            
            for event in self.game.events: # for specified controls
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_e: 
                        self.in_inventory = not self.in_inventory
                    
                    if event.key == pg.K_f: 
                        self.add_item_to_inventory({"name": "Potion", "quantity": 3, "type": "health", "value": 50})
                    
                    if event.key == pg.K_g: 
                        self.add_item_to_inventory({"name": "Test", "quantity": 3, "type": "health", "value": 50})
                    
                    if event.key == pg.K_k:
                        self.vel_y += -10
                    
    def start_attack(self):
        if not self.attacking:
            self.attacking = True
            self.current_frame = 0
            self.attack_timer = 0
            attack = random.randint(1, 2)
            pg.mixer.Sound(f"assets/sounds/attack/swing{attack}.wav").play().set_volume(self.game.volume) # temporary

    def update_attack_hitbox(self):
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

        sprite_x = self.hitbox.centerx - self.cam_x - image.get_width() // 2
        sprite_y = self.hitbox.centery - self.cam_y + 2 - image.get_height() // 2 # 2 cuz feet visually not touching ground
        
        self.game.screen.blit(image, (sprite_x, sprite_y))

    def update_camera(self):
        # can change the target here
        target_cam_x = self.x - self.game.screen_width / 2
        target_cam_y = self.y - self.game.screen_height / 1.5

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
        if self.game.environment.menu == "play":
            if not hasattr(self, "settings_loaded") or not self.settings_loaded:
                self.load_settings()
                self.settings_loaded = True 
            
            self.update_camera()
            self.handle_controls()
            self.checks()
            self.handle_gravity()
            self.update_collision()
            self.animate()
            self.update_attack_hitbox()
            self.render_inventory()
            # self.render_hitboxes()
            self.render_health()
            self.render()
            
        else:
            if hasattr(self, "settings_loaded"):
                del self.settings_loaded
