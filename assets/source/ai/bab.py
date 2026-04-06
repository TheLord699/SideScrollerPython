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

def set_state(entity, new_state):
    entity["bab_state"] = new_state

def do_idle(entity, ai_system):
    entity["vel_x"] = 0
    entity["bab_idle_timer"] -= 1
    if entity["bab_idle_timer"] <= 0:
        entity["bab_idle_timer"] = random.randint(30, 90)
        set_state(entity, STATE_WANDER)
        ai_system.reset_wander_timer(entity)

def do_wander(entity, ai_system):
    ai_system.ai_wander(entity)
    if random.random() < 0.005:
        set_state(entity, STATE_IDLE)
        entity["bab_idle_timer"] = random.randint(30, 90)

def do_alert(entity, ai_system):
    entity["vel_x"] = 0
    entity["bab_alert_timer"] -= 1
    if entity["bab_alert_timer"] <= 0:
        set_state(entity, STATE_CHASE)

def do_chase(entity, ai_system):
    distance, delta_x, delta_y = get_player_distance(entity, ai_system)

    stop_distance = entity.get("stop_distance", 40)
    forget_range = entity.get("forget_range", 350)
    sprint_mult = entity.get("sprint_mult", 1.8)

    if distance <= stop_distance:
        set_state(entity, STATE_ATTACK)
        return

    if distance >= forget_range:
        set_state(entity, STATE_WANDER)
        ai_system.reset_wander_timer(entity)
        return

    new_direction = 1 if delta_x > 0 else -1

    if (
        entity.get("ai_direction") != new_direction
        or ai_system.check_wall_collision(entity)
        or not ai_system.check_floor_ahead(entity)
    ):
        entity["ai_direction"] = new_direction

    if ai_system.check_floor_ahead(entity):
        entity["vel_x"] = entity["ai_direction"] * entity.get("move_speed", 1) * sprint_mult
        
    else:
        entity["vel_x"] = 0

    if delta_y < -60 and entity.get("on_ground", False):
        entity["vel_y"] = -entity.get("jump_force", 10)

def do_attack(entity, ai_system):
    distance, delta_x, ignored = get_player_distance(entity, ai_system)

    entity["ai_direction"] = 1 if delta_x > 0 else -1
    entity["vel_x"] = 0

    ai_system.ai_attack(entity)

    if distance > entity.get("stop_distance", 40) * 1.5:
        set_state(entity, STATE_CHASE)

def do_retreat(entity, ai_system):
    distance, delta_x, ignored = get_player_distance(entity, ai_system)

    flee_direction = -1 if delta_x > 0 else 1
    entity["ai_direction"] = flee_direction

    if ai_system.check_wall_collision(entity) or not ai_system.check_floor_ahead(entity):
        set_state(entity, STATE_CHASE)
        return

    entity["vel_x"] = flee_direction * entity.get("move_speed", 1) * entity.get("retreat_mult", 1.4)

    health_ratio = entity["health"] / max(entity.get("max_health", entity["health"]), 1)
    if health_ratio > entity.get("retreat_hp_ratio", 0.25) + 0.1:
        set_state(entity, STATE_CHASE)

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

    distance, delta_x, ignored = get_player_distance(entity, ai_system)
    state = entity["bab_state"]

    health_ratio = entity["health"] / max(entity.get("max_health", entity["health"]), 1)
    if health_ratio <= entity.get("retreat_hp_ratio", 0.25) and state != STATE_RETREAT:
        set_state(entity, STATE_RETREAT)
        state = STATE_RETREAT

    if state in (STATE_IDLE, STATE_WANDER) and distance < entity.get("aggro_range", 200):
        set_state(entity, STATE_ALERT)
        entity["bab_alert_timer"] = entity.get("alert_duration", 45)
        entity["vel_x"] = 0
        return

    handler = STATE_HANDLERS.get(entity["bab_state"])
    if handler:
        handler(entity, ai_system)