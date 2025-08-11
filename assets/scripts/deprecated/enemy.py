import pygame as pg
import random
import math

class Enemy:
  def __init__(self, game):
    self.game = game
    self.screen_width = self.game.screen_width
    self.screen_height = self.game.screen_height

    self.enemy_list = []

    self.x = 0
    self.y = 0

    self.animate_start_time = pg.time.get_ticks()

    self.frame = 0
    self.direction = "down"

    self.invulnerable = False

    self.enemy_dict = {
      "bug": {
        "health": 3,
        "speed": 3,
        "sprite": "assets/sprites/enemy/bug.png",
        "invulnerable_time": 1000,
        "damage": 1,
        "size": (50, 50),
        "ai": "chase",
      },
      "goblin": {
        "health": 5,
        "speed": 4,
        "sprite": "assets/sprites/enemy/goblin.png",
        "invulnerable_time": 1500,
        "damage": 2,
        "size": (60, 60),
        "ai": "random", 
      },
    }

  def load_enemy(self, enemy_type, x, y):
    if enemy_type in self.enemy_dict:
      enemy_stats = self.enemy_dict[enemy_type]
      new_enemy = {
        "x": x,
        "y": y,
        "health": enemy_stats["health"],
        "speed": enemy_stats["speed"],
        "sprite_path": enemy_stats["sprite"],
        "invulnerable_time": enemy_stats["invulnerable_time"],
        "damage": enemy_stats["damage"],
        "size": enemy_stats["size"],
        "enemy_hitbox": pg.Rect(x - enemy_stats["size"][0] / 2, y - enemy_stats["size"][1] / 2, enemy_stats["size"][0], enemy_stats["size"][1]),
        "invulnerable": False,
        "ai": enemy_stats["ai"],  
      }

      self.enemy_list.append(new_enemy)

    else:
      print(f"Enemy type {enemy_type} not found in dictionary.")

  def update_ai(self):
    for enemy in self.enemy_list:
      if enemy["ai"] == "random":
        self.random_ai(enemy)
          
      elif enemy["ai"] == "chase":
        self.chase_player_ai(enemy)

  def random_ai(self, enemy):
    directions = ["left", "right", "up", "down"]
    direction = random.choice(directions)
    if direction == "left":
      enemy["x"] -= enemy["speed"]
        
    elif direction == "right":
      enemy["x"] += enemy["speed"]
      
    elif direction == "up":
      enemy["y"] -= enemy["speed"]
        
    elif direction == "down":
      enemy["y"] += enemy["speed"]

  def chase_player_ai(self, enemy):
    dx = self.player_x - enemy["x"]
    dy = self.player_y - enemy["y"]
    distance = math.sqrt(dx**2 + dy**2)
    
    if distance != 0:
      dx /= distance  
      dy /= distance  

    enemy["x"] += dx * enemy["speed"]
    enemy["y"] += dy * enemy["speed"]

  def update_camera(self):
    self.cam_x = self.game.player.cam_x
    self.cam_y = self.game.player.cam_y

  def update_collision(self):
    for enemy in self.enemy_list:
      enemy_hitbox = enemy["enemy_hitbox"]
      for tile_hitbox in self.game.map.tile_hitboxes:
        if enemy_hitbox.colliderect(tile_hitbox):
            overlap_x = min(
              enemy_hitbox.right - tile_hitbox.left,
              tile_hitbox.right - enemy_hitbox.left
            )
            overlap_y = min(
              enemy_hitbox.bottom - tile_hitbox.top,
              tile_hitbox.bottom - enemy_hitbox.top
            )

            if overlap_x < overlap_y:
              if enemy_hitbox.centerx < tile_hitbox.centerx:
                enemy["x"] -= overlap_x
                  
              else:
                enemy["x"] += overlap_x
                    
            else:
              if enemy_hitbox.centery < tile_hitbox.centery:
                enemy["y"] -= overlap_y
                  
              else:
                enemy["y"] += overlap_y
                
        if enemy_hitbox.colliderect(self.game.player.attack_hitbox):
          print("ouch")
          self.take_damage(enemy)

  def render(self):
    for enemy in self.enemy_list:
      screen_x = enemy["x"] - self.cam_x - enemy["size"][0] / 2
      screen_y = enemy["y"] - self.cam_y - enemy["size"][1] / 2

      enemy_image = pg.image.load(enemy["sprite_path"])
      scaled_image = pg.transform.scale(enemy_image, enemy["size"]).convert_alpha()

      self.game.screen.blit(scaled_image, (screen_x, screen_y))

  def take_damage(self, enemy):
    current_time = pg.time.get_ticks()
    if not enemy["invulnerable"] or (current_time - enemy["invulnerable_time"] > enemy["invulnerable_time"]):
      enemy["health"] -= 1
      enemy["invulnerable"] = True
      enemy["invulnerable_time"] = current_time

  def checks(self):
    self.player_x = self.game.player.x
    self.player_y = self.game.player.y
    
    for enemy in self.enemy_list:
      if enemy["health"] <= 0:
        self.enemy_list.remove(enemy)
        
      if enemy["invulnerable"] and pg.time.get_ticks() - enemy["invulnerable_time"] > enemy["invulnerable_time"]:
        enemy["invulnerable"] = False

  def update(self):
    if self.game.environment.menu in {"play"}:
      self.update_camera()
      self.checks()
      self.update_collision()
      self.update_ai()
      self.render()
