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
font_small = pg.font.SysFont("Consolas", 13)

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
editing_instance_key = None
editing_instance_value = ""
mouse_held = False
last_placed_pos = None
zoom_level = 1.0
copied_tiles = []
highlighted_tiles = []
shift_selecting = False
show_entities = True

instance_panel_open = False
instance_panel_width = 280
instance_panel_scroll = 0

entity_preview_cache = {}

editing_animation = False
current_animated_tile = None

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
    except Exception as e:
        print(f"Failed to load map: {e}")
        return None, None, None

    tiles = map_data.get("tiles", [])
    tilesheets = map_data.get("tilesheets", [{
        "path": os.path.normpath(map_data.get("tile_sheet_path", "")),
        "tile_dimension": map_data.get("tile_dimension", 32)
    }])

    for tile in tiles:
        tile.pop("damage", None)
        tile.pop("slippy", None)
        tile.pop("friction", None)
        tile.pop("swimmable", None)
        tile.pop("ripple", None)

    entity_placements = map_data.get("entity_placements", [])
    
    for ep in entity_placements:
        ep.setdefault("overrides", {})
    
    tiles = tiles + entity_placements

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
                "surfaces": [], "tile_size": 32,
                "visual_size": BASE_TILE_SIZE * VISUAL_SCALE,
                "cols": 0, "rows": 0, "scale_factor": 1
            })
    
    return all_surfaces

def load_entity_data():
    try:
        with open(ENTITIES_FILE, "r") as f:
            return json.load(f)
    
    except Exception as e:
        print(f"Failed to load entity data: {e}")
        return {"items": {}, "npcs": {}, "enemies": {}, "actors": {}}

def get_entity_preview(entity_info: dict, size: int = 40):
    tile_sheet = entity_info.get("tile_sheet")
    index = entity_info.get("index")
    
    if not tile_sheet or index is None:
        return None

    sheet_path, tile_w, tile_h = tile_sheet

    if isinstance(index, (list, tuple)) and len(index) == 2:
        row, col = int(index[0]), int(index[1])
    else:
        return None

    cache_key = (sheet_path, tile_w, tile_h, row, col, size)
    
    if cache_key in entity_preview_cache:
        return entity_preview_cache[cache_key]

    try:
        sheet = pg.image.load(sheet_path).convert_alpha()
        tile = sheet.subsurface((col * tile_w, row * tile_h, tile_w, tile_h))
        preview = pg.transform.scale(tile, (size, size))
        entity_preview_cache[cache_key] = preview
        
        return preview
    
    except Exception as e:
        print(f"Entity preview error ({sheet_path}): {e}")
        return None

def save_map(folder, tiles, tilesheets):
    saved_sheets = []
    
    for sheet in tilesheets:
        sheet_filename = os.path.basename(sheet["path"])
        sheet_dest = os.path.join(TILESHEETS_ROOT, sheet_filename)
        
        if not os.path.exists(sheet_dest):
            os.makedirs(TILESHEETS_ROOT, exist_ok=True)
            shutil.copy2(sheet["path"], sheet_dest)
        
        saved_sheets.append({
            "path": os.path.join("assets", "sprites", "maps", "tile_sheets",
                                 sheet_filename).replace("\\", "/"),
            "tile_dimension": sheet["tile_dimension"]
        })

    map_tiles = [t for t in tiles if t.get("type") != "entity"]
    entity_placements = [t for t in tiles if t.get("type") == "entity"]

    map_info = {
        "tilesheets": saved_sheets,
        "tiles": map_tiles,
        "entity_placements": entity_placements
    }

    os.makedirs(folder, exist_ok=True)
    
    with open(os.path.join(folder, "map_info.json"), "w") as f:
        json.dump(map_info, f, indent=2)
    
    print(f"Map saved → {folder}  ({len(map_tiles)} tiles, {len(entity_placements)} entities)")

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
    
    with open(version_path, "w") as f:
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
                with open(os.path.join(versions_dir, fname), "r") as f:
                    data = json.load(f)
                versions.append(VersionEntry(data["timestamp"], data["comment"], data))
            
            except:
                pass
    
    return versions

def draw_grid(panel_width):
    visual_size = (all_tile_surfaces[0]["visual_size"] if all_tile_surfaces
                   else BASE_TILE_SIZE * VISUAL_SCALE) * zoom_level
    
    for x in range(0, int((screen.get_width() - panel_width) / zoom_level), int(visual_size)):
        pg.draw.line(screen, (50, 50, 50), (x * zoom_level, 0),
                     (x * zoom_level, screen.get_height()))
    
    for y in range(0, int(screen.get_height() / zoom_level), int(visual_size)):
        pg.draw.line(screen, (50, 50, 50), (0, y * zoom_level),
                     ((screen.get_width() - panel_width), y * zoom_level))

