import os
import sys
import json
import pygame
import pygame_gui
from pygame.locals import *
from typing import List, Dict, Optional

class GameObject:
    def __init__(self, name: str):
        self.name = name
        self.components = []
        self.transform = {
            "position": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0]
        }
        self.children = []
        self.parent = None

    def add_component(self, component):
        self.components.append(component)
        component.game_object = self

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "transform": self.transform,
            "components": [comp.to_dict() for comp in self.components],
            "children": [child.to_dict() for child in self.children]
        }

    @classmethod
    def from_dict(cls, data: Dict):
        obj = cls(data["name"])
        obj.transform = data["transform"]
        # Load components and children here
        return obj

class Component:
    def __init__(self):
        self.game_object = None

    def to_dict(self) -> Dict:
        return {"type": self.__class__.__name__}

class MeshRenderer(Component):
    def __init__(self, mesh_path: Optional[str] = None):
        super().__init__()
        self.mesh_path = mesh_path
        self.texture_path = None
        self.visible = True

    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            "mesh_path": self.mesh_path,
            "texture_path": self.texture_path,
            "visible": self.visible
        })
        return data

class ScriptComponent(Component):
    def __init__(self, script_path: Optional[str] = None):
        super().__init__()
        self.script_path = script_path
        self.properties = {}

    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            "script_path": self.script_path,
            "properties": self.properties
        })
        return data

class Project:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        self.scenes = []
        self.current_scene = None
        self.assets = []

    def create_scene(self, name: str) -> Dict:
        scene = {"name": name, "objects": []}
        self.scenes.append(scene)
        if not self.current_scene:
            self.current_scene = scene
        return scene

    def save(self):
        project_data = {
            "name": self.name,
            "scenes": self.scenes,
            "current_scene": self.current_scene["name"] if self.current_scene else None
        }

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        with open(os.path.join(self.path, "project.json"), "w") as f:
            json.dump(project_data, f, indent=2)

    @classmethod
    def load(cls, path: str):
        with open(os.path.join(path, "project.json"), "r") as f:
            data = json.load(f)

        project = cls(data["name"], path)
        project.scenes = data["scenes"]

        if data["current_scene"]:
            for scene in project.scenes:
                if scene["name"] == data["current_scene"]:
                    project.current_scene = scene
                    break

        return project

