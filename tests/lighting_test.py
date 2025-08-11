import pygame as pg
import os
import math
from background import Background
from game import Environment
from player import Player
from entities import Entities
from map import Map
from ui import UI 
from particles import Particles
from memory_debugger import MemoryDebugger

class LightSource:
    def __init__(self, game, x, y, radius=150, color=(255, 220, 180), intensity=0.8):
        self.game = game
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.intensity = intensity  # 0-1 value
        self.light_surface = self.create_light_surface()
        
    def create_light_surface(self):
        """Create a smoother radial gradient with falloff"""
        diameter = self.radius * 2
        surface = pg.Surface((diameter, diameter), pg.SRCALPHA)
        
        center_x, center_y = self.radius, self.radius
        max_dist = self.radius
        
        # Create smoother gradient using per-pixel alpha
        for x in range(diameter):
            for y in range(diameter):
                dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                if dist <= max_dist:
                    # Smooth falloff curve (quadratic)
                    ratio = 1 - (dist / max_dist)**2
                    alpha = int(255 * ratio * self.intensity)
                    # Apply color with varying alpha
                    surface.set_at((x, y), (*self.color, alpha))
                    
        return surface
        
    def update(self, cam_x, cam_y):
        """Update position relative to camera"""
        self.screen_x = self.x - cam_x
        self.screen_y = self.y - cam_y
        
    def draw(self, screen):
        """Draw the light with smooth blending"""
        if (self.screen_x + self.radius < 0 or 
            self.screen_x - self.radius > self.game.screen_width or
            self.screen_y + self.radius < 0 or 
            self.screen_y - self.radius > self.game.screen_height):
            return  # Skip drawing if offscreen
            
        screen.blit(
            self.light_surface,
            (self.screen_x - self.radius, self.screen_y - self.radius),
            special_flags=pg.BLEND_ADD
        )

class Game:
    def __init__(self):
        pg.init()
        self.clock = pg.time.Clock()
        
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

        version = "0.0.0"
        icon = pg.image.load("assets/sprites/enemy/bug.png")

        self.screen_width, self.screen_height = 800, 600
        self.screen = pg.display.set_mode(
            (self.screen_width, self.screen_height), 
            pg.DOUBLEBUF | pg.HWSURFACE | pg.RESIZABLE | pg.SCALED
        )

        pg.display.set_caption(f"SideScroller {version}")
        pg.display.set_icon(icon)

        # Enhanced lighting system
        self.light_sources = []
        self.base_darkness = 50  # 0-255 (higher = darker environment)
        self.darkness_surface = pg.Surface((self.screen_width, self.screen_height))
        self.darkness_surface.fill((self.base_darkness, self.base_darkness, self.base_darkness))
        
        self.init_game_objects()
        
        # Add test light source that follows player
        self.test_light = LightSource(
            self, 
            400, 300, 
            radius=200,
            color=(255, 200, 150),
            intensity=0.9
        )
        self.light_sources.append(self.test_light)
        
        # Add stationary ambient light
        self.ambient_light = LightSource(
            self,
            1000, 500,
            radius=400,
            color=(100, 100, 150),
            intensity=0.3
        )
        self.light_sources.append(self.ambient_light)
        
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

    def update(self):
        self.environment.update()
        self.background.update()
        self.map.update()
        self.entities.update()
        self.player.update()
        self.ui.update()
        self.particles.update()
        
        # Update light positions
        for light in self.light_sources:
            light.update(self.player.cam_x, self.player.cam_y)
            
        # Make test light follow player with slight offset
        self.test_light.x = self.player.x + 30
        self.test_light.y = self.player.y - 20

    def render_lighting(self):
        """Render the complete lighting system"""
        # 1. Prepare darkness surface (base ambient darkness)
        self.darkness_surface.fill((self.base_darkness, self.base_darkness, self.base_darkness))
        
        # 2. Apply lights (additive blending)
        for light in self.light_sources:
            light.draw(self.darkness_surface)
        
        # 3. Apply to screen (multiplicative blending)
        self.screen.blit(
            self.darkness_surface,
            (0, 0),
            special_flags=pg.BLEND_MULT
        )

    def game_loop(self):
        running = True
        
        while running:
            self.events = pg.event.get()
            for event in self.events:
                if event.type == pg.QUIT:
                    running = False

                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_n:  # Spawn new light
                        new_light = LightSource(
                            self,
                            self.player.x + 100,
                            self.player.y,
                            radius=150 + pg.time.get_ticks() % 100,  # Vary size
                            color=(
                                150 + pg.time.get_ticks() % 100,
                                150 + pg.time.get_ticks() % 100,
                                255
                            ),
                            intensity=0.7
                        )
                        self.light_sources.append(new_light)
                    
                    if event.key == pg.K_v:  # Toggle base darkness
                        self.base_darkness = 30 if self.base_darkness > 100 else 120

            # Main rendering
            self.screen.fill((0, 0, 0))
            self.update()
            
            # Apply lighting (after everything else)
            self.render_lighting()
            
            # Debug info
            self.memory_debugger.render()
            #self.render_fps()

            pg.display.flip()
            self.clock.tick(self.environment.fps)

        pg.quit()

if __name__ == "__main__":
    Game()