def draw_tiles(tiles, all_tile_surfaces, camera_x, camera_y,
               show_layers=False, current_layer=0, layer_mode=False, panel_width=256):
    current_time = time.time()
    
    regular_tiles = [t for t in tiles if t.get("type") != "entity"]
    
    for tile in sorted(regular_tiles, key=lambda t: t["layer"]):
        visual_size = all_tile_surfaces[tile.get("tilesheet", 0)]["visual_size"] * zoom_level
        tx = tile["x"] * visual_size - camera_x * zoom_level
        ty = tile["y"] * visual_size - camera_y * zoom_level

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
                img = pg.transform.scale(img,
                    (int(img.get_width() * zoom_level), int(img.get_height() * zoom_level)))
                img = pg.transform.rotate(img, tile.get("direction", 0))
                
                if layer_mode and tile["layer"] != current_layer:
                    img.fill((255, 255, 255, 96), None, pg.BLEND_RGBA_MULT)
                
                screen.blit(img, (tx, ty))

        if show_layers:
            layer_text = font.render(str(tile["layer"]), True, (255, 255, 255))
            text_rect = layer_text.get_rect(center=(tx + visual_size // 2, ty + visual_size // 2))
            screen.blit(layer_text, text_rect)

        if display_hitboxes and tile.get("hitbox", False):
            pg.draw.rect(screen, (255, 0, 0), (tx, ty, visual_size, visual_size), 2)

        if tile in highlighted_tiles:
            pg.draw.rect(screen, (0, 255, 255), (tx, ty, visual_size, visual_size), 3)
    
    if show_entities:
        entity_tiles = [t for t in tiles if t.get("type") == "entity"]
        
        for tile in entity_tiles:
            visual_size = all_tile_surfaces[0]["visual_size"] * zoom_level
            tx = tile["x"] * visual_size - camera_x * zoom_level
            ty = tile["y"] * visual_size - camera_y * zoom_level
            
            ent_type = tile.get("entity_type", "items")
            ent_name = tile.get("entity_name", "")
            
            singular_to_plural = {"item": "items", "npc": "npcs", "enemy": "enemies", "actor": "actors"}
            lookup_type = singular_to_plural.get(ent_type, ent_type)
            
            ent_info = entity_data.get(lookup_type, {}).get(ent_name)
            preview = get_entity_preview(ent_info, int(visual_size)) if ent_info else None
            
            if preview:
                screen.blit(preview, (tx, ty))
                
            else:
                pg.draw.rect(screen, (200, 100, 200), (tx, ty, visual_size, visual_size))
            
            label = font_small.render(ent_name[:8], True, (255, 255, 255))
            bg_rect = pg.Rect(tx, ty + visual_size - 16, visual_size, 16)
            pg.draw.rect(screen, (0, 0, 0), bg_rect)
            screen.blit(label, (tx + 2, ty + visual_size - 15))
            
            if tile.get("overrides"):
                badge = font_small.render("✎", True, (255, 220, 0))
                screen.blit(badge, (tx + 2, ty + 2))
            
            if show_layers:
                layer_text = font.render(str(tile["layer"]), True, (255, 255, 255))
                text_rect = layer_text.get_rect(center=(tx + visual_size // 2, ty + visual_size // 2))
                screen.blit(layer_text, text_rect)
            
            if tile in highlighted_tiles:
                pg.draw.rect(screen, (0, 255, 255), (tx, ty, visual_size, visual_size), 3)

def get_tile_at(mx, my, tiles, all_tile_surfaces, camera_x, camera_y,
                current_layer=None, panel_width=256, prefer_entities=False):
    if mx > screen.get_width() - panel_width:
        return None
    
    visual_size = (all_tile_surfaces[0]["visual_size"] if all_tile_surfaces
                   else BASE_TILE_SIZE * VISUAL_SCALE) * zoom_level
    
    if precision_mode:
        gx = round((mx + camera_x * zoom_level) / visual_size * 2) / 2
        gy = round((my + camera_y * zoom_level) / visual_size * 2) / 2
        
        matches = []
        for t in tiles:
            if (abs(t["x"] - gx) < 0.01 and abs(t["y"] - gy) < 0.01 and
                    (current_layer is None or t["layer"] == current_layer)):
                if t.get("type") == "entity" and not show_entities:
                    continue
                matches.append(t)
    
    else:
        gx = (mx + camera_x * zoom_level) // visual_size
        gy = (my + camera_y * zoom_level) // visual_size
        
        matches = []
        for t in tiles:
            if (t["x"] == gx and t["y"] == gy and
                    (current_layer is None or t["layer"] == current_layer)):
                if t.get("type") == "entity" and not show_entities:
                    continue
                matches.append(t)
    
    if not matches:
        return None
    
    if prefer_entities:
        for match in matches:
            if match.get("type") == "entity":
                return match
    
    return matches[0]

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
            
            if i == selected_tile_info["tile"]:
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
    idx = int(row * tiles_per_row + col)
    current_sheet = all_tile_surfaces[selected_tile_info["tilesheet"]]
    
    if 0 <= idx < len(current_sheet["surfaces"]):
        return {"tilesheet": selected_tile_info["tilesheet"], "tile": idx}
    
    return None

def draw_entity_selector(entity_data, selected_entity_type, selected_entity,
                         scroll_y, panel_width):
    panel_rect = pg.Rect(screen.get_width() - panel_width, 0, panel_width, screen.get_height())
    pg.draw.rect(screen, (25, 25, 35), panel_rect)
    pg.draw.rect(screen, (70, 70, 100), panel_rect, 2)
    
    resize_handle = pg.Rect(screen.get_width() - panel_width - 5, 0, 10, screen.get_height())
    pg.draw.rect(screen, (100, 100, 100), resize_handle)
    
    panel_x = screen.get_width() - panel_width + 5
    panel_y = 5 - scroll_y

    for i, entity_type in enumerate(ENTITY_TYPES):
        tab_width = panel_width // len(ENTITY_TYPES)
        tab_rect = pg.Rect(panel_x + i * tab_width, panel_y, tab_width, 30)
        color = (60, 60, 80) if selected_entity_type != entity_type else (90, 90, 130)
        pg.draw.rect(screen, color, tab_rect)
        pg.draw.rect(screen, (50, 50, 70), tab_rect, 1)
        label = font_small.render(entity_type.capitalize(), True, (220, 220, 255))
        screen.blit(label, (tab_rect.x + 4, tab_rect.y + 7))

    if entity_data and selected_entity_type in entity_data:
        entities = entity_data[selected_entity_type]
        item_height = 58
        
        for i, (name, data) in enumerate(entities.items()):
            y = panel_y + 30 + i * item_height
            
            if y + item_height > 0 and y < screen.get_height():
                entry_rect = pg.Rect(panel_x, y, panel_width - 10, item_height - 4)
                is_selected = (selected_entity == name)
                color = (50, 50, 70) if not is_selected else (75, 75, 110)
                pg.draw.rect(screen, color, entry_rect)
                pg.draw.rect(screen, (70, 70, 100), entry_rect, 1)

                preview = get_entity_preview(data, 44)
                
                if preview:
                    screen.blit(preview, (panel_x + 4, y + 7))
                    text_x = panel_x + 54
                
                else:
                    ph = pg.Surface((44, 44), pg.SRCALPHA)
                    ph.fill((120, 60, 120, 180))
                    screen.blit(ph, (panel_x + 4, y + 7))
                    text_x = panel_x + 54

                name_text = font.render(name, True, (255, 255, 255))
                screen.blit(name_text, (text_x, y + 8))
                
                type_label = data.get("type", "?")
                type_text = font_small.render(type_label, True, (160, 160, 200))
                screen.blit(type_text, (text_x, y + 30))

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
    item_height = 58
    entity_idx = int(rel_y // item_height)
    
    if selected_entity_type in entity_data:
        entities = list(entity_data[selected_entity_type].items())
        
        if 0 <= entity_idx < len(entities):
            return selected_entity_type, entities[entity_idx][0]
    
    return None, None

SKIP_INSTANCE_KEYS = {"tile_sheet", "index", "states", "script", "entity_abilities"}

EDITABLE_INSTANCE_DEFAULTS = [
    "health", "max_health", "width", "height",
    "hitbox_width", "hitbox_height", "move_speed",
    "attack_damage", "aggro_range", "jump_force",
    "push_force", "value", "quantity", "animation_speed",
]

def draw_instance_panel(tile, entity_data):
    global instance_panel_scroll
    
    pw = instance_panel_width
    ph = screen.get_height()
    pg.draw.rect(screen, (20, 20, 30), (0, 0, pw, ph))
    pg.draw.rect(screen, (80, 80, 120), (0, 0, pw, ph), 2)

    rects = {}
    y = 10 - instance_panel_scroll

    etype = tile.get("entity_type", "?")
    ename = tile.get("entity_name", "?")
    header = font.render(f"Instance: {ename}", True, (255, 220, 80))
    screen.blit(header, (8, y))
    y += 22
    
    sub = font_small.render(f"type: {etype}  layer: {tile.get('layer',0)}", True, (160, 160, 200))
    screen.blit(sub, (8, y))
    y += 20

    plural = {"item": "items", "npc": "npcs", "enemy": "enemies", "actor": "actors"}
    data_key = plural.get(etype, etype)
    ent_info = entity_data.get(data_key, entity_data.get(etype, {})).get(ename, {})
    preview = get_entity_preview(ent_info, 64)
    
    if preview:
        screen.blit(preview, (pw // 2 - 32, y))

    y += 72

    pg.draw.line(screen, (80, 80, 120), (4, y), (pw - 4, y), 1)
    y += 8

    overrides = tile.setdefault("overrides", {})

    base_keys = [k for k in ent_info.keys() if k not in SKIP_INSTANCE_KEYS
                 and isinstance(ent_info[k], (int, float, str, bool))]
    
    all_keys = list(dict.fromkeys(base_keys + EDITABLE_INSTANCE_DEFAULTS))
    
    for k in overrides:
        if k not in all_keys:
            all_keys.append(k)

    instr = font_small.render("[Click val to edit]  [Del to remove override]", True, (120, 120, 160))
    screen.blit(instr, (4, y))
    y += 18

    for key in all_keys:
        if y > screen.get_height() + instance_panel_scroll:
            break
        
        if y < -20:
            y += 24
            continue

        base_val = ent_info.get(key, "—")
        override_val = overrides.get(key)
        has_override = key in overrides

        row_rect = pg.Rect(4, y, pw - 8, 22)
        bg_color = (40, 40, 60) if not has_override else (60, 40, 80)
        pg.draw.rect(screen, bg_color, row_rect)
        pg.draw.rect(screen, (80, 80, 120) if has_override else (50, 50, 70), row_rect, 1)

        if editing_instance_key == key:
            pg.draw.rect(screen, (100, 80, 160), row_rect, 2)

        key_surf = font_small.render(key + ":", True, (200, 200, 220))
        screen.blit(key_surf, (8, y + 3))

        if editing_instance_key == key:
            val_text = editing_instance_value + "|"
            val_col = (255, 255, 100)
        
        elif has_override:
            val_text = str(override_val)
            val_col = (255, 180, 80)
        
        else:
            val_text = str(base_val)
            val_col = (140, 140, 160)

        val_surf = font_small.render(val_text, True, val_col)
        screen.blit(val_surf, (pw - val_surf.get_width() - 6, y + 3))

        rects[key] = row_rect
        y += 24

    close_rect = pg.Rect(4, ph - 34, pw - 8, 28)
    pg.draw.rect(screen, (100, 40, 40), close_rect)
    pg.draw.rect(screen, (180, 60, 60), close_rect, 1)
    ct = font.render("Close  [I]", True, (255, 200, 200))
    screen.blit(ct, (close_rect.centerx - ct.get_width() // 2, close_rect.y + 5))
    rects["__close__"] = close_rect

    return rects

def draw_version_menu(versions, scroll_offset, selected_index):
    menu_width, menu_height = 600, 500
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
    
    if selected_index >= 0 and selected_index < len(versions):
        preview_text = font.render(
            f"Previewing version {versions[selected_index].timestamp}", True, (255, 255, 255))
        screen.blit(preview_text, (x + 20, y + menu_height - 60))
        
        revert_text = font.render("Press R to revert or X to delete", True, (255, 200, 200))
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
    
    frame_x = x + 20
    frame_y = y + 90
    
    for i, frame in enumerate(tile["animation"]["frames"]):
        tilesheet_idx = tile.get("tilesheet", 0)
        if (tilesheet_idx < len(all_tile_surfaces) and
                frame < len(all_tile_surfaces[tilesheet_idx]["surfaces"])):
            screen.blit(all_tile_surfaces[tilesheet_idx]["surfaces"][frame], (frame_x, frame_y))
            
            if i == selected_tile_info.get("selected_frame", 0):
                pg.draw.rect(screen, (0, 255, 0), (frame_x, frame_y, visual_size, visual_size), 2)
            
            num_text = font.render(str(i + 1), True, (255, 255, 255))
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
        inst_text = font_small.render(line, True, (150, 150, 255))
        screen.blit(inst_text, (x + menu_width - 200, y + 60 + i * 25))
    
    preview_text = font.render("Preview:", True, (200, 200, 200))
    screen.blit(preview_text, (x + 20, y + 90 + visual_size + 50))
    
    current_time = time.time()
    frames = tile["animation"]["frames"]
    speed = tile["animation"]["speed"]
    frame_idx = (int((current_time % (len(frames) * speed)) / speed)
                 if not selected_tile_info.get("pause_preview", False)
                 else selected_tile_info.get("selected_frame", 0))
    
    if frames and frame_idx < len(frames):
        tilesheet_idx = tile.get("tilesheet", 0)
        if (tilesheet_idx < len(all_tile_surfaces) and
                frames[frame_idx] < len(all_tile_surfaces[tilesheet_idx]["surfaces"])):
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
            if selected_tile_info.get("tile") is not None:
                if selected_tile_info["tilesheet"] == tile.get("tilesheet", 0):
                    if len(tile["animation"]["frames"]) < MAX_ANIMATION_FRAMES:
                        tile["animation"]["frames"].append(selected_tile_info["tile"])
                    
        elif event.key == pg.K_UP:
            tile["animation"]["speed"] = max(0.05, tile["animation"]["speed"] - 0.05)
            
        elif event.key == pg.K_DOWN:
            tile["animation"]["speed"] = min(2.0, tile["animation"]["speed"] + 0.05)
            
        elif event.key == pg.K_SPACE:
            selected_tile_info["pause_preview"] = not selected_tile_info.get("pause_preview", False)
    
    return False

def commit_instance_edit(tile, key, raw_value, entity_data):
    etype = tile.get("entity_type", "")
    ename = tile.get("entity_name", "")
    plural = {"item": "items", "npc": "npcs", "enemy": "enemies", "actor": "actors"}
    data_key = plural.get(etype, etype)
    base = entity_data.get(data_key, entity_data.get(etype, {})).get(ename, {})
    base_val = base.get(key)
    overrides = tile.setdefault("overrides", {})

    if not raw_value.strip():
        overrides.pop(key, None)
        return

    try:
        if isinstance(base_val, bool):
            overrides[key] = raw_value.lower() in ("true", "1", "yes")

        elif isinstance(base_val, int):
            overrides[key] = int(raw_value)

        elif isinstance(base_val, float):
            overrides[key] = float(raw_value)

        else:
            overrides[key] = raw_value

    except ValueError:
        try:
            overrides[key] = float(raw_value)

        except ValueError:
            overrides[key] = raw_value

print("=== Tile Map Editor ===")

mode = ask_input("Edit existing map? (yes/no)", "no").lower()
tiles = []
all_tile_surfaces = []
selected_tile_info = {"tilesheet": 0, "tile": 0, "selected_frame": 0, "pause_preview": False}
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

show_version_menu = False
versions = []
version_scroll_offset = 0
selected_version_index = -1

instance_panel_open = False
instance_panel_tile = None
instance_panel_row_rects = {}
editing_instance_key = None
editing_instance_value = ""
instance_panel_scroll = 0

if mode in ("yes", "y"):
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
    tile_sheet_path = ask_input("Enter tilesheet image path",
                                "assets/sprites/maps/tile_sheets/Assets.png")
    
    while True:
        try:
            tile_dimension = int(ask_input("Enter tile dimension in pixels", "32"))
            break
        
        except ValueError:
            print("Please enter a valid integer.")
    
    tilesheets = [{"path": tile_sheet_path, "tile_dimension": tile_dimension}]
    
    try:
        all_tile_surfaces = load_tilesheets(tilesheets)
    
    except Exception as e:
        print(f"Failed to load tilesheet: {e}")
        sys.exit()
    
    tiles = []

clock = pg.time.Clock()
running = True
resizing_entity_panel = False

while running:
    screen.fill((30, 30, 30))
    mx, my = pg.mouse.get_pos()

    visual_size = (all_tile_surfaces[0]["visual_size"] if all_tile_surfaces
                   else BASE_TILE_SIZE * VISUAL_SCALE) * zoom_level

    active_right_panel = current_entity_panel_width if show_entity_panel else current_panel_width

    if not editing_animation:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

            elif event.type == pg.VIDEORESIZE:
                screen = pg.display.set_mode((event.w, event.h), pg.RESIZABLE)

            elif event.type == pg.MOUSEWHEEL:
                if instance_panel_open and mx < instance_panel_width and show_entities:
                    instance_panel_scroll = max(0, instance_panel_scroll - event.y * 20)
                
                elif pg.key.get_pressed()[pg.K_LCTRL]:
                    if event.y > 0:
                        zoom_level = min(4.0, zoom_level * 1.1)
                    
                    else:
                        zoom_level = max(0.25, zoom_level / 1.1)
                
                elif show_entity_panel and mx >= screen.get_width() - current_entity_panel_width and show_entities:
                    entity_scroll_y -= event.y * scroll_speed
                
                elif mx >= screen.get_width() - current_panel_width:
                    scroll_y -= event.y * scroll_speed
                    
                    if all_tile_surfaces and selected_tile_info["tilesheet"] < len(all_tile_surfaces):
                        tiles_per_row = max(1, (current_panel_width - 10) //
                                           all_tile_surfaces[0]["visual_size"])
                        rows_needed = (len(all_tile_surfaces[selected_tile_info["tilesheet"]]["surfaces"])
                                       + tiles_per_row - 1) // tiles_per_row
                        max_scroll = max(0, (rows_needed + 1) * all_tile_surfaces[0]["visual_size"]
                                         - screen.get_height() + 10)
                        scroll_y = max(0, min(scroll_y, max_scroll))

            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_held = True

                    if instance_panel_open and mx < instance_panel_width and show_entities:
                        clicked_key = None
                        
                        for k, r in instance_panel_row_rects.items():
                            if r.collidepoint(mx, my):
                                clicked_key = k
                                break

                        if clicked_key == "__close__":
                            instance_panel_open = False
                            instance_panel_tile = None
                            editing_instance_key = None
                        
                        elif clicked_key is not None:
                            if editing_instance_key == clicked_key:
                                pass
                            
                            else:
                                if editing_instance_key and instance_panel_tile is not None:
                                    commit_instance_edit(
                                        instance_panel_tile, editing_instance_key,
                                        editing_instance_value, entity_data)
                                
                                editing_instance_key = clicked_key
                                etype = instance_panel_tile.get("entity_type", "")
                                ename = instance_panel_tile.get("entity_name", "")
                                plural = {"item": "items", "npc": "npcs", "enemy": "enemies", "actor": "actors"}
                                data_key = plural.get(etype, etype)
                                base = entity_data.get(data_key, entity_data.get(etype, {})).get(ename, {})
                                ov = instance_panel_tile.get("overrides", {})
                                editing_instance_value = str(ov.get(clicked_key, base.get(clicked_key, "")))
                        
                        continue

                    if show_version_menu:
                        menu_x = (screen.get_width() - 600) // 2
                        menu_y = (screen.get_height() - 500) // 2
                        item_index = version_scroll_offset + ((my - menu_y - 60) // 40)
                        
                        if 0 <= item_index < len(versions):
                            selected_version_index = item_index

                    elif show_entity_panel and show_entities:
                        resize_handle_left = screen.get_width() - current_entity_panel_width - 5
                        
                        if (resize_handle_left <= mx <= resize_handle_left + 10):
                            resizing_entity_panel = True
                        
                        elif mx >= screen.get_width() - current_entity_panel_width:
                            clicked_type, clicked_entity = entity_selector_click(
                                mx, my, entity_scroll_y, current_entity_panel_width,
                                entity_data, selected_entity_type)
                            
                            if clicked_type and clicked_type != selected_entity_type:
                                selected_entity_type = clicked_type
                                selected_entity = None
                                placing_entity = False
                            
                            elif clicked_entity:
                                if clicked_entity == selected_entity and placing_entity:
                                    selected_entity = None
                                    placing_entity = False
                                
                                else:
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

                                type_map = {"items": "item", "npcs": "npc", "enemies": "enemy", "actors": "actor"}
                                
                                new_entity_tile = {
                                    "x": gx,
                                    "y": gy,
                                    "type": "entity",
                                    "entity_type": type_map.get(selected_entity_type, selected_entity_type),
                                    "entity_name": selected_entity,
                                    "layer": current_layer,
                                    "overrides": {}
                                }
                                
                                tiles.append(new_entity_tile)

                    else:
                        resize_handle_left = screen.get_width() - current_panel_width - 5
                        
                        if (resize_handle_left <= mx <= resize_handle_left + 10):
                            resizing_panel = True
                        
                        elif mx >= screen.get_width() - current_panel_width:
                            clicked_tile = tile_selector_click(
                                mx, my, scroll_y, current_panel_width, all_tile_surfaces)
                            
                            if clicked_tile is not None:
                                selected_tile_info = clicked_tile
                                selected_tile_info["selected_frame"] = 0
                                selected_tile_info["pause_preview"] = False
                        
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
                                        t["layer"] == current_layer and
                                        t.get("type") != "entity"]
                            
                            for t in existing:
                                tiles.remove(t)

                            last_placed_pos = (gx, gy)
                            
                            new_tile = {
                                "x": gx, "y": gy,
                                "id": selected_tile_info["tile"],
                                "tilesheet": selected_tile_info["tilesheet"],
                                "direction": rotation,
                                "layer": current_layer,
                                "hitbox": placing_hitbox
                            }
                            
                            tiles.append(new_tile)
                            highlighted_tiles = ([new_tile] if not pg.key.get_pressed()[pg.K_LSHIFT]
                                                 else highlighted_tiles + [new_tile])

                elif event.button == 3:
                    if not show_version_menu and not (instance_panel_open and mx < instance_panel_width):
                        if not show_entities:
                            hit = get_tile_at(mx, my, tiles, all_tile_surfaces, camera_x, camera_y,
                                            current_layer if layer_mode else None, active_right_panel, prefer_entities=False)
                        else:
                            hit = get_tile_at(mx, my, tiles, all_tile_surfaces, camera_x, camera_y,
                                            current_layer if layer_mode else None, active_right_panel, prefer_entities=True)
                        
                        if hit:
                            if show_entity_panel and show_entities:
                                if hit.get("type") == "entity":
                                    tiles.remove(hit)
                                    
                                    if instance_panel_tile is hit:
                                        instance_panel_open = False
                                        instance_panel_tile = None
                                    
                                    if hit in highlighted_tiles:
                                        highlighted_tiles.remove(hit)
                            
                            elif hit.get("type") != "entity":
                                if pg.key.get_pressed()[pg.K_LSHIFT]:
                                    if hit in highlighted_tiles:
                                        highlighted_tiles.remove(hit)
                                    
                                    else:
                                        highlighted_tiles.append(hit)
                                
                                else:
                                    tiles.remove(hit)
                                    
                                    if hit in highlighted_tiles:
                                        highlighted_tiles.remove(hit)

            elif event.type == pg.MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_held = False
                    resizing_panel = False
                    resizing_entity_panel = False
                    last_placed_pos = None

            elif event.type == pg.MOUSEMOTION:
                if (mouse_held and not show_version_menu and not show_entity_panel
                    and mx < screen.get_width() - current_panel_width
                    and not (instance_panel_open and mx < instance_panel_width)):
                    
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
                                    t["layer"] == current_layer and
                                    t.get("type") != "entity"]
                        
                        for t in existing:
                            tiles.remove(t)
                        
                        last_placed_pos = (gx, gy)
                        
                        new_tile = {
                            "x": gx, "y": gy,
                            "id": selected_tile_info["tile"],
                            "tilesheet": selected_tile_info["tilesheet"],
                            "direction": rotation,
                            "layer": current_layer,
                            "hitbox": placing_hitbox
                        }
                        
                        tiles.append(new_tile)
                        highlighted_tiles = ([new_tile] if not pg.key.get_pressed()[pg.K_LSHIFT]
                                             else highlighted_tiles + [new_tile])

                if resizing_panel:
                    new_width = screen.get_width() - mx
                    current_panel_width = max(MIN_TILE_PANEL_WIDTH,
                                              min(new_width, screen.get_width() - 200))
                
                elif resizing_entity_panel and show_entities:
                    new_width = screen.get_width() - mx
                    current_entity_panel_width = max(MIN_ENTITY_PANEL_WIDTH,
                                                     min(new_width, screen.get_width() - 200))

            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_y:
                    show_entities = not show_entities
                    if not show_entities:
                        instance_panel_open = False
                        instance_panel_tile = None
                        placing_entity = False
                    continue
                
                if instance_panel_open and editing_instance_key is not None and show_entities:
                    if event.key == pg.K_RETURN:
                        commit_instance_edit(
                            instance_panel_tile, editing_instance_key,
                            editing_instance_value, entity_data)
                        editing_instance_key = None
                        editing_instance_value = ""
                    
                    elif event.key == pg.K_ESCAPE:
                        editing_instance_key = None
                        editing_instance_value = ""
                    
                    elif event.key == pg.K_BACKSPACE:
                        editing_instance_value = editing_instance_value[:-1]
                    
                    elif event.key == pg.K_DELETE:
                        instance_panel_tile.get("overrides", {}).pop(editing_instance_key, None)
                        editing_instance_key = None
                        editing_instance_value = ""
                    
                    else:
                        editing_instance_value += event.unicode
                    
                    continue

                if event.key == pg.K_i and show_entities:
                    hit = get_tile_at(mx, my, tiles, all_tile_surfaces, camera_x, camera_y,
                                      current_layer if layer_mode else None, active_right_panel, prefer_entities=True)
                    
                    if hit and hit.get("type") == "entity":
                        if instance_panel_open and instance_panel_tile is hit:
                            instance_panel_open = False
                            instance_panel_tile = None
                        
                        else:
                            instance_panel_open = True
                            instance_panel_tile = hit
                            editing_instance_key = None
                            editing_instance_value = ""
                            instance_panel_scroll = 0
                    
                    elif not hit:
                        instance_panel_open = False
                
                elif event.key == pg.K_i and not show_entities:
                    hit = get_tile_at(mx, my, tiles, all_tile_surfaces, camera_x, camera_y,
                                      current_layer if layer_mode else None, active_right_panel, prefer_entities=False)
                    
                    if hit and hit.get("type") != "entity":
                        if "animation" in hit:
                            editing_animation = True
                            current_animated_tile = hit
                            selected_tile_info["selected_frame"] = 0
                            selected_tile_info["pause_preview"] = False
                        
                        else:
                            hit["animation"] = {
                                "frames": [hit["id"]],
                                "speed": ANIMATION_SPEED
                            }
                            editing_animation = True
                            current_animated_tile = hit
                            selected_tile_info["selected_frame"] = 0
                            selected_tile_info["pause_preview"] = False

                elif event.key == pg.K_v:
                    show_version_menu = not show_version_menu
                    selected_version_index = -1
                    
                    if show_version_menu:
                        versions = load_versions(map_folder)

                elif event.key == pg.K_r and show_version_menu and selected_version_index >= 0:
                    version = versions[selected_version_index]
                    tiles = version.data["tiles"]
                    tilesheets = version.data["tilesheets"]
                    all_tile_surfaces = load_tilesheets(tilesheets)
                    show_version_menu = False

                elif event.key == pg.K_x and show_version_menu and selected_version_index >= 0:
                    version = versions[selected_version_index]
                    del versions[selected_version_index]
                    versions_dir = os.path.join(map_folder, "versions")
                    version_filepath = os.path.join(versions_dir, f"version_{version.timestamp}.json")
                    
                    if os.path.exists(version_filepath):
                        os.remove(version_filepath)
                    
                    versions = load_versions(map_folder)

                elif event.key == pg.K_t:
                    show_entity_panel = not show_entity_panel
                    
                    if show_entity_panel:
                        entity_data = load_entity_data()
                    
                    else:
                        placing_entity = False

                elif event.key == pg.K_q:
                    save_map(map_folder, tiles, tilesheets)

                elif event.key == pg.K_e:
                    comment = ask_input("Enter save comment (optional)", "")
                    save_version(map_folder, tiles, tilesheets, comment)
                    versions = load_versions(map_folder)

                elif event.key == pg.K_ESCAPE:
                    show_version_menu = False
                    editing_instance_key = None
                    highlighted_tiles = []
                    placing_entity = False
                    
                    if instance_panel_open:
                        instance_panel_open = False
                        instance_panel_tile = None

                elif event.key == pg.K_DELETE and show_entities:
                    if instance_panel_open and instance_panel_tile is not None:
                        if instance_panel_tile in tiles:
                            tiles.remove(instance_panel_tile)
                        
                        instance_panel_open = False
                        instance_panel_tile = None
                        editing_instance_key = None

                elif not show_version_menu:
                    if event.key == pg.K_p:
                        precision_mode = not precision_mode
                    
                    elif event.key == pg.K_RIGHT:
                        if all_tile_surfaces and selected_tile_info["tilesheet"] < len(all_tile_surfaces):
                            selected_tile_info["tile"] = (
                                (selected_tile_info["tile"] + 1) %
                                len(all_tile_surfaces[selected_tile_info["tilesheet"]]["surfaces"]))
                    
                    elif event.key == pg.K_LEFT:
                        if all_tile_surfaces and selected_tile_info["tilesheet"] < len(all_tile_surfaces):
                            selected_tile_info["tile"] = (
                                (selected_tile_info["tile"] - 1) %
                                len(all_tile_surfaces[selected_tile_info["tilesheet"]]["surfaces"]))
                    
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
                    
                    elif event.key == pg.K_0 and highlighted_tiles:
                        copied_tiles = highlighted_tiles.copy()
                    
                    elif event.key == pg.K_c and copied_tiles:
                        min_x = min(t["x"] for t in copied_tiles)
                        min_y = min(t["y"] for t in copied_tiles)
                        
                        gx = (round((mx + camera_x * zoom_level) / visual_size * 2) / 2
                              if precision_mode else
                              (mx + camera_x * zoom_level) // visual_size)
                        
                        gy = (round((my + camera_y * zoom_level) / visual_size * 2) / 2
                              if precision_mode else
                              (my + camera_y * zoom_level) // visual_size)
                        
                        for t in copied_tiles:
                            nt = t.copy()
                            nt["x"] = gx + (t["x"] - min_x)
                            nt["y"] = gy + (t["y"] - min_y)
                            nt["layer"] = current_layer
                            tiles.append(nt)
                    
                    elif event.key == pg.K_n:
                        new_path = ask_input("Enter path to new tilesheet image")
                        
                        if new_path:
                            try:
                                tile_dim = int(ask_input("Enter tile dimension", "32"))
                                loaded = load_tilesheets([{"path": new_path, "tile_dimension": tile_dim}])
                                
                                if loaded:
                                    all_tile_surfaces.extend(loaded)
                                    tilesheets.append({"path": new_path, "tile_dimension": tile_dim})
                                    selected_tile_info["tilesheet"] = len(all_tile_surfaces) - 1
                                    selected_tile_info["tile"] = 0
                            
                            except Exception as e:
                                print(f"Failed to add tilesheet: {e}")

    if not editing_animation:
        if all_tile_surfaces:
            draw_tiles(tiles, all_tile_surfaces, camera_x, camera_y,
                       show_layers, current_layer, layer_mode, active_right_panel)

        if all_tile_surfaces and not show_entity_panel:
            draw_tile_selector(all_tile_surfaces, selected_tile_info, scroll_y, current_panel_width)

        if show_entity_panel and show_entities:
            draw_entity_selector(entity_data, selected_entity_type, selected_entity,
                                 entity_scroll_y, current_entity_panel_width)
            
            if placing_entity and selected_entity:
                ent_info = entity_data.get(selected_entity_type, {}).get(selected_entity, {})
                ghost = get_entity_preview(ent_info, int(visual_size))
                
                if ghost:
                    g = ghost.copy()
                    g.set_alpha(160)
                    screen.blit(g, (mx - int(visual_size) // 2, my - int(visual_size) // 2))
                
                else:
                    ghost_surf = pg.Surface((int(visual_size), int(visual_size)), pg.SRCALPHA)
                    ghost_surf.fill((200, 100, 200, 120))
                    screen.blit(ghost_surf, (mx - int(visual_size) // 2, my - int(visual_size) // 2))

        if (not show_entity_panel and mx < screen.get_width() - current_panel_width
                and all_tile_surfaces
                and selected_tile_info["tilesheet"] < len(all_tile_surfaces)
                and not (instance_panel_open and mx < instance_panel_width)):
            
            if selected_tile_info["tile"] < len(
                    all_tile_surfaces[selected_tile_info["tilesheet"]]["surfaces"]):
                preview_tile = all_tile_surfaces[selected_tile_info["tilesheet"]]["surfaces"][
                    selected_tile_info["tile"]].copy()
                preview_tile = pg.transform.scale(preview_tile,
                    (int(preview_tile.get_width() * zoom_level),
                     int(preview_tile.get_height() * zoom_level)))
                preview_tile.fill((255, 255, 255, 128), None, pg.BLEND_RGBA_MULT)
                preview_tile = pg.transform.rotate(preview_tile, rotation)
                
                if precision_mode:
                    px = (round((mx + camera_x * zoom_level) / visual_size * 2) / 2
                          * visual_size - camera_x * zoom_level)
                    py = (round((my + camera_y * zoom_level) / visual_size * 2) / 2
                          * visual_size - camera_y * zoom_level)
                
                else:
                    px = ((mx + camera_x * zoom_level) // visual_size) * visual_size - camera_x * zoom_level
                    py = ((my + camera_y * zoom_level) // visual_size) * visual_size - camera_y * zoom_level
                
                screen.blit(preview_tile, (px, py))

        if instance_panel_open and instance_panel_tile is not None and show_entities:
            if instance_panel_tile not in tiles:
                instance_panel_open = False
                instance_panel_tile = None
            
            else:
                instance_panel_row_rects = draw_instance_panel(instance_panel_tile, entity_data)

        mode_flags = []
        
        if show_layers:
            mode_flags.append("LAYERS")
        
        if display_hitboxes:
            mode_flags.append("HITBOXES")
        
        if layer_mode:
            mode_flags.append("LAYER MODE")
        
        if precision_mode:
            mode_flags.append("PRECISION")
        
        if not show_entities:
            mode_flags.append("ENTITIES HIDDEN [Y] - Tile editing only | I = Edit tile animation")
        
        if show_entity_panel and show_entities:
            if placing_entity and selected_entity:
                mode_flags.append(f"PLACING: {selected_entity}  [ESC to cancel]")
            
            else:
                mode_flags.append("ENTITY PANEL [T] — click an entity to select brush")
        
        if instance_panel_open and instance_panel_tile:
            mode_flags.append(f"EDITING: {instance_panel_tile.get('entity_name','?')}  [DEL=delete entity]")

        info = (f"Tile:{selected_tile_info['tile']} (S{selected_tile_info['tilesheet']+1}) "
                f"Rot:{rotation}°  Layer:{current_layer}  Hitbox:{placing_hitbox}  "
                f"Cam:({int(camera_x)},{int(camera_y)})  Zoom:{zoom_level:.1f}x  "
                f"[Q=Save  E=Version  T=Entities  Y=Toggle Entities  I=Edit Animation  ESC=Clear]")
        
        text = font.render(info, True, (255, 255, 255))
        screen.blit(text, (10, 10))
        
        if mode_flags:
            mode_text = font.render(" | ".join(mode_flags), True, (180, 255, 180))
            screen.blit(mode_text, (10, 10 + text.get_height() + 4))

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

    if instance_panel_open and mx < instance_panel_width:
        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_IBEAM)
    
    elif ((show_entity_panel and show_entities and
           screen.get_width() - current_entity_panel_width - 5 <= mx <=
           screen.get_width() - current_entity_panel_width + 5) or
          (not show_entity_panel and
           screen.get_width() - current_panel_width - 5 <= mx <=
           screen.get_width() - current_panel_width + 5)):
        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_SIZEWE)
    
    elif precision_mode:
        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_CROSSHAIR)
    
    else:
        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

    pg.display.flip()
    clock.tick(60)

pg.quit()