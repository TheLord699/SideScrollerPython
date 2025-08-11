import pygame as pg
import math
import json
import os

class Background:
	def __init__(self, game):
		self.game = game
  
		self.load_settings()

	def load_settings(self):
		self.cam_x = 0
		self.cam_y = 0
  
		self.menu_time = 0
  
		self.bg_settings = {}
		self.layers = []

		self.menu_scrolling = False 

	def load(self, map_path):
		print("Background reset")
		self.load_settings()
		
		background_file = os.path.join(map_path, "background.json")
		if not os.path.exists(background_file):
			print(f"Background file does not exist: {background_file}")
			return
		
		try:
			with open(background_file, "r") as file:
				bg_attributes = json.load(file)
				self.bg_settings = {int(bg_id): attributes for bg_id, attributes in bg_attributes.items()}
				
				for bg_id, bg_data in self.bg_settings.items():
					image_filename = bg_data.get("image", "")
					image_path = image_filename if image_filename else None
					image_surface = None

					if image_path and os.path.exists(image_path):
						image_surface = pg.image.load(image_path).convert_alpha()
						original_width, original_height = image_surface.get_size()
						width = bg_data.get("width", original_width)
						height = bg_data.get("height", original_height)
						
						if (width, height) != (original_width, original_height):
							image_surface = pg.transform.scale(image_surface, (width, height))
							
					else:
						print(f"Image file not found: {image_path}")

					layer_info = {
						"x": bg_data.get("x", 0),
						"y": bg_data.get("y", 0),
						"width": width,
						"height": height,
						"layer": bg_data.get("layer", 1),
						"multiplier": bg_data.get("multiplier", 1),
						"repeat_directions": bg_data.get("repeat_directions", []),
						"move_directions": bg_data.get("move_directions", []),
						"move_speed": bg_data.get("move_speed", 0),
						"bob_amount": bg_data.get("bob_amount", 0),
						"image": image_surface
					}
		
					self.layers.append(layer_info)
				
				self.layers.sort(key=lambda bg: bg["layer"])
				
		except Exception as e:
			print(f"Failed to load background info: {e}")

	def update_camera(self):
		if self.game.environment.menu in {"play", "death"}:
			if hasattr(self.game, "player"):
				self.cam_x = self.game.player.cam_x
				self.cam_y = self.game.player.cam_y
		
		elif self.game.environment.menu in {"main", "settings"}: 
			if not self.menu_scrolling:
				self.cam_x = 0
				self.cam_y = 0
				self.menu_scrolling = True
				self.menu_time = 0
			
			self.cam_x -= 2
			self.menu_time += 0.05
			self.cam_y = math.sin(self.menu_time) * 20
			
		else:
			self.menu_scrolling = False

	def update_layers(self):
		current_time = pg.time.get_ticks() * 0.002
		
		for index, bg in enumerate(self.layers):
			move_speed = bg["move_speed"]
			
			if move_speed > 0:
				if "right" in bg["move_directions"]:
					bg["x"] += move_speed
					
				if "left" in bg["move_directions"]:
					bg["x"] -= move_speed
					
				if "up" in bg["move_directions"]:
					bg["y"] -= move_speed
					
				if "down" in bg["move_directions"]:
					bg["y"] += move_speed
			
			if bg["bob_amount"] > 0:
				layer_time_factor = current_time + (index * 0.5)
				bg["y"] += math.sin(layer_time_factor) * bg["bob_amount"]

	def render(self):
		for bg in self.layers:
			if not bg["image"]:
				continue
			
			render_x = bg["x"] - (self.cam_x * bg["multiplier"])
			render_y = bg["y"] - (self.cam_y * bg["multiplier"])
			
			if render_y + bg["height"] < 0 or render_y > self.game.screen_height:
				continue
			
			repeat_horizontal = "horizontal" in bg["repeat_directions"]
			repeat_vertical = "vertical" in bg["repeat_directions"]
			
			bg_width = bg["width"]
			bg_height = bg["height"]
			
			if not repeat_horizontal and not repeat_vertical:
				if render_x + bg_width < 0 or render_x > self.game.screen_width:
					continue
				
				self.game.screen.blit(bg["image"], (render_x, render_y))
				
			elif repeat_horizontal and repeat_vertical:
				start_x = render_x % bg_width
				if start_x != 0:
					start_x -= bg_width
     
				start_x = math.floor(start_x)
				
				start_y = render_y % bg_height
				if start_y != 0:
					start_y -= bg_height
     
				start_y = math.floor(start_y)

				for x in range(start_x, self.game.screen_width, bg_width):
					for y in range(start_y, self.game.screen_height, bg_height):
						self.game.screen.blit(bg["image"], (x, y))
						
			elif repeat_horizontal:
				start_x = render_x % bg_width
				if start_x != 0:
					start_x -= bg_width
     
				start_x = math.floor(start_x)
				
				for x in range(start_x, self.game.screen_width, bg_width):
					self.game.screen.blit(bg["image"], (x, render_y))
					
			elif repeat_vertical:
				start_y = render_y % bg_height
				if start_y != 0:
					start_y -= bg_height
     
				start_y = math.floor(start_y)
				
				for y in range(start_y, self.game.screen_height, bg_height):
					self.game.screen.blit(bg["image"], (render_x, y))

	def update(self):
		self.update_camera()
		self.update_layers()
		self.render()