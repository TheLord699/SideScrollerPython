import pygame as pg
def interact_with_entity(self): # need to change to get from each dict(example: items, enemies, npcs), need to get from entity_info not entities
    for dict in self.game.entities.entity_info:
        for entity in self.game.entities.entities:
            if entity == "items":
                entity_hitbox = pg.Rect(entity[dict]["x"] - entity[dict]["width"] / 2, entity[dict]["y"] - entity[dict]["height"] / 2, entity[dict]["width"], entity[dict]["height"])

                if self.interact_radius.colliderect(entity_hitbox):
                    self.add_item_to_inventory({"name": entity["name"], "quantity": 1, "type": "item", "value": entity["value"]})
                    
                    self.game.entities.entities.remove(entity)
        