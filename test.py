import pygame
import math
import random
import sys
from typing import List, Tuple, Optional
from enum import Enum

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
FPS = 60

# Colors
WATER_BLUE = (30, 58, 138)
WATER_LIGHT = (59, 130, 246)
WATER_DARK = (15, 23, 42)
SHIP_GRAY = (107, 114, 128)
SHIP_DARK = (75, 85, 99)
HIT_RED = (239, 68, 68)
HIT_ORANGE = (251, 146, 60)
MISS_WHITE = (255, 255, 255)
MISS_BLUE = (147, 197, 253)
GRID_LINES = (75, 85, 99)
UI_DARK = (31, 41, 55)
UI_LIGHT = (156, 163, 175)
TEXT_WHITE = (255, 255, 255)
TEXT_GOLD = (251, 191, 36)
EXPLOSION_COLORS = [(255, 100, 0), (255, 150, 0), (255, 200, 0), (255, 255, 100)]

class GameState(Enum):
    MENU = 0
    PLACING_SHIPS = 1
    PLAYER_TURN = 2
    AI_TURN = 3
    GAME_OVER = 4
    PAUSED = 5

class CellState(Enum):
    EMPTY = 0
    SHIP = 1
    HIT = 2
    MISS = 3
    SUNK = 4

class Particle:
    def __init__(self, x, y, vel_x, vel_y, color, size, lifetime):
        self.x = x
        self.y = y
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.gravity = 0.2

    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        self.vel_y += self.gravity
        self.lifetime -= 1
        
        # Fade out
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        self.color = (*self.color[:3], max(0, alpha))

    def draw(self, screen, camera):
        if self.lifetime > 0:
            screen_pos = camera.project_3d(self.x, 0, self.y)
            if screen_pos:
                pygame.draw.circle(screen, self.color[:3], screen_pos, max(1, int(self.size)))

class Ship:
    def __init__(self, size: int, name: str):
        self.size = size
        self.name = name
        self.positions: List[Tuple[int, int]] = []
        self.hits = 0
        self.is_sunk = False
        self.sunk_animation = 0
    
    def place(self, x: int, y: int, horizontal: bool):
        self.positions = []
        for i in range(self.size):
            if horizontal:
                self.positions.append((x + i, y))
            else:
                self.positions.append((x, y + i))
    
    def check_hit(self, x: int, y: int) -> bool:
        if (x, y) in self.positions:
            self.hits += 1
            if self.hits >= self.size:
                self.is_sunk = True
                self.sunk_animation = 60  # Animation frames
            return True
        return False

class GameBoard:
    def __init__(self):
        self.grid = [[CellState.EMPTY for _ in range(10)] for _ in range(10)]
        self.ships: List[Ship] = []
        self.ship_positions = {}  # Maps position to ship
        self.explosions = []
        self.particles = []
    
    def can_place_ship(self, ship: Ship, x: int, y: int, horizontal: bool) -> bool:
        # Check bounds
        if horizontal:
            if x + ship.size > 10 or y >= 10:
                return False
        else:
            if x >= 10 or y + ship.size > 10:
                return False
        
        # Check for collisions
        for i in range(ship.size):
            check_x = x + i if horizontal else x
            check_y = y if horizontal else y + i
            
            # Check the cell and adjacent cells
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    adj_x, adj_y = check_x + dx, check_y + dy
                    if 0 <= adj_x < 10 and 0 <= adj_y < 10:
                        if self.grid[adj_y][adj_x] == CellState.SHIP:
                            return False
        return True
    
    def place_ship(self, ship: Ship, x: int, y: int, horizontal: bool) -> bool:
        if not self.can_place_ship(ship, x, y, horizontal):
            return False
        
        ship.place(x, y, horizontal)
        for pos in ship.positions:
            self.grid[pos[1]][pos[0]] = CellState.SHIP
            self.ship_positions[pos] = ship
        
        self.ships.append(ship)
        return True
    
    def attack(self, x: int, y: int) -> Tuple[bool, bool]:  # (hit, sunk)
        if self.grid[y][x] in [CellState.HIT, CellState.MISS, CellState.SUNK]:
            return False, False
        
        if (x, y) in self.ship_positions:
            ship = self.ship_positions[(x, y)]
            ship.check_hit(x, y)
            self.grid[y][x] = CellState.HIT
            
            # Create explosion effect
            self.create_explosion(x, y, True)
            
            if ship.is_sunk:
                # Mark all ship positions as sunk
                for pos in ship.positions:
                    self.grid[pos[1]][pos[0]] = CellState.SUNK
                return True, True
            return True, False
        else:
            self.grid[y][x] = CellState.MISS
            self.create_explosion(x, y, False)
            return False, False
    
    def create_explosion(self, x: int, y: int, is_hit: bool):
        colors = EXPLOSION_COLORS if is_hit else [(100, 150, 255), (150, 200, 255)]
        for _ in range(15 if is_hit else 8):
            vel_x = random.uniform(-3, 3)
            vel_y = random.uniform(-5, -1)
            color = random.choice(colors)
            size = random.uniform(2, 5) if is_hit else random.uniform(1, 3)
            lifetime = random.randint(30, 60)
            
            particle = Particle(x, y, vel_x, vel_y, color, size, lifetime)
            self.particles.append(particle)
    
    def update_effects(self):
        # Update particles
        self.particles = [p for p in self.particles if p.lifetime > 0]
        for particle in self.particles:
            particle.update()
        
        # Update ship sinking animations
        for ship in self.ships:
            if ship.sunk_animation > 0:
                ship.sunk_animation -= 1
    
    def all_ships_sunk(self) -> bool:
        return all(ship.is_sunk for ship in self.ships)

