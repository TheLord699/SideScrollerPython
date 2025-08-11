import pygame as pg
import math
import random
import json
import os

class Vehicle:
    def __init__(self, game, vehicle_type, x, y, properties=None):
        self.game = game
        self.type = vehicle_type  # "ground" or "flight"
        self.x = x
        self.y = y
        self.scale = self.game.environment.scale
        
        # Default properties that can be overridden
        self.default_properties = {
            "ground": {
                "width": 60,
                "height": 30,
                "max_speed": 15,
                "acceleration": 0.5,
                "deceleration": 0.7,
                "turn_rate": 2.5,
                "traction": 0.9,
                "drift_factor": 0.6,
                "boost_power": 3,
                "boost_duration": 1000,
                "boost_cooldown": 3000,
                "health": 100,
                "mass": 2.0,
                "sprite": None,
                "engine_sound": None,
                "boost_sound": None,
                "collision_sound": None
            },
            "flight": {
                "width": 50,
                "height": 40,
                "max_speed": 20,
                "acceleration": 0.3,
                "vertical_acceleration": 0.4,
                "deceleration": 0.2,
                "turn_rate": 1.8,
                "max_altitude": 500,
                "min_altitude": 50,
                "lift": 0.15,
                "health": 80,
                "mass": 1.5,
                "sprite": None,
                "engine_sound": None,
                "boost_sound": None,
                "collision_sound": None
            }
        }
        
        # Override defaults with provided properties
        self.properties = self.default_properties[self.type].copy()
        if properties:
            self.properties.update(properties)
        
        # Physics state
        self.velocity_x = 0
        self.velocity_y = 0
        self.direction = 0  # Angle in degrees (0 = right, 90 = up)
        self.speed = 0
        self.angular_velocity = 0
        self.boost_timer = 0
        self.boost_cooldown = 0
        self.health = self.properties["health"]
        self.damage_timer = 0
        
        # Control state
        self.occupied = False
        self.occupant = None
        self.controls = {
            "throttle": False,
            "brake": False,
            "left": False,
            "right": False,
            "up": False,
            "down": False,
            "boost": False,
            "exit": False
        }
        
        # Visuals
        self.sprite = None
        if self.properties["sprite"]:
            self.load_sprite(self.properties["sprite"])
        
        # Sounds
        self.sounds = {
            "engine": None,
            "boost": None,
            "collision": None
        }
        self.load_sounds()
        
        # Particles
        self.exhaust_particles = []
        self.skid_particles = []
        self.last_particle_time = 0
        
        # Collision
        self.hitbox = pg.Rect(
            self.x - self.properties["width"] / 2,
            self.y - self.properties["height"] / 2,
            self.properties["width"],
            self.properties["height"]
        )
        
    def load_sprite(self, sprite_path):
        try:
            self.sprite = pg.image.load(sprite_path).convert_alpha()
            self.sprite = pg.transform.scale(
                self.sprite, 
                (int(self.properties["width"] * self.scale), 
                 int(self.properties["height"] * self.scale))
            )
        except:
            # Fallback to a colored rectangle if sprite fails to load
            self.sprite = None
    
    def load_sounds(self):
        if self.properties["engine_sound"]:
            try:
                self.sounds["engine"] = pg.mixer.Sound(self.properties["engine_sound"])
                self.sounds["engine"].set_volume(self.game.environment.volume / 10)
            except:
                pass
                
        if self.properties["boost_sound"]:
            try:
                self.sounds["boost"] = pg.mixer.Sound(self.properties["boost_sound"])
                self.sounds["boost"].set_volume(self.game.environment.volume / 10)
            except:
                pass
                
        if self.properties["collision_sound"]:
            try:
                self.sounds["collision"] = pg.mixer.Sound(self.properties["collision_sound"])
                self.sounds["collision"].set_volume(self.game.environment.volume / 10)
            except:
                pass
    
    def enter(self, player):
        if not self.occupied:
            self.occupied = True
            self.occupant = player
            player.in_vehicle = self
            player.visible = False
            
            # Position player at vehicle center
            player.x = self.x
            player.y = self.y
            
            # Play engine sound
            if self.sounds["engine"]:
                self.sounds["engine"].play(loops=-1)
    
    def exit(self):
        if self.occupied:
            player = self.occupant
            player.in_vehicle = None
            player.visible = True
            
            # Position player near vehicle
            exit_offset = max(self.properties["width"], self.properties["height"]) + 10
            angle_rad = math.radians(self.direction)
            player.x = self.x + math.cos(angle_rad) * exit_offset
            player.y = self.y - math.sin(angle_rad) * exit_offset
            
            self.occupied = False
            self.occupant = None
            
            # Stop engine sound
            if self.sounds["engine"]:
                self.sounds["engine"].stop()
    
    def update_controls(self, events):
        if not self.occupied:
            return
            
        # Reset control states
        for key in self.controls:
            self.controls[key] = False
            
        # Check keyboard controls
        keys = pg.key.get_pressed()
        
        # Different control schemes for different vehicle types
        if self.type == "ground":
            self.controls["throttle"] = keys[pg.K_w] or keys[pg.K_UP]
            self.controls["brake"] = keys[pg.K_s] or keys[pg.K_DOWN]
            self.controls["left"] = keys[pg.K_a] or keys[pg.K_LEFT]
            self.controls["right"] = keys[pg.K_d] or keys[pg.K_RIGHT]
            self.controls["boost"] = keys[pg.K_LSHIFT]
            self.controls["exit"] = keys[pg.K_e]
            
        elif self.type == "flight":
            self.controls["throttle"] = keys[pg.K_w]
            self.controls["brake"] = keys[pg.K_s]
            self.controls["left"] = keys[pg.K_a]
            self.controls["right"] = keys[pg.K_d]
            self.controls["up"] = keys[pg.K_UP] or keys[pg.K_SPACE]
            self.controls["down"] = keys[pg.K_DOWN] or keys[pg.K_LCTRL]
            self.controls["boost"] = keys[pg.K_LSHIFT]
            self.controls["exit"] = keys[pg.K_e]
            
        # Check joystick controls if available
        joystick = self.game.environment.joystick
        if joystick:
            # Left stick for movement
            axis_x = joystick.get_axis(0)
            axis_y = joystick.get_axis(1)
            
            if abs(axis_x) > 0.1:
                if axis_x < 0:
                    self.controls["left"] = True
                else:
                    self.controls["right"] = True
                    
            if abs(axis_y) > 0.1:
                if axis_y < 0:
                    if self.type == "ground":
                        self.controls["throttle"] = True
                    else:
                        self.controls["up"] = True
                else:
                    if self.type == "ground":
                        self.controls["brake"] = True
                    else:
                        self.controls["down"] = True
            
            # Buttons
            self.controls["boost"] = joystick.get_button(4) or joystick.get_button(5)  # LB or RB
            self.controls["exit"] = joystick.get_button(1)  # B button
            
        # Handle exit
        for event in events:
            if event.type == pg.KEYDOWN and event.key == pg.K_e:
                self.controls["exit"] = True
            elif event.type == pg.JOYBUTTONDOWN and event.button == 1:
                self.controls["exit"] = True
                
        if self.controls["exit"]:
            self.exit()
    
    def update_physics(self):
        # Apply different physics based on vehicle type
        if self.type == "ground":
            self.update_ground_physics()
        elif self.type == "flight":
            self.update_flight_physics()
        
        # Gravity for ground vehicles if not on ground
        if self.type == "ground":
            if not getattr(self, "on_ground", False):
                self.velocity_y += 0.5  # Gravity
            else:
                self.velocity_y = 0  # Reset vertical velocity when on ground

        # Prevent horizontal drift when falling and not pressing throttle/brake
        if self.type == "ground" and not getattr(self, "on_ground", False) and not (self.controls["throttle"] or self.controls["brake"]):
            self.velocity_x *= 0.95  # Dampen horizontal velocity when airborne

        # Apply velocity
        self.x += self.velocity_x
        self.y += self.velocity_y
        
        # Update direction based on angular velocity
        self.direction += self.angular_velocity
        self.direction %= 360  # Keep within 0-360 degrees
        
        # Update hitbox position
        self.hitbox.x = self.x - self.properties["width"] / 2
        self.hitbox.y = self.y - self.properties["height"] / 2
        
        # Update boost timers
        if self.boost_timer > 0:
            self.boost_timer -= self.game.delta_time
            if self.boost_timer <= 0:
                self.boost_cooldown = self.properties["boost_cooldown"]
                
        if self.boost_cooldown > 0:
            self.boost_cooldown -= self.game.delta_time
            
        # Update damage timer
        if self.damage_timer > 0:
            self.damage_timer -= self.game.delta_time
            
        # Generate particles
        self.generate_particles()
    
    def update_ground_physics(self):
        # Calculate current speed
        self.speed = math.sqrt(self.velocity_x**2 + self.velocity_y**2)
        
        # Handle acceleration/deceleration
        if self.controls["throttle"]:
            # Accelerate in current direction
            acceleration = self.properties["acceleration"]
            if self.controls["boost"] and self.boost_cooldown <= 0 and self.boost_timer <= 0:
                acceleration *= self.properties["boost_power"]
                self.boost_timer = self.properties["boost_duration"]
                if self.sounds["boost"]:
                    self.sounds["boost"].play()
            
            angle_rad = math.radians(self.direction)
            self.velocity_x += math.cos(angle_rad) * acceleration
            self.velocity_y -= math.sin(angle_rad) * acceleration
            
        elif self.controls["brake"]:
            # Decelerate
            deceleration = self.properties["deceleration"]
            self.velocity_x *= (1 - deceleration)
            self.velocity_y *= (1 - deceleration)
            
        # Handle turning
        if self.speed > 0.1:  # Only turn when moving
            turn_rate = self.properties["turn_rate"]
            
            if self.controls["left"]:
                self.angular_velocity = -turn_rate * (1 if self.speed < 5 else 5/self.speed)
            elif self.controls["right"]:
                self.angular_velocity = turn_rate * (1 if self.speed < 5 else 5/self.speed)
            else:
                self.angular_velocity = 0
                
            # Apply traction/drifting
            current_angle = math.degrees(math.atan2(-self.velocity_y, self.velocity_x)) % 360
            angle_diff = (current_angle - self.direction) % 360
            if angle_diff > 180:
                angle_diff -= 360
                
            traction = self.properties["traction"]
            if abs(angle_diff) > 30:  # Drifting condition
                traction *= self.properties["drift_factor"]
                
            # Adjust velocity toward facing direction
            target_vel_x = math.cos(math.radians(self.direction)) * self.speed
            target_vel_y = -math.sin(math.radians(self.direction)) * self.speed
            self.velocity_x += (target_vel_x - self.velocity_x) * traction
            self.velocity_y += (target_vel_y - self.velocity_y) * traction
            
        # Apply friction
        self.velocity_x *= 0.98
        self.velocity_y *= 0.98
        
        # Limit speed
        max_speed = self.properties["max_speed"]
        if self.boost_timer > 0:
            max_speed *= 1.5
    def update_flight_physics(self):
        # Handle forward/backward movement
        if self.controls["throttle"]:
            acceleration = self.properties["acceleration"]
            if self.controls["boost"] and self.boost_cooldown <= 0 and self.boost_timer <= 0:
                acceleration *= 2
                self.boost_timer = self.properties["boost_duration"]
                if self.sounds["boost"]:
                    self.sounds["boost"].play()
                    
            angle_rad = math.radians(self.direction)
            self.velocity_x += math.cos(angle_rad) * acceleration
            self.velocity_y -= math.sin(angle_rad) * acceleration
            
        elif self.controls["brake"]:
            deceleration = self.properties["deceleration"]
            self.velocity_x *= (1 - deceleration)
            self.velocity_y *= (1 - deceleration)
            
        # Handle turning
        turn_rate = self.properties["turn_rate"]
        if self.controls["left"]:
            self.angular_velocity = -turn_rate
        elif self.controls["right"]:
            self.angular_velocity = turn_rate
        else:
            self.angular_velocity = 0
            
        # Handle vertical movement (up/down)
        vertical_accel = self.properties["vertical_acceleration"]
        if self.controls["up"]:
            self.velocity_y -= vertical_accel
        elif self.controls["down"]:
            self.velocity_y += vertical_accel

        # Only apply lift if throttle or up is pressed (prevents flying up on spawn)
        if self.controls["throttle"] or self.controls["up"]:
            self.velocity_y -= self.properties["lift"]
        
        # Apply air resistance
        self.velocity_x *= 0.995
        self.velocity_y *= 0.995
        
        # Limit speed
        max_speed = self.properties["max_speed"]
        if self.boost_timer > 0:
            max_speed *= 1.8
            
        current_speed = math.sqrt(self.velocity_x**2 + self.velocity_y**2)
        if current_speed > max_speed:
            scale = max_speed / current_speed
            self.velocity_x *= scale
            self.velocity_y *= scale
            
        # Limit altitude
        if self.y < self.properties["min_altitude"]:
            self.y = self.properties["min_altitude"]
            self.velocity_y = max(0, self.velocity_y)
        elif self.y > self.properties["max_altitude"]:
            self.y = self.properties["max_altitude"]
            self.velocity_y = min(0, self.velocity_y)
        # Limit altitude
        if self.y < self.properties["min_altitude"]:
            self.y = self.properties["min_altitude"]
            self.velocity_y = max(0, self.velocity_y)
        elif self.y > self.properties["max_altitude"]:
            self.y = self.properties["max_altitude"]
            self.velocity_y = min(0, self.velocity_y)
    
    def generate_particles(self):
        current_time = pg.time.get_ticks()
        if current_time - self.last_particle_time < 50:  # Limit particle generation rate
            return
            
        self.last_particle_time = current_time
        
        # Different particles for different vehicle types and states
        if self.type == "ground":
            # Exhaust particles when accelerating
            if self.controls["throttle"] and self.speed > 0.5:
                angle_rad = math.radians(self.direction + 180)  # Opposite of facing direction
                offset_x = math.cos(math.radians(self.direction)) * -self.properties["width"] / 2
                offset_y = -math.sin(math.radians(self.direction)) * -self.properties["width"] / 2
                
                for _ in range(2):
                    speed_variation = random.uniform(0.5, 1.5)
                    particle_speed = self.speed * 0.3 * speed_variation
                    vel_x = math.cos(angle_rad + random.uniform(-0.2, 0.2)) * particle_speed
                    vel_y = -math.sin(angle_rad + random.uniform(-0.2, 0.2)) * particle_speed
                    
                    self.game.particles.generate(
                        pos=(self.x + offset_x, self.y + offset_y),
                        velocity=(vel_x, vel_y),
                        color=(random.randint(150, 255), random.randint(50, 150), 0),
                        radius=random.randint(2, 4),
                        lifespan=random.randint(20, 40),
                        fade=True
                    )
            
            # Skid particles when turning sharply
            if abs(self.angular_velocity) > 1.5 and self.speed > 3:
                side = -1 if self.angular_velocity > 0 else 1
                angle_rad = math.radians(self.direction + 90 * side)
                
                for _ in range(3):
                    offset_x = math.cos(math.radians(self.direction)) * random.uniform(-10, 10)
                    offset_y = -math.sin(math.radians(self.direction)) * random.uniform(-10, 10)
                    
                    vel_x = math.cos(angle_rad) * random.uniform(0.5, 1.5)
                    vel_y = -math.sin(angle_rad) * random.uniform(0.5, 1.5)
                    
                    self.game.particles.generate(
                        pos=(self.x + offset_x, self.y + offset_y),
                        velocity=(vel_x, vel_y),
                        color=(100, 100, 100),
                        radius=random.randint(1, 3),
                        lifespan=random.randint(30, 60),
                        fade=True
                    )
                    
        elif self.type == "flight":
            # Engine exhaust particles
            if self.speed > 0.5 or abs(self.velocity_y) > 0.5:
                angle_rad = math.radians(self.direction + 180)  # Opposite of facing direction
                offset_x = math.cos(math.radians(self.direction)) * -self.properties["width"] / 2
                offset_y = -math.sin(math.radians(self.direction)) * -self.properties["width"] / 2
                
                for _ in range(3):
                    speed_variation = random.uniform(0.8, 1.2)
                    vel_x = math.cos(angle_rad + random.uniform(-0.1, 0.1)) * speed_variation
                    vel_y = -math.sin(angle_rad + random.uniform(-0.1, 0.1)) * speed_variation
                    
                    # Adjust for vertical movement
                    if self.velocity_y < 0:  # Moving up
                        vel_y -= random.uniform(0, 0.5)
                    elif self.velocity_y > 0:  # Moving down
                        vel_y += random.uniform(0, 0.5)
                        
                    color = (random.randint(200, 255), random.randint(100, 200), 0)
                    if self.boost_timer > 0:
                        color = (255, random.randint(150, 255), random.randint(0, 100))
                        
                    self.game.particles.generate(
                        pos=(self.x + offset_x, self.y + offset_y),
                        velocity=(vel_x, vel_y),
                        color=color,
                        radius=random.randint(2, 5),
                        lifespan=random.randint(30, 50),
                        fade=True
                    )
        
    def check_collisions(self):
        # Reset ground state before checking collisions
        self.on_ground = False
        
        # Get nearby tiles for collision checking
        nearby_tiles = self.game.map.get_nearby_tiles(self.hitbox)
        
        # Check collision with terrain tiles
        for tile_hitbox, tile_id in nearby_tiles:
            tile_attributes = self.game.map.tile_attributes.get(tile_id, {})
            
            # Skip if tile is marked as non-collidable
            if tile_attributes.get("non_collidable", False):
                continue
                
            if self.hitbox.colliderect(tile_hitbox):
                self.handle_tile_collision(tile_hitbox, tile_attributes)
        
        # Check collision with other entities
        for entity in self.game.entities.entities:
            if hasattr(entity, "hitbox") and entity != self and self.hitbox.colliderect(entity.hitbox):
                self.handle_entity_collision(entity)

    def handle_tile_collision(self, tile_hitbox, tile_attributes):
        # Calculate overlap in both axes
        overlap_x = min(self.hitbox.right - tile_hitbox.left, 
                    tile_hitbox.right - self.hitbox.left)
        overlap_y = min(self.hitbox.bottom - tile_hitbox.top, 
                    tile_hitbox.bottom - self.hitbox.top)
        
        # Determine which axis has the smallest overlap (shallowest collision)
        if overlap_x < overlap_y:
            # Horizontal collision
            if self.hitbox.centerx < tile_hitbox.centerx:
                # Collision from left
                self.x -= overlap_x
            else:
                # Collision from right
                self.x += overlap_x
            
            # Bounce off horizontally
            self.velocity_x *= -0.5
            
            # Stop horizontal movement if overlap was very small
            if overlap_x < 2:
                self.velocity_x = 0
        else:
            # Vertical collision
            if self.hitbox.centery < tile_hitbox.centery:
                # Collision from top (landing on something)
                self.y -= overlap_y
                self.on_ground = True
                
                # Only bounce if falling fast enough
                if self.velocity_y > 2:
                    self.velocity_y *= -0.4
                else:
                    self.velocity_y = 0
            else:
                # Collision from bottom (hitting head)
                self.y += overlap_y
                self.velocity_y *= -0.3
        
        # Update hitbox position after collision resolution
        self.hitbox.x = self.x - self.properties["width"] / 2
        self.hitbox.y = self.y - self.properties["height"] / 2
        
        # Apply damage if tile is damaging and we're moving fast enough
        collision_speed = math.sqrt(self.velocity_x**2 + self.velocity_y**2)
        damage = tile_attributes.get("damage", 0)
        
        if damage > 0 and collision_speed > 3 and self.damage_timer <= 0:
            self.take_damage(damage * collision_speed)

    def handle_entity_collision(self, entity):
        # Calculate overlap in both axes
        overlap_x = min(self.hitbox.right - entity.hitbox.left, 
                    entity.hitbox.right - self.hitbox.left)
        overlap_y = min(self.hitbox.bottom - entity.hitbox.top, 
                    entity.hitbox.bottom - self.hitbox.top)
        
        # Resolve collision based on smallest overlap
        if overlap_x < overlap_y:
            if self.hitbox.centerx < entity.hitbox.centerx:
                self.x -= overlap_x / 2
            else:
                self.x += overlap_x / 2
            self.velocity_x *= -0.5
        else:
            if self.hitbox.centery < entity.hitbox.centery:
                self.y -= overlap_y / 2
            else:
                self.y += overlap_y / 2
            self.velocity_y *= -0.5
        
        # Apply damage based on speed
        collision_speed = math.sqrt(self.velocity_x**2 + self.velocity_y**2)
        if collision_speed > 3 and self.damage_timer <= 0:
            damage = collision_speed * 2
            self.take_damage(damage)
            
            # Also damage the other entity if it can take damage
            if hasattr(entity, "take_damage"):
                entity.take_damage(damage)

    def take_damage(self, amount):
        if self.damage_timer <= 0:
            self.health -= amount
            self.damage_timer = 1000  # 1 second invulnerability
            
            # Play collision sound if available
            if self.sounds["collision"]:
                self.sounds["collision"].play()
                
            # Generate collision particles
            for _ in range(int(amount)):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(0.5, 2)
                self.game.particles.generate(
                    pos=(self.x, self.y),
                    velocity=(math.cos(angle) * speed, -math.sin(angle) * speed),
                    color=(200, 50, 50),
                    radius=random.randint(2, 4),
                    lifespan=random.randint(30, 60),
                    fade=True
                )
            
            # Check if vehicle is destroyed
            if self.health <= 0:
                self.destroy()
        
    def destroy(self):
        # Explosion effect
        for _ in range(30):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 5)
            self.game.particles.generate(
                pos=(self.x, self.y),
                velocity=(math.cos(angle) * speed, -math.sin(angle) * speed),
                color=(255, random.randint(100, 200), 0),
                radius=random.randint(3, 6),
                lifespan=random.randint(40, 80),
                fade=True
            )
        
        # Eject player if occupied
        if self.occupied:
            self.exit()
            
        # Remove vehicle from game
        if hasattr(self.game, "vehicles") and self in self.game.vehicles:
            self.game.vehicles.remove(self)
    
    def render(self):
        # Draw vehicle sprite or fallback shape
        if self.sprite:
            # Rotate sprite based on direction
            rotated_sprite = pg.transform.rotate(self.sprite, self.direction)
            sprite_rect = rotated_sprite.get_rect(center=(self.x - self.game.player.cam_x, 
                                                         self.y - self.game.player.cam_y))
            self.game.screen.blit(rotated_sprite, sprite_rect)
        else:
            # Fallback: Draw a colored rectangle with direction indicator
            color = (0, 100, 255) if self.type == "flight" else (100, 200, 0)
            if self.occupied:
                color = (200, 100, 0)
                
            # Main body
            pg.draw.rect(self.game.screen, color, (
                self.x - self.properties["width"] / 2 - self.game.player.cam_x,
                self.y - self.properties["height"] / 2 - self.game.player.cam_y,
                self.properties["width"],
                self.properties["height"]
            ))
            
            # Direction indicator
            angle_rad = math.radians(self.direction)
            pg.draw.line(self.game.screen, (255, 255, 255), 
                (self.x - self.game.player.cam_x, self.y - self.game.player.cam_y),
                (self.x + math.cos(angle_rad) * self.properties["width"] / 2 - self.game.player.cam_x,
                 self.y - math.sin(angle_rad) * self.properties["width"] / 2 - self.game.player.cam_y),
                3)
        
        # Draw health bar if damaged
        if self.health < self.properties["health"]:
            health_width = 40
            health_height = 5
            health_ratio = self.health / self.properties["health"]
            
            pg.draw.rect(self.game.screen, (50, 50, 50), (
                self.x - health_width / 2 - self.game.player.cam_x,
                self.y - self.properties["height"] / 2 - 10 - self.game.player.cam_y,
                health_width,
                health_height
            ))
            
            pg.draw.rect(self.game.screen, (0, 255, 0), (
                self.x - health_width / 2 - self.game.player.cam_x,
                self.y - self.properties["height"] / 2 - 10 - self.game.player.cam_y,
                health_width * health_ratio,
                health_height
            ))
        
        # Draw boost indicator if on cooldown
        if self.boost_cooldown > 0:
            boost_width = 30
            boost_height = 3
            boost_ratio = 1 - (self.boost_cooldown / self.properties["boost_cooldown"])
            
            pg.draw.rect(self.game.screen, (50, 50, 50), (
                self.x - boost_width / 2 - self.game.player.cam_x,
                self.y + self.properties["height"] / 2 + 5 - self.game.player.cam_y,
                boost_width,
                boost_height
            ))
            
            pg.draw.rect(self.game.screen, (0, 150, 255), (
                self.x - boost_width / 2 - self.game.player.cam_x,
                self.y + self.properties["height"] / 2 + 5 - self.game.player.cam_y,
                boost_width * boost_ratio,
                boost_height
            ))
    
    def update(self, events):
        if self.occupied:
            self.update_controls(events)
            
        self.update_physics()
        self.check_collisions()

