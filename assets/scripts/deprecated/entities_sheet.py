import pygame as pg
import json
import os

class Entities:
    def __init__(self, game):
        self.game = game
        
        self.entity_info = {}
        self.item_sprites = {}
        
        self.entities = []
        
        self.on_ground = False
        self.tilesheet = None


        self.load_settings()
        self.load_tilesheet("assets/sprites/gui/items/Sheet.png", 16, 16)

    def load_entity_info(self):
        with open('assets/settings/entities.json', 'r') as f:
            self.entity_info = json.load(f)

    def load_tilesheet(self, path, tile_width, tile_height):
        if os.path.exists(path):
            self.tilesheet = pg.image.load(path).convert_alpha()
            sheet_width, sheet_height = self.tilesheet.get_size()
            
            print(f"Tilesheet size: {sheet_width}x{sheet_height}")

            for row in range(sheet_height // tile_height):
                for col in range(sheet_width // tile_width):
                    rect = pg.Rect(col * tile_width, row * tile_height, tile_width, tile_height)
                    sprite = self.tilesheet.subsurface(rect).copy()
                    key = f"item_{row}_{col}"
                    self.item_sprites[key] = sprite
                    
                    print(f"Loaded {key}")

        else:
            print(f"Tilesheet not found: {path}")

    def load_settings(self):
        self.x = 0
        self.y = 0
        
        self.width = 0
        self.height = 0
        
        self.weight = 0
        
        self.health = 0
        
        self.vel_x = 0
        self.vel_y = 0
        
        self.entity_info = {}
        
        self.entities = []
        
        self.on_ground = False
        
        self.load_entity_info()

    def reset(self):
        self.entities.clear()

    def item(self, item_name):
        if item_name in self.entity_info["items"]:
            return self.entity_info["items"][item_name]
        return None

    def enemy(self, enemy_name):
        if enemy_name in self.entity_info["enemies"]:
            return self.entity_info["enemies"][enemy_name]
        return None

    def create_item(self, item_name, x, y):
        item = self.item(item_name)
        if item:
            item_index = item.get("index", None)
            image = self.item_sprites.get(item_index, pg.image.load("assets/sprites/missing_texture.png"))
            
            entity = {
                "type": "item",
                "name": item_name,
                "x": x,
                "y": y,
                "width": item.get("width", 32), 
                "height": item.get("height", 32), 
                "weight": item.get("weight", 1),
                "image": image
            }
            self.entities.append(entity)

    def create_enemy(self, enemy_name, x, y):
        enemy = self.enemy(enemy_name)
        if enemy:
            entity = {
                "type": "enemy",
                "name": enemy_name,
                "x": x,
                "y": y,
                "width": enemy.get("width", 32),
                "height": enemy.get("height", 32),
                "weight": enemy.get("weight", 1),
                "health": enemy.get("health", 100),
                "image": self.load_image(f"assets/sprites/enemy/{enemy_name}.png")
            }
            self.entities.append(entity)

    def update_collision(self, entity):
        entity_hitbox = pg.Rect(entity["x"] - entity["width"] / 2, entity["y"] - entity["height"] / 2, entity["width"], entity["height"])

        for index, tile_hitbox in enumerate(self.game.map.tile_hitboxes):
            tile_id = self.game.map.tile_id[index]
            tile_attributes = self.game.map.tile_attributes.get(tile_id, {})
            swimmable = tile_attributes.get("swimmable", False)

            if entity_hitbox.colliderect(tile_hitbox):
                overlap_x = min(entity_hitbox.right - tile_hitbox.left, tile_hitbox.right - entity_hitbox.left)
                overlap_y = min(entity_hitbox.bottom - tile_hitbox.top, tile_hitbox.bottom - entity_hitbox.top)

                if overlap_x < overlap_y:
                    if not swimmable:
                        entity["x"] -= overlap_x if entity_hitbox.centerx > tile_hitbox.centerx else -overlap_x
                        
                else:
                    if entity_hitbox.centery < tile_hitbox.centery:
                        entity["y"] -= overlap_y
                        self.vel_y = 0
                        self.on_ground = True
                        
                    else:  
                        entity["y"] += overlap_y
                        self.vel_y = 0

    def apply_gravity(self, entity):
        if not self.is_on_ground(entity):
            step = round(max(1, self.vel_y))
            for _ in range(step):
                entity["y"] += 1
                
                if self.is_on_ground(entity): 
                    self.vel_y = 0
                    break
            
            self.vel_y += self.game.environment.gravity * entity["weight"]
            
            if self.vel_y > self.game.environment.max_fall_speed:
                self.vel_y = self.game.environment.max_fall_speed 

    def is_on_ground(self, entity):
        entity_hitbox = pg.Rect(entity["x"] - entity["width"] / 2, entity["y"] - entity["height"] / 2, entity["width"], entity["height"])

        for tile_hitbox in self.game.map.tile_hitboxes:
            if entity_hitbox.colliderect(tile_hitbox):
                if entity_hitbox.bottom >= tile_hitbox.top:
                    entity["y"] = tile_hitbox.top - entity["height"] / 2
                    self.on_ground = True
                    return True
                    
        self.on_ground = False
        return False

    def render(self):
        cam_x, cam_y = self.game.player.cam_x, self.game.player.cam_y
        
        for entity in self.entities:
            if entity["image"]:
                scaled_image = pg.transform.scale(entity["image"], (entity["width"], entity["height"]))
                
                sprite_x = entity["x"] - cam_x - entity["width"] // 2
                sprite_y = entity["y"] - cam_y - entity["height"] // 2 
                self.game.screen.blit(scaled_image, (sprite_x, sprite_y))

                entity_hitbox = pg.Rect(entity["x"] - entity["width"] / 2 - cam_x, entity["y"] - entity["height"] / 2 - cam_y, entity["width"], entity["height"])
                
                # pg.draw.rect(self.game.screen, (255, 0, 0), entity_hitbox, 2)

    def update(self):
        for entity in self.entities:
            self.update_collision(entity)
            self.apply_gravity(entity)
            self.render()
