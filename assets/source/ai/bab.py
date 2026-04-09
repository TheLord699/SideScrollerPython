import math
import random

STATE_IDLE = "idle"
STATE_WANDER = "wander"
STATE_ALERT = "alert"
STATE_CHASE = "chase"
STATE_ATTACK = "attack"
STATE_RETREAT = "retreat"

def get_player_distance(entity, ai_system):
    player = ai_system.game.player
    delta_x = player.x - entity["x"]
    delta_y = player.y - entity["y"]
    
    return math.hypot(delta_x, delta_y), delta_x, delta_y

def init_state(entity):
    entity.setdefault("bab_state", STATE_IDLE)
    entity.setdefault("bab_alert_timer", 0)
    entity.setdefault("bab_idle_timer", random.randint(30, 90))
    entity.setdefault("chase_initialized", False)

def set_state(entity, new_state):
    if new_state == STATE_CHASE:
        entity["chase_initialized"] = False
    entity["bab_state"] = new_state

def do_idle(entity, ai_system):
    entity["vel_x"] = 0
    entity["bab_idle_timer"] -= 1
    if entity["bab_idle_timer"] <= 0:
        entity["bab_idle_timer"] = random.randint(30, 90)
        set_state(entity, STATE_WANDER)
        ai_system.reset_wander_timer(entity)

def do_wander(entity, ai_system):
    if entity.get("knockback_timer", 0) > 0:
        return
    
    if "ai_timer" not in entity:
        ai_system.reset_wander_timer(entity)

    if entity["ai_direction"] != 0 and not ai_system.check_floor_ahead(entity):
        entity["ai_direction"] *= -1
        ai_system.reset_wander_timer(entity)
        return

    if entity["ai_direction"] != 0 and ai_system.check_wall_collision(entity):
        entity["ai_direction"] *= -1
        ai_system.reset_wander_timer(entity)
        return

    entity["ai_timer"] -= 1
    if entity["ai_timer"] <= 0:
        ai_system.reset_wander_timer(entity)

    entity["vel_x"] = entity.get("move_speed", 1) * entity["ai_direction"]

    if random.random() < 0.01 and entity.get("on_ground", False):
        entity["vel_y"] = -entity.get("jump_force", 10)

def do_alert(entity, ai_system):
    player = ai_system.game.player
    delta_x = player.x - entity["x"]
    direction = 1 if delta_x > 0 else -1
    
    entity["ai_direction"] = direction
    entity["vel_x"] = direction * entity.get("move_speed", 1)
    
    entity["bab_alert_timer"] -= 1
    if entity["bab_alert_timer"] <= 0:
        set_state(entity, STATE_CHASE)

def do_chase(entity, ai_system, distance, delta_x, delta_y):
    aggro_range = entity.get("aggro_range", 300)
    stop_distance = entity.get("stop_distance", 50)

    if distance < aggro_range:
        if distance > stop_distance:
            new_direction = 1 if delta_x > 0 else -1
            entity["ai_direction"] = new_direction

            target_vel_x = entity["ai_direction"] * entity.get("move_speed", 1) * 1.5
            
            if not entity.get("chase_initialized", True):
                entity["vel_x"] = target_vel_x
                entity["chase_initialized"] = True
                
            else:
                acceleration = entity.get("acceleration", 0.5)
                if abs(entity["vel_x"] - target_vel_x) > acceleration:
                    entity["vel_x"] += (1 if target_vel_x > entity["vel_x"] else -1) * acceleration
                    
                else:
                    entity["vel_x"] = target_vel_x

            if not ai_system.check_floor_ahead(entity):
                if entity.get("on_ground", False):
                    entity["vel_y"] = -entity.get("jump_force", 10)
                
        else:
            entity["vel_x"] *= 0.9

        if delta_y < -50 and entity.get("on_ground", False):
            entity["vel_y"] = -entity.get("jump_force", 10)

        if distance < stop_distance:
            set_state(entity, STATE_ATTACK)
            
    else:
        do_wander(entity, ai_system)

def do_attack(entity, ai_system, distance, delta_x):
    entity["ai_direction"] = 1 if delta_x > 0 else -1
    entity["vel_x"] *= 0.85

    if "attack_timer" not in entity:
        entity["attack_timer"] = 0

    if entity["attack_timer"] <= 0:
        ai_system.ai_attack(entity)
        entity["attack_timer"] = entity.get("attack_cooldown_max", 30)

    else:
        entity["attack_timer"] -= 1

    if distance > entity.get("stop_distance", 50):
        set_state(entity, STATE_CHASE)

def do_retreat(entity, ai_system, distance, delta_x):
    flee_direction = -1 if delta_x > 0 else 1
    entity["ai_direction"] = flee_direction

    if ai_system.check_wall_collision(entity) or not ai_system.check_floor_ahead(entity):
        if distance < entity.get("aggro_range", 300):
            set_state(entity, STATE_CHASE)
            
        else:
            set_state(entity, STATE_WANDER)
            
        return

    target_vel_x = flee_direction * entity.get("move_speed", 1) * 1.2
    
    acceleration = entity.get("acceleration", 0.5)
    if abs(entity["vel_x"] - target_vel_x) > acceleration:
        entity["vel_x"] += (1 if target_vel_x > entity["vel_x"] else -1) * acceleration
        
    else:
        entity["vel_x"] = target_vel_x

    health_ratio = entity["health"] / max(entity.get("max_health", entity["health"]), 1)
    retreat_threshold = entity.get("retreat_hp_ratio", 0.25)
    
    if health_ratio > retreat_threshold + 0.1:
        if distance < entity.get("aggro_range", 300):
            set_state(entity, STATE_CHASE)
            
        else:
            set_state(entity, STATE_WANDER)

STATE_HANDLERS = {
    STATE_IDLE: do_idle,
    STATE_WANDER: do_wander,
    STATE_ALERT: do_alert,
    STATE_CHASE: do_chase,
    STATE_ATTACK: do_attack,
    STATE_RETREAT: do_retreat,
}

def update(entity, ai_system):
    init_state(entity)

    player = ai_system.game.player

    if player.current_health <= 0:
        ai_system.ai_wander(entity)
        set_state(entity, STATE_WANDER)
        return

    distance, delta_x, delta_y = get_player_distance(entity, ai_system)
    state = entity["bab_state"]

    health_ratio = entity["health"] / max(entity.get("max_health", entity["health"]), 1)
    retreat_threshold = entity.get("retreat_hp_ratio", 0.25)
    
    if health_ratio <= retreat_threshold and state != STATE_RETREAT:
        set_state(entity, STATE_RETREAT)
        state = entity["bab_state"]

    if state == STATE_RETREAT:
        do_retreat(entity, ai_system, distance, delta_x)
        return

    if state in (STATE_IDLE, STATE_WANDER) and distance < entity.get("aggro_range", 200):
        set_state(entity, STATE_ALERT)
        entity["bab_alert_timer"] = entity.get("alert_duration", 15)
        entity["ai_direction"] = 1 if delta_x > 0 else -1
        entity["vel_x"] = entity["ai_direction"] * entity.get("move_speed", 1)
        
        return

    if state == STATE_CHASE:
        do_chase(entity, ai_system, distance, delta_x, delta_y)
        
    elif state == STATE_ATTACK:
        do_attack(entity, ai_system, distance, delta_x)
        
    else:
        handler = STATE_HANDLERS.get(state)
        if handler:
            handler(entity, ai_system)