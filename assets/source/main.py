import pygame as pg
import psutil
import sys
import os
import time
from collections import defaultdict

from background import Background 
from foreground import Foreground
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

class PerformanceMonitor:
    """Monitor and track update times for game components"""
    def __init__(self):
        self.update_times = defaultdict(list)
        self.max_samples = 60  # Keep last 60 samples (1 second at 60 FPS)
        self.show_performance = False
        
    def start_timing(self, component_name):
        """Start timing a component update"""
        self.update_times[component_name].append({
            'start': time.perf_counter(),
            'end': None
        })
        
    def end_timing(self, component_name):
        """End timing and store the duration"""
        if self.update_times[component_name]:
            current = self.update_times[component_name][-1]
            current['end'] = time.perf_counter()
            duration = current['end'] - current['start']
            
            # Keep only recent samples
            if len(self.update_times[component_name]) > self.max_samples:
                self.update_times[component_name].pop(0)
                
            return duration
        return 0
    
    def get_average_time(self, component_name):
        """Get average update time for a component in milliseconds"""
        times = [t['end'] - t['start'] for t in self.update_times[component_name] 
                if t['end'] is not None]
        if times:
            return sum(times) / len(times) * 1000  # Convert to milliseconds
        return 0
    
    def get_all_averages(self):
        """Get average times for all tracked components"""
        averages = {}
        for component in self.update_times.keys():
            avg = self.get_average_time(component)
            if avg > 0:
                averages[component] = avg
        return averages
    
    def render(self, screen, x, y, font):
        """Render performance metrics to screen"""
        if not self.show_performance:
            return
            
        averages = self.get_all_averages()
        if not averages:
            return
            
        # Sort by update time (slowest first)
        sorted_components = sorted(averages.items(), key=lambda x: x[1], reverse=True)
        
        y_offset = y
        title = font.render("Component Update Times (ms):", True, (255, 255, 100))
        screen.blit(title, (x, y_offset))
        y_offset += 25
        
        for component, avg_time in sorted_components[:15]:  # Show top 15 slowest
            # Color code based on performance
            if avg_time > 16:  # More than 1 frame at 60 FPS
                color = (255, 100, 100)  # Red - too slow
            elif avg_time > 8:  # Half a frame
                color = (255, 200, 100)  # Orange - slow
            elif avg_time > 4:
                color = (255, 255, 100)  # Yellow - okay
            else:
                color = (100, 255, 100)  # Green - fast
                
            text = font.render(f"{component}: {avg_time:.2f} ms", True, color)
            screen.blit(text, (x + 10, y_offset))
            y_offset += 20
            
        # Show total update time
        total_time = sum(averages.values())
        total_color = (255, 100, 100) if total_time > 16 else (255, 255, 100)
        total_text = font.render(f"TOTAL: {total_time:.2f} ms", True, total_color)
        screen.blit(total_text, (x, y_offset + 5))

