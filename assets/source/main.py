# Copyright (c) 2025 TheLawd
# Licensed under the MIT License
import pygame as pg
import psutil
import os

from pygame._sdl2 import Window, Renderer, Texture

from background import Background 
from game import Environment
from player import Player
from entities import Entities
from map import Map
from ui import UI 
from data_manager import DataManager
from particles import Particles
from memory_debugger import MemoryDebugger
from light_source import LightSource
from ai import AISystem

class Game:
  def __init__(self):
    pg.init()
    
    # will either remove both or add platform checks later
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) # I dont think this will work for builds/executables
    
    try:
      psutil.Process(os.getpid()).nice(psutil.HIGH_PRIORITY_CLASS) # windows only
      
    except:
      print("CPU prioritization not enabled (incompatible device)") # temp for now

    self.clock = pg.time.Clock()

    self.version = "0.4.5-dev"
    icon_surface = pg.image.load("assets/sprites/misc/bug.png")

    self.screen_width, self.screen_height = 800, 600
    self.window = Window(f"SideScroller {self.version}", size=(self.screen_width, self.screen_height))
    self.renderer = Renderer(self.window)
    
    self.debugging = False # will remove later

    self.icon_texture = Texture.from_surface(self.renderer, icon_surface)

    self.init_game_objects()
    self.game_loop()

  def init_game_objects(self):
    self.data_manager = DataManager()
    self.ui = UI(self)
    self.environment = Environment(self)
    self.ai = AISystem(self)
    self.map = Map(self)
    self.player = Player(self)
    self.entities = Entities(self)
    self.background = Background(self)
    self.particles = Particles(self)
    self.memory_debugger = MemoryDebugger(self)
    self.lighting = LightSource(self)

  def render_fps(self): # temp function, will remove later
    fps = self.clock.get_fps()
    default_font = pg.font.Font(None, 24)
    fps_surface = default_font.render(f"FPS: {round(fps)}", True, (255, 255, 255))
    fps_texture = Texture.from_surface(self.renderer, fps_surface)
    fps_texture.draw(dstrect=(self.screen_width - 120, 10, fps_surface.get_width(), fps_surface.get_height()))

  def update(self):
    self.environment.update()
    self.background.update()
    self.map.update()
    self.entities.update()
    self.player.update()
    self.particles.update()
    self.lighting.update()
    self.ui.update()

    # testing lights
    if self.environment.lighting:
      player_light = (
        self.player.x + self.player.hitbox_width / 2,
        self.player.y + self.player.hitbox_height / 2,
        200,
        2,
        (255, 255, 200),
        "moving"
      )
      self.lighting.active_lights.append(player_light)
    
  def handle_events(self):
    self.events = pg.event.get()
    for event in self.events:
      if event.type == pg.QUIT:
        self.running = False
        
    # will remove for release
      if self.memory_debugger.show_memory_info:
        self.memory_debugger.handle_mouse_event(event)
        self.memory_debugger.handle_terminal_input(event)

        if event.type == pg.KEYDOWN:
          if event.key in (pg.K_UP, pg.K_PAGEUP):
            self.memory_debugger.handle_scroll("up")

          elif event.key in (pg.K_DOWN, pg.K_PAGEDOWN):
            self.memory_debugger.handle_scroll("down")
            
      else:
        if event.type == pg.KEYDOWN:
          if event.key == pg.K_h:
            self.player.take_damage(0.1)

          elif event.key == pg.K_j:
            self.player.current_health += 0.5

          elif event.key == pg.K_k:
            self.player.vel_y = -15

          elif event.key == pg.K_l:
            self.player.max_health += 1
            self.player.current_health = self.player.max_health

          elif event.key == pg.K_b:
            self.environment.menu = "main"
          
          elif event.key == pg.K_g:
            self.environment.save_data()
            print("Game data saved.")

          elif event.key == pg.K_m:
            self.memory_debugger.toggle()

          elif event.key == pg.K_n:
            new_light = (
              self.player.x + self.player.hitbox_width / 2,
              self.player.y + self.player.hitbox_height / 2,
              200,
              1.0,
              (255, 255, 200),
              "stationary"
            )
            self.lighting.active_lights.append(new_light)

  def game_loop(self):
    self.running = True
    while self.running:
      self.handle_events()

      self.renderer.clear()

      self.update()
    
      # testing
      self.memory_debugger.render() # will remove later
      self.render_fps()

      self.renderer.present()
      self.clock.tick(self.environment.fps)

    pg.quit()

if __name__ == "__main__":
	Game()
