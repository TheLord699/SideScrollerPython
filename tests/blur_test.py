import pygame as pg
import os
import numpy as np

from background import Background
from game import Environment
from player import Player
from entities import Entities
from map import Map
from ui import UI 
from particles import Particles
from memory_debugger import MemoryDebugger

class Game:
    def __init__(self):
        pg.init()
        self.clock = pg.time.Clock()
        
        # Set working directory
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

        # Game setup
        version = "0.0.0"
        icon = pg.image.load("assets/sprites/enemy/bug.png")

        self.screen_width, self.screen_height = 800, 600
        self.screen = pg.display.set_mode(
            (self.screen_width, self.screen_height), 
            pg.DOUBLEBUF | pg.HWSURFACE | pg.RESIZABLE | pg.SCALED
        )

        pg.display.set_caption(f"SideScroller {version}")
        pg.display.set_icon(icon)

        # Blur effect variables
        self.blur_enabled = True
        self.blur_radius = 2
        self.blur_passes = 1
        self.blur_surface = pg.Surface((self.screen_width, self.screen_height))

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

    def apply_box_blur(self, surface, radius=2, passes=1):
        """Fast box blur using NumPy for pixel averaging."""
        # Convert surface to NumPy array
        arr = pg.surfarray.pixels3d(surface)
        blurred_arr = arr.copy()
        
        kernel = np.ones(2 * radius + 1) / (2 * radius + 1)
        
        for _ in range(passes):
            # Horizontal blur
            for y in range(arr.shape[1]):
                for channel in range(3):
                    blurred_arr[:, y, channel] = np.convolve(
                        arr[:, y, channel], kernel, mode='same'
                    )
            
            # Vertical blur
            for x in range(arr.shape[0]):
                for channel in range(3):
                    blurred_arr[x, :, channel] = np.convolve(
                        blurred_arr[x, :, channel], kernel, mode='same'
                    )
            
            arr = blurred_arr.copy()
        
        return pg.surfarray.make_surface(blurred_arr)

    def render_fps(self):
        """Display FPS counter (temporary)."""
        fps = self.clock.get_fps()
        fps_text = self.environment.fonts["pixel"].render(
            f"FPS: {round(fps)}", True, (255, 255, 255)
        )
        self.screen.blit(fps_text, (self.screen_width / 1.2, 10)) 

    def update(self):
        """Update all game objects."""
        self.environment.update()
        self.background.update()
        self.map.update()
        self.entities.update()
        self.player.update()
        self.ui.update()
        self.particles.update()

    def game_loop(self):
        """Main game loop with blur effect toggle."""
        running = True
        
        while running:
            # Event handling
            self.events = pg.event.get()
            for event in self.events:
                if event.type == pg.QUIT:
                    running = False

                if self.memory_debugger.show_memory_info:
                    self.memory_debugger.handle_mouse_event(event)
                    
                if not self.memory_debugger.show_memory_info:
                    if event.type == pg.KEYDOWN:
                        if event.key == pg.K_h: 
                            self.player.take_damage(0.1)
                            
                        if event.key == pg.K_j: 
                            self.player.current_health += 0.5
                        
                        if event.key == pg.K_k:
                            self.player.vel_y = 0
                            self.player.vel_y += -15
                            
                        if event.key == pg.K_l:
                            self.player.max_health += 1 
                            self.player.current_health = self.player.max_health
                            
                        if event.key == pg.K_b:
                            self.environment.menu = "main"
                      
                        if event.key == pg.K_m:
                            self.memory_debugger.toggle()
                            
                        if event.key == pg.K_n:  # Toggle blur effect
                            self.blur_enabled = not self.blur_enabled
                            
                        if self.memory_debugger.show_memory_info:
                            if event.key == pg.K_UP:
                                self.memory_debugger.handle_scroll("up")
                                
                            if event.key == pg.K_DOWN:
                                self.memory_debugger.handle_scroll("down")
                                
                            if event.key == pg.K_PAGEUP:
                                self.memory_debugger.handle_scroll("up")
                                
                            if event.key == pg.K_PAGEDOWN:
                                self.memory_debugger.handle_scroll("down")

            # Clear screen
            self.screen.fill((0, 0, 0))

            # Update game state
            self.update()
            
            # Apply blur if enabled
            if self.blur_enabled:
                # Capture current frame
                self.blur_surface.blit(self.screen, (0, 0))
                # Apply blur and redraw
                blurred = self.apply_box_blur(self.blur_surface, self.blur_radius, self.blur_passes)
                self.screen.blit(blurred, (0, 0))
            
            # Debug and UI rendering
            self.memory_debugger.render()
            self.render_fps()

            # Update display
            pg.display.flip()
            self.clock.tick(self.environment.fps)

        pg.quit()

if __name__ == "__main__":
    Game()