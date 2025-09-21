import pygame as pg
import traceback
import psutil
import os

from collections import defaultdict

class MemoryDebugger:
    def __init__(self, game):
        self.game = game
        self.show_memory_info = False
        self.memory_info = []
        self.scroll_offset = 0
        self.last_update_time = 0
        self.update_interval = 500
        self.font = pg.font.SysFont("Consolas", 14)

        self.dragging_scrollbar = False
        self.drag_offset_y = 0
        self.drag_start_scroll = 0

        self.menu_state = "main"
        self.selected_storage = None
        self.selected_object = None

        self.scroll_offsets = defaultdict(int)

        self.preview_cache = {}

        self.terminal_active = False
        self.terminal_input = ""
        self.terminal_history = []
        self.terminal_scroll = 0
        self.cursor_blink = 0
        self.cursor_visible = True
        self.last_cursor_toggle = 0
        self.terminal_font = pg.font.SysFont("Consolas", 14)
        
        self.terminal_event = pg.USEREVENT + 1

    def toggle(self):
        self.show_memory_info = not self.show_memory_info
        self.menu_state = "main"
        self.selected_group = None
        self.selected_storage = None
        self.selected_object = None
        self.scroll_offsets.clear()
        self.dragging_scrollbar = False
        self.update()

    def toggle_terminal(self):
        self.terminal_active = not self.terminal_active
        
        if not self.terminal_active:
            return

        self.terminal_input = ""
        self.cursor_visible = True
        self.last_cursor_toggle = pg.time.get_ticks()

    def handle_terminal_input(self, event):
        if not self.terminal_active:
            return

        current_time = pg.time.get_ticks()
        if current_time - self.last_cursor_toggle > 500:
            self.cursor_visible = not self.cursor_visible
            self.last_cursor_toggle = current_time

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_RETURN:
                self.execute_terminal_command()
                
            elif event.key == pg.K_BACKSPACE:
                if self.terminal_input:
                    self._delayed_backspace = True
                    pg.time.set_timer(self.terminal_event, 50, True)  
                    
            elif event.key == pg.K_UP:
                if self.terminal_history:
                    self.terminal_input = self.terminal_history[-1]
                    
            elif event.key == pg.K_DOWN:
                self.terminal_input = ""
                
            elif event.key == pg.K_ESCAPE:
                self.toggle_terminal()
                
            elif event.key == pg.K_PAGEUP:
                self.terminal_scroll = min(len(self.terminal_history), self.terminal_scroll + 5)
                
            elif event.key == pg.K_PAGEDOWN:
                self.terminal_scroll = max(0, self.terminal_scroll - 5)
                
            elif event.key == pg.K_TAB:
                pass 

        elif event.type == pg.TEXTINPUT:
            if len(self.terminal_input) < 100:
                self._delayed_input_char = event.text
                pg.time.set_timer(self.terminal_event, 50, True)
                
        elif event.type == self.terminal_event:
            if hasattr(self, '_delayed_input_char'):
                self.terminal_input += self._delayed_input_char
                
                del self._delayed_input_char
                
            if hasattr(self, '_delayed_backspace') and self._delayed_backspace:
                self.terminal_input = self.terminal_input[:-1]
                self._delayed_backspace = False

    def execute_terminal_command(self):
        if not self.terminal_input.strip():
            return
            
        command = self.terminal_input.strip()
        self.terminal_history.append(f"> {command}")
        
        try:
            if '=' in command:
                var_path, value = command.split('=', 1)
                var_path = var_path.strip()
                value = value.strip()
                
                try:
                    evaluated_value = eval(value, {}, {'game': self.game})
                    
                except:
                    evaluated_value = value
                
                parts = var_path.split('.')
                obj = self.game
                for part in parts[:-1]:
                    obj = getattr(obj, part)
                
                setattr(obj, parts[-1], evaluated_value)
                self.terminal_history.append(f"Set {var_path} = {evaluated_value}")
                
            else:
                result = eval(command, {}, {'game': self.game})
                self.terminal_history.append(str(result))
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.terminal_history.append(error_msg)
            traceback.print_exc()
            
        self.terminal_input = ""
        self.terminal_scroll = 0

    def render_terminal(self):
        if not self.terminal_active:
            return
            
        screen = self.game.screen
        width, height = self.game.screen_width, self.game.screen_height
        
        terminal_width = min(800, width - 40)
        terminal_height = min(400, height - 40)
        terminal_x = (width - terminal_width) // 2
        terminal_y = (height - terminal_height) // 2
        
        terminal_panel = pg.Surface((terminal_width, terminal_height), pg.SRCALPHA)
        terminal_panel.fill((0, 0, 0, 220))
        pg.draw.rect(terminal_panel, (100, 100, 100), (0, 0, terminal_width, terminal_height), 2)
        
        line_height = 18
        visible_lines = (terminal_height - 30) // line_height
        start_line = max(0, len(self.terminal_history) - visible_lines + self.terminal_scroll)
        
        for i in range(visible_lines):
            idx = start_line + i
            if 0 <= idx < len(self.terminal_history):
                line = self.terminal_history[idx]
                color = (200, 255, 200) if line.startswith('>') else (255, 255, 255)
                text_surf = self.terminal_font.render(line, True, color)
                terminal_panel.blit(text_surf, (10, 10 + i * line_height))
        
        input_y = terminal_height - 25
        pg.draw.rect(terminal_panel, (50, 50, 50), (0, input_y, terminal_width, 25))
        
        prompt = ">>> "
        prompt_surf = self.terminal_font.render(prompt, True, (255, 255, 255))
        terminal_panel.blit(prompt_surf, (10, input_y + 3))
        
        input_text = self.terminal_input
        input_surf = self.terminal_font.render(input_text, True, (255, 255, 255))
        terminal_panel.blit(input_surf, (10 + prompt_surf.get_width(), input_y + 3))
        
        if self.cursor_visible:
            cursor_x = 10 + prompt_surf.get_width() + input_surf.get_width()
            pg.draw.rect(terminal_panel, (255, 255, 255), (cursor_x, input_y + 3, 2, line_height - 4))
        
        help_text = "ESC: Close | UP: History | ENTER: Execute | TAB: Complete"
        help_surf = self.terminal_font.render(help_text, True, (150, 150, 150))
        terminal_panel.blit(help_surf, (terminal_width - help_surf.get_width() - 10, input_y - 20))
        
        screen.blit(terminal_panel, (terminal_x, terminal_y))

    def update(self):
        if self.menu_state == "main":
            current_time = pg.time.get_ticks()
            if current_time - self.last_update_time > self.update_interval:
                self.memory_info = self.get_memory_info()
                self.last_update_time = current_time

    def handle_scroll(self, direction):
        max_scroll = self.get_max_scroll()
        
        if direction == "up":
            self.scroll_offsets[self.menu_state] = max(0, self.scroll_offsets[self.menu_state] - 1)
            
        elif direction == "down":
            self.scroll_offsets[self.menu_state] = min(max_scroll, self.scroll_offsets[self.menu_state] + 1)

    def get_max_scroll(self):
        if self.menu_state == "main":
            return max(0, len(self.memory_info) - self.visible_lines())
            
        elif self.menu_state == "size_group":
            group_surfaces = self.get_current_group_surfaces()
            thumbs_per_row = self.thumbs_per_row()
            rows = (len(group_surfaces) + thumbs_per_row - 1) // thumbs_per_row
            return max(0, rows - self.visible_rows())
            
        elif self.menu_state == "storage_location":
            return max(0, len(self.get_current_storage_surfaces()) - self.visible_lines())
            
        elif self.menu_state == "object_info":
            return max(0, len(self.get_object_info()) - self.visible_lines())
            
        return 0

    def get_scrollbar_height(self, panel_height):
        if self.menu_state == "main":
            total_lines = len(self.memory_info)
            if total_lines <= 0:
                return panel_height
            return max(20, min(1.0, self.visible_lines() / total_lines) * panel_height)
            
        elif self.menu_state == "size_group":
            group_surfaces = self.get_current_group_surfaces()
            thumbs_per_row = self.thumbs_per_row()
            total_rows = (len(group_surfaces) + thumbs_per_row - 1) // thumbs_per_row
            if total_rows <= 0:
                return panel_height
            return max(20, min(1.0, self.visible_rows() / total_rows) * panel_height)
            
        elif self.menu_state == "storage_location":
            surfaces = self.get_current_storage_surfaces()
            if len(surfaces) <= 0:
                return panel_height
            return max(20, min(1.0, self.visible_lines() / len(surfaces)) * panel_height)
            
        elif self.menu_state == "object_info":
            info = self.get_object_info()
            if len(info) <= 0:
                return panel_height
            return max(20, min(1.0, self.visible_lines() / len(info)) * panel_height)
            
        return panel_height

    def handle_mouse_event(self, event):
        if self.terminal_active:
            return
            
        if not self.show_memory_info:
            return

        screen_w, screen_h = self.game.screen_width, self.game.screen_height
        panel_width = min(600, screen_w - 40)
        panel_height = min(400, screen_h - 40)
        panel_x = (screen_w - panel_width) // 2
        panel_y = (screen_h - panel_height) // 2

        scrollbar_x = panel_x + panel_width - 10
        scrollbar_height = self.get_scrollbar_height(panel_height)
        max_scroll = self.get_max_scroll()
        
        scroll_ratio = self.scroll_offsets[self.menu_state] / max(1, max_scroll)
        scrollbar_y = panel_y + scroll_ratio * (panel_height - scrollbar_height)

        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                mx, my = event.pos
                
                if scrollbar_x <= mx <= scrollbar_x + 8 and scrollbar_y <= my <= scrollbar_y + scrollbar_height:
                    self.dragging_scrollbar = True
                    self.drag_offset_y = my - scrollbar_y
                    self.drag_start_scroll = self.scroll_offsets[self.menu_state]
                    return

                if panel_x <= mx <= panel_x + panel_width and panel_y <= my <= panel_y + panel_height:
                    rel_x = mx - panel_x
                    rel_y = my - panel_y
                    
                    if self.menu_state == "main":
                        clicked_line = rel_y // 18 + self.scroll_offsets[self.menu_state]

                        objects_start = None
                        for idx, line in enumerate(self.memory_info):
                            if line.strip() == "Game Objects Count:":
                                objects_start = idx
                                break
                            
                        if objects_start and objects_start + 1 <= clicked_line <= objects_start + 4:
                            self.selected_object = self.memory_info[clicked_line].strip().split(":")[0].strip()
                            self.menu_state = "object_info"
                            self.scroll_offsets[self.menu_state] = 0
                            return

                        size_dist_start = None
                        for idx, line in enumerate(self.memory_info):
                            if line.strip() == "Image Size Distribution:":
                                size_dist_start = idx
                                break
                            
                        if size_dist_start and size_dist_start < clicked_line < size_dist_start + 12:
                            index = clicked_line - (size_dist_start + 1)
                            size_groups = self.collect_size_groups()
                            size_keys = sorted(size_groups.keys(), key=lambda k: len(size_groups[k]), reverse=True)
                            if index < len(size_keys):
                                self.selected_group = size_keys[index]
                                self.menu_state = "size_group"
                                self.scroll_offsets[self.menu_state] = 0
                                self.preview_cache.clear()
                                return

                        storage_start = None
                        for idx, line in enumerate(self.memory_info):
                            if line.strip() == "Storage Locations:":
                                storage_start = idx
                                break
                            
                        if storage_start and storage_start < clicked_line < storage_start + 100:
                            index = clicked_line - (storage_start + 1)
                            storage_locations = self.collect_storage_locations()
                            storage_keys = list(storage_locations.keys())
                            if 0 <= index < len(storage_keys):
                                self.selected_storage = storage_keys[index]
                                self.menu_state = "storage_location"
                                self.scroll_offsets[self.menu_state] = 0
                                self.preview_cache.clear()
                                return

        elif event.type == pg.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging_scrollbar = False

        elif event.type == pg.MOUSEMOTION:
            if self.dragging_scrollbar:
                my = event.pos[1]
                relative_y = my - panel_y - self.drag_offset_y
                relative_y = max(0, min(relative_y, panel_height - scrollbar_height))
                
                if max_scroll > 0:
                    scroll_ratio = relative_y / (panel_height - scrollbar_height)
                    self.scroll_offsets[self.menu_state] = int(scroll_ratio * max_scroll)

        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 4:
                self.handle_scroll("up")
                
            elif event.button == 5:
                self.handle_scroll("down")
                
            elif event.button == 3:
                if self.menu_state != "main":
                    self.menu_state = "main"
                    self.selected_group = None
                    self.selected_storage = None
                    self.selected_object = None
                    self.scroll_offsets[self.menu_state] = 0

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                if self.terminal_active:
                    self.toggle_terminal()
                    
                elif self.menu_state != "main":
                    self.menu_state = "main"
                    self.selected_group = None
                    self.selected_storage = None
                    self.selected_object = None
                    self.scroll_offsets[self.menu_state] = 0
                    
                else:
                    self.toggle()
                    
            elif event.key == pg.K_BACKQUOTE or event.key == pg.K_TAB:
                self.toggle_terminal()
                
            elif event.key == pg.K_UP:
                self.handle_scroll("up")
                
            elif event.key == pg.K_DOWN:
                self.handle_scroll("down")

    def visible_lines(self):
        panel_height = min(400, self.game.screen_height - 40)
        line_height = 18
        
        return panel_height // line_height

    def visible_rows(self):
        panel_height = min(400, self.game.screen_height - 40)
        y_offset = 40
        thumb_size = 64
        margin = 5
        
        return max(1, (panel_height - y_offset) // (thumb_size + margin))

    def thumbs_per_row(self):
        panel_width = min(600, self.game.screen_width - 40)
        thumb_size = 64
        margin = 5
        
        return max(1, panel_width // (thumb_size + margin))

    def collect_size_groups(self):
        all_surfaces = self.collect_all_surfaces()
        size_groups = defaultdict(list)
        for s in all_surfaces:
            size = f"{s.get_width()}x{s.get_height()}"
            size_groups[size].append(s)
            
        return size_groups

    def collect_storage_locations(self):
        storage_locations = defaultdict(list)
        visited_objects = set()

        game_objects = [
            ('UI', self.game.ui),
            ('Environment', self.game.environment),
            ('Map', self.game.map),
            ('Player', self.game.player),
            ('Entities', self.game.entities),
            ('Background', self.game.background),
            ('Particles', self.game.particles)
        ]

        def find_surfaces(obj, path):
            obj_id = id(obj)
            if obj_id in visited_objects:
                return
            visited_objects.add(obj_id)
            try:
                if isinstance(obj, pg.Surface):
                    storage_locations[path].append(obj)
                    
                elif isinstance(obj, (list, tuple)):
                    for i, item in enumerate(obj):
                        find_surfaces(item, f"{path}[{i}]")
                        
                elif isinstance(obj, dict):
                    for k, v in obj.items():
                        find_surfaces(v, f"{path}['{k}']")
                        
                elif hasattr(obj, '__dict__'):
                    for name, attr in vars(obj).items():
                        if not name.startswith('__'):
                            find_surfaces(attr, f"{path}.{name}")
            except Exception:
                pass

        for name, obj in game_objects:
            find_surfaces(obj, name)

        return storage_locations

    def get_current_group_surfaces(self):
        size_groups = self.collect_size_groups()
        return size_groups.get(self.selected_group, [])

    def get_current_storage_surfaces(self):
        storage_locations = self.collect_storage_locations()
        return storage_locations.get(self.selected_storage, [])

    def get_object_info(self):
        info = []
        if self.selected_object == "UI Elements":
            count = len(getattr(self.game.ui, 'ui_elements', []))
            info.append(f"UI Elements Count: {count}")
            info.append("")
            for i, element in enumerate(getattr(self.game.ui, 'ui_elements', [])[:20]):
                info.append(f"Element {i}: {str(element)}")
                
        elif self.selected_object == "Entities":
            count = len(getattr(self.game.entities, 'entities', []))
            info.append(f"Entities Count: {count}")
            info.append("")
            for i, entity in enumerate(getattr(self.game.entities, 'entities', [])[:20]):
                info.append(f"Entity {i}: {str(entity)}")
                
        elif self.selected_object == "Particles":
            count = len(getattr(self.game.particles, 'particles', []))
            info.append(f"Particles Count: {count}")
            info.append("")
            for i, particle in enumerate(getattr(self.game.particles, 'particles', [])[:20]):
                info.append(f"Particle {i}: {str(particle)}")
        return info

    def collect_all_surfaces(self):
        all_surfaces = []
        visited_objects = set()
        exclude_set = set(self.preview_cache.values())

        game_objects = [
            ('UI', self.game.ui),
            ('Environment', self.game.environment),
            ('Map', self.game.map),
            ('Player', self.game.player),
            ('Entities', self.game.entities),
            ('Background', self.game.background),
            ('Particles', self.game.particles)
        ]

        def find_surfaces(obj):
            obj_id = id(obj)
            if obj_id in visited_objects:
                return
            
            visited_objects.add(obj_id)
            try:
                if isinstance(obj, pg.Surface):
                    if obj not in exclude_set:
                        all_surfaces.append(obj)
                        
                elif isinstance(obj, (list, tuple)):
                    for item in obj:
                        find_surfaces(item)
                        
                elif isinstance(obj, dict):
                    for v in obj.values():
                        find_surfaces(v)
                        
                elif hasattr(obj, '__dict__'):
                    for attr in vars(obj).values():
                        find_surfaces(attr)
                        
            except Exception:
                pass

        for _, obj in game_objects:
            find_surfaces(obj)

        return all_surfaces

    def get_ram_usage(self):
        try:
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            virtual_memory = psutil.virtual_memory()
            total_ram = virtual_memory.total / 1024 / 1024 / 1024  # GB
            used_ram = virtual_memory.used / 1024 / 1024 / 1024  # GB
            free_ram = virtual_memory.available / 1024 / 1024 / 1024  # GB
            ram_percent = virtual_memory.percent
            
            return {
                "process_memory": process_memory,
                "total_ram": total_ram,
                "used_ram": used_ram,
                "free_ram": free_ram,
                "ram_percent": ram_percent
            }
        except Exception:
            return None

    def get_memory_info(self):
        info = []
        info.append("=== MEMORY DEBUGGER ===")
        info.append("Press ` or TAB for terminal. Scroll with mouse or keys. Press ESC to close.\n")
        
        ram_info = self.get_ram_usage()
        if ram_info:
            info.append("RAM Usage:")
            info.append(f"  Process Memory: {ram_info['process_memory']:.2f} MB")
            info.append(f"  System RAM: {ram_info['used_ram']:.2f} GB / {ram_info['total_ram']:.2f} GB ({ram_info['ram_percent']:.1f}% used)")
            info.append(f"  Free RAM: {ram_info['free_ram']:.2f} GB")
            info.append("")

        info.append("Game Objects Count:")
        info.append(f"  UI Elements: {len(getattr(self.game.ui, 'ui_elements', []))}")
        info.append(f"  Entities: {len(getattr(self.game.entities, 'entities', []))}")
        info.append(f"  Particles: {len(getattr(self.game.particles, 'particles', []))}")
        info.append("")

        all_surfaces = self.collect_all_surfaces()
        total_surfaces = len(all_surfaces)
        total_memory = sum(s.get_width() * s.get_height() * (4 if s.get_bytesize() == 4 else 3) for s in all_surfaces)

        info.append("Surface/Image Memory Info:")
        info.append(f"  Total Images Found: {total_surfaces}")
        info.append(f"  Total Image Memory: {total_memory / 1024:.1f} KB\n")
        info.append("")

        size_groups = self.collect_size_groups()
        if size_groups:
            info.append("Image Size Distribution:")
            for size, surfaces in sorted(size_groups.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
                mem = sum(s.get_width() * s.get_height() * (4 if s.get_bytesize() == 4 else 3) for s in surfaces)
                info.append(f"  {size:<10} {len(surfaces):>3} images  {mem / 1024:>7.1f} KB")
                
            info.append("")

        storage_locations = self.collect_storage_locations()
        if storage_locations:
            info.append("Storage Locations:")
            for location, surfaces in storage_locations.items():
                mem = sum(s.get_width() * s.get_height() * (4 if s.get_bytesize() == 4 else 3) for s in surfaces)
                info.append(f"  {location}: {len(surfaces)} images ({mem / 1024:.1f} KB)")
                
            info.append("")

        return info

    def find_line_index(self, keyword):
        try:
            return self.memory_info.index(keyword)
        
        except ValueError:
            return None

    def render(self):
        if not self.show_memory_info and not self.terminal_active:
            return

        self.update()

        screen = self.game.screen
        width, height = self.game.screen_width, self.game.screen_height

        if self.terminal_active:
            self.render_terminal()
            return

        panel_width = min(600, width - 40)
        panel_height = min(400, height - 40)
        panel_x = (width - panel_width) // 2
        panel_y = (height - panel_height) // 2

        panel = pg.Surface((panel_width, panel_height), pg.SRCALPHA)
        panel.fill((0, 0, 0, 220))
        pg.draw.rect(panel, (100, 100, 100), (0, 0, panel_width, panel_height), 2)

        scrollbar_x = panel_width - 10
        scrollbar_height = self.get_scrollbar_height(panel_height)
        max_scroll = self.get_max_scroll()
        
        scroll_ratio = self.scroll_offsets[self.menu_state] / max(1, max_scroll)
        scrollbar_y = scroll_ratio * (panel_height - scrollbar_height)

        if self.menu_state == "main":
            start_line = max(0, min(self.scroll_offsets[self.menu_state], len(self.memory_info) - self.visible_lines()))

            ram_start = self.find_line_index("RAM Usage:")
            objects_start = self.find_line_index("Game Objects Count:")
            size_dist_start = self.find_line_index("Image Size Distribution:")
            storage_start = self.find_line_index("Storage Locations:")

            for i in range(self.visible_lines()):
                line_idx = start_line + i
                if line_idx < len(self.memory_info):
                    text = self.memory_info[line_idx]
                    color = (200, 255, 200)

                    if ram_start is not None and ram_start <= line_idx < ram_start + 5:
                        color = (255, 200, 200)
                        
                    elif line_idx in {objects_start, size_dist_start, storage_start}:
                        color = (255, 255, 255)
                        
                    elif (objects_start is not None and size_dist_start is not None
                        and objects_start + 1 <= line_idx < size_dist_start):
                        color = (255, 200, 150)
                        
                    elif (size_dist_start is not None and storage_start is not None
                        and size_dist_start + 1 <= line_idx < storage_start):
                        color = (150, 255, 150)
                        
                    elif storage_start is not None and storage_start + 1 <= line_idx < len(self.memory_info):
                        color = (150, 200, 255)

                    text_surf = self.font.render(text, True, color)
                    panel.blit(text_surf, (10, 10 + i * 18))

        elif self.menu_state == "size_group":
            group_surfaces = self.get_current_group_surfaces()
            panel_title = f"Images of size {self.selected_group} (ESC or Right Click to go back)"
            title_surf = self.font.render(panel_title, True, (255, 255, 255))
            panel.blit(title_surf, (10, 10))

            y_offset = 40
            thumb_size = 64
            margin = 5
            thumbs_per_row = self.thumbs_per_row()

            start_row = self.scroll_offsets[self.menu_state]
            visible_rows = self.visible_rows()

            for row in range(visible_rows):
                for col in range(thumbs_per_row):
                    idx = (start_row + row) * thumbs_per_row + col
                    if idx >= len(group_surfaces):
                        break
                        
                    surf = group_surfaces[idx]
                    x = 10 + col * (thumb_size + margin)
                    y = y_offset + row * (thumb_size + margin)

                    if surf not in self.preview_cache:
                        try:
                            self.preview_cache[surf] = pg.transform.scale(surf, (thumb_size, thumb_size))
                            
                        except Exception:
                            self.preview_cache[surf] = pg.Surface((thumb_size, thumb_size))
                            self.preview_cache[surf].fill((100, 0, 0))

                    panel.blit(self.preview_cache[surf], (x, y))
                    pg.draw.rect(panel, (100, 255, 100), (x, y, thumb_size, thumb_size), 1)

        elif self.menu_state == "storage_location":
            surfaces = self.get_current_storage_surfaces()
            panel_title = f"Storage Location: {self.selected_storage} (ESC or Right Click to go back)"
            title_surf = self.font.render(panel_title, True, (255, 255, 255))
            panel.blit(title_surf, (10, 10))

            start_line = self.scroll_offsets[self.menu_state]
            for i in range(self.visible_lines()):
                idx = start_line + i
                if idx >= len(surfaces):
                    break
                surf = surfaces[idx]
                info_text = f"Surface {idx} size: {surf.get_width()}x{surf.get_height()}"
                text_surf = self.font.render(info_text, True, (200, 200, 255))
                panel.blit(text_surf, (10, 30 + i * 18))

        elif self.menu_state == "object_info":
            info = self.get_object_info()
            panel_title = f"{self.selected_object} Info (ESC or Right Click to go back)"
            title_surf = self.font.render(panel_title, True, (255, 255, 255))
            panel.blit(title_surf, (10, 10))

            start_line = self.scroll_offsets[self.menu_state]
            for i in range(self.visible_lines()):
                idx = start_line + i
                if idx >= len(info):
                    break
                
                text_surf = self.font.render(info[idx], True, (200, 255, 200))
                panel.blit(text_surf, (10, 30 + i * 18))

        if max_scroll > 0:
            pg.draw.rect(panel, (100, 100, 100), (scrollbar_x, 0, 8, panel_height))
            pg.draw.rect(panel, (200, 200, 200), (scrollbar_x, scrollbar_y, 8, scrollbar_height))

        screen.blit(panel, (panel_x, panel_y))