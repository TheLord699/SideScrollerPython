import pygame as pg
import json
import os
import sys
import shutil
import time

from PIL import Image
from datetime import datetime

pg.init()
screen = pg.display.set_mode((1280, 720), pg.RESIZABLE)
pg.display.set_caption("Tile Map Editor")
font = pg.font.SysFont("Consolas", 18)

MAPS_ROOT = "assets/maps"
TILESHEETS_ROOT = "assets/sprites/maps/tile_sheets"
ENTITIES_FILE = "assets/settings/entities.json"
TILE_PANEL_WIDTH = 256
MIN_TILE_PANEL_WIDTH = 150
ENTITY_PANEL_WIDTH = 300
MIN_ENTITY_PANEL_WIDTH = 200
VERSION_HISTORY_MAX = 50
ANIMATION_SPEED = 0.1
MAX_ANIMATION_FRAMES = 10
ENTITY_TYPES = ["items", "npcs", "enemies", "actors"]
VISUAL_SCALE = 2
BASE_TILE_SIZE = 16

display_hitboxes = False
resizing_panel = False
resizing_entity_panel = False
show_layers = False
layer_mode = False
precision_mode = False
scroll_speed = 20
show_entity_panel = False
placing_entity = False
inspecting_entity = None
editing_attribute = None
current_attribute_value = ""
mouse_held = False
last_placed_pos = None
zoom_level = 1.0
copied_tiles = []
highlighted_tiles = []
shift_selecting = False

class VersionEntry:
    def __init__(self, timestamp, comment, data):
        self.timestamp = timestamp
        self.comment = comment
        self.data = data

def ask_input(prompt, default=None):
    print(prompt + (f" (default: {default})" if default else "") + ": ", end="")
    val = input()
    if not val.strip() and default is not None:
        return default
    
    return val

def list_maps():
    if not os.path.exists(MAPS_ROOT):
        os.makedirs(MAPS_ROOT)
        
    return [d for d in os.listdir(MAPS_ROOT) if os.path.isdir(os.path.join(MAPS_ROOT, d))]

def select_map():
    maps = list_maps()
    if not maps:
        print("No existing maps found.")
        
        return None
    
    print("Existing maps:")
    for i, m in enumerate(maps):
        print(f"{i+1}: {m}")
        
    choice = ask_input("Enter map number to edit or leave blank to cancel")
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(maps):
            return maps[idx]
        
    return None

def load_map(map_name):
    folder = os.path.join(MAPS_ROOT, map_name)
    try:
        with open(os.path.join(folder, "map_info.json"), "r") as f:
            map_data = json.load(f)
            
        with open(os.path.join(folder, "attributes.json"), "r") as f:
            attr_data = json.load(f)
            
    except Exception as e:
        print(f"Failed to load map: {e}")
        return None, None, None

    tiles = map_data.get("tiles", [])
    tilesheets = map_data.get("tilesheets", [{
        "path": os.path.normpath(map_data.get("tile_sheet_path", "")),
        "tile_dimension": map_data.get("tile_dimension", 32)
    }])
    
    for idx, attr in attr_data.items():
        try:
            i = int(idx)
            if i < len(tiles):
                tiles[i].update(attr)
                
        except:
            pass
        
    return tiles, tilesheets, folder

def load_tilesheets(tilesheets):
    all_surfaces = []
    for sheet in tilesheets:
        try:
            tilesheet_img = pg.image.load(sheet["path"]).convert_alpha()
            sheet_width, sheet_height = tilesheet_img.get_size()
            tile_size = sheet["tile_dimension"]
            sheet_surfaces = []
            
            scale_factor = (BASE_TILE_SIZE * VISUAL_SCALE) / tile_size
            
            for y in range(0, sheet_height - tile_size + 1, tile_size):
                for x in range(0, sheet_width - tile_size + 1, tile_size):
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
                "visual_size": BASE_TILE_SIZE * VISUAL_SCALE,
                "cols": 0,
                "rows": 0,
                "scale_factor": 1
            })
    
    return all_surfaces

def load_entity_data():
    try:
        with open(ENTITIES_FILE, 'r') as f:
            return json.load(f)
        
    except Exception as e:
        print(f"Failed to load entity data: {e}")
        return {"items": {}, "npcs": {}, "enemies": {}, "actors": {}}

