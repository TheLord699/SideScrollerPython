STATE_IDLE = "idle"

def init_state(entity):
    entity.setdefault("sword_taken", False)

def on_interact(entity, game):
    if entity.get("sword_taken", False):
        return
    
    game.player.weapon_inventory.append("basic_sword")
    entity["sword_taken"] = True
    
    if entity in game.entities.entities:
        game.entities.entities.remove(entity)