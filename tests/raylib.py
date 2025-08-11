import raylibpy as rl
import random
import math

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 450

NUM_STARS = 1000
STAR_FIELD_RADIUS = 50.0  # Distance from player where stars spawn
STAR_CULL_DISTANCE = 60.0  # Distance beyond which stars aren't drawn
PLAYER_SPEED = 0.5

class Star:
    def __init__(self):
        # Random initial position in a cube around origin
        self.pos = [
            random.uniform(-STAR_FIELD_RADIUS, STAR_FIELD_RADIUS),
            random.uniform(-STAR_FIELD_RADIUS, STAR_FIELD_RADIUS),
            random.uniform(-STAR_FIELD_RADIUS, STAR_FIELD_RADIUS),
        ]
        self.size = random.uniform(0.1, 0.3)

    def update(self, player_pos):
        # If star is too far behind player (z), recycle it forward
        if self.pos[2] - player_pos[2] > STAR_FIELD_RADIUS:
            self.pos[0] = random.uniform(-STAR_FIELD_RADIUS, STAR_FIELD_RADIUS) + player_pos[0]
            self.pos[1] = random.uniform(-STAR_FIELD_RADIUS, STAR_FIELD_RADIUS) + player_pos[1]
            self.pos[2] = player_pos[2] - STAR_FIELD_RADIUS  # place far in front of player

    def draw(self, player_pos):
        # Cull stars too far away for performance
        dx = self.pos[0] - player_pos[0]
        dy = self.pos[1] - player_pos[1]
        dz = self.pos[2] - player_pos[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        if dist > STAR_CULL_DISTANCE:
            return

        rl.draw_cube(self.pos, self.size, self.size, self.size, rl.WHITE)

def main():
    rl.init_window(SCREEN_WIDTH, SCREEN_HEIGHT, b"Infinite Starfield Cube")
    rl.set_target_fps(60)

    # Setup camera
    camera = rl.Camera()
    camera.position = (0.0, 0.0, 5.0)  # Behind the player cube initially
    camera.target = (0.0, 0.0, 0.0)
    camera.up = (0.0, 1.0, 0.0)
    camera.fovy = 45.0
    camera.type = rl.CAMERA_PERSPECTIVE

    # Player cube position
    player_pos = [0.0, 0.0, 0.0]

    # Generate stars
    stars = [Star() for _ in range(NUM_STARS)]

    while not rl.window_should_close():
        # Handle input - simple flying controls
        if rl.is_key_down(rl.KEY_W):
            player_pos[2] -= PLAYER_SPEED
        if rl.is_key_down(rl.KEY_S):
            player_pos[2] += PLAYER_SPEED
        if rl.is_key_down(rl.KEY_A):
            player_pos[0] -= PLAYER_SPEED
        if rl.is_key_down(rl.KEY_D):
            player_pos[0] += PLAYER_SPEED
        if rl.is_key_down(rl.KEY_SPACE):
            player_pos[1] += PLAYER_SPEED
        if rl.is_key_down(rl.KEY_LEFT_SHIFT):
            player_pos[1] -= PLAYER_SPEED

        # Update camera to follow player cube from behind
        camera.position = (player_pos[0], player_pos[1] + 2.0, player_pos[2] + 5.0)
        camera.target = tuple(player_pos)

        # Update stars
        for star in stars:
            star.update(player_pos)

        # Drawing
        rl.begin_drawing()
        rl.clear_background(rl.BLACK)

        rl.begin_mode3d(camera)

        # Draw player cube in red
        rl.draw_cube(player_pos, 1.0, 1.0, 1.0, rl.RED)
        rl.draw_cube_wires(player_pos, 1.0, 1.0, 1.0, rl.MAROON)

        # Draw stars
        for star in stars:
            star.draw(player_pos)

        rl.end_mode3d()

        # UI text
        rl.draw_text(b"Use WASD + Space/Shift to fly", 10, 10, 20, rl.RAYWHITE)

        rl.end_drawing()

    rl.close_window()

if __name__ == "__main__":
    main()
