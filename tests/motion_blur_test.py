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

class MotionBlur:
    def __init__(self, game, intensity=0.7, samples=3):
        self.game = game
        self.intensity = intensity  # 0-1, how strong the blur is
        self.samples = samples      # How many frames to blend
        self.buffer = []
        
    def update(self):
        # Capture current frame
        current_frame = pg.Surface((self.game.screen_width, self.game.screen_height))
        current_frame.blit(self.game.screen, (0, 0))
        
        # Store frame in buffer
        self.buffer.append(current_frame)
        if len(self.buffer) > self.samples:
            self.buffer.pop(0)
            
    def apply(self, screen):
        if len(self.buffer) < 2:  # Not enough frames for blur
            return
            
        # Clear screen
        screen.fill((0, 0, 0))
        
        # Blend previous frames
        for i, frame in enumerate(self.buffer):
            alpha = int(255 * self.intensity * (i+1)/len(self.buffer))
            frame.set_alpha(alpha)
            screen.blit(frame, (0, 0))

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

        # Motion blur effect
        self.motion_blur = MotionBlur(self, intensity=0.6, samples=9)
        self.blur_enabled = True  # Toggle with 'n' key

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

    def render_fps(self):
        fps = self.clock.get_fps()
        fps_text = self.environment.fonts["pixel"].render(f"FPS: {round(fps)}", True, (255, 255, 255))
        self.screen.blit(fps_text, (self.screen_width / 1.2, 10)) 

    def update(self):
        self.environment.update()
        self.background.update()
        self.map.update()
        self.entities.update()
        self.player.update()
        self.ui.update()
        self.particles.update()
        
        # Update motion blur with camera movement
        if self.blur_enabled:
            self.motion_blur.update()

    def game_loop(self):
        running = True
        
        while running:
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
                            
                        if event.key == pg.K_n:  # Toggle motion blur
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

            # Main rendering
            self.screen.fill((0, 0, 0))
            self.update()
            
            # Apply motion blur if enabled
            if self.blur_enabled:
                self.motion_blur.apply(self.screen)
            
            # Debug info (drawn after blur so it stays sharp)
            self.memory_debugger.render()
            self.render_fps()

            pg.display.flip()
            self.clock.tick(self.environment.fps)

        pg.quit()

if __name__ == "__main__":
    Game()