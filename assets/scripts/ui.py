import pygame as pg

# poor implementation of a class that handles all UI in the game 
# one instance of this class is created in the game class, and it handles all UI in the game
# and should be refactored to have seperate instances for each entity
# will make more OOP friendly and more conventional
class UI:
    def __init__(self, game):
        self.game = game
        
        self.ui_elements = []
        
        self.loaded_sheets = {}
        self.loaded_images = {}
        
    def load_sheet(self, sheet_name, path):
        if sheet_name in self.loaded_sheets:
            return
        
        try:
            self.loaded_sheets[sheet_name] = pg.image.load(path).convert_alpha()
            
        except Exception as e:
            print(f"Error loading sprite sheet {path}: {e}")

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
    
    def load_font(self, font, size=24):
        if isinstance(font, pg.font.Font):
            return font
        
        try:
            return pg.font.Font(font, size) if font else pg.font.Font(None, size)
        
        except Exception as e:
            print(f"Error loading font: {e}")
            return pg.font.Font(None, size)

    def create_ui(self, x, y, width, height, alpha=None, is_button=False, scale_multiplier=1.1,
                    image_path=None, sprite_sheet_path=None, sprite_width=16, sprite_height=16,
                    image_id=None, element_id=None, centered=False, callback=None, is_hold=False,
                    label=None, font=None, font_size=24, text_color=(255, 255, 255), render_order=0,
                    is_slider=False, min_value=0, max_value=100, initial_value=50, step_size=1, variable=None):

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
                            parts = image_id.split('_')
                            if len(parts) == 3:
                                row, col = int(parts[1]), int(parts[2])
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

            show_missing_texture = (missing_texture or original_image is None) and not is_slider and not (label and not is_button)
            
            if show_missing_texture:
                original_image = self.game.environment.missing_texture.copy()
                original_image = pg.transform.scale(original_image, (width, height))

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
                "label": label,
                "font": self.load_font(font, font_size),
                "text_color": text_color,
                "text_surface": None,
                "render_order": render_order,
                "is_slider": is_slider,
                "min_value": min_value,
                "max_value": max_value,
                "current_value": initial_value,
                "step_size": step_size,
                "slider_rect": pg.Rect(x, y, width, height),
                "slider_knob": pg.Rect(x + (initial_value - min_value) / (max_value - min_value) * width, y, 20, height),
                "variable": variable,
                "grabbed": False
            }

            if centered:
                ui_element["rect"] = original_image.get_rect(center=(x, y)) if original_image else pg.Rect(x, y, width, height)
                
            else:
                ui_element["rect"] = pg.Rect(x, y, width, height)

            if label:
                ui_element["text_surface"] = ui_element["font"].render(label, False, text_color)
                ui_element["text_rect"] = ui_element["text_surface"].get_rect(center=ui_element["rect"].center)

            if original_image:
                ui_element["image"] = ui_element["original_image"].copy()
                ui_element["center"] = (ui_element["rect"].centerx, ui_element["rect"].centery)

            self.ui_elements.append(ui_element)

        except Exception as e:
            print(f"Error creating UI element {element_id}: {e}")

    def remove_ui_element(self, element_id):
        self.ui_elements = [el for el in self.ui_elements if el["id"] != element_id]

    def update(self):
        mouse_pos = pg.mouse.get_pos()
        mouse_pressed = pg.mouse.get_pressed()

        self.ui_elements.sort(key=lambda x: x.get("render_order", 0))

        for element in self.ui_elements:
            if element["is_button"]:
                if element["original_image"] and element["alpha"] and "mask" not in element:
                    element["mask"] = pg.mask.from_surface(element["original_image"])

                offset_x = mouse_pos[0] - element["rect"].x
                offset_y = mouse_pos[1] - element["rect"].y

                if element["rect"].collidepoint(mouse_pos):
                    if element["alpha"]:
                        if (0 <= offset_x < element["mask"].get_size()[0]) and (0 <= offset_y < element["mask"].get_size()[1]):
                            if element["mask"].get_at((offset_x, offset_y)):
                                if not element["scaled"]:
                                    new_width = int(element["rect"].width * element["scale_multiplier"])
                                    new_height = int(element["rect"].height * element["scale_multiplier"])
                                    element["image"] = pg.transform.scale(element["original_image"], (new_width, new_height))
                                    element["rect"] = element["image"].get_rect(center=element["center"])
                                    element["scaled"] = True
                                    element["mask"] = pg.mask.from_surface(element["image"])

                            else:
                                if element["scaled"]:
                                    element["image"] = element["original_image"].copy()
                                    element["rect"] = element["image"].get_rect(center=element["center"])
                                    element["scaled"] = False
                                    element.pop("mask", None)

                        else:
                            if element["scaled"]:
                                element["image"] = element["original_image"].copy()
                                element["rect"] = element["image"].get_rect(center=element["center"])
                                element["scaled"] = False
                                element.pop("mask", None)

                    else:
                        if not element["scaled"]:
                            new_width = int(element["rect"].width * element["scale_multiplier"])
                            new_height = int(element["rect"].height * element["scale_multiplier"])
                            element["image"] = pg.transform.scale(element["original_image"], (new_width, new_height))
                            element["rect"] = element["image"].get_rect(center=element["center"])
                            element["scaled"] = True
                            element["mask"] = pg.mask.from_surface(element["image"])

            if element["is_button"]:
                if element["rect"].collidepoint(mouse_pos):
                    if mouse_pressed[0]:
                        if element["is_hold"]:
                            if element["callback"]:
                                element["callback"]()
                                
                        elif not element["holding"]:
                            if element["callback"]:
                                element["callback"]()
                            element["holding"] = True
                            
                    else:
                        element["holding"] = False
                        
                        
                else:
                    element["holding"] = False

            if element["is_slider"]:
                track_rect = element["slider_rect"]
                knob_rect = element["slider_knob"]

                pg.draw.rect(self.game.screen, (200, 200, 200), track_rect)
                pg.draw.rect(self.game.screen, (0, 0, 255), knob_rect)

                if pg.mouse.get_pressed()[0]:
                    if knob_rect.collidepoint(mouse_pos):
                        element["grabbed"] = True
                
                else:
                    element["grabbed"] = False
                        
                if element["grabbed"]:
                    knob_rect.x = max(track_rect.x, min(mouse_pos[0] - knob_rect.width // 2, track_rect.right - knob_rect.width))

                relative_position = (knob_rect.x - track_rect.x) / track_rect.width

                new_value = element["min_value"] + relative_position * (element["max_value"] - element["min_value"])

                if element["step_size"] > 0:
                    new_value = round(new_value / element["step_size"]) * element["step_size"]

                    new_value = max(min(new_value, element["max_value"]), element["min_value"])

                element["current_value"] = new_value
                
                if element["variable"]:
                    element["variable"](new_value)

                element["slider_knob"] = knob_rect

            if element["original_image"]:
                self.game.screen.blit(element["image"], element["rect"])

            if element["label"] and element["text_surface"]:
                self.game.screen.blit(element["text_surface"], element["text_rect"])
                
