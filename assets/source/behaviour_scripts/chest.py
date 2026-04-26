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
    loot_table = entity.get("loot", [
        {"name": "Gold", "min": 1, "max": 3, "chance": 0.8},
        {"name": "Potion", "min": 0, "max": 1, "chance": 0.4},
        {"name": "Red Gem", "min": 0, "max": 1, "chance": 0.2}
    ])

    item_counter = 0
    for loot_item in loot_table:
        if random.random() < loot_item["chance"]:
            quantity = random.randint(loot_item["min"], loot_item["max"])
            for loot in range(quantity):
                angle = random.uniform(0, 2 * 3.14159)
                radius = random.uniform(10, 25)
                
                offset_x = radius * random.choice([-1, 1])
                offset_y = radius * 0.5 * random.choice([-1, 1])
                
                spawn_x = entity["x"] + offset_x - 13
                spawn_y = entity["y"] + offset_y - 10
                
                game.entities.create_entity("item", loot_item["name"], spawn_x, spawn_y)
                item_counter += 1

def on_interact(entity, game):
    if entity.get("chest_opened", False):
        return

    entity["chest_opened"] = True
    entity["interactable"] = False
    set_state(entity, STATE_OPEN)
    
    sound_entry = game.entities.sounds.get("open", [None])[0]
    if sound_entry:
        vol = game.environment.volume / 10 * sound_entry["volume"]
        sound_entry["sound"].set_volume(vol)
        sound_entry["sound"].play()

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
