import pygame as pg
import os

class Environment:
  def __init__(self, game):
    self.game = game
    
    self.fps = 60
    
    self.volume = 0.5 # multiplier
    self.gravity = 0.5 # 0.5
    self.max_fall_speed = 20 # terminal vel for all entities + player
    self.scale = 3 # 3 (experimental)
    self.max_particles = 20 # 20
    
    self.max_darkness = 50 # 50, greater is lighter
    self.lighting = False
    self.bloom = False
    self.bloom_tint = (255, 255, 255)
    
    self.menu = "main"
    self.last_menu = None
    
    self.menu_background_loaded = False
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
    self.menu_functions = {
      "main": self.main_menu,
      "select_menu": self.select_menu,
      "play": self.start_game,
      "settings": self.settings_menu,
      "death": self.death_menu
    }
    self.maps = {
      "TestMap": "assets/maps/LayerTest/",
      "Test2": "assets/maps/LayerTest2/"
    }
    self.music = {
      "main": pg.mixer.Sound("assets/sounds/music/Alone_In_The_Town.wav"),
      "TestMap": pg.mixer.Sound("assets/sounds/music/Maternal_Heart.wav"), # "assets/sounds/music/Maternal_Heart.wav" "assets/sounds/music/Aphex_Twin_-_Xtal_HQ.mp3"
    }
    
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
    
  def save_data(self):
    self.game.data_manager.set_setting("seed", self.seed)
    self.game.data_manager.set_setting("volume", self.volume)
    self.game.data_manager.set_setting("show_indicators", self.game.entities.show_indicators)
    self.game.data_manager.set_setting("enable_particles", self.game.particles.enable_particles)
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
    self.game.player.load_settings()
    self.game.data_manager.load_data()
    self.seed = self.game.data_manager.get_setting("seed")
    self.volume = self.game.data_manager.get_setting("volume")
    self.game.entities.show_indicators = self.game.data_manager.get_setting("show_indicators")
    self.game.particles.enable_particles = self.game.data_manager.get_setting("enable_particles")
    self.game.player.max_health = self.game.data_manager.get_setting("player_max_health")
    self.game.player.current_health = self.game.data_manager.get_setting("player_current_health")
    self.game.player.direction = self.game.data_manager.get_setting("player_direction")
    self.game.player.x = self.game.data_manager.get_setting("player_x")
    self.game.player.y = self.game.data_manager.get_setting("player_y")

    saved_inventory = self.game.data_manager.get_setting("player_inventory", [])
    self.game.player.inventory = {}
    
    for index, saved_item in enumerate(saved_inventory):
      self.game.player.inventory[index] = saved_item
    
  def update_slider_value(self, element_id, value): # ts needs to be changed
    if element_id == "volume_slider":
      self.volume = value

  def main_menu(self):
    self.lighting = False
    self.handle_music("main")
    self.load_background("assets/maps/LayerTest")
    
    self.game.ui.create_ui(
      x=-40, y=-30, sprite_width=95, sprite_height=32, 
      width=200, height=100,
      alpha=True,
      scale_multiplier=1,
      label=f"ver: {self.game.version}",
      font=self.fonts["fantasy"],
      element_id="version",
      font_size=16,
      render_order=0
    )
    self.game.ui.create_ui(
      x=self.game.screen_width / 2.6, y=100, sprite_width=95, sprite_height=32, 
      centered=False, width=200, height=100,
      alpha=True,
      scale_multiplier=1,
      label="Generic Side Scroller",
      font=self.fonts["fantasy"],
      element_id="title",
      font_size=28,
      render_order=0
    )
    self.game.ui.create_ui(
      sprite_sheet_path="ui_sheet", image_id=[33, 0],
      x=self.game.screen_width / 2, y=250, sprite_width=95, sprite_height=32, 
      centered=True, width=200, height=100,
      alpha=True, is_button=True,
      scale_multiplier=1.1,
      label="Play",
      click_sound={"sound": pg.mixer.Sound("assets/sounds/ui/01_chest_open_4.wav"), "volume": 2.0},
      font=self.fonts["fantasy"],
      element_id="play_button",
      callback=self.change_menu("select_menu"),
      hover_range=3.5,
      render_order=0
    )
    self.game.ui.create_ui(
      sprite_sheet_path="ui_sheet", image_id=[33, 0],
      x=self.game.screen_width / 2, y=400, sprite_width=95, sprite_height=32, 
      centered=True, width=200, height=100,
      alpha=True, is_button=True,
      scale_multiplier=1.1,
      label="Settings",
      click_sound={"sound": pg.mixer.Sound("assets/sounds/ui/01_chest_open_4.wav"), "volume": 2.0},
      font=self.fonts["fantasy"],
      element_id="settings_button",
      callback=self.change_menu("settings"),
      hover_range=3.5,
      render_order=0
    )
  
  def select_menu(self):
    self.game.ui.create_ui(
      sprite_sheet_path="ui_sheet", image_id=[33, 0],
      x=self.game.screen_width / 2, y=250, sprite_width=95, sprite_height=32, 
      centered=True, width=200, height=100,
      alpha=True, is_button=True,
      scale_multiplier=1.1,
      label="New Game",
      click_sound={"sound": pg.mixer.Sound("assets/sounds/ui/01_chest_open_4.wav"), "volume": 2.0},
      font=self.fonts["fantasy"],
      element_id="new_game_button",
      callback=lambda: (self.change_menu("play")()),#callback=lambda: (setattr(self, "transition", True), self.change_menu("play")()),
      hover_range=3.5,
      render_order=0
    )
    self.game.ui.create_ui(
      sprite_sheet_path="ui_sheet", image_id=[33, 0],
      x=self.game.screen_width / 2, y=400, sprite_width=95, sprite_height=32, 
      centered=True, width=200, height=100,
      alpha=True, is_button=True,
      scale_multiplier=1.1,
      label="Load Game",
      click_sound={"sound": pg.mixer.Sound("assets/sounds/ui/01_chest_open_4.wav"), "volume": 2.0},
      font=self.fonts["fantasy"],
      element_id="load_button",
      callback=lambda: (setattr(self, "menu", "play"), setattr(self.game.player, "settings_loaded", True), self.load_data()),
      hover_range=3.5,
      render_order=0
    )
    self.game.ui.create_ui(
      sprite_sheet_path="ui_sheet", image_id=[0, 0],
      x=self.game.screen_width / 7, y=500, sprite_width=32, sprite_height=32, 
      centered=True, width=100, height=100,
      alpha=True, is_button=True,
      scale_multiplier=1.1,
      element_id="back_button",
      click_sound={"sound": pg.mixer.Sound("assets/sounds/ui/01_chest_open_4.wav"), "volume": 2.0},
      callback=self.change_menu("main"),
      hover_range=3.5,
      render_order=0
    )
  
  def settings_menu(self):   
    self.game.ui.create_ui(
      sprite_sheet_path="ui_sheet", image_id=[0, 0],
      x=self.game.screen_width / 7, y=500, sprite_width=32, sprite_height=32, 
      centered=True, width=100, height=100,
      alpha=True, is_button=True,
      scale_multiplier=1.1,
      element_id="back_button",
      click_sound={"sound": pg.mixer.Sound("assets/sounds/ui/01_chest_open_4.wav"), "volume": 2.0},
      callback=self.change_menu("main"),
      hover_range=3.5,
      render_order=0
    )
    self.game.ui.create_ui(
      x=self.game.screen_width / 2.6, y=200, width=200, height=20, is_slider=True,
      min_value=0.0, max_value=1.1, initial_value=self.volume,
      step_size=0.01, element_id="volume_slider", 
      click_sound={"sound": pg.mixer.Sound("assets/sounds/ui/01_chest_open_4.wav"), "volume": 2.0},
      variable=lambda value: self.update_slider_value("volume_slider", value),
    )
    
    self.game.ui.create_ui(
      x=self.game.screen_width / 2.6, y=125, width=200, height=20,
      element_id="volume_text", label="Volume",
      font=self.fonts["fantasy"],
    )
    self.game.ui.create_ui(
      sprite_sheet_path="ui_sheet", image_id=[33, 0],
      x=self.game.screen_width / 2, y=325, sprite_width=95, sprite_height=32, 
      centered=True, width=200, height=100,
      alpha=True, is_button=True,
      scale_multiplier=1.1,
      dynamic_value=lambda: "Indicators: On" if self.game.entities.show_indicators else "Indicators: Off",
      font=self.fonts["fantasy"],
      font_size=16,
      element_id="indicator_button",
      click_sound={"sound": pg.mixer.Sound("assets/sounds/ui/01_chest_open_4.wav"), "volume": 2.0},
      callback=lambda: (setattr(self.game.entities, "show_indicators", not self.game.entities.show_indicators)),
      hover_range=3.5,
      render_order=0
    )
    self.game.ui.create_ui(
      sprite_sheet_path="ui_sheet", image_id=[33, 0],
      x=self.game.screen_width / 2, y=450, sprite_width=95, sprite_height=32, 
      centered=True, width=200, height=100,
      alpha=True, is_button=True,
      scale_multiplier=1.1,
      dynamic_value=lambda: "Particles: On" if self.game.particles.enable_particles else "Particles: Off",
      font=self.fonts["fantasy"],
      font_size=16,
      element_id="particle_button",
      click_sound={"sound": pg.mixer.Sound("assets/sounds/ui/01_chest_open_4.wav"), "volume": 2.0},
      callback=lambda: (setattr(self.game.particles, "enable_particles", not self.game.particles.enable_particles)),
      hover_range=3.5,
      render_order=0
    )

  def death_menu(self):
    self.game.ui.create_ui(
      x=self.game.screen_width / 2.6, y=150, sprite_width=95, sprite_height=32, 
      centered=False, width=200, height=100,
      alpha=True,
      scale_multiplier=1,
      label="You Died",
      font=self.fonts["fantasy"],
      element_id="Death_message",
      font_size=35,
      render_order=0
    )
    self.game.ui.create_ui(
      sprite_sheet_path="ui_sheet", image_id=[33, 0],
      x=self.game.screen_width / 2, y=350, sprite_width=95, sprite_height=32, 
      centered=True, width=200, height=100,
      alpha=True, is_button=True,
      scale_multiplier=1.1,
      element_id="restart_button",
      label="Restart",
      font=self.fonts["fantasy"],
      click_sound={"sound": pg.mixer.Sound("assets/sounds/ui/01_chest_open_4.wav"), "volume": 2.0},
      callback=lambda: (self.game.player.load_settings(), setattr(self, "menu", "play")),
      hover_range=3.5,
      render_order=0
    )
    self.current_track = None

  def start_game(self):
    if getattr(self, "current_map", None) != self.maps["TestMap"]: 
      # will load from json
      self.handle_music("TestMap")
      #self.lighting = True
      self.load_map("TestMap")
      self.load_background("assets/maps/LayerTest")
      
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
      self.game.entities.create_entity("actor", "Rock", 350, 500)
      self.game.entities.create_entity("enemy", "Bab", 380, 500)
      self.game.entities.create_entity("enemy", "Bab", 2300, 500)
        
  def run_menu(self):
    self.reset()
    if self.menu in self.menu_functions:
      self.menu_functions[self.menu]()
    self.last_menu = self.menu

  def load_background(self, map_path):
    if not self.menu_background_loaded:
      self.game.background.load(map_path)
      self.menu_background_loaded = True

  def reset(self):
    if self.menu == "death":
      return 

    if self.menu in {"play", "main"} and self.last_menu not in {"settings", "select_menu"}:
      self.menu_background_loaded = False
      pg.mixer.stop()

    self.clear_ui()
    self.game.entities.reset()
    self.game.lighting.clear_all_lights()
    self.current_map = None

  def clear_ui(self):
    self.game.ui.ui_elements.clear()
    #self.game.ui.clear_all_cache()
    
  def load_map(self, map_name): 
    self.current_map = self.maps[map_name]
    self.game.map.load(self.current_map)

  def change_menu(self, new_menu):
    return lambda: setattr(self, "menu", new_menu)

  def update(self):
    self.current_time = pg.time.get_ticks()
    self.get_controller()
    
    if self.current_track:
      self.music_channel.set_volume(self.volume * 0.1)
    
    if self.menu != self.last_menu:
      self.run_menu()