class Camera3D:
    def __init__(self):
        self.angle_x = 0.4
        self.angle_y = 0.0
        self.distance = 18
        self.center_x = SCREEN_WIDTH // 2
        self.center_y = SCREEN_HEIGHT // 2
        self.target_angle_x = self.angle_x
        self.target_angle_y = self.angle_y
        self.zoom_target = self.distance
    
    def update(self):
        # Smooth camera movement
        self.angle_x += (self.target_angle_x - self.angle_x) * 0.1
        self.angle_y += (self.target_angle_y - self.angle_y) * 0.1
        self.distance += (self.zoom_target - self.distance) * 0.1
    
    def project_3d(self, x: float, y: float, z: float) -> Optional[Tuple[int, int]]:
        # Apply rotation
        cos_y, sin_y = math.cos(self.angle_y), math.sin(self.angle_y)
        cos_x, sin_x = math.cos(self.angle_x), math.sin(self.angle_x)
        
        # Rotate around Y axis
        new_x = x * cos_y - z * sin_y
        new_z = x * sin_y + z * cos_y
        
        # Rotate around X axis
        new_y = y * cos_x - new_z * sin_x
        new_z = y * sin_x + new_z * cos_x
        
        # Apply perspective projection
        if new_z + self.distance > 0.1:
            screen_x = int(self.center_x + (new_x * 250) / (new_z + self.distance))
            screen_y = int(self.center_y - (new_y * 250) / (new_z + self.distance))
            return screen_x, screen_y
        return None

class BattleshipAI:
    def __init__(self):
        self.last_hit = None
        self.hunt_stack = []
        self.hit_direction = None
        self.hunt_mode = False
        self.difficulty = "normal"  # easy, normal, hard
        self.shot_history = []
    
    def get_move(self, board: GameBoard) -> Tuple[int, int]:
        if self.hunt_mode and self.hunt_stack:
            return self.hunt_stack.pop()
        
        # Find available targets
        available = []
        for y in range(10):
            for x in range(10):
                if board.grid[y][x] not in [CellState.HIT, CellState.MISS, CellState.SUNK]:
                    available.append((x, y))
        
        if not available:
            return 0, 0
        
        # Difficulty-based targeting
        if self.difficulty == "easy":
            return random.choice(available)
        elif self.difficulty == "hard":
            return self._smart_targeting(available, board)
        else:  # normal
            # Mix of smart and random
            if random.random() < 0.7:
                return self._smart_targeting(available, board)
            else:
                return random.choice(available)
    
    def _smart_targeting(self, available, board):
        # Prefer checkerboard pattern for initial shots
        smart_targets = [pos for pos in available if (pos[0] + pos[1]) % 2 == 0]
        if smart_targets and not self.hunt_mode:
            return random.choice(smart_targets)
        return random.choice(available)
    
    def process_result(self, x: int, y: int, hit: bool, sunk: bool):
        self.shot_history.append((x, y, hit, sunk))
        
        if hit:
            if not self.hunt_mode:
                self.hunt_mode = True
                self.last_hit = (x, y)
                # Add adjacent cells to hunt stack
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    new_x, new_y = x + dx, y + dy
                    if 0 <= new_x < 10 and 0 <= new_y < 10:
                        self.hunt_stack.append((new_x, new_y))
            
            if sunk:
                self.hunt_mode = False
                self.hunt_stack.clear()
                self.last_hit = None

