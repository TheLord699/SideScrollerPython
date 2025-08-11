import pygame as pg
import os

from background import Background
from game import Environment
from player import Player
from entities import Entities
from map import Map
from ui import UI 
from particles import Particles
from memory_debugger import MemoryDebugger
from light_source import LightSource

import pygame_shaders

class Game:
  def __init__(self):
    pg.init()
    self.clock = pg.time.Clock()

    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    version = "0.0.0"
    icon = pg.image.load("assets/sprites/enemy/bug.png")

    self.screen_width, self.screen_height = 800, 600
    self.screen = pg.display.set_mode((self.screen_width, self.screen_height), pg.DOUBLEBUF | pg.HWSURFACE | pg.RESIZABLE | pg.OPENGL)
    
    self.screen_shader = pygame_shaders.DefaultScreenShader(self.screen) # <- Here we supply our default display, it's this display which will be displayed onto the opengl context via the screen_shader

    pg.display.set_caption(f"SideScroller {version}")
    pg.display.set_icon(icon)
    
        
    self.shader = pygame_shaders.Shader(pygame_shaders.DEFAULT_VERTEX_SHADER, "custom_frag.glsl", self.screen) #<- give it to our shader

    self.init_game_objects()
    self.game_loop()

  def init_game_objects(self):
    self.ui = UI(self)
    self.environment = Environment(self)
    self.map = Map(self)
    self.player = Player(self)
    self.entities = Entities(self)
    self.background = Background(self)
    self.particles = Particles(self)
    self.memory_debugger = MemoryDebugger(self)
    self.lighting = LightSource(self)

  def render_fps(self):
    fps = self.clock.get_fps()
    fps_text = self.environment.fonts["pixel"].render(f"FPS: {round(fps)}", True, (255, 255, 255))
    self.screen.blit(fps_text, (self.screen_width - 120, 10))

  def update(self):
      self.environment.update()
      self.background.update()
      self.map.update()
      self.entities.update()
      self.player.update()
      self.particles.update()
      self.lighting.update()
      self.ui.update()

      # Testing lights
      if self.environment.lighting:
        player_light = (
          self.player.x + self.player.hitbox_width / 2,
          self.player.y + self.player.hitbox_height / 2,
          200,
          2,
          (255, 255, 200),
          'temporary'
        )
        self.lighting.active_lights.append(player_light)
      
  def game_loop(self):
    running = True
    while running:
      self.events = pg.event.get()
      for event in self.events:
        if event.type == pg.QUIT:
          running = False

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

            elif event.key == pg.K_m:
              self.memory_debugger.toggle()
              
            elif event.key == pg.K_RIGHT:
              print(len(self.lighting.stationary_lights))

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

      self.screen.fill((0, 0, 0))

      self.update()
    
      # testing
      self.memory_debugger.render()
      self.render_fps()
      
      target_shader = self.shader.render()
      
      self.screen.blit(target_shader, (0, 0))
      
      self.screen_shader.render()

      pg.display.flip()
      self.clock.tick(self.environment.fps)

    pg.quit()

if __name__ == "__main__":
	Game()
