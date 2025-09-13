import numpy as np
import pygame as pg

class LightSource:
    def __init__(self, game):
        self.game = game

        self.stationary_lights = []
        self.moving_lights = []
        self.active_lights = []
        
        self.light_mask_cache = {}
        self.blur_kernel_cache = {}

        self.light_surface = None
        self.temp_surface = None
        self.tint_surface = None

        # might remove later
        self.max_cache_size = 100

        self.ambient_light = self.game.environment.max_darkness
        self.enable_bloom = self.game.environment.bloom
        self.bloom_tint = self.game.environment.bloom_tint

        self.resize_light_surface()

    def resize_light_surface(self):
        size = (self.game.screen_width, self.game.screen_height)
        self.light_surface = pg.Surface(size, pg.SRCALPHA)
        self.temp_surface = pg.Surface(size).convert()
        self.tint_surface = None # reset in case of size change

    def add_stationary_light(self, x, y, radius, intensity, colour=(255, 255, 255)):
        self.stationary_lights.append({
            "x": x, "y": y, "radius": radius, "intensity": intensity,
            "colour": colour, "type": "stationary"
        })

    def add_moving_light(self, x, y, radius, intensity, colour=(255, 255, 255)):
        self.moving_lights.append({
            "x": x, "y": y, "radius": radius, "intensity": intensity,
            "colour": colour, "type": "moving"
        })

    def remove_stationary_light(self, index):
        if 0 <= index < len(self.stationary_lights):
            self.stationary_lights.pop(index)

    def clear_moving_lights(self):
        self.moving_lights.clear()

    def clear_all_lights(self):
        self.stationary_lights.clear()
        self.moving_lights.clear()
        self.active_lights.clear()
        
        self.light_mask_cache.clear()
        self.blur_kernel_cache.clear()

    def get_light_mask(self, radius, colour, intensity):
        if radius <= 0 or intensity <= 0:
            return None

        key = (radius, colour, round(intensity, 2))
        if key in self.light_mask_cache:
            return self.light_mask_cache[key]

        if len(self.light_mask_cache) > self.max_cache_size:
            self.light_mask_cache.clear()

        # black magic bullshit
        size = radius * 2
        Y, X = np.ogrid[:size, :size]
        dx = X - radius
        dy = Y - radius
        dist_squared = dx**2 + dy**2
        radius_squared = radius**2

        falloff = np.zeros_like(dist_squared, dtype=np.float32)
        mask = dist_squared <= radius_squared
        falloff[mask] = 1 - (dist_squared[mask] / radius_squared)
        brightness = np.clip(falloff * intensity, 0, 1)

        arr = np.zeros((size, size, 4), dtype=np.uint8)
        arr[..., 0] = (colour[0] * brightness).astype(np.uint8)
        arr[..., 1] = (colour[1] * brightness).astype(np.uint8)
        arr[..., 2] = (colour[2] * brightness).astype(np.uint8)
        arr[..., 3] = (255 * brightness).astype(np.uint8)

        surface = pg.Surface((size, size), pg.SRCALPHA)
        pg.surfarray.blit_array(surface, arr[..., :3])
        alpha = pg.surfarray.pixels_alpha(surface)
        alpha[:, :] = arr[..., 3]
        del alpha

        self.light_mask_cache[key] = surface
        return surface

    def gaussian_blur(self, surface, radius=8, scale_factor=0.25):
        small_size = (
            int(surface.get_width() * scale_factor),
            int(surface.get_height() * scale_factor)
        )
        
        small_surface = pg.transform.smoothscale(surface, small_size)

        alpha_arr = pg.surfarray.pixels_alpha(small_surface).astype(np.float32)

        if radius not in self.blur_kernel_cache:
            kernel_size = int(radius * 2 + 1)
            kernel = np.exp(-np.linspace(-radius, radius, kernel_size)**2 / (2 * radius**2))
            kernel /= kernel.sum()
            self.blur_kernel_cache[radius] = kernel
            
        else:
            kernel = self.blur_kernel_cache[radius]

        blurred = np.copy(alpha_arr)
        for y in range(blurred.shape[0]):
            blurred[y, :] = np.convolve(blurred[y, :], kernel, mode="same")
            
        for x in range(blurred.shape[1]):
            blurred[:, x] = np.convolve(blurred[:, x], kernel, mode="same")

        blurred = np.clip(blurred, 0, 255).astype(np.uint8)
        rgb = pg.surfarray.pixels3d(small_surface)
        final_array = np.zeros((blurred.shape[0], blurred.shape[1], 4), dtype=np.uint8)
        final_array[..., :3] = rgb
        final_array[..., 3] = blurred

        blurred_surface = pg.Surface(small_size, pg.SRCALPHA)
        pg.surfarray.blit_array(blurred_surface, final_array[..., :3])
        alpha = pg.surfarray.pixels_alpha(blurred_surface)
        alpha[:, :] = final_array[..., 3]
        del alpha

        return pg.transform.smoothscale(blurred_surface, surface.get_size())

    def render_light(self, light):
        screen_x = int(light["x"] - self.game.player.cam_x)
        screen_y = int(light["y"] - self.game.player.cam_y)
        radius = light["radius"]
        
        sw, sh = self.game.screen_width, self.game.screen_height

        left, right = screen_x - radius, screen_x + radius
        top, bottom = screen_y - radius, screen_y + radius

        if right < 0 or left > sw or bottom < 0 or top > sh:
            return

        mask = self.get_light_mask(radius, light["colour"], light["intensity"])
        
        if mask:
            self.light_surface.blit(mask, (left, top), special_flags=pg.BLEND_ADD)
            
    def screen_transition(self, colour=(0, 0, 0), duration=1000):
        clock = pg.time.Clock()
        sw, sh = self.game.screen_width, self.game.screen_height
        center_x, center_y = sw // 2, sh // 2
        max_radius = int(max(sw, sh))
        steps = 60
        shrink_steps = steps // 2
        unshrink_steps = steps // 2
        step_time = duration // steps

        for i in range(shrink_steps):
            progress = 1 - (i / shrink_steps)
            radius = int(max_radius * progress)
            transition_surface = pg.Surface((sw, sh), pg.SRCALPHA)
            transition_surface.fill((*colour, 255))
            pg.draw.circle(transition_surface, (0, 0, 0, 0), (center_x, center_y), radius)
            self.game.screen.blit(transition_surface, (0, 0))
            pg.display.flip()
            clock.tick(1000 // step_time)

        for i in range(unshrink_steps):
            progress = i / unshrink_steps
            radius = int(max_radius * progress)
            transition_surface = pg.Surface((sw, sh), pg.SRCALPHA)
            transition_surface.fill((*colour, 255))
            pg.draw.circle(transition_surface, (0, 0, 0, 0), (center_x, center_y), radius)
            self.game.screen.blit(transition_surface, (0, 0))
            pg.display.flip()
            clock.tick(1000 // step_time)

    def render(self):
        self.light_surface.fill((0, 0, 0, 255))

        for light in self.stationary_lights:
            self.render_light(light)
            
        for light in self.moving_lights:
            self.render_light(light)

        if self.enable_bloom:
            bloom_surface = self.gaussian_blur(self.light_surface, radius=8, scale_factor=0.25)

            if self.bloom_tint:
                if not self.tint_surface or self.tint_surface.get_size() != bloom_surface.get_size():
                    self.tint_surface = pg.Surface(bloom_surface.get_size(), pg.SRCALPHA)
                    self.tint_surface.fill((*self.bloom_tint, 0))
                bloom_surface.blit(self.tint_surface, (0, 0), special_flags=pg.BLEND_RGB_MULT)

            self.light_surface.blit(bloom_surface, (0, 0), special_flags=pg.BLEND_ADD)

        self.temp_surface.fill((self.ambient_light, self.ambient_light, self.ambient_light))
        self.temp_surface.blit(self.light_surface, (0, 0), special_flags=pg.BLEND_ADD)
        self.game.screen.blit(self.temp_surface, (0, 0), special_flags=pg.BLEND_MULT)

    def handle_lights(self):
        for light in self.active_lights:
            if len(light) < 6 or light[5] == "moving":
                self.add_moving_light(*light[:5])
                
            else:
                self.add_stationary_light(*light[:5])
                
        self.active_lights.clear()

    def update(self):
        if self.game.environment.lighting:
            self.clear_moving_lights()
            self.handle_lights()
            self.render()