class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.load_sounds()
    
    def load_sounds(self):
        # Create simple sound effects using pygame's built-in capabilities
        try:
            # Create basic sound effects
            self.sounds['hit'] = self.create_tone(440, 0.2)
            self.sounds['miss'] = self.create_tone(220, 0.1)
            self.sounds['sunk'] = self.create_tone(880, 0.5)
            self.sounds['place'] = self.create_tone(330, 0.1)
        except:
            # Fallback if sound creation fails
            self.sounds = {}
    
    def create_tone(self, frequency, duration):
        sample_rate = 22050
        frames = int(duration * sample_rate)
        arr = []
        for i in range(frames):
            wave = 4096 * math.sin(2 * math.pi * frequency * i / sample_rate)
            arr.append([int(wave), int(wave)])
        sound = pygame.sndarray.make_sound(pygame.array.array('i', arr))
        return sound
    
    def play(self, sound_name):
        if sound_name in self.sounds:
            self.sounds[sound_name].play()

class BattleshipGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("3D Naval Warfare - Battleship")
        self.clock = pygame.time.Clock()
        
        self.player_board = GameBoard()
        self.ai_board = GameBoard()
        self.camera = Camera3D()
        self.ai = BattleshipAI()
        self.sound_manager = SoundManager()
        
        self.state = GameState.MENU
        self.ships_to_place = [
            Ship(5, "Aircraft Carrier"),
            Ship(4, "Battleship"),
            Ship(3, "Cruiser"),
            Ship(3, "Submarine"),
            Ship(2, "Destroyer")
        ]
        self.current_ship_index = 0
        self.ship_horizontal = True
        
        self.message = ""
        self.message_timer = 0
        self.font_small = pygame.font.Font(None, 24)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 48)
        self.font_title = pygame.font.Font(None, 72)
        
        self.player_score = 0
        self.ai_score = 0
        self.game_time = 0
        self.turn_timer = 0
        
        # Animation variables
        self.water_animation = 0
        self.ui_pulse = 0
        
        # Setup AI ships
        self._place_ai_ships()
    
    def _place_ai_ships(self):
        ships = [Ship(5, "Aircraft Carrier"), Ship(4, "Battleship"), Ship(3, "Cruiser"), 
                Ship(3, "Submarine"), Ship(2, "Destroyer")]
        
        for ship in ships:
            placed = False
            attempts = 0
            while not placed and attempts < 100:
                x = random.randint(0, 9)
                y = random.randint(0, 9)
                horizontal = random.choice([True, False])
                if self.ai_board.place_ship(ship, x, y, horizontal):
                    placed = True
                attempts += 1
    
    def set_message(self, text, duration=180):
        self.message = text
        self.message_timer = duration
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == GameState.MENU:
                        return False
                    elif self.state == GameState.PAUSED:
                        self.state = GameState.PLAYER_TURN
                    else:
                        self.state = GameState.PAUSED
                
                elif event.key == pygame.K_r and self.state == GameState.PLACING_SHIPS:
                    self.ship_horizontal = not self.ship_horizontal
                    self.set_message(f"Ship orientation: {'Horizontal' if self.ship_horizontal else 'Vertical'}", 60)
                
                elif event.key == pygame.K_SPACE:
                    if self.state == GameState.GAME_OVER:
                        self.restart_game()
                    elif self.state == GameState.MENU:
                        self.start_new_game()
                
                elif event.key == pygame.K_1 and self.state == GameState.MENU:
                    self.ai.difficulty = "easy"
                    self.set_message("Difficulty set to Easy")
                elif event.key == pygame.K_2 and self.state == GameState.MENU:
                    self.ai.difficulty = "normal"
                    self.set_message("Difficulty set to Normal")
                elif event.key == pygame.K_3 and self.state == GameState.MENU:
                    self.ai.difficulty = "hard"
                    self.set_message("Difficulty set to Hard")
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self._handle_mouse_click()
                elif event.button == 4:  # Mouse wheel up
                    self.camera.zoom_target = max(10, self.camera.zoom_target - 2)
                elif event.button == 5:  # Mouse wheel down
                    self.camera.zoom_target = min(25, self.camera.zoom_target + 2)
            
            elif event.type == pygame.MOUSEMOTION:
                if pygame.mouse.get_pressed()[2]:  # Right mouse drag
                    dx, dy = event.rel
                    self.camera.target_angle_y += dx * 0.01
                    self.camera.target_angle_x += dy * 0.01
                    self.camera.target_angle_x = max(-1.5, min(1.5, self.camera.target_angle_x))
        
        return True
    
    def _handle_mouse_click(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        
        if self.state == GameState.MENU:
            self.start_new_game()
        
        elif self.state == GameState.PLACING_SHIPS:
            grid_pos = self._screen_to_grid(mouse_x, mouse_y, is_player_board=True)
            if grid_pos:
                x, y = grid_pos
                ship = self.ships_to_place[self.current_ship_index]
                if self.player_board.place_ship(ship, x, y, self.ship_horizontal):
                    self.sound_manager.play('place')
                    self.current_ship_index += 1
                    if self.current_ship_index >= len(self.ships_to_place):
                        self.state = GameState.PLAYER_TURN
                        self.set_message("All ships deployed! Begin your attack, Admiral!")
                    else:
                        next_ship = self.ships_to_place[self.current_ship_index]
                        self.set_message(f"Deploy your {next_ship.name} ({next_ship.size} cells)")
                else:
                    self.set_message("Invalid placement! Ships cannot overlap or touch.", 120)
        
        elif self.state == GameState.PLAYER_TURN:
            grid_pos = self._screen_to_grid(mouse_x, mouse_y, is_player_board=False)
            if grid_pos:
                x, y = grid_pos
                hit, sunk = self.ai_board.attack(x, y)
                if hit or self.ai_board.grid[y][x] not in [CellState.HIT, CellState.MISS, CellState.SUNK]:
                    if hit:
                        self.sound_manager.play('hit')
                        if sunk:
                            self.sound_manager.play('sunk')
                            self.player_score += 1
                            self.set_message("DIRECT HIT! Enemy vessel destroyed!")
                        else:
                            self.set_message("DIRECT HIT! Enemy vessel damaged!")
                        
                        if self.ai_board.all_ships_sunk():
                            self.state = GameState.GAME_OVER
                            self.set_message("VICTORY! You have defeated the enemy fleet!")
                            return
                    else:
                        self.sound_manager.play('miss')
                        self.set_message("Shot missed target.")
                    
                    self.state = GameState.AI_TURN
                    self.turn_timer = 60  # AI delay
    
    def _screen_to_grid(self, screen_x: int, screen_y: int, is_player_board: bool) -> Optional[Tuple[int, int]]:
        offset = -6 if is_player_board else 6
        
        best_match = None
        min_distance = float('inf')
        
        for y in range(10):
            for x in range(10):
                world_x = x - 4.5 + offset
                world_y = 0
                world_z = y - 4.5
                
                proj_pos = self.camera.project_3d(world_x, world_y, world_z)
                if proj_pos:
                    proj_x, proj_y = proj_pos
                    distance = math.sqrt((proj_x - screen_x)**2 + (proj_y - screen_y)**2)
                    if distance < 30 and distance < min_distance:
                        min_distance = distance
                        best_match = (x, y)
        
        return best_match
    
    def start_new_game(self):
        self.state = GameState.PLACING_SHIPS
        self.current_ship_index = 0
        self.player_board = GameBoard()
        self.ai_board = GameBoard()
        self._place_ai_ships()
        self.game_time = 0
        ship = self.ships_to_place[0]
        self.set_message(f"Deploy your {ship.name} ({ship.size} cells). Press R to rotate.")
    
    def restart_game(self):
        self.player_score = 0
        self.ai_score = 0
        self.start_new_game()
    
    def update(self):
        self.game_time += 1
        self.water_animation += 0.02
        self.ui_pulse += 0.1
        
        if self.message_timer > 0:
            self.message_timer -= 1
        
        self.camera.update()
        self.player_board.update_effects()
        self.ai_board.update_effects()
        
        if self.state == GameState.AI_TURN:
            if self.turn_timer > 0:
                self.turn_timer -= 1
            else:
                x, y = self.ai.get_move(self.player_board)
                hit, sunk = self.player_board.attack(x, y)
                self.ai.process_result(x, y, hit, sunk)
                
                if hit:
                    self.sound_manager.play('hit')
                    if sunk:
                        self.sound_manager.play('sunk')
                        self.ai_score += 1
                        self.set_message("Enemy scored a direct hit! Your ship is destroyed!")
                    else:
                        self.set_message("Enemy hit! Your ship is damaged!")
                    
                    if self.player_board.all_ships_sunk():
                        self.state = GameState.GAME_OVER
                        self.set_message("DEFEAT! Your fleet has been destroyed!")
                        return
                else:
                    self.sound_manager.play('miss')
                    self.set_message("Enemy missed!")
                
                self.state = GameState.PLAYER_TURN
    
    def draw_water_effect(self, x, z, offset_x):
        world_x = x - 4.5 + offset_x
        world_z = z - 4.5
        
        # Animated water height
        wave_height = math.sin(self.water_animation + world_x * 0.5) * 0.1 + math.cos(self.water_animation + world_z * 0.3) * 0.05
        
        corners = []
        for dx, dz in [(0, 0), (1, 0), (1, 1), (0, 1)]:
            wave_h = math.sin(self.water_animation + (world_x + dx) * 0.5) * 0.1 + math.cos(self.water_animation + (world_z + dz) * 0.3) * 0.05
            pos = self.camera.project_3d(world_x + dx, wave_h, world_z + dz)
            if pos:
                corners.append(pos)
        
        return corners if len(corners) == 4 else None
    
    def draw_grid(self, board: GameBoard, offset_x: float, show_ships: bool = True):
        for y in range(10):
            for x in range(10):
                # Get water surface
                corners = self.draw_water_effect(x, y, offset_x)
                if not corners:
                    continue
                
                # Determine cell color based on state
                cell_state = board.grid[y][x]
                base_color = WATER_BLUE
                
                if cell_state == CellState.EMPTY:
                    color = WATER_BLUE
                elif cell_state == CellState.SHIP and show_ships:
                    color = SHIP_GRAY
                elif cell_state == CellState.SHIP and not show_ships:
                    color = WATER_BLUE
                elif cell_state == CellState.HIT:
                    color = HIT_RED
                elif cell_state == CellState.MISS:
                    color = MISS_BLUE
                elif cell_state == CellState.SUNK:
                    color = SHIP_DARK
                else:
                    color = WATER_BLUE
                
                # Add some variation to water color
                if cell_state in [CellState.EMPTY, CellState.SHIP] and (not show_ships or cell_state == CellState.EMPTY):
                    wave_factor = math.sin(self.water_animation + x * 0.3 + y * 0.2) * 0.1 + 0.9
                    color = tuple(int(c * wave_factor) for c in color)
                
                pygame.draw.polygon(self.screen, color, corners)
                pygame.draw.polygon(self.screen, GRID_LINES, corners, 1)
                
                # Draw ship details for sunk ships
                if cell_state == CellState.SUNK and (x, y) in board.ship_positions:
                    ship = board.ship_positions[(x, y)]
                    if ship.sunk_animation > 0:
                        # Sinking animation
                        sink_offset = (60 - ship.sunk_animation) * 0.1
                        darker_corners = []
                        for corner in corners:
                            darker_corners.append((corner[0], corner[1] + sink_offset))
                        pygame.draw.polygon(self.screen, SHIP_DARK, darker_corners)
        
        # Draw particles
        for particle in board.particles:
            particle.draw(self.screen, self.camera)
    
    def draw_ship_preview(self):
        if self.state != GameState.PLACING_SHIPS:
            return
        
        mouse_x, mouse_y = pygame.mouse.get_pos()
        grid_pos = self._screen_to_grid(mouse_x, mouse_y, is_player_board=True)
        
        if grid_pos:
            x, y = grid_pos
            ship = self.ships_to_place[self.current_ship_index]
            
            # Check if placement is valid
            valid = self.player_board.can_place_ship(ship, x, y, self.ship_horizontal)
            color = (0, 255, 0, 100) if valid else (255, 0, 0, 100)
            
            # Draw preview
            for i in range(ship.size):
                preview_x = x + i if self.ship_horizontal else x
                preview_y = y if self.ship_horizontal else y + i
                
                if 0 <= preview_x < 10 and 0 <= preview_y < 10:
                    world_x = preview_x - 4.5 - 6
                    world_z = preview_y - 4.5
                    
                    corners = []
                    for dx, dz in [(0, 0), (1, 0), (1, 1), (0, 1)]:
                        pos = self.camera.project_3d(world_x + dx, 0.2, world_z + dz)
                        if pos:
                            corners.append(pos)
                    
                    if len(corners) == 4:
                        # Create surface with alpha
                        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                        pygame.draw.polygon(surf, color, corners)
                        self.screen.blit(surf, (0, 0))
    
    def draw_ui(self):
        # Background gradient
        for y in range(SCREEN_HEIGHT):
            alpha = int(255 * (1 - y / SCREEN_HEIGHT) * 0.3)
            color = (*WATER_DARK, alpha)
            surf = pygame.Surface((SCREEN_WIDTH, 1), pygame.SRCALPHA)
            surf.fill(color)
            self.screen.blit(surf, (0, y))
        
        if self.state == GameState.MENU:
            self.draw_menu()
        else:
            self.draw_game_ui()
    
    def draw_menu(self):
        # Title with glow effect
        title_text = "3D NAVAL WARFARE"
        subtitle_text = "BATTLESHIP"
        
        # Glow effect
        glow_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for offset in range(5, 0, -1):
            glow_color = (*TEXT_GOLD, 50 // offset)
            title_glow = self.font_title.render(title_text, True, glow_color)
            subtitle_glow = self.font_large.render(subtitle_text, True, glow_color)
            
            glow_surface.blit(title_glow, (SCREEN_WIDTH // 2 - title_glow.get_width() // 2 + offset, 100 + offset))
            glow_surface.blit(subtitle_glow, (SCREEN_WIDTH // 2 - subtitle_glow.get_width() // 2 + offset, 180 + offset))
        
        self.screen.blit(glow_surface, (0, 0))
        
        # Main title
        title_surface = self.font_title.render(title_text, True, TEXT_WHITE)
        subtitle_surface = self.font_large.render(subtitle_text, True, TEXT_GOLD)
        
        self.screen.blit(title_surface, (SCREEN_WIDTH // 2 - title_surface.get_width() // 2, 100))
        self.screen.blit(subtitle_surface, (SCREEN_WIDTH // 2 - subtitle_surface.get_width() // 2, 180))
        
        # Menu options
        menu_items = [
            "SPACE - Start New Game",
            "1/2/3 - Set Difficulty (Easy/Normal/Hard)",
            f"Current Difficulty: {self.ai.difficulty.upper()}",
            "",
            "Controls:",
            "Left Click - Place ships / Attack",
            "Right Click + Drag - Rotate camera",
            "Mouse Wheel - Zoom",
            "R - Rotate ship (during placement)",
            "ESC - Pause game"
        ]
        
        start_y = 300
        for i, item in enumerate(menu_items):
            if item == "":
                continue
            
            color = TEXT_GOLD if "Current Difficulty" in item else TEXT_WHITE
            if "SPACE" in item:
                # Pulsing effect for start option
                pulse = abs(math.sin(self.ui_pulse)) * 0.3 + 0.7
                color = tuple(int(c * pulse) for c in TEXT_GOLD)
            
            text_surface = self.font_medium.render(item, True, color)
            self.screen.blit(text_surface, (SCREEN_WIDTH // 2 - text_surface.get_width() // 2, start_y + i * 35))
    
    def draw_game_ui(self):
        # Game status bar
        status_bg = pygame.Surface((SCREEN_WIDTH, 80), pygame.SRCALPHA)
        status_bg.fill((*UI_DARK, 200))
        self.screen.blit(status_bg, (0, 0))
        
        # Game title
        title = self.font_medium.render("3D NAVAL WARFARE", True, TEXT_GOLD)
        self.screen.blit(title, (20, 20))
        
        # Score
        score_text = f"Player: {self.player_score}  |  AI: {self.ai_score}"
        score_surface = self.font_small.render(score_text, True, TEXT_WHITE)
        self.screen.blit(score_surface, (SCREEN_WIDTH - score_surface.get_width() - 20, 20))
        
        # Game time
        minutes = self.game_time // (60 * 60)
        seconds = (self.game_time // 60) % 60
        time_text = f"Time: {minutes:02d}:{seconds:02d}"
        time_surface = self.font_small.render(time_text, True, TEXT_WHITE)
        self.screen.blit(time_surface, (SCREEN_WIDTH - time_surface.get_width() - 20, 45))
        
        # Current message
        if self.message_timer > 0:
            message_bg = pygame.Surface((SCREEN_WIDTH, 60), pygame.SRCALPHA)
            message_bg.fill((*UI_DARK, 180))
            self.screen.blit(message_bg, (0, SCREEN_HEIGHT - 120))
            
            message_surface = self.font_medium.render(self.message, True, TEXT_WHITE)
            self.screen.blit(message_surface, (SCREEN_WIDTH // 2 - message_surface.get_width() // 2, SCREEN_HEIGHT - 100))
        
        # Board labels
        player_label = self.font_medium.render("YOUR FLEET", True, TEXT_WHITE)
        ai_label = self.font_medium.render("ENEMY WATERS", True, TEXT_WHITE)
        self.screen.blit(player_label, (200, 100))
        self.screen.blit(ai_label, (SCREEN_WIDTH - 250, 100))
        
        # Ship placement info
        if self.state == GameState.PLACING_SHIPS:
            ship = self.ships_to_place[self.current_ship_index]
            info_text = f"Placing: {ship.name} ({ship.size} cells) - {'Horizontal' if self.ship_horizontal else 'Vertical'}"
            info_surface = self.font_small.render(info_text, True, TEXT_GOLD)
            self.screen.blit(info_surface, (20, SCREEN_HEIGHT - 40))
            
            # Ships remaining
            remaining = len(self.ships_to_place) - self.current_ship_index
            remaining_text = f"Ships remaining: {remaining}"
            remaining_surface = self.font_small.render(remaining_text, True, TEXT_WHITE)
            self.screen.blit(remaining_surface, (SCREEN_WIDTH - remaining_surface.get_width() - 20, SCREEN_HEIGHT - 40))
        
        # Turn indicator
        elif self.state in [GameState.PLAYER_TURN, GameState.AI_TURN]:
            turn_text = "YOUR TURN" if self.state == GameState.PLAYER_TURN else "ENEMY TURN"
            turn_color = TEXT_GOLD if self.state == GameState.PLAYER_TURN else HIT_RED
            
            if self.state == GameState.PLAYER_TURN:
                pulse = abs(math.sin(self.ui_pulse * 2)) * 0.3 + 0.7
                turn_color = tuple(int(c * pulse) for c in turn_color)
            
            turn_surface = self.font_medium.render(turn_text, True, turn_color)
            self.screen.blit(turn_surface, (SCREEN_WIDTH // 2 - turn_surface.get_width() // 2, SCREEN_HEIGHT - 40))
        
        # Game over screen
        elif self.state == GameState.GAME_OVER:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((*UI_DARK, 150))
            self.screen.blit(overlay, (0, 0))
            
            game_over_text = "VICTORY!" if self.player_board.all_ships_sunk() == False else "DEFEAT!"
            game_over_color = TEXT_GOLD if "VICTORY" in game_over_text else HIT_RED
            
            game_over_surface = self.font_title.render(game_over_text, True, game_over_color)
            self.screen.blit(game_over_surface, (SCREEN_WIDTH // 2 - game_over_surface.get_width() // 2, SCREEN_HEIGHT // 2 - 100))
            
            restart_text = "Press SPACE to play again"
            restart_surface = self.font_medium.render(restart_text, True, TEXT_WHITE)
            self.screen.blit(restart_surface, (SCREEN_WIDTH // 2 - restart_surface.get_width() // 2, SCREEN_HEIGHT // 2 + 50))
        
        # Pause screen
        elif self.state == GameState.PAUSED:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((*UI_DARK, 100))
            self.screen.blit(overlay, (0, 0))
            
            pause_text = "PAUSED"
            pause_surface = self.font_large.render(pause_text, True, TEXT_WHITE)
            self.screen.blit(pause_surface, (SCREEN_WIDTH // 2 - pause_surface.get_width() // 2, SCREEN_HEIGHT // 2))
    
    def draw(self):
        self.screen.fill(WATER_DARK)
        
        if self.state != GameState.MENU:
            # Draw both game boards
            self.draw_grid(self.player_board, -6, show_ships=True)   # Player board on left
            self.draw_grid(self.ai_board, 6, show_ships=False)      # AI board on right (hidden ships)
            
            # Draw ship placement preview
            self.draw_ship_preview()
        
        self.draw_ui()
        pygame.display.flip()
    
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = BattleshipGame()
    game.run()
    
    #make an fps game in python using pygame and moderngl, make classes ai full fps controlls hit detection different loadouts and more