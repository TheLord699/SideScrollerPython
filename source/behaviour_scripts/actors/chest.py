import random

STATE_IDLE = "idle"
STATE_OPEN = "open"

def init_state(entity):
    entity.setdefault("chest_opened", False)
    entity.setdefault("animation_finished", False)

def set_state(entity, new_state):
    entity["current_state"] = new_state
    entity["animation_frame"] = 0
    entity["animation_timer"] = 0

def spawn_loot(entity, game):
    loot_config = entity.get("loot_table", {})
    loot_table = loot_config.get("items", [])
    default_loot = loot_config.get("default")
    
    amount_config = loot_config.get("amount", {"min": 1, "max": 1})
    amount = random.randint(amount_config["min"], amount_config["max"])
    
    items_to_spawn = []

    for _ in range(amount):
        available_loot = [
            loot_item
            for loot_item in loot_table
            if random.random() < loot_item["chance"]
        ]

        if available_loot:
            loot_item = random.choice(available_loot)
            items_to_spawn.append(loot_item["name"])
            
        elif default_loot:
            items_to_spawn.append(default_loot)

    for item_name in items_to_spawn:
        if item_name not in game.player.item_info.get("items", {}):
            print(f"Warning: Item '{item_name}' not found in entities_config.json")
            continue

        radius = random.uniform(10, 25)
        
        offset_x = radius * random.choice([-1, 1])
        offset_y = radius * 0.5 * random.choice([-1, 1])
        
        spawn_x = entity["x"] + offset_x - 13
        spawn_y = entity["y"] + offset_y - 10
        
        game.entities.create_entity("item", item_name, spawn_x, spawn_y)
        
def on_interact(entity, game):
    if entity.get("chest_opened", False):
        return

    entity["chest_opened"] = True
    entity["interactable"] = False
    set_state(entity, STATE_OPEN)
    
    game.entities.play_sound(entity, "open")

def update(entity, ai_system):
    init_state(entity)

    current_state = entity.get("current_state", STATE_IDLE)

    if current_state == STATE_OPEN:
        anim_frames = entity.get("animation_frames", {}).get("open", {}).get("frames", [])
        if anim_frames and entity["animation_frame"] >= len(anim_frames) - 1:
            if not entity.get("animation_finished", False):
                entity["animation_finished"] = True
                spawn_loot(entity, ai_system.game)
                
        return 

    elif current_state == STATE_IDLE:
        return