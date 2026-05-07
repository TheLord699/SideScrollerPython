STATE_IDLE = "idle"

def init_state(entity):
    entity.setdefault("bow_taken", False)

def on_interact(entity, game):
    if entity.get("bow_taken", False):
        return
    
    game.player.weapon_inventory.append("basic_bow")
    entity["bow_taken"] = True
    
    if entity in game.entities.entities:
        game.entities.entities.remove(entity)