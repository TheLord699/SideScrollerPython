import pygame as pg
import json
import os
import time
import random

class Map:
    def __init__(self, game):
        self.game = game
        
        self.tiles = []
        self.tile_hitboxes = []
        self.tile_id = []
        
        self.grid = []
        
        self.grid_width = 0
        self.grid_height = 0
        
        self.grid_cell_size = 0
        self.grid_offset_x = 0
        self.grid_offset_y = 0
        
        self.map_scale = self.game.environment.scale
        self.base_tile_size = 16
        self.visual_tile_size = self.base_tile_size * self.map_scale
        
        self.cam_x = 0
        self.cam_y = 0
        
        self.tile_dimension = 0
        
        self.tile_sheets = []
        self.all_tile_surfaces = []
        self.tile_attributes = {}
        self.non_empty_cells = set()

    def load(self, map_path):
        map_info_file = os.path.join(map_path, "map_info.json")
        attributes_file = os.path.join(map_path, "attributes.json")

        if not os.path.exists(map_info_file):
            print(f"Error: Map file does not exist: {map_info_file}")
            return False

        try:
            with open(map_info_file, "r") as file:
                map_data = json.load(file)
                
            try:
                self.tile_sheets = map_data["tilesheets"]
                
            except:
                self.tile_sheets = [{
                    "path": map_data.get("tile_sheet_path", ""),
                    "tile_dimension": map_data.get("tile_dimension", 0)
                }]
                
            self.tiles = map_data.get("tiles", [])
            self.tile_dimension = self.tile_sheets[0]["tile_dimension"] if self.tile_sheets else 0

            self.tile_attributes = {}
            if os.path.exists(attributes_file):
                try:
                    with open(attributes_file, "r") as file:
                        attributes_data = json.load(file)
                    self.tile_attributes = {int(k): v for k, v in attributes_data.items()}
                    
                except Exception as e:
                    print(f"Warning: Failed to load tile attributes - {e}")

            self.all_tile_surfaces = self.load_tilesheets(self.tile_sheets)
            if not self.all_tile_surfaces:
                print("Error: Failed to load any tilesheets")
                return False

            self.generate_tile_hitboxes()
            self.init_spatial_grid()

            print(f"Map loaded successfully from: {map_path}")
            return True

        except Exception as e:
            print(f"Error: Failed to load map info - {e}")
            return False

    def load_tilesheets(self, tilesheets):
        all_surfaces = []
        for sheet in tilesheets:
            try:
                tilesheet_img = pg.image.load(sheet["path"]).convert_alpha()
                sheet_width, sheet_height = tilesheet_img.get_size()
                tile_size = sheet["tile_dimension"]
                sheet_surfaces = []

                scale_factor = self.visual_tile_size / tile_size
                
                for y in range(0, sheet_height, tile_size):
                    for x in range(0, sheet_width, tile_size):
                        tile = tilesheet_img.subsurface((x, y, tile_size, tile_size))
                        tile = pg.transform.scale(tile, 
                            (int(tile_size * scale_factor), int(tile_size * scale_factor)))
                        
                        sheet_surfaces.append(tile)
                
                all_surfaces.append({
                    "surfaces": sheet_surfaces,
                    "tile_size": tile_size,
                    "visual_size": int(tile_size * scale_factor),
                    "cols": sheet_width // tile_size,
                    "rows": sheet_height // tile_size,
                    "scale_factor": scale_factor
                })

            except Exception as e:
                print(f"Failed to load tilesheet {sheet['path']}: {e}")
                all_surfaces.append({
                    "surfaces": [],
                    "tile_size": 32,
                    "visual_size": self.visual_tile_size,
                    "cols": 0,
                    "rows": 0,
                    "scale_factor": 1
                })

        return all_surfaces

    def generate_tile_hitboxes(self):
        self.tile_hitboxes = []
        self.tile_id = []

        for tile in self.tiles:
            if tile.get("hitbox", False):
                tilesheet_idx = tile.get("tilesheet", 0)
                if tilesheet_idx < len(self.all_tile_surfaces):
                    visual_size = self.all_tile_surfaces[tilesheet_idx]["visual_size"]
                    
                else:
                    visual_size = self.visual_tile_size
                
                tile_x = tile["x"] * visual_size
                tile_y = tile["y"] * visual_size

                hitbox_rect = pg.Rect(tile_x, tile_y, visual_size, visual_size)
                self.tile_hitboxes.append(hitbox_rect)
                self.tile_id.append(tile["id"])

        print(f"Generated {len(self.tile_hitboxes)} tile hitboxes.")

    def init_spatial_grid(self):
        self.non_empty_cells = set()
        if not self.tile_hitboxes:
            self.grid = []
            self.grid_width = 0
            self.grid_height = 0
            return

        min_x = min(hitbox.left for hitbox in self.tile_hitboxes)
        min_y = min(hitbox.top for hitbox in self.tile_hitboxes)
        max_x = max(hitbox.right for hitbox in self.tile_hitboxes)
        max_y = max(hitbox.bottom for hitbox in self.tile_hitboxes)

        self.grid_cell_size = self.visual_tile_size * 4
        self.grid_width = int((max_x - min_x) // self.grid_cell_size) + 1
        self.grid_height = int((max_y - min_y) // self.grid_cell_size) + 1
        self.grid_offset_x = min_x
        self.grid_offset_y = min_y

        self.grid = [[] for _ in range(self.grid_width * self.grid_height)]

        for i, hitbox in enumerate(self.tile_hitboxes):
            min_col = int((hitbox.left - self.grid_offset_x) // self.grid_cell_size)
            max_col = int((hitbox.right - self.grid_offset_x) // self.grid_cell_size)
            min_row = int((hitbox.top - self.grid_offset_y) // self.grid_cell_size)
            max_row = int((hitbox.bottom - self.grid_offset_y) // self.grid_cell_size)

            min_col = max(0, min_col)
            max_col = min(self.grid_width - 1, max_col)
            min_row = max(0, min_row)
            max_row = min(self.grid_height - 1, max_row)

            for row in range(min_row, max_row + 1):
                for col in range(min_col, max_col + 1):
                    idx = row * self.grid_width + col
                    self.grid[idx].append(i)
                    self.non_empty_cells.add((row, col))

        print(f"Initialized spatial grid: {self.grid_width}x{self.grid_height} cells")

    def get_nearby_tiles(self, hitbox, padding=50):
        search_area = hitbox.inflate(padding * 2, padding * 2)
        nearby_tiles = []

        min_col = int((search_area.left - self.grid_offset_x) // self.grid_cell_size)
        max_col = int((search_area.right - self.grid_offset_x) // self.grid_cell_size)
        min_row = int((search_area.top - self.grid_offset_y) // self.grid_cell_size)
        max_row = int((search_area.bottom - self.grid_offset_y) // self.grid_cell_size)

        min_col = max(0, min_col)
        max_col = min(self.grid_width - 1, max_col)
        min_row = max(0, min_row)
        max_row = min(self.grid_height - 1, max_row)

        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                if (row, col) not in self.non_empty_cells:
                    continue
                
                for tile_idx in self.grid[row * self.grid_width + col]:
                    tile_hitbox = self.tile_hitboxes[tile_idx]
                    if search_area.colliderect(tile_hitbox):
                        nearby_tiles.append((tile_hitbox, self.tile_id[tile_idx]))

        return nearby_tiles

    def render(self):
        current_time = time.time()
        screen_width, screen_height = self.game.screen_width, self.game.screen_height
        
        min_x = self.cam_x
        min_y = self.cam_y
        max_x = min_x + screen_width
        max_y = min_y + screen_height
        
        render_batches = {}
        
        for tile in self.tiles:
            tilesheet_idx = tile.get("tilesheet", 0)
            if tilesheet_idx >= len(self.all_tile_surfaces):
                continue
                
            visual_size = self.all_tile_surfaces[tilesheet_idx]["visual_size"]
            tx = tile["x"] * visual_size
            ty = tile["y"] * visual_size
            
            if (tx + visual_size < min_x or tx > max_x or 
                ty + visual_size < min_y or ty > max_y):
                continue
                
            if "animation" in tile:
                anim = tile["animation"]
                frames = anim["frames"]
                speed = anim.get("speed", 0.1)
                frame_idx = int((current_time % (len(frames) * speed)) / speed)
                tile_id = frames[frame_idx]
                
            else:
                tile_id = tile["id"]
                
            tile_surfaces = self.all_tile_surfaces[tilesheet_idx]["surfaces"]
            if tile_id >= len(tile_surfaces):
                continue
                
            batch_key = (tile["layer"], tilesheet_idx)
            
            if batch_key not in render_batches:
                render_batches[batch_key] = []
                
            render_batches[batch_key].append((
                tile_surfaces[tile_id],
                (tx - self.cam_x, ty - self.cam_y),
                tile.get("direction", 0)
            ))
        
        for (layer, tilesheet_idx), batch in sorted(render_batches.items()):
            for surface, pos, direction in batch:
                if direction != 0:
                    img = pg.transform.rotate(surface, direction)
                    self.game.screen.blit(img, pos)
                    
                else:
                    self.game.screen.blit(surface, pos)

    def render_debug(self, hitbox=None, padding=15):
        if not self.game.debugging:
            return
        
        screen_rect = self.game.screen.get_rect()

        font_small = pg.font.SysFont('Arial', 10)
        font_medium = pg.font.SysFont('Arial', 12)

        cell_size = self.grid_cell_size
        offset_x = self.grid_offset_x - self.cam_x
        offset_y = self.grid_offset_y - self.cam_y

        start_col = max(0, (0 - offset_x) // cell_size)
        end_col = min(self.grid_width, (screen_rect.width - offset_x) // cell_size + 1)
        start_row = max(0, (0 - offset_y) // cell_size)
        end_row = min(self.grid_height, (screen_rect.height - offset_y) // cell_size + 1)

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                x = col * cell_size + offset_x
                y = row * cell_size + offset_y

                pg.draw.rect(self.game.screen, (100, 100, 100, 50), (x, y, cell_size, cell_size), 1)

                cell_index = row * self.grid_width + col
                count = len(self.grid[cell_index])
                if count > 0:
                    text = font_small.render(str(count), True, (255, 255, 255))
                    self.game.screen.blit(text, (x + 2, y + 2))

        for tile_hitbox in self.tile_hitboxes:
            rect = pg.Rect(
                tile_hitbox.x - self.cam_x,
                tile_hitbox.y - self.cam_y,
                tile_hitbox.width,
                tile_hitbox.height,
            )
            if rect.colliderect(screen_rect):
                pg.draw.rect(self.game.screen, (255, 0, 0, 100), rect, 1)

        if hitbox:
            nearby_tiles = self.get_nearby_tiles(hitbox, padding)
            for tile_hitbox, tile_id in nearby_tiles:
                rect = pg.Rect(
                    tile_hitbox.x - self.cam_x,
                    tile_hitbox.y - self.cam_y,
                    tile_hitbox.width,
                    tile_hitbox.height,
                )
                if rect.colliderect(screen_rect):
                    pg.draw.rect(self.game.screen, (0, 255, 0), rect, 2)

                    text = font_medium.render(str(tile_id), True, (255, 255, 255))
                    self.game.screen.blit(text, (rect.x + 2, rect.y + 2))

            search_area = hitbox.inflate(padding * 2, padding * 2)
            search_rect = pg.Rect(
                search_area.x - self.cam_x,
                search_area.y - self.cam_y,
                search_area.width,
                search_area.height,
            )
            if search_rect.colliderect(screen_rect):
                pg.draw.rect(self.game.screen, (255, 255, 0), search_rect, 1)

            hitbox_rect = pg.Rect(
                hitbox.x - self.cam_x,
                hitbox.y - self.cam_y,
                hitbox.width,
                hitbox.height,
            )
            if hitbox_rect.colliderect(screen_rect):
                pg.draw.rect(self.game.screen, (0, 0, 255), hitbox_rect, 2)

    def update(self):
        if self.game.environment.menu in {"play", "death", "pause"}:
            if hasattr(self.game, "player") and self.game.player:
                self.cam_x = int(self.game.player.cam_x)
                self.cam_y = int(self.game.player.cam_y)
                
            else:
                self.handle_camera_movement()
                
            self.render()
            self.render_debug(self.game.player.hitbox)