class VehicleManager:
    def __init__(self, game):
        self.game = game
        self.vehicles = []
        
        # Load vehicle definitions from JSON
        self.load_vehicle_definitions()
        
    def load_vehicle_definitions(self):
        try:
            with open(os.path.join("assets", "settings", "vehicles.json"), "r") as file:
                self.vehicle_definitions = json.load(file)
        except:
            self.vehicle_definitions = {
                "basic_car": {
                    "type": "ground",
                    "width": 60,
                    "height": 30,
                    "max_speed": 12,
                    "acceleration": 0.4,
                    "turn_rate": 2.0,
                    "sprite": "assets/sprites/vehicles/basic_car.png"
                },
                "hover_bike": {
                    "type": "flight",
                    "width": 40,
                    "height": 30,
                    "max_speed": 18,
                    "acceleration": 0.3,
                    "turn_rate": 3.0,
                    "sprite": "assets/sprites/vehicles/hover_bike.png"
                }
            }
    
    def create_vehicle(self, vehicle_type, x, y):
        if vehicle_type in self.vehicle_definitions:
            properties = self.vehicle_definitions[vehicle_type]
            vehicle = Vehicle(self.game, properties["type"], x, y, properties)
            self.vehicles.append(vehicle)
            return vehicle
        return None
    
    def update(self):
        self.render()
        for vehicle in self.vehicles[:]:  # Create a copy for iteration
            vehicle.update(self.game.events)
            
            # Remove destroyed vehicles
            if hasattr(vehicle, "health") and vehicle.health <= 0:
                self.vehicles.remove(vehicle)
    
    def render(self):
        for vehicle in self.vehicles:
            vehicle.render()