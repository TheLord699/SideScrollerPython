import math
import random

STATE_IDLE   = "idle"
STATE_WANDER = "wander"
STATE_CHASE  = "chase"
STATE_ATTACK = "attack"

JUMP_CHANCE        = 0.04
WANDER_JUMP_CHANCE = 0.01

def get_player_distance(entity, ai_system):
    player = ai_system.game.player
    delta_x = player.x - entity["x"]
    delta_y = player.y - entity["y"]
    return math.hypot(delta_x, delta_y), delta_x, delta_y

def set_facing(entity, direction):
    if direction != 0:
        entity["facing"] = direction
        entity["facing_direction"] = direction

def init_state(entity):
    entity.setdefault("slime_state", STATE_IDLE)
    entity.setdefault("slime_idle_timer", random.randint(30, 90))
    entity.setdefault("facing", 1)
    entity.setdefault("facing_direction", 1)

def set_state(entity, new_state):
    entity["slime_state"] = new_state

def try_jump(entity, force_multiplier=1.0):
    if entity.get("on_ground", False) or entity.get("was_on_ground", False):
        entity["pending_jump"] = entity.get("jump_force", 10) * force_multiplier

def do_idle(entity, ai_system):
    entity["vel_x"] = 0
    entity["slime_idle_timer"] -= 1

    if random.random() < 0.002:
        try_jump(entity, force_multiplier=0.5)

    if entity["slime_idle_timer"] <= 0:
        entity["slime_idle_timer"] = random.randint(30, 90)
        set_state(entity, STATE_WANDER)
        ai_system.reset_wander_timer(entity)

def do_wander(entity, ai_system):
    if entity.get("knockback_timer", 0) > 0:
        return

    if "ai_timer" not in entity:
        ai_system.reset_wander_timer(entity)

    if entity["ai_direction"] != 0:
        if not ai_system.check_floor_ahead(entity) or ai_system.check_wall_collision(entity):
            entity["ai_direction"] *= -1
            ai_system.reset_wander_timer(entity)

    entity["ai_timer"] -= 1
    if entity["ai_timer"] <= 0:
        ai_system.reset_wander_timer(entity)

    entity["vel_x"] = entity.get("move_speed", 1) * entity["ai_direction"]
    set_facing(entity, entity["ai_direction"])

    if random.random() < WANDER_JUMP_CHANCE:
        try_jump(entity, force_multiplier=0.6)

def do_chase(entity, ai_system, distance, delta_x, delta_y):
    aggro_range   = entity.get("aggro_range", 200)
    stop_distance = entity.get("stop_distance", 25)

    if distance > aggro_range:
        do_wander(entity, ai_system)
        set_state(entity, STATE_WANDER)
        return

    direction = 1 if delta_x > 0 else -1
    entity["ai_direction"] = direction
    set_facing(entity, direction)

    if distance > stop_distance:
        if entity.get("on_ground", False):
            if not ai_system.check_floor_ahead(entity):
                entity["vel_x"] = 0
                return
            
            if ai_system.check_wall_collision(entity):
                entity["vel_x"] = 0
                return
            
            entity["vel_x"] = direction * entity.get("move_speed", 1) * 1.2
            
        else:
            entity["vel_x"] += direction * 0.2
            entity["vel_x"] = max(-entity.get("move_speed", 1) * 2, min(entity["vel_x"], entity.get("move_speed", 1) * 2))

        if random.random() < JUMP_CHANCE:
            up_boost = 1.3 if delta_y < -40 else 1.0
            try_jump(entity, force_multiplier=up_boost)

        if ai_system.check_wall_collision(entity):
            try_jump(entity, force_multiplier=1.0)

    else:
        entity["vel_x"] *= 0.85
        set_state(entity, STATE_ATTACK)

def do_attack(entity, ai_system, distance, delta_x):
    direction = 1 if delta_x > 0 else -1
    entity["ai_direction"] = direction
    set_facing(entity, direction)

    entity["vel_x"] *= 0.8

    if "attack_timer" not in entity:
        entity["attack_timer"] = 0

    if entity["attack_timer"] <= 0:
        try_jump(entity, force_multiplier=0.4)
        entity["vel_x"] = direction * entity.get("move_speed", 1) * 1.2

        ai_system.ai_attack(entity)
        entity["attack_timer"] = entity.get("attack_cooldown_max", 18)

    else:
        entity["attack_timer"] -= 1

    if distance > entity.get("stop_distance", 25):
        set_state(entity, STATE_CHASE)

def update(entity, ai_system):
    init_state(entity)

    player = ai_system.game.player

    if player.current_health <= 0:
        ai_system.ai_wander(entity)
        set_state(entity, STATE_WANDER)
        return

    if entity.get("knockback_timer", 0) > 0:
        return

    distance, delta_x, delta_y = get_player_distance(entity, ai_system)
    state = entity["slime_state"]

    if state in (STATE_IDLE, STATE_WANDER) and distance < entity.get("aggro_range", 200):
        set_state(entity, STATE_CHASE)
        try_jump(entity, force_multiplier=0.8)
        return

    if state == STATE_IDLE:
        do_idle(entity, ai_system)

    elif state == STATE_WANDER:
        do_wander(entity, ai_system)

    elif state == STATE_CHASE:
        do_chase(entity, ai_system, distance, delta_x, delta_y)

    elif state == STATE_ATTACK:
        do_attack(entity, ai_system, distance, delta_x)