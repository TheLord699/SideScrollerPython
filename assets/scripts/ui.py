import pygame as pg

class UI:
    def __init__(self, game):
        self.game = game
        
        self.ui_elements = []
        self.loaded_sheets = {}
        self.loaded_images = {}
        self.loaded_fonts = {}
        
        self.mouse_locked = False
        
    def load_sheet(self, sheet_name, path):
        if sheet_name in self.loaded_sheets:
            return 
        
        try:
            self.loaded_sheets[sheet_name] = pg.image.load(path).convert_alpha()
            
        except Exception as e:
            print(f"Error loading sprite sheet {path}: {e}")
            self.loaded_sheets[sheet_name]

    def load_image(self, image_path, alpha=None):
        if image_path in self.loaded_images:
            return self.loaded_images[image_path]

        try:
            image = pg.image.load(image_path).convert_alpha() if alpha else pg.image.load(image_path).convert()
            self.loaded_images[image_path] = image
            return image
        
        except Exception as e:
            print(f"Error loading image from {image_path}: {e}")
            return self.game.environment.missing_texture.copy()
    
    def load_font(self, font_path, size=24):
        font_key = f"{font_path}_{size}"
        
        if font_key in self.loaded_fonts:
            return self.loaded_fonts[font_key]
        
        try:
            if font_path:
                font = pg.font.Font(font_path, size)
                
            else:
                font = pg.font.Font(None, size)
                
            self.loaded_fonts[font_key] = font
            return font
        
        except Exception as e:
            print(f"Error loading font: {e}")
            font = pg.font.Font(None, size)
            self.loaded_fonts[font_key] = font
            return font

    def create_ui(self, x, y, width, height, alpha=None, is_button=False, scale_multiplier=1.1,
                    image_path=None, sprite_sheet_path=None, sprite_width=16, sprite_height=16,
                    image_id=None, element_id=None, centered=False, callback=None, is_hold=False,
                    label=None, font=None, font_size=24, text_color=(255, 255, 255), render_order=0,
                    is_slider=False, min_value=0, max_value=100, initial_value=50, step_size=1, variable=None,
                    is_dialogue=False, typing_speed=30, auto_advance=False, advance_speed=2000,
                    parallax_factor=None, follow_factor=None, hover_range=None, dynamic_value=None,
                    click_sound=None, release_sound=None):
        
        try:
            if any(el["id"] == element_id for el in self.ui_elements):
                return  

            original_image = None
            missing_texture = False

            if image_path:
                original_image = self.load_image(image_path, alpha)
                if original_image == self.game.environment.missing_texture:
                    missing_texture = True
                    
                original_image = pg.transform.scale(original_image, (width, height))

            elif sprite_sheet_path:
                sheet = self.loaded_sheets.get(sprite_sheet_path)

                if sheet:
                    try:
                        rows = sheet.get_height() // sprite_height
                        cols = sheet.get_width() // sprite_width

                        if image_id: 
                            row, col = image_id[0], image_id[1]
                            if 0 <= row < rows and 0 <= col < cols:
                                original_image = sheet.subsurface(pg.Rect(col * sprite_width, row * sprite_height, sprite_width, sprite_height))
                                original_image = pg.transform.scale(original_image, (width, height))
                                
                            else:
                                missing_texture = True
                                    
                    except Exception as e:
                        print(f"Error loading sprite from preloaded sheet {sprite_sheet_path}: {e}")
                        missing_texture = True
                        
                else:
                    missing_texture = True
                    print(f"Sprite sheet {sprite_sheet_path} not found, using missing texture")

            show_missing_texture = (missing_texture or original_image is None) and not is_slider and not (label and not is_button)
            
            if show_missing_texture:
                original_image = self.game.environment.missing_texture.copy()
                original_image = pg.transform.scale(original_image, (width, height))

            dynamic_display = None
            if dynamic_value is not None:
                if callable(dynamic_value):
                    dynamic_display = dynamic_value()
                    
                else:
                    dynamic_display = str(dynamic_value)
            
            display_label = dynamic_display if dynamic_display is not None else label

            if is_dialogue and display_label:
                full_text = display_label
                current_text = ""
                typing_index = 0
                last_typing_time = pg.time.get_ticks()
                typing_complete = False
                advance_timer = pg.time.get_ticks()
                
            else:
                full_text = None
                current_text = display_label
                typing_index = 0
                last_typing_time = 0
                typing_complete = True
                advance_timer = 0

            ui_font = self.load_font(font, font_size)
            text_surface = None
            if current_text:
                text_surface = ui_font.render(current_text, False, text_color)

            ui_element = {
                "original_image": original_image,
                "alpha": alpha,
                "is_button": is_button,
                "scale_multiplier": scale_multiplier,
                "scaled": False,
                "id": element_id,
                "callback": callback,
                "is_hold": is_hold,
                "holding": False,
                "label": current_text if not is_dialogue else "",
                "full_text": full_text,
                "font_path": font,
                "font_size": font_size,
                "text_color": text_color,
                "text_surface": text_surface,
                "render_order": render_order,
                "is_slider": is_slider,
                "min_value": min_value,
                "max_value": max_value,
                "current_value": initial_value,
                "step_size": step_size,
                "slider_rect": pg.Rect(x, y, width, height),
                "slider_knob": pg.Rect(x + (initial_value - min_value) / (max_value - min_value) * width, y, 20, height),
                "variable": variable,
                "grabbed": False,
                "is_dialogue": is_dialogue,
                "typing_speed": typing_speed,
                "typing_index": typing_index,
                "last_typing_time": last_typing_time,
                "typing_complete": typing_complete,
                "auto_advance": auto_advance,
                "advance_speed": advance_speed,
                "advance_timer": advance_timer,
                "parallax_factor": parallax_factor,
                "follow_factor": follow_factor,
                "hover_range": hover_range,
                "base_position": (x, y),
                "current_offset": (0, 0),
                "width": width,
                "height": height,
                "centered": centered,
                "dynamic_value": dynamic_value,
                "click_sound": click_sound,
                "release_sound": release_sound,
            }

            if centered:
                ui_element["rect"] = original_image.get_rect(center=(x, y)) if original_image else pg.Rect(x, y, width, height)
                
            else:
                ui_element["rect"] = pg.Rect(x, y, width, height)

            if text_surface:
                ui_element["text_rect"] = text_surface.get_rect(center=ui_element["rect"].center)

            if original_image:
                ui_element["image"] = ui_element["original_image"].copy()
                ui_element["center"] = (ui_element["rect"].centerx, ui_element["rect"].centery)

            self.ui_elements.append(ui_element)

        except Exception as e:
            print(f"Error creating UI element {element_id}: {e}")

    def remove_ui_element(self, element_id):
        self.ui_elements = [el for el in self.ui_elements if el["id"] != element_id]

    def clear_all_cache(self):
        self.loaded_sheets.clear()
        self.loaded_images.clear()
        self.loaded_fonts.clear()

    def update_dynamic_values(self):
        for element in self.ui_elements:
            if element.get("dynamic_value") is not None:
                if callable(element["dynamic_value"]):
                    current_value = element["dynamic_value"]()
                else:
                    current_value = element["dynamic_value"]
                
                current_display = str(current_value)
                
                if current_display != element.get("dynamic_display"):
                    element["dynamic_display"] = current_display
                    element["label"] = current_display
                    
                    if not element.get("is_dialogue", False):
                        ui_font = self.load_font(element["font_path"], element["font_size"])
                        element["text_surface"] = ui_font.render(current_display, False, element["text_color"])
                        
                        if "rect" in element:
                            element["text_rect"] = element["text_surface"].get_rect(center=element["rect"].center)

    def update_dialogue_text(self, element):
        if not element["is_dialogue"] or element["typing_complete"]:
            return

        current_time = pg.time.get_ticks()
        
        time_since_last = current_time - element["last_typing_time"]
        time_per_char = 1000 / element["typing_speed"]
        
        if time_since_last >= time_per_char:
            chars_to_add = int(time_since_last / time_per_char)
            element["typing_index"] = min(element["typing_index"] + chars_to_add, len(element["full_text"]))
            element["label"] = element["full_text"][:element["typing_index"]]
            element["last_typing_time"] = current_time
            
            element["text_surface"] = self.load_font(element["font_path"], element["font_size"]).render(element["label"], False, element["text_color"])
            element["text_rect"] = element["text_surface"].get_rect(center=element["rect"].center)
            
            if element["typing_index"] >= len(element["full_text"]):
                element["typing_complete"] = True
                element["advance_timer"] = current_time

        if element["auto_advance"] and element["typing_complete"]:
            if current_time - element["advance_timer"] >= element["advance_speed"]:
                if element["callback"]:
                    element["callback"]()
                    
                element["advance_timer"] = current_time

    def update_ui_movement(self, element, mouse_pos):
        screen_center_x = self.game.screen_width / 2
        screen_center_y = self.game.screen_height / 2
        
        norm_mouse_x = (mouse_pos[0] - screen_center_x) / screen_center_x
        norm_mouse_y = (mouse_pos[1] - screen_center_y) / screen_center_y
        
        offset_x, offset_y = 0, 0
        
        if element["parallax_factor"]:
            offset_x += -norm_mouse_x * element["parallax_factor"] * element["rect"].width
            offset_y += -norm_mouse_y * element["parallax_factor"] * element["rect"].height
        
        if element["follow_factor"]:
            element_center_x = element["rect"].centerx
            element_center_y = element["rect"].centery
            
            direction_x = mouse_pos[0] - element_center_x
            direction_y = mouse_pos[1] - element_center_y
            
            distance = max(1, (direction_x ** 2 + direction_y ** 2) ** 0.5)
            
            offset_x += direction_x * element["follow_factor"]
            offset_y += direction_y * element["follow_factor"]
        
        if element["hover_range"] and element["is_button"]:
            cx, cy = element["rect"].center
            dx = mouse_pos[0] - cx
            dy = mouse_pos[1] - cy
            dist = (dx * dx + dy * dy) ** 0.5

            hover_radius = max(element["rect"].width, element["rect"].height) * 0.5

            min_distance = 13
            if dist > min_distance and dist < hover_radius:
                strength = 1.0 - (dist / hover_radius)
                max_offset = float(element["hover_range"])

                if dist > 0:
                    normalized_dx = dx / dist
                    normalized_dy = dy / dist
                    
                    scale = (max_offset * strength * strength) / hover_radius
                    offset_x += normalized_dx * scale * hover_radius
                    offset_y += normalized_dy * scale * hover_radius
        
        current_offset_x, current_offset_y = element["current_offset"]
        smooth_factor = 0.2
        
        new_offset_x = current_offset_x * (1 - smooth_factor) + offset_x * smooth_factor
        new_offset_y = current_offset_y * (1 - smooth_factor) + offset_y * smooth_factor
        
        element["current_offset"] = (new_offset_x, new_offset_y)

        if element["centered"]:
            element["rect"] = element["image"].get_rect(
                center=(element["base_position"][0] + new_offset_x, element["base_position"][1] + new_offset_y)
            ) if element["original_image"] else pg.Rect(
                element["base_position"][0] + new_offset_x - element["width"]/2,
                element["base_position"][1] + new_offset_y - element["height"]/2,
                element["width"], element["height"]
            )
            
        else:
            element["rect"] = pg.Rect(
                element["base_position"][0] + new_offset_x,
                element["base_position"][1] + new_offset_y,
                element["width"], element["height"]
            )
        
        if element.get("text_surface"):
            if element["scaled"] and "scaled_text_rect" in element:
                element["scaled_text_rect"] = element["scaled_text_surface"].get_rect(center=element["rect"].center)
                
            elif "text_rect" in element:
                element["text_rect"] = element["text_surface"].get_rect(center=element["rect"].center)

    def update_button_interaction(self, element, mouse_pos, mouse_pressed):
        if getattr(self, "mouse_locked", False):
            if not mouse_pressed[0]:
                self.mouse_locked = False
            return

        if element["original_image"] and element.get("alpha") and "mask" not in element:
            element["mask"] = pg.mask.from_surface(element["original_image"])

        hovered = element["rect"].collidepoint(mouse_pos)

        if hovered and element.get("alpha") and "mask" in element:
            offset_x = mouse_pos[0] - element["rect"].x
            offset_y = mouse_pos[1] - element["rect"].y
            if not (0 <= offset_x < element["mask"].get_size()[0] and 0 <= offset_y < element["mask"].get_size()[1] and element["mask"].get_at((offset_x, offset_y))):
                hovered = False

        if hovered and mouse_pressed[0] and not element.get("scaled"):
            old_center = element["rect"].center
            new_width = int(element["rect"].width * element["scale_multiplier"])
            new_height = int(element["rect"].height * element["scale_multiplier"])
            
            element["image"] = pg.transform.scale(element["original_image"], (new_width, new_height))
            element["rect"] = element["image"].get_rect(center=old_center)
            element["scaled"] = True
            element["mask"] = pg.mask.from_surface(element["image"])

            if element.get("text_surface"):
                text_scale = element["scale_multiplier"]
                scaled_text_surface = pg.transform.scale(
                    element["text_surface"],
                    (int(element["text_surface"].get_width() * text_scale),
                    int(element["text_surface"].get_height() * text_scale)))
                element["scaled_text_surface"] = scaled_text_surface
                element["scaled_text_rect"] = scaled_text_surface.get_rect(center=element["rect"].center)

            if element["click_sound"]:
                sound = element["click_sound"]["sound"]
                volume = element["click_sound"]["volume"]
                sound.set_volume(self.game.environment.volume / 10 * volume)
                sound.play()

        elif element.get("scaled") and (not hovered or not mouse_pressed[0]):
            old_center = element["rect"].center
            element["image"] = element["original_image"].copy()
            element["rect"] = element["image"].get_rect(center=old_center)
            element["scaled"] = False
            element.pop("mask", None)
            element.pop("scaled_text_surface", None)
            element.pop("scaled_text_rect", None)

        if hovered:
            if mouse_pressed[0]:
                element["holding"] = True
                
            elif element["holding"]:
                if element["callback"]:
                    element["callback"]()
                    
                element["holding"] = False
                self.mouse_locked = True
                
                if element["release_sound"]:
                    sound = element["release_sound"]["sound"]
                    volume = element["release_sound"]["volume"]
                    sound.set_volume(self.game.environment.volume / 10 * volume)
                    sound.play()

        else:
            element["holding"] = False

    def update_slider_interaction(self, element, mouse_pos, mouse_pressed):
        track_rect = element["slider_rect"]
        knob_rect = element["slider_knob"]

        pg.draw.rect(self.game.screen, (200, 200, 200), track_rect)
        pg.draw.rect(self.game.screen, (0, 0, 255), knob_rect)

        if pg.mouse.get_pressed()[0]:
            if knob_rect.collidepoint(mouse_pos) and not element["grabbed"]:
                element["grabbed"] = True
                if element["click_sound"]:
                    sound = element["click_sound"]["sound"]
                    volume = element["click_sound"]["volume"]
                    sound.set_volume(self.game.environment.volume / 10 * volume)
                    sound.play()
        
        else:
            if element["grabbed"] and element["release_sound"]:
                sound = element["release_sound"]["sound"]
                volume = element["release_sound"]["volume"]
                sound.set_volume(self.game.environment.volume / 10 * volume)
                sound.play()
                
            element["grabbed"] = False
            
        if element["grabbed"]:
            knob_rect.x = max(track_rect.x, min(mouse_pos[0] - knob_rect.width / 2, track_rect.right - knob_rect.width))
            
        relative_position = (knob_rect.x - track_rect.x) / track_rect.width
        new_value = element["min_value"] + relative_position * (element["max_value"] - element["min_value"])

        if element["step_size"] > 0:
            new_value = round(new_value / element["step_size"]) * element["step_size"]
            new_value = max(min(new_value, element["max_value"]), element["min_value"])
            
        element["current_value"] = new_value
        
        if element["variable"]:
            element["variable"](new_value)
            
        element["slider_knob"] = knob_rect
    
    def reset_ui_position(self, element_id):
        for element in self.ui_elements:
            if element["id"] == element_id:
                element["current_offset"] = (0, 0)
                
                if element["centered"]:
                    element["rect"] = element["original_image"].get_rect(
                        center=element["base_position"]
                    ) if element["original_image"] else pg.Rect(
                        element["base_position"][0] - element["width"]/2,
                        element["base_position"][1] - element["height"]/2,
                        element["width"], element["height"]
                    )
                    
                else:
                    element["rect"] = pg.Rect(
                        element["base_position"][0],
                        element["base_position"][1],
                        element["width"], element["height"]
                    )
    
                if "text_rect" in element:
                    element["text_rect"] = element["text_surface"].get_rect(center=element["rect"].center)
                    
                break

    def render_ui_element(self, element):
        if element["original_image"]:
            self.game.screen.blit(element["image"], element["rect"])

        if element.get("text_surface"):
            if element["scaled"] and "scaled_text_surface" in element:
                self.game.screen.blit(element["scaled_text_surface"], element["scaled_text_rect"])
                
            elif "text_surface" in element:
                self.game.screen.blit(element["text_surface"], element["text_rect"])

    def update(self):
        mouse_pos = pg.mouse.get_pos()
        mouse_pressed = pg.mouse.get_pressed()

        self.ui_elements.sort(key=lambda x: x.get("render_order", 0))
        
        self.update_dynamic_values()

        for element in self.ui_elements:
            if any([element.get("parallax_factor"), element.get("follow_factor"), element.get("hover_range")]):
                self.update_ui_movement(element, mouse_pos)
            
            if element.get("is_dialogue"):
                self.update_dialogue_text(element)

            if element.get("is_button"):
                self.update_button_interaction(element, mouse_pos, mouse_pressed)

            if element.get("is_slider"):
                self.update_slider_interaction(element, mouse_pos, mouse_pressed)

            self.render_ui_element(element)