class Editor:
    def __init__(self):
        pygame.init()
        self.screen_width, self.screen_height = 1280, 720
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Python Unity-like Editor")

        self.clock = pygame.time.Clock()
        self.running = True
        self.ui_manager = pygame_gui.UIManager((self.screen_width, self.screen_height))

        # Editor state
        self.current_project = None
        self.projects_path = os.path.expanduser("~/PythonUnityProjects")
        self.show_main_menu = True
        self.show_project_creation = False
        self.new_project_name = ""

        # Scene data
        self.scene_objects = []
        self.selected_object = None

        # UI elements
        self.create_ui_elements()

    def create_ui_elements(self):
        # Main menu elements
        self.new_project_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((self.screen_width//2 - 100, 200), (200, 40)),
            text="New Project",
            manager=self.ui_manager
        )

        self.load_project_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((self.screen_width//2 - 100, 260), (200, 40)),
            text="Load Project",
            manager=self.ui_manager
        )

        # Project creation dialog
        self.project_dialog = pygame_gui.windows.UIConfirmationDialog(
            rect=pygame.Rect((self.screen_width//2 - 200, self.screen_height//2 - 150), (400, 300)),
            manager=self.ui_manager,
            window_title="Create New Project",
            action_long_desc="Enter project details:",
            action_short_name="Create",
            blocking=True
        )
        self.project_dialog.hide()

        self.project_name_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((self.screen_width//2 - 150, self.screen_height//2 - 50), (300, 30)),
            manager=self.ui_manager
        )
        self.project_name_input.hide()

        # Editor UI elements
        self.hierarchy_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect((0, 30), (250, self.screen_height - 30)),
            manager=self.ui_manager,
            starting_layer_height=1
        )

        self.inspector_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect((self.screen_width - 300, 30), (300, self.screen_height - 30)),
            manager=self.ui_manager,
            starting_layer_height=1
        )

        self.scene_view = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect((250, 30), (self.screen_width - 550, self.screen_height - 30)),
            manager=self.ui_manager,
            starting_layer_height=1
        )

        # Hide editor UI initially
        self.hierarchy_panel.hide()
        self.inspector_panel.hide()
        self.scene_view.hide()

    def run(self):
        while self.running:
            time_delta = self.clock.tick(60)/1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                self.ui_manager.process_events(event)

                if event.type == pygame.USEREVENT:
                    if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == self.new_project_button:
                            self.show_project_creation = True
                            self.project_dialog.show()
                            self.project_name_input.show()
                        elif event.ui_element == self.load_project_button:
                            self.load_project_dialog()

                    elif event.user_type == pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED:
                        if event.ui_element == self.project_dialog:
                            if self.project_name_input.get_text():
                                self.create_project(self.project_name_input.get_text())
                                self.show_main_menu = False
                                self.project_dialog.hide()
                                self.project_name_input.hide()
                                self.new_project_button.hide()
                                self.load_project_button.hide()
                                self.hierarchy_panel.show()
                                self.inspector_panel.show()
                                self.scene_view.show()

            self.ui_manager.update(time_delta)
            self.screen.fill((50, 50, 50))

            if self.show_main_menu:
                self.draw_main_menu()
            else:
                self.draw_editor()

            self.ui_manager.draw_ui(self.screen)
            pygame.display.update()

    def draw_main_menu(self):
        # Draw background or title
        title_font = pygame.font.SysFont('Arial', 40)
        title_text = title_font.render("Python Unity-like Editor", True, (255, 255, 255))
        self.screen.blit(title_text, (self.screen_width//2 - title_text.get_width()//2, 100))

    def draw_editor(self):
        # Draw scene view background
        scene_surface = pygame.Surface((self.scene_view.rect.width, self.scene_view.rect.height))
        scene_surface.fill((30, 30, 30))
        self.screen.blit(scene_surface, (self.scene_view.rect.x, self.scene_view.rect.y))

        # Draw hierarchy panel background
        hierarchy_surface = pygame.Surface((self.hierarchy_panel.rect.width, self.hierarchy_panel.rect.height))
        hierarchy_surface.fill((40, 40, 40))
        self.screen.blit(hierarchy_surface, (self.hierarchy_panel.rect.x, self.hierarchy_panel.rect.y))

        # Draw inspector panel background
        inspector_surface = pygame.Surface((self.inspector_panel.rect.width, self.inspector_panel.rect.height))
        inspector_surface.fill((40, 40, 40))
        self.screen.blit(inspector_surface, (self.inspector_panel.rect.x, self.inspector_panel.rect.y))

        # Draw scene objects in hierarchy
        font = pygame.font.SysFont('Arial', 14)
        y_offset = 10
        for obj in self.scene_objects:
            obj_text = font.render(obj.name, True, (255, 255, 255))
            self.screen.blit(obj_text, (self.hierarchy_panel.rect.x + 10, self.hierarchy_panel.rect.y + y_offset))
            y_offset += 25

        # Draw selected object properties in inspector
        if self.selected_object:
            font = pygame.font.SysFont('Arial', 16)
            name_text = font.render(self.selected_object.name, True, (255, 255, 255))
            self.screen.blit(name_text, (self.inspector_panel.rect.x + 10, self.inspector_panel.rect.y + 10))

            # Draw transform properties
            transform_text = font.render("Transform", True, (200, 200, 200))
            self.screen.blit(transform_text, (self.inspector_panel.rect.x + 10, self.inspector_panel.rect.y + 40))

            pos_text = font.render(f"Position: {self.selected_object.transform['position']}", True, (200, 200, 200))
            self.screen.blit(pos_text, (self.inspector_panel.rect.x + 20, self.inspector_panel.rect.y + 70))

            rot_text = font.render(f"Rotation: {self.selected_object.transform['rotation']}", True, (200, 200, 200))
            self.screen.blit(rot_text, (self.inspector_panel.rect.x + 20, self.inspector_panel.rect.y + 100))

            scale_text = font.render(f"Scale: {self.selected_object.transform['scale']}", True, (200, 200, 200))
            self.screen.blit(scale_text, (self.inspector_panel.rect.x + 20, self.inspector_panel.rect.y + 130))

    def create_project(self, name: str):
        project_path = os.path.join(self.projects_path, name)
        if not os.path.exists(project_path):
            os.makedirs(project_path)
            os.makedirs(os.path.join(project_path, "Assets"))
            os.makedirs(os.path.join(project_path, "Assets/Models"))
            os.makedirs(os.path.join(project_path, "Assets/Scripts"))
            os.makedirs(os.path.join(project_path, "Assets/Textures"))

            self.current_project = Project(name, project_path)
            self.current_project.create_scene("SampleScene")
            self.current_project.save()

    def load_project_dialog(self):
        if os.path.exists(self.projects_path):
            projects = [d for d in os.listdir(self.projects_path) 
                       if os.path.isdir(os.path.join(self.projects_path, d))]
            if projects:
                self.current_project = Project.load(os.path.join(self.projects_path, projects[0]))
                self.show_main_menu = False
                self.new_project_button.hide()
                self.load_project_button.hide()
                self.hierarchy_panel.show()
                self.inspector_panel.show()
                self.scene_view.show()
                self.scene_objects = []

    def create_empty_object(self) -> GameObject:
        obj = GameObject(f"GameObject_{len(self.scene_objects) + 1}")
        self.scene_objects.append(obj)
        if not self.selected_object:
            self.selected_object = obj
        return obj

    def create_cube_object(self) -> GameObject:
        obj = self.create_empty_object()
        obj.name = "Cube"
        obj.add_component(MeshRenderer())
        return obj

if __name__ == "__main__":
    editor = Editor()
    editor.run()