def save_individual_tiles(tiles, tilesheets, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    used_tiles = {}
    
    for t in tiles:
        sheet_idx = t.get("tilesheet", 0)
        if sheet_idx >= len(tilesheets):
            continue
            
        if t.get("type") != "entity":
            used_tiles.setdefault(sheet_idx, set()).add(t["id"])
            
        if "animation" in t:
            for frame in t["animation"]["frames"]:
                used_tiles[sheet_idx].add(frame)

    for sheet_idx, tile_ids in used_tiles.items():
        if sheet_idx >= len(tilesheets):
            continue
            
        try:
            tilesheet = Image.open(tilesheets[sheet_idx]["path"])
            tile_dimension = tilesheets[sheet_idx]["tile_dimension"]
            
            sheet_width, sheet_height = tilesheet.size
            cols = sheet_width // tile_dimension
            rows = sheet_height // tile_dimension
            
            tiles_dir = os.path.join(output_folder, "assets", f"sheet_{sheet_idx}")
            os.makedirs(tiles_dir, exist_ok=True)
            
            for tile_id in tile_ids:
                if tile_id >= cols * rows:
                    continue
                    
                col = tile_id % cols
                row = tile_id // cols
                
                x = col * tile_dimension
                y = row * tile_dimension
                
                tile_img = tilesheet.crop((x, y, x + tile_dimension, y + tile_dimension))
                tile_img.save(os.path.join(tiles_dir, f"tile_{tile_id}.png"))
            
        except Exception as e:
            print(f"Failed to save tiles from sheet {sheet_idx}: {e}")

def save_map(folder, tiles, tilesheets):
    saved_sheets = []
    for sheet in tilesheets:
        sheet_filename = os.path.basename(sheet["path"])
        sheet_dest = os.path.join(TILESHEETS_ROOT, sheet_filename)
        
        if not os.path.exists(sheet_dest):
            os.makedirs(TILESHEETS_ROOT, exist_ok=True)
            shutil.copy2(sheet["path"], sheet_dest)

        saved_sheets.append({
            "path": os.path.join("assets", "sprites", "maps", "tile_sheets", sheet_filename).replace("\\", "/"),
            "tile_dimension": sheet["tile_dimension"]
        })

    map_info = {
        "tilesheets": saved_sheets,
        "tiles": tiles
    }
    
    with open(os.path.join(folder, "map_info.json"), "w") as f:
        json.dump(map_info, f, indent=2)

def save_version(map_folder, tiles, tilesheets, comment=""):
    versions_dir = os.path.join(map_folder, "versions")
    os.makedirs(versions_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%d%m%Y-%H%M%S")
    version_data = {
        "timestamp": timestamp,
        "comment": comment,
        "tiles": tiles,
        "tilesheets": tilesheets
    }
    
    version_path = os.path.join(versions_dir, f"version_{timestamp}.json")
    with open(version_path, 'w') as f:
        json.dump(version_data, f)
    
    versions = sorted(os.listdir(versions_dir), reverse=True)
    for old_version in versions[VERSION_HISTORY_MAX:]:
        os.remove(os.path.join(versions_dir, old_version))

def load_versions(map_folder):
    versions_dir = os.path.join(map_folder, "versions")
    if not os.path.exists(versions_dir):
        return []
    
    versions = []
    for fname in sorted(os.listdir(versions_dir), reverse=True):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(versions_dir, fname), 'r') as f:
                    data = json.load(f)
                    versions.append(VersionEntry(
                        data['timestamp'],
                        data['comment'],
                        data
                    ))
                    
            except:
                pass
            
    return versions

def draw_grid(panel_width):
    visual_size = (all_tile_surfaces[0]["visual_size"] if all_tile_surfaces else BASE_TILE_SIZE * VISUAL_SCALE) * zoom_level
    
    for x in range(0, int((screen.get_width() - panel_width) / zoom_level), int(visual_size)):
        pg.draw.line(screen, (50, 50, 50), (x * zoom_level, 0), (x * zoom_level, screen.get_height()))
        
    for y in range(0, int(screen.get_height() / zoom_level), int(visual_size)):
        pg.draw.line(screen, (50, 50, 50), (0, y * zoom_level), ((screen.get_width() - panel_width), y * zoom_level))
    
    if precision_mode:
        for x in range(0, int((screen.get_width() - panel_width) / zoom_level), int(visual_size // 2)):
            color = (70, 70, 70) if x % visual_size == 0 else (40, 40, 40)
            pg.draw.line(screen, color, (x * zoom_level, 0), (x * zoom_level, screen.get_height()))
            
        for y in range(0, int(screen.get_height() / zoom_level), int(visual_size // 2)):
            color = (70, 70, 70) if y % visual_size == 0 else (40, 40, 40)
            pg.draw.line(screen, color, (0, y * zoom_level), ((screen.get_width() - panel_width), y * zoom_level))

def draw_tiles(tiles, all_tile_surfaces, camera_x, camera_y, show_layers=False, current_layer=0, layer_mode=False, panel_width=256):
    current_time = time.time()
    
    for tile in sorted(tiles, key=lambda t: t["layer"]):
        visual_size = all_tile_surfaces[tile.get("tilesheet", 0)]["visual_size"] * zoom_level
        tx = tile["x"] * visual_size - camera_x * zoom_level
        ty = tile["y"] * visual_size - camera_y * zoom_level
        
        if tile.get("type") == "entity":
            pg.draw.rect(screen, (200, 100, 200), (tx, ty, visual_size, visual_size))
            name = tile.get("entity_name", "entity")
            name_text = font.render(name[:5], True, (255, 255, 255))
            screen.blit(name_text, (tx + 5, ty + 5))
            continue
            
        if "animation" in tile:
            anim = tile["animation"]
            frames = anim["frames"]
            speed = anim.get("speed", ANIMATION_SPEED)
            frame_idx = int((current_time % (len(frames) * speed)) / speed)
            tile_id = frames[frame_idx]
            
        else:
            tile_id = tile["id"]
            
        tilesheet_idx = tile.get("tilesheet", 0)
        if tilesheet_idx < len(all_tile_surfaces):
            tile_surfaces = all_tile_surfaces[tilesheet_idx]["surfaces"]
            if tile_id < len(tile_surfaces):
                img = tile_surfaces[tile_id].copy()
                img = pg.transform.scale(img, (int(img.get_width() * zoom_level), int(img.get_height() * zoom_level)))
                img = pg.transform.rotate(img, tile.get("direction", 0))
                
                if layer_mode and tile["layer"] != current_layer:
                    img.fill((255, 255, 255, 96), None, pg.BLEND_RGBA_MULT)
                    
                screen.blit(img, (tx, ty))
        
        if show_layers:
            layer_text = font.render(str(tile["layer"]), True, (255, 255, 255))
            text_rect = layer_text.get_rect(center=(tx + visual_size//2, ty + visual_size//2))
            screen.blit(layer_text, text_rect)

        if display_hitboxes:
            if tile.get("hitbox", False):
                pg.draw.rect(screen, (255, 0, 0), (tx, ty, visual_size, visual_size), 2)

        if tile in highlighted_tiles:
            pg.draw.rect(screen, (0, 255, 255), (tx, ty, visual_size, visual_size), 3)

def get_tile_at(mx, my, tiles, all_tile_surfaces, camera_x, camera_y, current_layer=None, panel_width=256):
    if mx > screen.get_width() - panel_width:
        return None
        
    visual_size = (all_tile_surfaces[0]["visual_size"] if all_tile_surfaces else BASE_TILE_SIZE * VISUAL_SCALE) * zoom_level
    
    if precision_mode:
        gx = round((mx + camera_x * zoom_level) / visual_size * 2) / 2
        gy = round((my + camera_y * zoom_level) / visual_size * 2) / 2
        for t in tiles:
            if (abs(t["x"] - gx) < 0.01 and abs(t["y"] - gy) < 0.01 and 
                (current_layer is None or t["layer"] == current_layer)):
                return t
            
    else:
        gx = (mx + camera_x * zoom_level) // visual_size
        gy = (my + camera_y * zoom_level) // visual_size
        for t in tiles:
            if (t["x"] == gx and t["y"] == gy and 
                (current_layer is None or t["layer"] == current_layer)):
                return t
            
    return None

def draw_tile_selector(all_tile_surfaces, selected_tile_info, scroll_y, panel_width):
    if not all_tile_surfaces or selected_tile_info["tilesheet"] >= len(all_tile_surfaces):
        return
        
    visual_size = all_tile_surfaces[selected_tile_info["tilesheet"]]["visual_size"]
    
    panel_rect = pg.Rect(screen.get_width() - panel_width, 0, panel_width, screen.get_height())
    pg.draw.rect(screen, (30, 30, 30), panel_rect)
    pg.draw.rect(screen, (50, 50, 50), panel_rect, 2)
    
    resize_handle = pg.Rect(screen.get_width() - panel_width - 5, 0, 10, screen.get_height())
    pg.draw.rect(screen, (100, 100, 100), resize_handle)
    
    panel_x = screen.get_width() - panel_width + 5
    panel_y = 5 - scroll_y
    
    for i in range(len(all_tile_surfaces)):
        tab_width = panel_width // max(1, len(all_tile_surfaces))
        tab_rect = pg.Rect(panel_x + i * tab_width, panel_y, tab_width, 30)
        color = (70, 70, 70) if selected_tile_info["tilesheet"] != i else (100, 100, 100)
        pg.draw.rect(screen, color, tab_rect)
        pg.draw.rect(screen, (50, 50, 50), tab_rect, 1)
        
        label = font.render(f"Sheet {i+1}", True, (255, 255, 255))
        screen.blit(label, (tab_rect.x + 5, tab_rect.y + 5))
    
    current_sheet = all_tile_surfaces[selected_tile_info["tilesheet"]]
    tiles_per_row = max(1, (panel_width - 10) // visual_size)
    
    for i, tile in enumerate(current_sheet["surfaces"]):
        row = (i // tiles_per_row) + 1
        col = i % tiles_per_row
        x = panel_x + col * visual_size
        y = panel_y + row * visual_size + 30
        
        if y + visual_size > 0 and y < screen.get_height():
            screen.blit(tile, (x, y))
            if i == selected_tile_info["tile"] and selected_tile_info["tilesheet"] == selected_tile_info["tilesheet"]:
                pg.draw.rect(screen, (0, 255, 0), (x, y, visual_size, visual_size), 3)

def tile_selector_click(mx, my, scroll_y, panel_width, all_tile_surfaces):
    if not all_tile_surfaces:
        return None
        
    visual_size = all_tile_surfaces[0]["visual_size"]
    
    panel_x = screen.get_width() - panel_width + 5
    panel_y = 5 - scroll_y
    
    if mx < panel_x or mx > screen.get_width():
        return None
    
    tab_height = 30
    if my < panel_y + tab_height:
        tab_width = panel_width // max(1, len(all_tile_surfaces))
        tab_idx = (mx - panel_x) // tab_width
        
        if 0 <= tab_idx < len(all_tile_surfaces):
            return {"tilesheet": tab_idx, "tile": 0}
        
        return None
    
    rel_x = mx - panel_x
    rel_y = my - panel_y - tab_height
    
    if selected_tile_info["tilesheet"] >= len(all_tile_surfaces):
        return None
    
    tiles_per_row = max(1, (panel_width - 10) // visual_size)
    col = rel_x // visual_size
    row = rel_y // visual_size - 1
    
    idx = row * tiles_per_row + col
    current_sheet = all_tile_surfaces[selected_tile_info["tilesheet"]]
    
    if 0 <= idx < len(current_sheet["surfaces"]):
        return {"tilesheet": selected_tile_info["tilesheet"], "tile": idx}
    
    return None

def draw_entity_selector(entity_data, selected_entity_type, selected_entity, scroll_y, panel_width):
    panel_rect = pg.Rect(screen.get_width() - panel_width, 0, panel_width, screen.get_height())
    pg.draw.rect(screen, (40, 40, 40), panel_rect)
    pg.draw.rect(screen, (70, 70, 70), panel_rect, 2)
    
    resize_handle = pg.Rect(screen.get_width() - panel_width - 5, 0, 10, screen.get_height())
    pg.draw.rect(screen, (100, 100, 100), resize_handle)
    
    panel_x = screen.get_width() - panel_width + 5
    panel_y = 5 - scroll_y
    
    for i, entity_type in enumerate(ENTITY_TYPES):
        tab_width = panel_width // len(ENTITY_TYPES)
        tab_rect = pg.Rect(panel_x + i * tab_width, panel_y, tab_width, 30)
        color = (70, 70, 70) if selected_entity_type != entity_type else (100, 100, 100)
        
        pg.draw.rect(screen, color, tab_rect)
        pg.draw.rect(screen, (50, 50, 50), tab_rect, 1)
        
        label = font.render(entity_type.capitalize(), True, (255, 255, 255))
        screen.blit(label, (tab_rect.x + 5, tab_rect.y + 5))
    
    if entity_data and selected_entity_type in entity_data:
        entities = entity_data[selected_entity_type]
        item_height = 60
        
        for i, (name, data) in enumerate(entities.items()):
            y = panel_y + 30 + i * item_height
            
            if y + item_height > 0 and y < screen.get_height():
                entry_rect = pg.Rect(panel_x, y, panel_width - 10, item_height - 5)
                is_selected = (selected_entity == name and selected_entity_type == selected_entity_type)
                color = (60, 60, 60) if not is_selected else (80, 80, 80)
                
                pg.draw.rect(screen, color, entry_rect)
                pg.draw.rect(screen, (50, 50, 50), entry_rect, 1)
                
                name_text = font.render(name, True, (255, 255, 255))
                screen.blit(name_text, (panel_x + 10, y + 5))
                
                type_text = font.render(data.get("type", "unknown"), True, (200, 200, 200))
                screen.blit(type_text, (panel_x + 10, y + 25))
                
                if "tile_sheet" in data and data["tile_sheet"]:
                    try:
                        sheet_path, tile_w, tile_h = data["tile_sheet"]
                        sheet = pg.image.load(sheet_path).convert_alpha()
                        row, col = map(int, data["index"].split("_")[1:3])
                        tile = sheet.subsurface((col * tile_w, row * tile_h, tile_w, tile_h))
                        tile = pg.transform.scale(tile, (40, 40))
                        screen.blit(tile, (panel_x + panel_width - 50, y + 10))
                        
                    except Exception as e:
                        print(f"Error loading entity preview: {e}")

def entity_selector_click(mx, my, scroll_y, panel_width, entity_data, selected_entity_type):
    panel_x = screen.get_width() - panel_width + 5
    panel_y = 5 - scroll_y
    
    if mx < panel_x or mx > screen.get_width():
        return None, None
    
    tab_height = 30
    if my < panel_y + tab_height:
        tab_width = panel_width // len(ENTITY_TYPES)
        tab_idx = (mx - panel_x) // tab_width
        
        if 0 <= tab_idx < len(ENTITY_TYPES):
            return ENTITY_TYPES[tab_idx], None
        
        return None, None
    
    rel_y = my - panel_y - tab_height
    item_height = 60
    entity_idx = rel_y // item_height
    
    if selected_entity_type in entity_data:
        entities = list(entity_data[selected_entity_type].items())
        if 0 <= entity_idx < len(entities):
            return selected_entity_type, entities[entity_idx][0]
    
    return None, None

def draw_entity_inspector(entity, entity_data, panel_width):
    if not entity or "entity_type" not in entity or "entity_name" not in entity:
        return
    
    panel_rect = pg.Rect(0, 0, panel_width, screen.get_height())
    pg.draw.rect(screen, (50, 50, 50), panel_rect)
    pg.draw.rect(screen, (80, 80, 80), panel_rect, 2)
    
    panel_x = 10
    panel_y = 10
    
    header_text = font.render(f"Entity: {entity['entity_name']}", True, (255, 255, 255))
    screen.blit(header_text, (panel_x, panel_y))
    panel_y += 30
    
    type_text = font.render(f"Type: {entity['entity_type']}", True, (200, 200, 200))
    screen.blit(type_text, (panel_x, panel_y))
    panel_y += 30
    
    pos_text = font.render(f"Position: ({entity['x']}, {entity['y']})", True, (200, 200, 200))
    screen.blit(pos_text, (panel_x, panel_y))
    panel_y += 30
    
    layer_text = font.render(f"Layer: {entity['layer']}", True, (200, 200, 200))
    screen.blit(layer_text, (panel_x, panel_y))
    panel_y += 40
    
    if entity['entity_type'] in entity_data and entity['entity_name'] in entity_data[entity['entity_type']]:
        entity_info = entity_data[entity['entity_type']][entity['entity_name']]
        
        for attr, value in entity_info.items():
            if attr in ["tile_sheet", "index"]:
                continue
                
            attr_rect = pg.Rect(panel_x, panel_y, panel_width - 20, 25)
            is_editing = (editing_attribute == attr)
            
            if is_editing:
                pg.draw.rect(screen, (80, 80, 120), attr_rect)
                
            else:
                pg.draw.rect(screen, (60, 60, 60), attr_rect)
                
            pg.draw.rect(screen, (80, 80, 80), attr_rect, 1)
            
            attr_text = font.render(f"{attr}:", True, (255, 255, 255))
            screen.blit(attr_text, (panel_x + 5, panel_y + 3))
            
            if is_editing:
                value_text = font.render(current_attribute_value, True, (255, 255, 0))
                
            else:
                value_text = font.render(str(value), True, (200, 200, 255))
                
            screen.blit(value_text, (panel_x + 120, panel_y + 3))
            
            panel_y += 30
    
    save_rect = pg.Rect(panel_x, screen.get_height() - 40, 100, 30)
    pg.draw.rect(screen, (0, 150, 0), save_rect)
    pg.draw.rect(screen, (0, 200, 0), save_rect, 1)
    save_text = font.render("Save", True, (255, 255, 255))
    screen.blit(save_text, (panel_x + 30, screen.get_height() - 35))
    
    cancel_rect = pg.Rect(panel_x + 110, screen.get_height() - 40, 100, 30)
    pg.draw.rect(screen, (150, 0, 0), cancel_rect)
    pg.draw.rect(screen, (200, 0, 0), cancel_rect, 1)
    cancel_text = font.render("Cancel", True, (255, 255, 255))
    screen.blit(cancel_text, (panel_x + 130, screen.get_height() - 35))
    
    return save_rect, cancel_rect

def draw_version_menu(versions, scroll_offset, selected_index):
    menu_width = 600
    menu_height = 500
    x = (screen.get_width() - menu_width) // 2
    y = (screen.get_height() - menu_height) // 2
    
    pg.draw.rect(screen, (40, 40, 40), (x, y, menu_width, menu_height))
    pg.draw.rect(screen, (70, 70, 70), (x, y, menu_width, menu_height), 2)
    
    title_text = font.render("Version History  —  Press [V] to Close", True, (255, 255, 255))
    screen.blit(title_text, (x + 20, y + 20))
    
    list_y = y + 60
    item_height = 40
    visible_items = (menu_height - 100) // item_height
    
    for i in range(scroll_offset, min(len(versions), scroll_offset + visible_items)):
        version = versions[i]
        item_y = list_y + (i - scroll_offset) * item_height
        
        if i == selected_index:
            pg.draw.rect(screen, (80, 80, 80), (x + 20, item_y, menu_width - 40, 30))
            
        time_text = font.render(version.timestamp, True, (200, 200, 200))
        comment_text = font.render(version.comment[:50], True, (150, 150, 255))
        
        screen.blit(time_text, (x + 30, item_y + 5))
        screen.blit(comment_text, (x + 250, item_y + 5))
        
    if len(versions) > visible_items:
        scroll_height = menu_height - 100
        thumb_height = scroll_height * (visible_items / len(versions))
        pg.draw.rect(screen, (100, 100, 100), 
                    (x + menu_width - 30, list_y, 20, scroll_height))
        
    if selected_index >= 0 and selected_index < len(versions):
        preview_text = font.render(f"Previewing version {versions[selected_index].timestamp}", True, (255, 255, 255))
        screen.blit(preview_text, (x + 20, y + menu_height - 60))
        
        revert_text = font.render("Press R to revert to this version or X to delete", True, (255, 200, 200))
        screen.blit(revert_text, (x + 20, y + menu_height - 30))

def draw_animation_editor(tile, all_tile_surfaces, selected_tile_info, panel_width):
    if not all_tile_surfaces or tile.get("tilesheet", 0) >= len(all_tile_surfaces):
        return
        
    visual_size = all_tile_surfaces[tile.get("tilesheet", 0)]["visual_size"]
    
    menu_width = 600
    menu_height = 400
    x = (screen.get_width() - menu_width) // 2
    y = (screen.get_height() - menu_height) // 2
    
    pg.draw.rect(screen, (40, 40, 40), (x, y, menu_width, menu_height))
    pg.draw.rect(screen, (70, 70, 70), (x, y, menu_width, menu_height), 2)
    
    title_text = font.render("Animation Editor", True, (255, 255, 255))
    screen.blit(title_text, (x + 20, y + 20))
    
    frames_text = font.render("Current Animation Frames:", True, (200, 200, 200))
    screen.blit(frames_text, (x + 20, y + 60))
    
    frame_x = x + 20
    frame_y = y + 90
    for i, frame in enumerate(tile["animation"]["frames"]):
        tilesheet_idx = tile.get("tilesheet", 0)
        if tilesheet_idx < len(all_tile_surfaces) and frame < len(all_tile_surfaces[tilesheet_idx]["surfaces"]):
            screen.blit(all_tile_surfaces[tilesheet_idx]["surfaces"][frame], (frame_x, frame_y))
            
            if i == selected_tile_info.get("selected_frame", 0):
                pg.draw.rect(screen, (0, 255, 0), (frame_x, frame_y, visual_size, visual_size), 2)
            
            num_text = font.render(str(i+1), True, (255, 255, 255))
            screen.blit(num_text, (frame_x + 5, frame_y + 5))
            
            frame_x += visual_size + 10
    
    speed_text = font.render(f"Speed: {tile['animation']['speed']:.2f}s per frame", True, (200, 200, 200))
    screen.blit(speed_text, (x + 20, y + 90 + visual_size + 20))
    
    instructions = [
        "Left/Right: Select frame",
        "F: Add selected tile as frame",
        "Delete: Remove selected frame",
        "Up/Down: Adjust speed",
        "Space: Play/Pause preview",
        "Enter: Save changes",
        "ESC: Cancel"
    ]
    
    for i, line in enumerate(instructions):
        inst_text = font.render(line, True, (150, 150, 255))
        screen.blit(inst_text, (x + menu_width - 200, y + 60 + i * 25))
    
    preview_text = font.render("Preview:", True, (200, 200, 200))
    screen.blit(preview_text, (x + 20, y + 90 + visual_size + 50))
    
    current_time = time.time()
    frames = tile["animation"]["frames"]
    speed = tile["animation"]["speed"]
    frame_idx = int((current_time % (len(frames) * speed)) / speed) if not selected_tile_info.get("pause_preview", False) else selected_tile_info.get("selected_frame", 0)
    
    if frames and frame_idx < len(frames):
        tilesheet_idx = tile.get("tilesheet", 0)
        if tilesheet_idx < len(all_tile_surfaces) and frames[frame_idx] < len(all_tile_surfaces[tilesheet_idx]["surfaces"]):
            preview_tile = all_tile_surfaces[tilesheet_idx]["surfaces"][frames[frame_idx]]
            screen.blit(preview_tile, (x + 100, y + 90 + visual_size + 50))

def handle_animation_editor_events(event, tile, selected_tile_info, all_tile_surfaces):
    if event.type == pg.KEYDOWN:
        if event.key == pg.K_RETURN:
            return True
        
        elif event.key == pg.K_ESCAPE:
            return True
        
        elif event.key == pg.K_LEFT:
            selected_tile_info["selected_frame"] = max(0, selected_tile_info.get("selected_frame", 0) - 1)
            
        elif event.key == pg.K_RIGHT:
            selected_tile_info["selected_frame"] = min(len(tile["animation"]["frames"]) - 1, 
                                                    selected_tile_info.get("selected_frame", 0) + 1)
            
        elif event.key == pg.K_DELETE:
            if "selected_frame" in selected_tile_info and len(tile["animation"]["frames"]) > 1:
                del tile["animation"]["frames"][selected_tile_info["selected_frame"]]
                if selected_tile_info["selected_frame"] >= len(tile["animation"]["frames"]):
                    selected_tile_info["selected_frame"] = len(tile["animation"]["frames"]) - 1
                    
        elif event.key == pg.K_f:
            if "tile" in selected_tile_info and selected_tile_info["tile"] is not None:
                if selected_tile_info["tilesheet"] == tile.get("tilesheet", 0):
                    tile["animation"]["frames"].append(selected_tile_info["tile"])
                    
        elif event.key == pg.K_UP:
            tile["animation"]["speed"] = max(0.05, tile["animation"]["speed"] - 0.05)
            
        elif event.key == pg.K_DOWN:
            tile["animation"]["speed"] = min(2.0, tile["animation"]["speed"] + 0.05)
            
        elif event.key == pg.K_SPACE:
            selected_tile_info["pause_preview"] = not selected_tile_info.get("pause_preview", False)
    
    return False

print("=== Tile Map Editor ===")

mode = ask_input("Edit existing map? (yes/no)", "no").lower()
tiles = []
all_tile_surfaces = []
selected_tile_info = {"tilesheet": 0, "tile": 0}
rotation = 0
current_layer = 0
placing_hitbox = False
camera_x, camera_y = 0, 0
scroll_y = 0
current_panel_width = TILE_PANEL_WIDTH

entity_data = load_entity_data()
selected_entity_type = "items"
selected_entity = None
entity_scroll_y = 0
current_entity_panel_width = ENTITY_PANEL_WIDTH
placing_entity = False
inspecting_entity = None
editing_attribute = None
current_attribute_value = ""

show_version_menu = False
versions = []
version_scroll_offset = 0
selected_version_index = -1
last_save_time = pg.time.get_ticks()

editing_animation = False
current_animated_tile = None

if mode == "yes" or mode == "y":
    map_name = select_map()
    if map_name:
        tiles, tilesheets, map_folder = load_map(map_name)
        all_tile_surfaces = load_tilesheets(tilesheets)
        versions = load_versions(map_folder)
        
    else:
        print("No map selected, exiting.")
        sys.exit()
        
else:
    map_name = ask_input("Enter new map name", "my_map")
    map_folder = os.path.join(MAPS_ROOT, map_name)
    tile_sheet_path = ask_input("Enter tilesheet image path", "assets/sprites/maps/tile_sheets/Assets.png")
    
    while True:
        try:
            tile_dimension = int(ask_input("Enter tile dimension in pixels", "32"))
            break
        
        except ValueError:
            print("Please enter a valid integer.")

    tilesheets = [{
        "path": tile_sheet_path,
        "tile_dimension": tile_dimension
    }]
    
    try:
        all_tile_surfaces = load_tilesheets(tilesheets)
        
    except Exception as e:
        print(f"Failed to load tilesheet: {e}")
        sys.exit()

    tiles = []

clock = pg.time.Clock()
running = True

while running:
    screen.fill((30, 30, 30))
    mx, my = pg.mouse.get_pos()

    visual_size = (all_tile_surfaces[0]["visual_size"] if all_tile_surfaces else BASE_TILE_SIZE * VISUAL_SCALE) * zoom_level

    if not editing_animation:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

            elif event.type == pg.VIDEORESIZE:
                screen = pg.display.set_mode((event.w, event.h), pg.RESIZABLE)
                
            elif event.type == pg.MOUSEWHEEL:
                if pg.key.get_pressed()[pg.K_LCTRL]:
                    if event.y > 0:
                        zoom_level = min(4.0, zoom_level * 1.1)
                    else:
                        zoom_level = max(0.25, zoom_level / 1.1)
                        
                elif show_entity_panel and mx >= screen.get_width() - current_entity_panel_width:
                    entity_scroll_y -= event.y * scroll_speed
                    
                elif mx >= screen.get_width() - current_panel_width:
                    scroll_y -= event.y * scroll_speed
                    if all_tile_surfaces and selected_tile_info["tilesheet"] < len(all_tile_surfaces):
                        tiles_per_row = max(1, (current_panel_width - 10) // (all_tile_surfaces[0]["visual_size"]))
                        rows_needed = (len(all_tile_surfaces[selected_tile_info["tilesheet"]]["surfaces"]) + tiles_per_row - 1) // tiles_per_row
                        max_scroll = max(0, (rows_needed + 1) * all_tile_surfaces[0]["visual_size"] - screen.get_height() + 10)
                        scroll_y = max(0, min(scroll_y, max_scroll))

            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_held = True
                    if show_version_menu:
                        menu_x = (screen.get_width() - 600) // 2
                        menu_y = (screen.get_height() - 500) // 2
                        item_index = version_scroll_offset + ((my - menu_y - 60) // 40)
                        if 0 <= item_index < len(versions):
                            selected_version_index = item_index
                            
                    elif inspecting_entity:
                        save_rect, cancel_rect = draw_entity_inspector(inspecting_entity, entity_data, current_entity_panel_width)
                        
                        if save_rect and save_rect.collidepoint(mx, my):
                            if editing_attribute:
                                try:
                                    if isinstance(entity_data[inspecting_entity["entity_type"]][inspecting_entity["entity_name"]][editing_attribute], bool):
                                        value = current_attribute_value.lower() in ["true", "1", "yes"]
                                        
                                    elif isinstance(entity_data[inspecting_entity["entity_type"]][inspecting_entity["entity_name"]][editing_attribute], int):
                                        value = int(current_attribute_value)
                                        
                                    elif isinstance(entity_data[inspecting_entity["entity_type"]][inspecting_entity["entity_name"]][editing_attribute], float):
                                        value = float(current_attribute_value)
                                        
                                    else:
                                        value = current_attribute_value
                                        
                                    entity_data[inspecting_entity["entity_type"]][inspecting_entity["entity_name"]][editing_attribute] = value
                                    
                                except ValueError:
                                    print("Invalid value for attribute")
                            
                            editing_attribute = None
                            current_attribute_value = ""
                            
                            try:
                                with open(ENTITIES_FILE, 'w') as f:
                                    json.dump(entity_data, f, indent=2)
                                    
                            except Exception as e:
                                print(f"Failed to save entity data: {e}")
                                
                        elif cancel_rect and cancel_rect.collidepoint(mx, my):
                            inspecting_entity = None
                            editing_attribute = None
                            current_attribute_value = ""
                            
                        elif event.button == 1:
                            panel_x = 10
                            panel_y = 10 + 30 * 4
                            
                            if inspecting_entity["entity_type"] in entity_data and inspecting_entity["entity_name"] in entity_data[inspecting_entity["entity_type"]]:
                                entity_info = entity_data[inspecting_entity["entity_type"]][inspecting_entity["entity_name"]]
                                
                                for attr in entity_info:
                                    if attr in ["tile_sheet", "index"]:
                                        continue
                                        
                                    attr_rect = pg.Rect(panel_x, panel_y, current_entity_panel_width - 20, 25)
                                    if attr_rect.collidepoint(mx, my):
                                        editing_attribute = attr
                                        current_attribute_value = str(entity_info[attr])
                                        break
                                        
                                    panel_y += 30
                    elif show_entity_panel:
                        resize_handle_left = screen.get_width() - current_entity_panel_width - 5
                        if (resize_handle_left <= mx <= resize_handle_left + 10 and 
                            0 <= my <= screen.get_height()):
                            resizing_entity_panel = True
                            
                        elif mx >= screen.get_width() - current_entity_panel_width:
                            clicked_type, clicked_entity = entity_selector_click(mx, my, entity_scroll_y, current_entity_panel_width, entity_data, selected_entity_type)
                            if clicked_type:
                                selected_entity_type = clicked_type
                                
                            if clicked_entity:
                                selected_entity = clicked_entity
                                placing_entity = True
                        else:
                            if placing_entity and selected_entity:
                                if precision_mode:
                                    gx = round((mx + camera_x * zoom_level) / visual_size * 2) / 2
                                    gy = round((my + camera_y * zoom_level) / visual_size * 2) / 2
                                    
                                else:
                                    gx = (mx + camera_x * zoom_level) // visual_size
                                    gy = (my + camera_y * zoom_level) // visual_size

                                tiles.append({
                                    "x": gx,
                                    "y": gy,
                                    "type": "entity",
                                    "entity_type": selected_entity_type,
                                    "entity_name": selected_entity,
                                    "layer": current_layer
                                })
                               
                    else:
                        resize_handle_left = screen.get_width() - current_panel_width - 5
                        if (resize_handle_left <= mx <= resize_handle_left + 10 and 
                            0 <= my <= screen.get_height()):
                            resizing_panel = True
                            
                        elif mx >= screen.get_width() - current_panel_width:
                            clicked_tile = tile_selector_click(mx, my, scroll_y, current_panel_width, all_tile_surfaces)
                            if clicked_tile is not None:
                                selected_tile_info = clicked_tile
                                
                        else:
                            if precision_mode:
                                gx = round((mx + camera_x * zoom_level) / visual_size * 2) / 2
                                gy = round((my + camera_y * zoom_level) / visual_size * 2) / 2
                                
                            else:
                                gx = (mx + camera_x * zoom_level) // visual_size
                                gy = (my + camera_y * zoom_level) // visual_size

                            existing = [t for t in tiles 
                                      if abs(t["x"] - gx) < 0.01 and 
                                         abs(t["y"] - gy) < 0.01 and 
                                         t["layer"] == current_layer]
                            
                            for t in existing:
                                tiles.remove(t)

                            last_placed_pos = (gx, gy)
                            new_tile = {
                                "x": gx,
                                "y": gy,
                                "id": selected_tile_info["tile"],
                                "tilesheet": selected_tile_info["tilesheet"],
                                "direction": rotation,
                                "layer": current_layer,
                                "hitbox": placing_hitbox
                            }
                            tiles.append(new_tile)
                            
                            if pg.key.get_pressed()[pg.K_LSHIFT]:
                                highlighted_tiles.append(new_tile)
                                
                            else:
                                highlighted_tiles = [new_tile]

                elif event.button == 3:  # Right click for deletion
                    if not show_version_menu and not inspecting_entity:
                        tile = get_tile_at(mx, my, tiles, all_tile_surfaces, camera_x, camera_y, 
                                        current_layer if layer_mode else None, current_panel_width)
                        if tile:
                            if pg.key.get_pressed()[pg.K_LSHIFT]:
                                if tile in highlighted_tiles:
                                    highlighted_tiles.remove(tile)
                                    
                                else:
                                    highlighted_tiles.append(tile)
                                    
                            else:
                                tiles.remove(tile)
                                if tile in highlighted_tiles:
                                    highlighted_tiles.remove(tile)

            elif event.type == pg.MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_held = False
                    resizing_panel = False
                    resizing_entity_panel = False
                    placing_entity = False
                    last_placed_pos = None

            elif event.type == pg.MOUSEMOTION:
                if mouse_held and not show_version_menu and not inspecting_entity and not show_entity_panel and mx < screen.get_width() - current_panel_width:
                    if precision_mode:
                        gx = round((mx + camera_x * zoom_level) / visual_size * 2) / 2
                        gy = round((my + camera_y * zoom_level) / visual_size * 2) / 2
                        
                    else:
                        gx = (mx + camera_x * zoom_level) // visual_size
                        gy = (my + camera_y * zoom_level) // visual_size

                    if last_placed_pos is None or (gx, gy) != last_placed_pos:
                        existing = [t for t in tiles 
                                  if abs(t["x"] - gx) < 0.01 and 
                                     abs(t["y"] - gy) < 0.01 and 
                                     t["layer"] == current_layer]
                        for t in existing:
                            tiles.remove(t)

                        last_placed_pos = (gx, gy)
                        new_tile = {
                            "x": gx,
                            "y": gy,
                            "id": selected_tile_info["tile"],
                            "tilesheet": selected_tile_info["tilesheet"],
                            "direction": rotation,
                            "layer": current_layer,
                            "hitbox": placing_hitbox
                        }
                        tiles.append(new_tile)
                        
                        if pg.key.get_pressed()[pg.K_LSHIFT]:
                            highlighted_tiles.append(new_tile)
                            
                        else:
                            highlighted_tiles = [new_tile]

                if resizing_panel:
                    new_width = screen.get_width() - mx
                    current_panel_width = max(MIN_TILE_PANEL_WIDTH, min(new_width, screen.get_width() - 200))
                    if all_tile_surfaces and selected_tile_info["tilesheet"] < len(all_tile_surfaces):
                        tiles_per_row = max(1, (current_panel_width - 10) // all_tile_surfaces[0]["visual_size"])
                        rows_needed = (len(all_tile_surfaces[selected_tile_info["tilesheet"]]["surfaces"]) + tiles_per_row - 1) // tiles_per_row
                        max_scroll = max(0, (rows_needed + 1) * all_tile_surfaces[0]["visual_size"] - screen.get_height() + 10)
                        scroll_y = max(0, min(scroll_y, max_scroll))
                        
                elif resizing_entity_panel:
                    new_width = screen.get_width() - mx
                    current_entity_panel_width = max(MIN_ENTITY_PANEL_WIDTH, min(new_width, screen.get_width() - 200))

            elif event.type == pg.KEYDOWN:
                if inspecting_entity and editing_attribute:
                    if event.key == pg.K_RETURN:
                        try:
                            if isinstance(entity_data[inspecting_entity["entity_type"]][inspecting_entity["entity_name"]][editing_attribute], bool):
                                value = current_attribute_value.lower() in ["true", "1", "yes"]
                                
                            elif isinstance(entity_data[inspecting_entity["entity_type"]][inspecting_entity["entity_name"]][editing_attribute], int):
                                value = int(current_attribute_value)
                                
                            elif isinstance(entity_data[inspecting_entity["entity_type"]][inspecting_entity["entity_name"]][editing_attribute], float):
                                value = float(current_attribute_value)
                                
                            else:
                                value = current_attribute_value
                                
                            entity_data[inspecting_entity["entity_type"]][inspecting_entity["entity_name"]][editing_attribute] = value
                            editing_attribute = None
                            current_attribute_value = ""
                            
                            try:
                                with open(ENTITIES_FILE, 'w') as f:
                                    json.dump(entity_data, f, indent=2)
                                    
                            except Exception as e:
                                print(f"Failed to save entity data: {e}")
                                
                        except ValueError:
                            print("Invalid value for attribute")
                            
                    elif event.key == pg.K_ESCAPE:
                        editing_attribute = None
                        current_attribute_value = ""
                        
                    elif event.key == pg.K_BACKSPACE:
                        current_attribute_value = current_attribute_value[:-1]
                        
                    else:
                        current_attribute_value += event.unicode
                        
                elif event.key == pg.K_v:
                    show_version_menu = not show_version_menu
                    selected_version_index = -1
                    if show_version_menu:
                        versions = load_versions(map_folder)
                
                elif event.key == pg.K_r and show_version_menu and selected_version_index >= 0:
                    version = versions[selected_version_index]
                    tiles = version.data['tiles']
                    tilesheets = version.data['tilesheets']
                    all_tile_surfaces = load_tilesheets(tilesheets)
                    show_version_menu = False
                    
                elif event.key == pg.K_x and show_version_menu and selected_version_index >= 0:
                    version = versions[selected_version_index]
                    print("Deleting version:", version.timestamp)
                    del versions[selected_version_index]

                    versions_dir = os.path.join(map_folder, "versions")
                    version_filepath = os.path.normpath(os.path.join(versions_dir, f"version_{version.timestamp}.json"))
                    if os.path.exists(version_filepath):
                        os.remove(version_filepath)
                        print("Deleted:", version_filepath)
                        
                    else:
                        print("File not found:", version_filepath)

                    versions = load_versions(map_folder)

                elif event.key == pg.K_t:
                    show_entity_panel = not show_entity_panel
                    if show_entity_panel:
                        entity_data = load_entity_data()
                        
                    else:
                        inspecting_entity = None

                elif event.key == pg.K_q:
                    save_map(map_folder, tiles, tilesheets)
                    
                elif event.key == pg.K_e:
                    comment = ask_input("Enter save comment (optional)")
                    save_version(map_folder, tiles, tilesheets, comment)
                    versions = load_versions(map_folder)
                    
                elif event.key == pg.K_ESCAPE:
                    show_version_menu = False
                    inspecting_entity = None
                    editing_attribute = None
                    highlighted_tiles = []
                    
                elif not show_version_menu:
                    if event.key == pg.K_LSHIFT:
                        shift_selecting = True
                    elif event.key == pg.K_p:
                        precision_mode = not precision_mode
                        
                    elif event.key == pg.K_RIGHT:
                        if all_tile_surfaces and selected_tile_info["tilesheet"] < len(all_tile_surfaces):
                            selected_tile_info["tile"] = (selected_tile_info["tile"] + 1) % len(all_tile_surfaces[selected_tile_info["tilesheet"]]["surfaces"])
                            
                    elif event.key == pg.K_LEFT:
                        if all_tile_surfaces and selected_tile_info["tilesheet"] < len(all_tile_surfaces):
                            selected_tile_info["tile"] = (selected_tile_info["tile"] - 1) % len(all_tile_surfaces[selected_tile_info["tilesheet"]]["surfaces"])
                            
                    elif event.key == pg.K_r:
                        rotation = (rotation + 90) % 360
                        
                    elif event.key == pg.K_h:
                        placing_hitbox = not placing_hitbox
                        
                    elif event.key == pg.K_k:
                        current_layer -= 1
                        
                    elif event.key == pg.K_l:
                        current_layer += 1
                        
                    elif event.key == pg.K_w:
                        camera_y -= visual_size * 2
                        
                    elif event.key == pg.K_a:
                        camera_x -= visual_size * 2
                        
                    elif event.key == pg.K_d:
                        camera_x += visual_size * 2
                        
                    elif event.key == pg.K_s:
                        camera_y += visual_size * 2
                        
                    elif event.key == pg.K_z:
                        show_layers = not show_layers
                        
                    elif event.key == pg.K_x:
                        layer_mode = not layer_mode
                        
                    elif event.key == pg.K_g:
                        display_hitboxes = not display_hitboxes
                        
                    elif event.key == pg.K_c and copied_tiles:
                        if precision_mode:
                            min_x = min(t["x"] for t in copied_tiles)
                            min_y = min(t["y"] for t in copied_tiles)
                            
                            gx = round((mx + camera_x * zoom_level) / visual_size * 2) / 2
                            gy = round((my + camera_y * zoom_level) / visual_size * 2) / 2
                            
                            for tile in copied_tiles:
                                new_tile = tile.copy()
                                new_tile["x"] = gx + (tile["x"] - min_x)
                                new_tile["y"] = gy + (tile["y"] - min_y)
                                new_tile["layer"] = current_layer
                                
                                tiles.append(new_tile)
                        else:
                            min_x = min(t["x"] for t in copied_tiles)
                            min_y = min(t["y"] for t in copied_tiles)
                            
                            gx = (mx + camera_x * zoom_level) // visual_size
                            gy = (my + camera_y * zoom_level) // visual_size
                            
                            for tile in copied_tiles:
                                new_tile = tile.copy()
                                new_tile["x"] = gx + (tile["x"] - min_x)
                                new_tile["y"] = gy + (tile["y"] - min_y)
                                new_tile["layer"] = current_layer
                                
                                tiles.append(new_tile)
                            
                    elif event.key == pg.K_m:
                        tile = get_tile_at(mx, my, tiles, all_tile_surfaces, camera_x, camera_y, current_layer if layer_mode else None, current_panel_width)
                        if tile:
                            mirrored_tile = tile.copy()
                            mirrored_tile["direction"] = (tile.get("direction", 0) + 180) % 360
                            tiles.append(mirrored_tile)
                            
                    elif event.key == pg.K_0 and highlighted_tiles:
                        copied_tiles = highlighted_tiles.copy()
                        
                    elif event.key == pg.K_c:
                        for tile in reversed(tiles):
                            if tile.get("type") == "entity":
                                tx = tile["x"] * visual_size - camera_x * zoom_level
                                ty = tile["y"] * visual_size - camera_y * zoom_level
                                entity_rect = pg.Rect(tx, ty, visual_size, visual_size)
                                if entity_rect.collidepoint(mx, my):
                                    inspecting_entity = tile
                                    break
                                
                    elif event.key == pg.K_n:
                        new_path = ask_input("Enter path to new tilesheet image")
                        if new_path:
                            try:
                                tile_dim = int(ask_input("Enter tile dimension", "32"))
                                new_sheets = tilesheets.copy()
                                new_sheets.append({
                                    "path": new_path,
                                    "tile_dimension": tile_dim
                                })
                                loaded = load_tilesheets([{"path": new_path, "tile_dimension": tile_dim}])
                                
                                if loaded:
                                    all_tile_surfaces.extend(loaded)
                                    tilesheets = new_sheets
                                    selected_tile_info["tilesheet"] = len(all_tile_surfaces) - 1
                                    selected_tile_info["tile"] = 0
                            except Exception as e:
                                print(f"Failed to add tilesheet: {e}")
                    elif event.key == pg.K_i:
                        tile = get_tile_at(mx, my, tiles, all_tile_surfaces, camera_x, camera_y, 
                                        current_layer if layer_mode else None, current_panel_width)
                        if tile:
                            if "animation" in tile:
                                editing_animation = True
                                current_animated_tile = tile
                                selected_tile_info["selected_frame"] = 0
                                selected_tile_info["pause_preview"] = False
                                
                            else:
                                tile["animation"] = {
                                    "frames": [tile["id"]],
                                    "speed": ANIMATION_SPEED
                                }
                    elif event.key == pg.K_f:
                        tile = get_tile_at(mx, my, tiles, all_tile_surfaces, camera_x, camera_y, current_layer if layer_mode else None, current_panel_width)
                        
                        if tile and "animation" in tile and len(tile["animation"]["frames"]) < MAX_ANIMATION_FRAMES:
                            if mx >= screen.get_width() - current_panel_width:
                                clicked_tile = tile_selector_click(mx, my, scroll_y, current_panel_width, all_tile_surfaces)
                                if (clicked_tile is not None and 
                                    clicked_tile["tilesheet"] == tile.get("tilesheet", 0)):
                                    tile["animation"]["frames"].append(clicked_tile["tile"])

            elif event.type == pg.KEYUP:
                if event.key == pg.K_LSHIFT:
                    shift_selecting = False

    if not editing_animation:
        if all_tile_surfaces:
            draw_tiles(tiles, all_tile_surfaces, camera_x, camera_y, show_layers, current_layer, layer_mode, current_panel_width)
        #draw_grid(current_panel_width) # not drawing for now
        
        if all_tile_surfaces and not show_entity_panel:
            draw_tile_selector(all_tile_surfaces, selected_tile_info, scroll_y, current_panel_width)

        if show_entity_panel:
            draw_entity_selector(entity_data, selected_entity_type, selected_entity, entity_scroll_y, current_entity_panel_width)
            
            if placing_entity and selected_entity and selected_entity_type in entity_data and selected_entity in entity_data[selected_entity_type]:
                preview_data = entity_data[selected_entity_type][selected_entity]
                if "tile_sheet" in preview_data:
                    try:
                        sheet_path, tile_w, tile_h = preview_data["tile_sheet"]
                        sheet = pg.image.load(sheet_path).convert_alpha()
                        row, col = map(int, preview_data["index"].split("_")[1:3])
                        preview = sheet.subsurface((col * tile_w, row * tile_h, tile_w, tile_h))
                        preview = pg.transform.scale(preview, (visual_size, visual_size))
                        preview.fill((255, 255, 255, 150), None, pg.BLEND_RGBA_MULT)
                        screen.blit(preview, (mx - visual_size//2, my - visual_size//2))
                        
                    except Exception as e:
                        print(f"Error drawing entity preview: {e}")
        
        if inspecting_entity:
            draw_entity_inspector(inspecting_entity, entity_data, current_entity_panel_width)

        if mx < screen.get_width() - current_panel_width and all_tile_surfaces and selected_tile_info["tilesheet"] < len(all_tile_surfaces):
            if selected_tile_info["tile"] < len(all_tile_surfaces[selected_tile_info["tilesheet"]]["surfaces"]):
                preview_tile = all_tile_surfaces[selected_tile_info["tilesheet"]]["surfaces"][selected_tile_info["tile"]].copy()
                preview_tile = pg.transform.scale(preview_tile, 
                    (int(preview_tile.get_width() * zoom_level), int(preview_tile.get_height() * zoom_level)))
                preview_tile.fill((255, 255, 255, 128), None, pg.BLEND_RGBA_MULT)
                preview_tile = pg.transform.rotate(preview_tile, rotation)
                
                if precision_mode:
                    px = round((mx + camera_x * zoom_level) / visual_size * 2) / 2 * visual_size - camera_x * zoom_level
                    py = round((my + camera_y * zoom_level) / visual_size * 2) / 2 * visual_size - camera_y * zoom_level
                    
                else:
                    px = ((mx + camera_x * zoom_level) // visual_size) * visual_size - camera_x * zoom_level
                    py = ((my + camera_y * zoom_level) // visual_size) * visual_size - camera_y * zoom_level
                
                screen.blit(preview_tile, (px, py))

        mode_info = []
        if show_layers:
            mode_info.append("SHOWING LAYERS")
            
        if display_hitboxes:
            mode_info.append("SHOWING HITBOXES")
            
        if layer_mode:
            mode_info.append("LAYER MODE")
            
        if precision_mode:
            mode_info.append("PRECISION MODE")
            
        if show_entity_panel:
            mode_info.append("ENTITY MODE")

        info = f"Tile: {selected_tile_info['tile']} (Sheet {selected_tile_info['tilesheet']+1})  Rot: {rotation}°  Layer: {current_layer}  Hitbox: {placing_hitbox}  Camera: ({camera_x}, {camera_y})  Brush: ({mx // visual_size}, {my // visual_size})  Zoom: {zoom_level:.1f}x"
        text = font.render(info, True, (255, 255, 255))
        screen.blit(text, (10, 10))

        if mode_info:
            mode_text = font.render(" | ".join(mode_info), True, (200, 255, 200))
            line_height = text.get_height()
            screen.blit(mode_text, (10, 10 + line_height + 5))

    if show_version_menu:
        draw_version_menu(versions, version_scroll_offset, selected_version_index)

    if editing_animation and current_animated_tile:
        draw_animation_editor(current_animated_tile, all_tile_surfaces, selected_tile_info, current_panel_width)
        
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
                
            elif event.type == pg.KEYDOWN:
                if handle_animation_editor_events(event, current_animated_tile, selected_tile_info, all_tile_surfaces):
                    editing_animation = False
                    current_animated_tile = None

    if (show_entity_panel and 
        screen.get_width() - current_entity_panel_width - 5 <= mx <= screen.get_width() - current_entity_panel_width + 5 and 
        0 <= my <= screen.get_height()):
        
        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_SIZEWE)
    elif (not show_entity_panel and 
          screen.get_width() - current_panel_width - 5 <= mx <= screen.get_width() - current_panel_width + 5 and 
          0 <= my <= screen.get_height()):
        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_SIZEWE)
        
    elif precision_mode:
        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_CROSSHAIR)
        
    else:
        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

    pg.display.flip()
    clock.tick(60)

pg.quit()