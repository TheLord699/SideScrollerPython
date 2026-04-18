import pygame as pg
import os

from helper_methods import load_json

class Environment:
  def __init__(self, game):
    self.game = game
    
    self.fps = 60
    
    self.volume = 0.5 # multiplier
    self.gravity = 0.5 # 0.5
    self.max_fall_speed = 20 # terminal vel for all entities + player
    self.scale = 3 # 3 (experimental)
    self.max_particles = 25 # 20
    self.vigorous_optimizations = False # if true entities and projectiles will stop all updates as soon as theyre off screen
    self.show_indicators = True
    
    self.max_darkness = 50 # 50, greater is lighter
    self.lighting = False
    self.bloom = False
    self.bloom_tint = (255, 255, 255)
    
    self.menu = "main"
    self.last_menu = None
    
    self.menu_background_foreground_loaded = False
    self.transition = False
        
    self.current_time = None
    self.current_track = None
    
    self.joystick = None
    
    self.seed = int.from_bytes(os.urandom(4), "big")
  
    self.music_channel = pg.mixer.Channel(1)
    self.music_channel.set_volume(self.volume * 0.1)
    
    self.missing_texture = pg.image.load("assets/sprites/missing_texture.png").convert_alpha()
    
    # will switch to load from json
    self.game.ui.load_sheet("item_sheet", "assets/sprites/gui/items/Sheet.png")
    self.game.ui.load_sheet("hearts", "assets/sprites/gui/health/Hearts.png")
    self.game.ui.load_sheet("ui_sheet", "assets/sprites/gui/ui.png")
    #self.game.ui.load_sheet("fox_npc", "assets/sprites/npc/fox.png")
    #self.game.ui.load_sheet("guy_npc", "assets/sprites/npc/pack2/guy.png")
    
    self.fonts = {
      "pixel": "assets/sprites/gui/fonts/pixel.ttf",
      "fantasy": "assets/sprites/gui/fonts/pixel_fantasy.ttf"
    }
    self.maps = {
      "TestMap": "assets/maps/LayerTest/",
      "Test2": "assets/maps/LayerTest2/"
    }
    self.music = {
      "main": pg.mixer.Sound("assets/sounds/music/Alone_In_The_Town.wav"),
      "TestMap": pg.mixer.Sound("assets/sounds/music/Maternal_Heart.wav"), # "assets/sounds/music/Maternal_Heart.wav" "assets/sounds/music/Aphex_Twin_-_Xtal_HQ.mp3"
    }

    self.menu_config = load_json("assets/settings/menu_config.json")

  def load_game(self):
    self.game.player.settings_loaded = True
    self.load_data()

  def restart_game(self):
    self.game.player.load_settings()
    self.menu = "play"

  def load_menu(self, menu_name):
    config = self.menu_config["menus"].get(menu_name)
    if not config:
      return

    if "lighting" in config:
      self.lighting = config["lighting"]

    if "music" in config:
      self.handle_music(config["music"])

    if "background" in config:
      self.load_background_foreground(config["background"])

    for element_cfg in config.get("elements", []):
      self.game.ui.build_element_from_config(element_cfg, self)

  def get_controller(self):
    if pg.joystick.get_count() == 0:
      if self.joystick is not None:
        print("Controller disconnected")
        self.joystick = None
      return

    if self.joystick is not None:
      return
      
    self.joystick = pg.joystick.Joystick(0)
    print(f"Controller connected: {self.joystick.get_name()}")

  def handle_music(self, new_track):
    if self.current_track == new_track:
      return
    
    self.music_channel.stop()
    self.music_channel.play(self.music[new_track], loops=-1)
    self.current_track = new_track
    
  def save_data(self): # need to save and load map soon
    self.game.data_manager.set_setting("seed", self.seed)
    self.game.data_manager.set_setting("volume", self.volume)
    self.game.data_manager.set_setting("show_indicators", self.show_indicators)
    self.game.data_manager.set_setting("vigorous_optimizations", self.vigorous_optimizations)
    self.game.data_manager.set_setting("enable_particles", self.game.particles.enable_particles)
    self.game.data_manager.set_setting("enable_foreground", self.game.foreground.enable_foreground)
    self.game.data_manager.set_setting("enable_cam_mouse", self.game.player.enable_cam_mouse)
    self.game.data_manager.set_setting("player_max_health", self.game.player.max_health)
    self.game.data_manager.set_setting("player_current_health", self.game.player.current_health)
    self.game.data_manager.set_setting("player_direction", self.game.player.direction)
    self.game.data_manager.set_setting("player_x", self.game.player.x)
    self.game.data_manager.set_setting("player_y", self.game.player.y)

    inventory_to_save = []
    for item in self.game.player.inventory.values():
      safe_item = {
        "name": item.get("name"),
        "type": item.get("type"),
        "value": item.get("value"),
        "quantity": item.get("quantity"),
        "health": item.get("health")
      }
      inventory_to_save.append(safe_item)

    self.game.data_manager.set_setting("player_inventory", inventory_to_save)

  def load_data(self):
    try:
      self.game.player.load_settings()
      self.game.data_manager.load_data()
      self.seed = self.game.data_manager.get_setting("seed")
      self.volume = self.game.data_manager.get_setting("volume")
      self.show_indicators = self.game.data_manager.get_setting("show_indicators")
      self.vigorous_optimizations = self.game.data_manager.get_setting("vigorous_optimizations")
      self.game.particles.enable_particles = self.game.data_manager.get_setting("enable_particles")
      self.game.foreground.enable_foreground = self.game.data_manager.get_setting("enable_foreground")
      self.game.player.enable_cam_mouse = self.game.data_manager.get_setting("enable_cam_mouse")
      self.game.player.max_health = self.game.data_manager.get_setting("player_max_health")
      self.game.player.current_health = self.game.data_manager.get_setting("player_current_health")
      self.game.player.direction = self.game.data_manager.get_setting("player_direction")
      self.game.player.x = self.game.data_manager.get_setting("player_x")
      self.game.player.y = self.game.data_manager.get_setting("player_y")

      saved_inventory = self.game.data_manager.get_setting("player_inventory", [])
      self.game.player.inventory = {}
      
      for index, saved_item in enumerate(saved_inventory):
        self.game.player.inventory[index] = saved_item

      self.menu = "play"
      
    except Exception as e:
      self.menu = "select_menu"
      print(f"Error loading game data: {e}")
    
  def update_slider_value(self, element_id, value): # ts needs to be changed
    if element_id == "volume_slider":
      self.volume = value

  def death_menu(self):
    self.current_track = None

  def start_game(self):
    if getattr(self, "current_map", None) != self.maps["TestMap"]:
      # will load from json
      self.handle_music("TestMap")
      #self.lighting = True
      self.load_map("TestMap")
      self.load_background_foreground("assets/maps/LayerTest")
      
      self.game.entities.reset()
      self.game.entities.create_entity("item", "Red Gem", 0, 500)
      self.game.entities.create_entity("enemy", "Bab", 200, 500)
      self.game.entities.create_entity("item", "Potion", 50, 500) 
      self.game.entities.create_entity("item", "Gold", 100, 500)
      self.game.entities.create_entity("item", "Gold", 150, 500)
      self.game.entities.create_entity("item", "Potion", -50, 500)
      self.game.entities.create_entity("npc", "Bob", 250, 500)
      self.game.entities.create_entity("npc", "Bab", 600, 500)
      self.game.entities.create_entity("npc", "Jimmy", 1500, 500)
      self.game.entities.create_entity("actor", "Rock", 0, 1200)
      self.game.entities.create_entity("enemy", "Jelly", 380, 500)
      self.game.entities.create_entity("enemy", "Jelly", 2300, 500)
        
  def run_menu(self):
    self.reset()
    if self.menu == "play":
      self.start_game()
      
    elif self.menu == "death":
      self.death_menu()
      self.load_menu(self.menu)
      
    else:
      self.load_menu(self.menu)
      
    self.last_menu = self.menu

  def load_background_foreground(self, map_path):
    if not self.menu_background_foreground_loaded:
      self.game.background.load(map_path)
      self.game.foreground.load(map_path)
      self.menu_background_foreground_loaded = True

  def reset(self):
    if self.menu == "death":
      return 

    if self.menu in {"play", "main"} and self.last_menu not in {"settings", "select_menu"}:
      self.menu_background_foreground_loaded = False
      pg.mixer.stop()

    self.clear_ui()
    self.game.entities.reset()
    self.game.lighting.clear_all_lights()
    self.game.projectiles_system.projectiles = []
    self.game.particles.particles = []
    
    self.current_map = None

  def clear_ui(self):
    self.game.ui.ui_elements.clear()
    #self.game.ui.clear_all_cache()
    
  def load_map(self, map_name):
    self.current_map = self.maps[map_name]
    self.game.map.load(self.current_map)

  def change_menu(self, new_menu):
    #self.game.map.tile_hitboxes = []
    return lambda: setattr(self, "menu", new_menu)

  def update(self):
    self.current_time = pg.time.get_ticks()
    self.get_controller()
    
    if self.current_track:
      self.music_channel.set_volume(self.volume * 0.1)
    
    if self.menu != self.last_menu:
      self.run_menu()