class Game:
    def __init__(self):
        pg.init()
        
        if getattr(sys, "frozen", False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        os.chdir(base_path)
        
        try:
            psutil.Process(os.getpid()).nice(psutil.HIGH_PRIORITY_CLASS)
        except:
            print("CPU prioritization not enabled (incompatible device)")

        self.clock = pg.time.Clock()
        self.version = "0.6.0-dev"
        icon = pg.image.load("assets/sprites/misc/bug.png")

        self.screen_width, self.screen_height = 800, 600
        self.screen = pg.display.set_mode((self.screen_width, self.screen_height), 
                                         pg.DOUBLEBUF | pg.HWSURFACE | pg.RESIZABLE | pg.SCALED, 
                                         vsync=1)

        self.debugging = False
        self.show_fps = False

        pg.display.set_caption(f"SideScroller {self.version}")
        pg.display.set_icon(icon)

        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor()

        self.init_objects()
        self.game_loop()

    def init_objects(self):
        self.data_manager = DataManager()
        self.ui = UI(self)
        self.environment = Environment(self)
        self.ai = AISystem(self)
        self.map = Map(self)
        self.player = Player(self)
        self.entities = Entities(self)
        self.background = Background(self)
        self.foreground = Foreground(self)
        self.particles = Particles(self)
        self.lighting = LightSource(self)
        self.memory_debugger = MemoryDebugger(self)

    def render_fps(self):
        fps = self.clock.get_fps()
        default_font = pg.font.Font(None, 24)
        fps_text = default_font.render(f"FPS: {round(fps)}", True, (255, 255, 255))
        self.screen.blit(fps_text, (self.screen_width - 120, 10))

        ram_usage = self.memory_debugger.get_ram_usage()
        y_offset = 35
        x_pos = self.screen_width - 800

        for key, value in ram_usage.items():
            ram_line = default_font.render(f"{key}: {value}", True, (255, 255, 255))
            self.screen.blit(ram_line, (x_pos, y_offset))
            y_offset += 20

    def update_with_timing(self):
        """Update all components with performance timing"""
        
        # Update environment
        self.performance_monitor.start_timing("Environment")
        self.environment.update()
        self.performance_monitor.end_timing("Environment")
        
        # Update background
        self.performance_monitor.start_timing("Background")
        self.background.update()
        self.performance_monitor.end_timing("Background")
        
        # Update map
        self.performance_monitor.start_timing("Map")
        self.map.update()
        self.performance_monitor.end_timing("Map")
        
        # Update entities
        self.performance_monitor.start_timing("Entities")
        self.entities.update()
        self.performance_monitor.end_timing("Entities")
        
        # Update player
        self.performance_monitor.start_timing("Player")
        self.player.update()
        self.performance_monitor.end_timing("Player")
        
        # Update particles
        self.performance_monitor.start_timing("Particles")
        self.particles.update()
        self.performance_monitor.end_timing("Particles")
        
        # Update lighting
        self.performance_monitor.start_timing("Lighting")
        self.lighting.update()
        self.performance_monitor.end_timing("Lighting")
        
        # Update foreground
        self.performance_monitor.start_timing("Foreground")
        self.foreground.update()
        self.performance_monitor.end_timing("Foreground")
        
        # Update UI
        self.performance_monitor.start_timing("UI")
        self.ui.update()
        self.performance_monitor.end_timing("UI")
        
        # Testing lights
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
                
            # Performance monitor toggle
            if event.type == pg.KEYDOWN and event.key == pg.K_p:
                self.performance_monitor.show_performance = not self.performance_monitor.show_performance
                
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
                    match event.key:
                        case pg.K_h:
                            self.player.take_damage(0.1)
                        case pg.K_j:
                            self.player.current_health += 0.5
                        case pg.K_k:
                            self.player.vel_y = -15
                        case pg.K_l:
                            self.player.max_health += 1
                            self.player.current_health = self.player.max_health
                        case pg.K_b:
                            self.environment.menu = "main"
                        case pg.K_g:
                            self.environment.save_data()
                            print("Game data saved.")
                        case pg.K_v:
                            if self.player.direction == "right":
                                self.entities.create_entity("enemy", "Bab", self.player.x + 100, self.player.y - 15)
                            else:
                                self.entities.create_entity("enemy", "Bab", self.player.x - 100, self.player.y - 15)
                        case pg.K_m:
                            self.memory_debugger.toggle()
                        case pg.K_n:
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

            self.screen.fill((0, 0, 0))

            # Update with performance timing
            self.update_with_timing()
        
            # Render performance monitor
            self.performance_monitor.render(self.screen, 10, 10, pg.font.Font(None, 16))
            
            # Render memory debugger
            self.memory_debugger.render()
            
            # Render FPS
            if self.show_fps:
                self.render_fps()

            pg.display.flip()
            self.clock.tick(self.environment.fps)

        pg.quit()

if __name__ == "__main__":
    Game()