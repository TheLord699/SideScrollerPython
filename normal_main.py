import os
import json
import moderngl
import numpy as np
import subprocess
import sys
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, 
                            QDockWidget, QTreeView, QListView, QTextEdit,
                            QFileSystemModel, QSplitter, QWidget, QVBoxLayout,
                            QLabel, QPushButton, QHBoxLayout, QListWidget, QListWidgetItem,
                            QTabWidget, QPlainTextEdit, QMenu, QMessageBox,
                            QInputDialog, QLineEdit, QComboBox, QDialog, QDialogButtonBox, QAction)
from PyQt5.QtCore import Qt, QDir, QModelIndex, QMimeData, QTimer, QSize, QPoint
from PyQt5.QtGui import QImage, QPixmap, QIcon, QTextCursor, QColor, QStandardItem
from PyQt5.QtGui import QStandardItemModel

# ---------------------------
# Core Engine Classes
# ---------------------------

@dataclass
class GameObject:
    name: str
    children: List['GameObject'] = field(default_factory=list)
    components: List['Component'] = field(default_factory=list)
    parent: Optional['GameObject'] = None
    transform: 'Transform' = None
    visible: bool = True
    selected: bool = False
    
    def __post_init__(self):
        self.transform = Transform(self)
        
    def add_child(self, child: 'GameObject'):
        child.parent = self
        self.children.append(child)
        
    def add_component(self, component: 'Component'):
        component.game_object = self
        self.components.append(component)
        
    def get_component(self, component_type: type) -> Optional['Component']:
        for comp in self.components:
            if isinstance(comp, component_type):
                return comp
        return None
    
    def update(self, delta_time: float):
        for component in self.components:
            component.update(delta_time)
        for child in self.children:
            child.update(delta_time)
            
    def render(self, ctx: moderngl.Context):
        if not self.visible:
            return
            
        for component in self.components:
            if hasattr(component, 'render'):
                component.render(ctx)
                
        for child in self.children:
            child.render(ctx)

@dataclass
class Transform:
    game_object: GameObject
    position: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    rotation: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    scale: np.ndarray = field(default_factory=lambda: np.array([1.0, 1.0, 1.0]))
    
    def model_matrix(self) -> np.ndarray:
        # Create model matrix from position, rotation, scale
        mat = np.eye(4)
        
        # Translation
        mat[0:3, 3] = self.position
        
        # Rotation (simplified - would use quaternions in real implementation)
        rx = np.eye(4)
        ry = np.eye(4)
        rz = np.eye(4)
        
        cos_x = np.cos(self.rotation[0])
        sin_x = np.sin(self.rotation[0])
        cos_y = np.cos(self.rotation[1])
        sin_y = np.sin(self.rotation[1])
        cos_z = np.cos(self.rotation[2])
        sin_z = np.sin(self.rotation[2])
        
        rx[1:3, 1:3] = np.array([[cos_x, -sin_x], [sin_x, cos_x]])
        ry[0::2, 0::2] = np.array([[cos_y, sin_y], [-sin_y, cos_y]])
        rz[0:2, 0:2] = np.array([[cos_z, -sin_z], [sin_z, cos_z]])
        
        rotation_matrix = rz @ ry @ rx
        mat = mat @ rotation_matrix
        
        # Scale
        scale_matrix = np.eye(4)
        np.fill_diagonal(scale_matrix[:3, :3], self.scale)
        mat = mat @ scale_matrix
        
        return mat

class Component:
    def __init__(self):
        self.game_object: Optional[GameObject] = None
        
    def update(self, delta_time: float):
        pass

class ScriptComponent(Component):
    def __init__(self, script_path: str = ""):
        super().__init__()
        self.script_path = script_path
        self.code = ""
        if script_path and os.path.exists(script_path):
            with open(script_path, 'r') as f:
                self.code = f.read()
        
    def update(self, delta_time: float):
        # In a real implementation, we'd execute the script here
        # For now, just a placeholder
        pass

class MeshRenderer(Component):
    BUILTIN_SHAPES = {
        'Cube': 'cube',
        'Sphere': 'sphere',
        'Plane': 'plane',
        'Capsule': 'capsule',
        'Cylinder': 'cylinder'
    }
    
    def __init__(self, mesh_path: str = ""):
        super().__init__()
        self.mesh_path = mesh_path
        self.shape_type = 'custom' if not mesh_path else mesh_path
        self.vao: Optional[moderngl.VertexArray] = None
        self.texture: Optional[moderngl.Texture] = None
        self.program: Optional[moderngl.Program] = None
        
    def load(self, ctx: moderngl.Context):
        if not self.mesh_path and self.shape_type not in self.BUILTIN_SHAPES.values():
            return
            
        self.program = ctx.program(
            vertex_shader='''
                #version 330
                in vec3 in_position;
                in vec3 in_normal;
                in vec2 in_uv;
                out vec3 v_normal;
                out vec2 v_uv;
                uniform mat4 model;
                uniform mat4 view;
                uniform mat4 projection;
                
                void main() {
                    gl_Position = projection * view * model * vec4(in_position, 1.0);
                    v_normal = mat3(transpose(inverse(model))) * in_normal;
                    v_uv = in_uv;
                }
            ''',
            fragment_shader='''
                #version 330
                in vec3 v_normal;
                in vec2 v_uv;
                out vec4 f_color;
                uniform sampler2D tex;
                uniform vec3 light_dir;
                
                void main() {
                    vec3 light_color = vec3(1.0, 1.0, 1.0);
                    float ambient = 0.2;
                    float diff = max(dot(normalize(v_normal), normalize(-light_dir)), 0.0);
                    vec4 tex_color = texture(tex, v_uv);
                    f_color = tex_color * vec4(light_color * (diff + ambient), 1.0);
                }
            '''
        )
        
        vertices, indices = self.generate_mesh_data()
        
        vbo = ctx.buffer(vertices.astype('f4'))
        ibo = ctx.buffer(indices.astype('i4'))
        
        self.vao = ctx.vertex_array(
            self.program,
            [
                (vbo, '3f 3f 2f', 'in_position', 'in_normal', 'in_uv')
            ],
            index_buffer=ibo
        )
        
        # Create a simple checkerboard texture
        tex_data = np.zeros((64, 64, 3), dtype='u1')
        tex_data[::8, ::8] = [255, 255, 255]
        self.texture = ctx.texture((64, 64), 3, tex_data.tobytes())
        
    def generate_mesh_data(self) -> Tuple[np.ndarray, np.ndarray]:
        if self.shape_type == 'cube':
            return self._generate_cube()
        elif self.shape_type == 'plane':
            return self._generate_plane()
        elif self.shape_type == 'sphere':
            return self._generate_sphere(16, 16)
        elif self.shape_type == 'capsule':
            return self._generate_capsule(16, 16, 0.5)
        elif self.shape_type == 'cylinder':
            return self._generate_cylinder(16)
        else:
            # Default to cube if shape not recognized
            return self._generate_cube()
    
    def _generate_cube(self) -> Tuple[np.ndarray, np.ndarray]:
        vertices = np.array([
            # Positions          # Normals           # UVs
            # Front face
            -0.5, -0.5,  0.5,   0.0,  0.0,  1.0,   0.0, 0.0,
             0.5, -0.5,  0.5,   0.0,  0.0,  1.0,   1.0, 0.0,
             0.5,  0.5,  0.5,   0.0,  0.0,  1.0,   1.0, 1.0,
            -0.5,  0.5,  0.5,   0.0,  0.0,  1.0,   0.0, 1.0,
            
            # Back face
            -0.5, -0.5, -0.5,   0.0,  0.0, -1.0,   1.0, 0.0,
             0.5, -0.5, -0.5,   0.0,  0.0, -1.0,   0.0, 0.0,
             0.5,  0.5, -0.5,   0.0,  0.0, -1.0,   0.0, 1.0,
            -0.5,  0.5, -0.5,   0.0,  0.0, -1.0,   1.0, 1.0,
            
            # Top face
            -0.5,  0.5, -0.5,   0.0,  1.0,  0.0,   0.0, 1.0,
             0.5,  0.5, -0.5,   0.0,  1.0,  0.0,   1.0, 1.0,
             0.5,  0.5,  0.5,   0.0,  1.0,  0.0,   1.0, 0.0,
            -0.5,  0.5,  0.5,   0.0,  1.0,  0.0,   0.0, 0.0,
            
            # Bottom face
            -0.5, -0.5, -0.5,   0.0, -1.0,  0.0,   1.0, 1.0,
             0.5, -0.5, -0.5,   0.0, -1.0,  0.0,   0.0, 1.0,
             0.5, -0.5,  0.5,   0.0, -1.0,  0.0,   0.0, 0.0,
            -0.5, -0.5,  0.5,   0.0, -1.0,  0.0,   1.0, 0.0,
            
            # Right face
             0.5, -0.5, -0.5,   1.0,  0.0,  0.0,   1.0, 0.0,
             0.5, -0.5,  0.5,   1.0,  0.0,  0.0,   0.0, 0.0,
             0.5,  0.5,  0.5,   1.0,  0.0,  0.0,   0.0, 1.0,
             0.5,  0.5, -0.5,   1.0,  0.0,  0.0,   1.0, 1.0,
            
            # Left face
            -0.5, -0.5, -0.5,  -1.0,  0.0,  0.0,   0.0, 0.0,
            -0.5, -0.5,  0.5,  -1.0,  0.0,  0.0,   1.0, 0.0,
            -0.5,  0.5,  0.5,  -1.0,  0.0,  0.0,   1.0, 1.0,
            -0.5,  0.5, -0.5,  -1.0,  0.0,  0.0,   0.0, 1.0,
        ], dtype='f4')
        
        indices = np.array([
            0, 1, 2, 0, 2, 3,    # Front
            4, 5, 6, 4, 6, 7,    # Back
            8, 9, 10, 8, 10, 11,  # Top
            12, 13, 14, 12, 14, 15, # Bottom
            16, 17, 18, 16, 18, 19, # Right
            20, 21, 22, 20, 22, 23  # Left
        ], dtype='i4')
        
        return vertices, indices
    
    def _generate_plane(self) -> Tuple[np.ndarray, np.ndarray]:
        vertices = np.array([
            # Positions          # Normals           # UVs
            -0.5, 0.0, -0.5,   0.0, 1.0, 0.0,    0.0, 0.0,
             0.5, 0.0, -0.5,   0.0, 1.0, 0.0,    1.0, 0.0,
             0.5, 0.0,  0.5,   0.0, 1.0, 0.0,    1.0, 1.0,
            -0.5, 0.0,  0.5,   0.0, 1.0, 0.0,    0.0, 1.0,
        ], dtype='f4')
        
        indices = np.array([0, 1, 2, 0, 2, 3], dtype='i4')
        return vertices, indices
    
    def _generate_sphere(self, segments: int, rings: int) -> Tuple[np.ndarray, np.ndarray]:
        vertices = []
        indices = []
        
        for i in range(rings + 1):
            v = i / rings
            phi = v * np.pi
            
            for j in range(segments + 1):
                u = j / segments
                theta = u * 2 * np.pi
                
                x = np.cos(theta) * np.sin(phi)
                y = np.cos(phi)
                z = np.sin(theta) * np.sin(phi)
                
                vertices.extend([x*0.5, y*0.5, z*0.5, x, y, z, u, 1-v])
                
                if i < rings and j < segments:
                    a = i * (segments + 1) + j
                    b = a + segments + 1
                    indices.extend([a, b, a+1, b, b+1, a+1])
        
        return np.array(vertices, dtype='f4'), np.array(indices, dtype='i4')
    
    def _generate_capsule(self, segments: int, rings: int, half_height: float) -> Tuple[np.ndarray, np.ndarray]:
        vertices = []
        indices = []
        
        # Cylinder part
        for i in range(2):
            y = half_height if i == 0 else -half_height
            
            for j in range(segments + 1):
                u = j / segments
                theta = u * 2 * np.pi
                
                x = np.cos(theta)
                z = np.sin(theta)
                
                vertices.extend([x*0.5, y, z*0.5, x, 0, z, u, i])
                
                if i < 1 and j < segments:
                    a = i * (segments + 1) + j
                    b = a + segments + 1
                    indices.extend([a, b, a+1, b, b+1, a+1])
        
        # Hemisphere caps
        for cap in [1, -1]:
            base_idx = len(vertices) // 8
            y_offset = half_height if cap == 1 else -half_height
            
            for i in range(rings // 2 + 1):
                v = i / (rings // 2)
                phi = v * np.pi / 2
                
                for j in range(segments + 1):
                    u = j / segments
                    theta = u * 2 * np.pi
                    
                    x = np.cos(theta) * np.sin(phi)
                    y = np.cos(phi) * cap
                    z = np.sin(theta) * np.sin(phi)
                    
                    vertices.extend([
                        x*0.5, y*0.5 + y_offset, z*0.5, 
                        x, y, z, 
                        u, 1-v if cap == 1 else v
                    ])
                    
                    if i < rings // 2 and j < segments:
                        a = base_idx + i * (segments + 1) + j
                        b = a + segments + 1
                        indices.extend([a, b, a+1, b, b+1, a+1])
        
        return np.array(vertices, dtype='f4'), np.array(indices, dtype='i4')
    
    def _generate_cylinder(self, segments: int) -> Tuple[np.ndarray, np.ndarray]:
        vertices = []
        indices = []
        
        # Sides
        for i in range(2):
            y = 0.5 if i == 0 else -0.5
            
            for j in range(segments + 1):
                u = j / segments
                theta = u * 2 * np.pi
                
                x = np.cos(theta)
                z = np.sin(theta)
                
                vertices.extend([x*0.5, y, z*0.5, x, 0, z, u, i])
                
                if i < 1 and j < segments:
                    a = i * (segments + 1) + j
                    b = a + segments + 1
                    indices.extend([a, b, a+1, b, b+1, a+1])
        
        # Caps
        for cap in [1, -1]:
            base_idx = len(vertices) // 8
            y = 0.5 * cap
            
            vertices.extend([0.0, y, 0.0, 0.0, cap, 0.0, 0.5, 0.5])
            
            for j in range(segments + 1):
                theta = j / segments * 2 * np.pi
                x = np.cos(theta)
                z = np.sin(theta)
                
                vertices.extend([x*0.5, y, z*0.5, 0.0, cap, 0.0, x*0.5+0.5, z*0.5+0.5])
                
                if j < segments:
                    indices.extend([base_idx, base_idx + j + 1, base_idx + j + 2])
        
        return np.array(vertices, dtype='f4'), np.array(indices, dtype='i4')
    
    def render(self, ctx: moderngl.Context, view_matrix: np.ndarray, projection_matrix: np.ndarray):
        if not self.vao:
            return
            
        self.texture.use()
        self.program['model'].write(self.game_object.transform.model_matrix().astype('f4'))
        self.program['view'].write(view_matrix.astype('f4'))
        self.program['projection'].write(projection_matrix.astype('f4'))
        self.program['light_dir'].value = (0.5, -1.0, 0.5)
        self.vao.render()

class Camera(Component):
    def __init__(self, fov: float = 60.0, near: float = 0.1, far: float = 100.0):
        super().__init__()
        self.fov = fov
        self.near = near
        self.far = far
        self.aspect_ratio = 1.0
        
    def view_matrix(self) -> np.ndarray:
        if not self.game_object:
            return np.eye(4)
            
        # Camera looks along negative Z in world space
        pos = self.game_object.transform.position
        target = pos + np.array([0, 0, -1])  # Simple forward vector
        up = np.array([0, 1, 0])
        
        # Create view matrix
        f = (target - pos) / np.linalg.norm(target - pos)
        s = np.cross(f, up) / np.linalg.norm(np.cross(f, up))
        u = np.cross(s, f)
        
        view = np.eye(4)
        view[0:3, 0] = s
        view[0:3, 1] = u
        view[0:3, 2] = -f
        view[0:3, 3] = -np.dot(s, pos), -np.dot(u, pos), np.dot(f, pos)
        
        return view
    
    def projection_matrix(self) -> np.ndarray:
        fov_rad = np.radians(self.fov)
        f = 1.0 / np.tan(fov_rad / 2.0)
        
        proj = np.zeros((4, 4))
        proj[0, 0] = f / self.aspect_ratio
        proj[1, 1] = f
        proj[2, 2] = (self.far + self.near) / (self.near - self.far)
        proj[2, 3] = (2 * self.far * self.near) / (self.near - self.far)
        proj[3, 2] = -1.0
        
        return proj

class AudioSource(Component):
    def __init__(self, audio_path: str = "", loop: bool = False):
        super().__init__()
        self.audio_path = audio_path
        self.loop = loop
        self.playing = False
        
    def play(self):
        self.playing = True
        # In a real implementation, would use a sound library like Pygame or OpenAL
        
    def stop(self):
        self.playing = False

# ---------------------------
# Project Management
# ---------------------------

class Project:
    def __init__(self, path: str):
        self.path = path
        self.name = os.path.basename(path)
        self.scenes: List[Scene] = []
        self.assets: List[str] = []
        self.current_scene: Optional[Scene] = None
        
        # Create project structure if new
        if not os.path.exists(path):
            os.makedirs(path)
            os.makedirs(os.path.join(path, 'Assets'))
            os.makedirs(os.path.join(path, 'Scenes'))
            os.makedirs(os.path.join(path, 'Scripts'))
            os.makedirs(os.path.join(path, 'Audio'))
            
            # Create default scene
            default_scene = Scene("Main")
            self.scenes.append(default_scene)
            self.current_scene = default_scene
            
            # Create default camera
            camera_obj = GameObject("Main Camera")
            camera_obj.add_component(Camera())
            default_scene.add_object(camera_obj)
            default_scene.camera = camera_obj
            
            self.save()
            
    def save(self):
        project_data = {
            'name': self.name,
            'scenes': [scene.name for scene in self.scenes],
            'current_scene': self.scenes.index(self.current_scene) if self.current_scene else 0
        }
        
        with open(os.path.join(self.path, 'project.json'), 'w') as f:
            json.dump(project_data, f, indent=2)
            
    def load_assets(self):
        self.assets = []
        assets_dir = os.path.join(self.path, 'Assets')
        if os.path.exists(assets_dir):
            for root, _, files in os.walk(assets_dir):
                for file in files:
                    self.assets.append(os.path.join(root, file))
                    
    def create_scene(self, name: str) -> 'Scene':
        scene = Scene(name)
        self.scenes.append(scene)
        
        # Create default camera for new scenes
        camera_obj = GameObject("Camera")
        camera_obj.add_component(Camera())
        scene.add_object(camera_obj)
        scene.camera = camera_obj
        
        return scene
        
    def save_scene(self, scene: 'Scene'):
        scene_path = os.path.join(self.path, 'Scenes', f'{scene.name}.scene')
        with open(scene_path, 'w') as f:
            json.dump(scene.serialize(), f, indent=2)
            
    def load_scene(self, name: str) -> 'Scene':
        scene_path = os.path.join(self.path, 'Scenes', f'{name}.scene')
        if os.path.exists(scene_path):
            with open(scene_path, 'r') as f:
                data = json.load(f)
                scene = Scene.deserialize(data)
                self.current_scene = scene
                return scene
        return self.create_scene(name)

class Scene:
    def __init__(self, name: str):
        self.name = name
        self.root_objects: List[GameObject] = []
        self.camera: Optional[GameObject] = None
        
    def add_object(self, game_object: GameObject):
        self.root_objects.append(game_object)
        
    def find_object(self, name: str) -> Optional[GameObject]:
        for obj in self.root_objects:
            if obj.name == name:
                return obj
            for child in obj.children:
                found = self._find_object_recursive(child, name)
                if found:
                    return found
        return None
        
    def _find_object_recursive(self, obj: GameObject, name: str) -> Optional[GameObject]:
        if obj.name == name:
            return obj
        for child in obj.children:
            found = self._find_object_recursive(child, name)
            if found:
                return found
        return None
        
    def serialize(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'objects': [self.serialize_object(obj) for obj in self.root_objects],
            'camera': self.camera.name if self.camera else None
        }
        
    def serialize_object(self, obj: GameObject) -> Dict[str, Any]:
        components = []
        
        for comp in obj.components:
            if isinstance(comp, ScriptComponent):
                components.append({
                    'type': 'Script',
                    'path': comp.script_path
                })
            elif isinstance(comp, MeshRenderer):
                components.append({
                    'type': 'MeshRenderer',
                    'mesh_path': comp.mesh_path,
                    'shape_type': comp.shape_type
                })
            elif isinstance(comp, Camera):
                components.append({
                    'type': 'Camera',
                    'fov': comp.fov,
                    'near': comp.near,
                    'far': comp.far
                })
            elif isinstance(comp, AudioSource):
                components.append({
                    'type': 'AudioSource',
                    'audio_path': comp.audio_path,
                    'loop': comp.loop
                })
                
        return {
            'name': obj.name,
            'position': obj.transform.position.tolist(),
            'rotation': obj.transform.rotation.tolist(),
            'scale': obj.transform.scale.tolist(),
            'visible': obj.visible,
            'components': components,
            'children': [self.serialize_object(child) for child in obj.children]
        }
        
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Scene':
        scene = cls(data['name'])
        for obj_data in data.get('objects', []):
            scene.root_objects.append(cls.deserialize_object(obj_data))
            
        if 'camera' in data and data['camera']:
            scene.camera = scene.find_object(data['camera'])
            
        return scene
        
    @classmethod
    def deserialize_object(cls, data: Dict[str, Any]) -> GameObject:
        obj = GameObject(data['name'])
        obj.transform.position = np.array(data.get('position', [0, 0, 0]))
        obj.transform.rotation = np.array(data.get('rotation', [0, 0, 0]))
        obj.transform.scale = np.array(data.get('scale', [1, 1, 1]))
        obj.visible = data.get('visible', True)
        
        for comp_data in data.get('components', []):
            if comp_data['type'] == 'Script':
                obj.add_component(ScriptComponent(comp_data['path']))
            elif comp_data['type'] == 'MeshRenderer':
                renderer = MeshRenderer(comp_data.get('mesh_path', ''))
                renderer.shape_type = comp_data.get('shape_type', 'custom')
                obj.add_component(renderer)
            elif comp_data['type'] == 'Camera':
                camera = Camera(
                    comp_data.get('fov', 60.0),
                    comp_data.get('near', 0.1),
                    comp_data.get('far', 100.0)
                )
                obj.add_component(camera)
            elif comp_data['type'] == 'AudioSource':
                audio = AudioSource(
                    comp_data.get('audio_path', ''),
                    comp_data.get('loop', False)
                )
                obj.add_component(audio)
                
        for child_data in data.get('children', []):
            obj.add_child(cls.deserialize_object(child_data))
            
        return obj

# ---------------------------
# Editor UI
# ---------------------------

class ConsoleWidget(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: Consolas, monospace;
                font-size: 10pt;
            }
        """)
        
    def write(self, text: str):
        self.appendPlainText(text)
        
    def flush(self):
        pass

class GameViewWidget(QWidget):
    def __init__(self, ctx, editor):
        super().__init__()
        self.ctx = ctx
        self.editor = editor
        self.setMinimumSize(400, 300)
        self.setAcceptDrops(True)
        
        # Camera matrices
        self.view_matrix = np.eye(4)
        self.projection_matrix = np.eye(4)
        
        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(16)  # ~60 FPS
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            # Handle dropped files (would be processed by editor)
            print(f"Dropped file: {path}")
            
    def paintEvent(self, event):
      if not hasattr(self, 'ctx'):
          return

      self.ctx.clear(0.1, 0.1, 0.1)

      editor = self.editor  # Use direct reference

      if editor.current_scene and editor.current_scene.camera:
          camera = editor.current_scene.camera.get_component(Camera)
          if camera:
              camera.aspect_ratio = self.width() / max(1, self.height())
              self.view_matrix = camera.view_matrix()
              self.projection_matrix = camera.projection_matrix()
              for obj in editor.current_scene.root_objects:
                  obj.render(self.ctx, self.view_matrix, self.projection_matrix)

class HierarchyWidget(QTreeView):
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.setHeaderHidden(True)
        self.setSelectionMode(QTreeView.SingleSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.doubleClicked.connect(self.on_item_double_clicked)
        # Add this line to set the model:
        self.setModel(QStandardItemModel())
        
    def show_context_menu(self, position):
        index = self.indexAt(position)
        menu = QMenu()
        
        if index.isValid():
            # Object context menu
            menu.addAction("Rename", lambda: self.rename_object(index))
            menu.addAction("Delete", lambda: self.delete_object(index))
            menu.addSeparator()
            
            # Add component submenu
            component_menu = menu.addMenu("Add Component")
            component_menu.addAction("Script", lambda: self.add_script_component(index))
            component_menu.addAction("Mesh Renderer", lambda: self.add_mesh_renderer(index))
            component_menu.addAction("Audio Source", lambda: self.add_audio_source(index))
            
            # Set as camera
            menu.addAction("Set as Camera", lambda: self.set_as_camera(index))
        else:
            # Empty space context menu
            menu.addAction("Create Empty", self.create_empty_object)
            
            # Create 3D object submenu
            create_menu = menu.addMenu("Create 3D Object")
            create_menu.addAction("Cube", lambda: self.create_3d_object('cube'))
            create_menu.addAction("Sphere", lambda: self.create_3d_object('sphere'))
            create_menu.addAction("Plane", lambda: self.create_3d_object('plane'))
            create_menu.addAction("Capsule", lambda: self.create_3d_object('capsule'))
            create_menu.addAction("Cylinder", lambda: self.create_3d_object('cylinder'))
            
        menu.exec_(self.viewport().mapToGlobal(position))
        
    def rename_object(self, index):
        model = self.model()
        old_name = model.data(index, Qt.DisplayRole)
        new_name, ok = QInputDialog.getText(self, "Rename Object", "New name:", QLineEdit.Normal, old_name)
        if ok and new_name:
            model.setData(index, new_name, Qt.DisplayRole)
            
    def delete_object(self, index):
        model = self.model()
        name = model.data(index, Qt.DisplayRole)
        reply = QMessageBox.question(self, "Delete Object", f"Delete {name}?", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Get the object and remove it from the scene
            obj = model.data(index, Qt.UserRole)
            if obj and self.editor.current_scene:
                if obj in self.editor.current_scene.root_objects:
                    self.editor.current_scene.root_objects.remove(obj)
                elif obj.parent:
                    obj.parent.children.remove(obj)
                self.editor.update_hierarchy()
                
    def add_script_component(self, index):
        model = self.model()
        obj = model.data(index, Qt.UserRole)
        if obj:
            # Open file dialog to select script
            path, _ = QFileDialog.getOpenFileName(self, "Select Script", 
                                                os.path.join(self.editor.project.path, 'Scripts'), 
                                                "Python Files (*.py)")
            if path:
                # Make path relative to project
                rel_path = os.path.relpath(path, self.editor.project.path)
                obj.add_component(ScriptComponent(rel_path))
                self.editor.update_inspector()
                
    def add_mesh_renderer(self, index):
        model = self.model()
        obj = model.data(index, Qt.UserRole)
        if obj:
            # Check if object already has a mesh renderer
            if obj.get_component(MeshRenderer):
                QMessageBox.information(self, "Info", "Object already has a Mesh Renderer")
                return
                
            # Open file dialog to select mesh or choose built-in shape
            dialog = QDialog(self)
            dialog.setWindowTitle("Add Mesh Renderer")
            layout = QVBoxLayout()
            
            combo = QComboBox()
            combo.addItem("Select a built-in shape...")
            combo.addItems(MeshRenderer.BUILTIN_SHAPES.keys())
            combo.addItem("Or load from file...")
            layout.addWidget(combo)
            
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            dialog.setLayout(layout)
            
            if dialog.exec_() == QDialog.Accepted:
                if combo.currentIndex() == 0:
                    return
                elif combo.currentIndex() == combo.count() - 1:
                    # Load from file
                    path, _ = QFileDialog.getOpenFileName(self, "Select Mesh File", 
                                                        os.path.join(self.editor.project.path, 'Assets'), 
                                                        "All Files (*)")
                    if path:
                        rel_path = os.path.relpath(path, self.editor.project.path)
                        renderer = MeshRenderer(rel_path)
                        obj.add_component(renderer)
                else:
                    # Built-in shape
                    shape_name = combo.currentText()
                    renderer = MeshRenderer()
                    renderer.shape_type = MeshRenderer.BUILTIN_SHAPES[shape_name]
                    obj.add_component(renderer)
                    
                self.editor.update_inspector()
                
    def add_audio_source(self, index):
        model = self.model()
        obj = model.data(index, Qt.UserRole)
        if obj:
            # Open file dialog to select audio file
            path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", 
                                                os.path.join(self.editor.project.path, 'Audio'), 
                                                "Audio Files (*.wav *.mp3 *.ogg)")
            if path:
                rel_path = os.path.relpath(path, self.editor.project.path)
                loop, ok = QInputDialog.getItem(self, "Audio Settings", "Loop:", 
                                              ["Yes", "No"], 0, False)
                if ok:
                    obj.add_component(AudioSource(rel_path, loop == "Yes"))
                    self.editor.update_inspector()
                    
    def set_as_camera(self, index):
        model = self.model()
        obj = model.data(index, Qt.UserRole)
        if obj and self.editor.current_scene:
            # Ensure the object has a camera component
            if not obj.get_component(Camera):
                obj.add_component(Camera())
                
            self.editor.current_scene.camera = obj
            self.editor.update_inspector()
            
    def create_empty_object(self):
        if self.editor.current_scene:
            name, ok = QInputDialog.getText(self, "Create Empty", "Object name:", 
                                          QLineEdit.Normal, "GameObject")
            if ok and name:
                obj = GameObject(name)
                self.editor.current_scene.add_object(obj)
                self.editor.update_hierarchy()
                
    def create_3d_object(self, shape_type: str):
        if self.editor.current_scene:
            name_map = {
                'cube': 'Cube',
                'sphere': 'Sphere',
                'plane': 'Plane',
                'capsule': 'Capsule',
                'cylinder': 'Cylinder'
            }
            name = name_map.get(shape_type, '3D Object')
            obj = GameObject(name)
            renderer = MeshRenderer()
            renderer.shape_type = shape_type
            obj.add_component(renderer)
            self.editor.current_scene.add_object(obj)
            self.editor.update_hierarchy()
            
    def on_item_double_clicked(self, index):
        model = self.model()
        obj = model.data(index, Qt.UserRole)
        if obj:
            self.editor.select_object(obj)

class InspectorWidget(QWidget):
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.current_object: Optional[GameObject] = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Name and basic info
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("No object selected")
        self.name_edit.editingFinished.connect(self.on_name_changed)
        layout.addWidget(self.name_edit)
        
        # Active checkbox
        self.active_checkbox = QPushButton("Visible")
        self.active_checkbox.setCheckable(True)
        self.active_checkbox.setChecked(True)
        self.active_checkbox.clicked.connect(self.on_active_changed)
        layout.addWidget(self.active_checkbox)
        
        # Transform section
        transform_group = QWidget()
        transform_layout = QVBoxLayout()
        transform_group.setLayout(transform_layout)
        
        transform_layout.addWidget(QLabel("Transform:"))
        
        # Position
        pos_group = QWidget()
        pos_layout = QHBoxLayout()
        pos_group.setLayout(pos_layout)
        pos_layout.addWidget(QLabel("Position:"))
        
        self.pos_x = QLineEdit("0.0")
        self.pos_y = QLineEdit("0.0")
        self.pos_z = QLineEdit("0.0")
        
        for edit in [self.pos_x, self.pos_y, self.pos_z]:
            edit.setMaximumWidth(60)
            edit.editingFinished.connect(self.on_transform_changed)
            pos_layout.addWidget(edit)
            
        transform_layout.addWidget(pos_group)
        
        # Rotation
        rot_group = QWidget()
        rot_layout = QHBoxLayout()
        rot_group.setLayout(rot_layout)
        rot_layout.addWidget(QLabel("Rotation:"))
        
        self.rot_x = QLineEdit("0.0")
        self.rot_y = QLineEdit("0.0")
        self.rot_z = QLineEdit("0.0")
        
        for edit in [self.rot_x, self.rot_y, self.rot_z]:
            edit.setMaximumWidth(60)
            edit.editingFinished.connect(self.on_transform_changed)
            rot_layout.addWidget(edit)
            
        transform_layout.addWidget(rot_group)
        
        # Scale
        scale_group = QWidget()
        scale_layout = QHBoxLayout()
        scale_group.setLayout(scale_layout)
        scale_layout.addWidget(QLabel("Scale:"))
        
        self.scale_x = QLineEdit("1.0")
        self.scale_y = QLineEdit("1.0")
        self.scale_z = QLineEdit("1.0")
        
        for edit in [self.scale_x, self.scale_y, self.scale_z]:
            edit.setMaximumWidth(60)
            edit.editingFinished.connect(self.on_transform_changed)
            scale_layout.addWidget(edit)
            
        transform_layout.addWidget(scale_group)
        
        layout.addWidget(transform_group)
        
        # Components list
        self.components_list = QListWidget()
        self.components_list.itemDoubleClicked.connect(self.on_component_double_clicked)
        layout.addWidget(QLabel("Components:"))
        layout.addWidget(self.components_list)
        
        # Add component button
        self.add_component_btn = QPushButton("Add Component")
        self.add_component_btn.clicked.connect(self.show_add_component_menu)
        layout.addWidget(self.add_component_btn)
        
        layout.addStretch()
        
    def show_add_component_menu(self):
        if not self.current_object:
            return
            
        menu = QMenu(self)
        
        # Standard components
        menu.addAction("Script", lambda: self.add_component(ScriptComponent))
        menu.addAction("Mesh Renderer", lambda: self.add_component(MeshRenderer))
        menu.addAction("Audio Source", lambda: self.add_component(AudioSource))
        menu.addAction("Camera", lambda: self.add_component(Camera))
        
        menu.exec_(self.add_component_btn.mapToGlobal(QPoint(0, self.add_component_btn.height())))
        
    def add_component(self, component_type):
        if not self.current_object:
            return
            
        if component_type == ScriptComponent:
            path, _ = QFileDialog.getOpenFileName(self, "Select Script", 
                                                os.path.join(self.editor.project.path, 'Scripts'), 
                                                "Python Files (*.py)")
            if path:
                rel_path = os.path.relpath(path, self.editor.project.path)
                self.current_object.add_component(ScriptComponent(rel_path))
                self.editor.update_inspector()
        elif component_type == MeshRenderer:
            # Similar to hierarchy's mesh renderer addition
            renderer = MeshRenderer()
            self.current_object.add_component(renderer)
            self.editor.update_inspector()
        elif component_type == AudioSource:
            path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", 
                                                os.path.join(self.editor.project.path, 'Audio'), 
                                                "Audio Files (*.wav *.mp3 *.ogg)")
            if path:
                rel_path = os.path.relpath(path, self.editor.project.path)
                self.current_object.add_component(AudioSource(rel_path))
                self.editor.update_inspector()
        elif component_type == Camera:
            self.current_object.add_component(Camera())
            self.editor.update_inspector()
            
    def on_name_changed(self):
        if self.current_object:
            self.current_object.name = self.name_edit.text()
            
    def on_active_changed(self, checked):
        if self.current_object:
            self.current_object.visible = checked
            
    def on_transform_changed(self):
        if not self.current_object:
            return
            
        try:
            x = float(self.pos_x.text())
            y = float(self.pos_y.text())
            z = float(self.pos_z.text())
            self.current_object.transform.position = np.array([x, y, z])
            
            x = float(self.rot_x.text())
            y = float(self.rot_y.text())
            z = float(self.rot_z.text())
            self.current_object.transform.rotation = np.array([x, y, z])
            
            x = float(self.scale_x.text())
            y = float(self.scale_y.text())
            z = float(self.scale_z.text())
            self.current_object.transform.scale = np.array([x, y, z])
        except ValueError:
            pass
            
    def on_component_double_clicked(self, item):
        if not self.current_object:
            return
            
        component = item.data(Qt.UserRole)
        if isinstance(component, ScriptComponent):
            self.editor.open_script_editor(component)
            
    def update_object(self, obj: Optional[GameObject]):
        self.current_object = obj
        
        if not obj:
            self.name_edit.setText("")
            self.name_edit.setPlaceholderText("No object selected")
            self.active_checkbox.setChecked(False)
            self.active_checkbox.setEnabled(False)
            
            self.pos_x.setText("0.0")
            self.pos_y.setText("0.0")
            self.pos_z.setText("0.0")
            
            self.rot_x.setText("0.0")
            self.rot_y.setText("0.0")
            self.rot_z.setText("0.0")
            
            self.scale_x.setText("1.0")
            self.scale_y.setText("1.0")
            self.scale_z.setText("1.0")
            
            self.components_list.clear()
            return
            
        self.name_edit.setText(obj.name)
        self.active_checkbox.setChecked(obj.visible)
        self.active_checkbox.setEnabled(True)
        
        # Update transform fields
        self.pos_x.setText(f"{obj.transform.position[0]:.3f}")
        self.pos_y.setText(f"{obj.transform.position[1]:.3f}")
        self.pos_z.setText(f"{obj.transform.position[2]:.3f}")
        
        self.rot_x.setText(f"{obj.transform.rotation[0]:.3f}")
        self.rot_y.setText(f"{obj.transform.rotation[1]:.3f}")
        self.rot_z.setText(f"{obj.transform.rotation[2]:.3f}")
        
        self.scale_x.setText(f"{obj.transform.scale[0]:.3f}")
        self.scale_y.setText(f"{obj.transform.scale[1]:.3f}")
        self.scale_z.setText(f"{obj.transform.scale[2]:.3f}")
        
        # Update components list
        self.components_list.clear()
        for component in obj.components:
            item = QListWidgetItem()
            
            if isinstance(component, ScriptComponent):
                item.setText(f"Script: {os.path.basename(component.script_path)}")
            elif isinstance(component, MeshRenderer):
                if component.shape_type in MeshRenderer.BUILTIN_SHAPES.values():
                    shape_name = [k for k, v in MeshRenderer.BUILTIN_SHAPES.items() if v == component.shape_type][0]
                    item.setText(f"Mesh Renderer: {shape_name}")
                else:
                    item.setText(f"Mesh Renderer: {os.path.basename(component.mesh_path)}")
            elif isinstance(component, Camera):
                item.setText("Camera")
            elif isinstance(component, AudioSource):
                item.setText(f"Audio Source: {os.path.basename(component.audio_path)}")
            else:
                item.setText(component.__class__.__name__)
                
            item.setData(Qt.UserRole, component)
            self.components_list.addItem(item)

class ScriptEditorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.current_script: Optional[ScriptComponent] = None
        
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Toolbar
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout()
        toolbar.setLayout(toolbar_layout)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_script)
        toolbar_layout.addWidget(self.save_btn)
        
        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self.run_script)
        toolbar_layout.addWidget(self.run_btn)
        
        toolbar_layout.addStretch()
        layout.addWidget(toolbar)
        
        # Editor
        self.editor = QPlainTextEdit()
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: Consolas, monospace;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.editor)
        
    def open_script(self, script: ScriptComponent):
        self.current_script = script
        if script.script_path and os.path.exists(script.script_path):
            with open(script.script_path, 'r') as f:
                self.editor.setPlainText(f.read())
        else:
            self.editor.setPlainText("# New script\n\n# Add your code here")
            
    def save_script(self):
        if not self.current_script:
            return
            
        if not self.current_script.script_path:
            # First time saving - ask for path
            path, _ = QFileDialog.getSaveFileName(self, "Save Script", 
                                                os.path.join(self.editor.project.path, 'Scripts'), 
                                                "Python Files (*.py)")
            if not path:
                return
                
            if not path.endswith('.py'):
                path += '.py'
                
            self.current_script.script_path = os.path.relpath(path, self.editor.project.path)
            
        # Save the file
        with open(os.path.join(self.editor.project.path, self.current_script.script_path), 'w') as f:
            f.write(self.editor.toPlainText())
            
        QMessageBox.information(self, "Success", "Script saved successfully")
        
    def run_script(self):
        if not self.current_script:
            return
            
        # Save first
        self.save_script()
        
        # Run the script in a subprocess
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(self.editor.project.path, self.current_script.script_path)],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                QMessageBox.information(self, "Success", "Script executed successfully")
            else:
                QMessageBox.critical(self, "Error", f"Script failed:\n{result.stderr}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run script: {str(e)}")

class SceneRunnerWidget(QWidget):
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.setup_ui()
        self.is_running = False
        
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Controls
        controls = QWidget()
        controls_layout = QHBoxLayout()
        controls.setLayout(controls_layout)
        
        self.run_btn = QPushButton("Run Scene")
        self.run_btn.clicked.connect(self.toggle_run_scene)
        controls_layout.addWidget(self.run_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_scene)
        controls_layout.addWidget(self.stop_btn)
        
        layout.addWidget(controls)
        
        # Output
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: Consolas, monospace;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.output)
        
    def toggle_run_scene(self):
        if self.is_running:
            self.stop_scene()
        else:
            self.run_scene()
            
    def run_scene(self):
        if not self.editor.current_scene:
            return
            
        self.output.clear()
        self.is_running = True
        self.run_btn.setText("Running...")
        self.stop_btn.setEnabled(True)
        
        # Redirect stdout to our output widget
        sys.stdout = self
        sys.stderr = self
        
        # In a real implementation, we'd properly run the scene with all scripts
        self.output.appendPlainText("Scene started...")
        
    def stop_scene(self):
        self.is_running = False
        self.run_btn.setText("Run Scene")
        self.stop_btn.setEnabled(False)
        
        # Restore stdout/stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        
        self.output.appendPlainText("Scene stopped.")
        
    def write(self, text):
        self.output.appendPlainText(text.strip())
        
    def flush(self):
        pass

class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyEngine Editor")
        self.setGeometry(100, 100, 1280, 720)
        
        # Engine context
        self.ctx: Optional[moderngl.Context] = None
        self.project: Optional[Project] = None
        self.current_scene: Optional[Scene] = None
        
        # In EditorWindow.setup_ui()
        self.game_view = GameViewWidget(self.ctx, self)
                
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        # Create ModernGL context
        self.ctx = moderngl.create_standalone_context()

        # Central widget will be the game view
        self.game_view = GameViewWidget(self.ctx, self)  # Pass self as editor
        self.setCentralWidget(self.game_view)
        
        # Left dock - Project/Hierarchy
        self.left_dock = QDockWidget("Hierarchy", self)
        self.left_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self.hierarchy = HierarchyWidget(self)
        self.left_dock.setWidget(self.hierarchy)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)
        
        # Right dock - Inspector
        self.right_dock = QDockWidget("Inspector", self)
        self.right_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self.inspector = InspectorWidget(self)
        self.right_dock.setWidget(self.inspector)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)
        
        # Bottom dock - Console/Script Editor/Scene Runner
        self.bottom_tab = QTabWidget()
        
        # Console
        self.console = ConsoleWidget()
        self.bottom_tab.addTab(self.console, "Console")
        
        # Script Editor
        self.script_editor = ScriptEditorWidget()
        self.bottom_tab.addTab(self.script_editor, "Script Editor")
        
        # Scene Runner
        self.scene_runner = SceneRunnerWidget(self)
        self.bottom_tab.addTab(self.scene_runner, "Scene Runner")
        
        self.bottom_dock = QDockWidget("Bottom", self)
        self.bottom_dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self.bottom_dock.setWidget(self.bottom_tab)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.bottom_dock)
        
        # Menu bar
        self.setup_menu()
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Set up drag and drop for the entire window
        self.setAcceptDrops(True)
        
    def setup_menu(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        file_menu.addAction('New Project', self.new_project)
        file_menu.addAction('Open Project', self.open_project)
        file_menu.addAction('Save', self.save_project)
        file_menu.addAction('Save Scene', self.save_current_scene)
        file_menu.addSeparator()
        file_menu.addAction('Exit', self.close)
        
        # Edit menu
        edit_menu = menubar.addMenu('Edit')
        edit_menu.addAction('Undo')
        edit_menu.addAction('Redo')
        
        # GameObject menu
        gameobject_menu = menubar.addMenu('GameObject')
        gameobject_menu.addAction('Create Empty', self.create_empty_object)
        
        create_3d_menu = gameobject_menu.addMenu('Create 3D Object')
        create_3d_menu.addAction('Cube', lambda: self.create_3d_object('cube'))
        create_3d_menu.addAction('Sphere', lambda: self.create_3d_object('sphere'))
        create_3d_menu.addAction('Plane', lambda: self.create_3d_object('plane'))
        create_3d_menu.addAction('Capsule', lambda: self.create_3d_object('capsule'))
        create_3d_menu.addAction('Cylinder', lambda: self.create_3d_object('cylinder'))
        
        # Scene menu
        scene_menu = menubar.addMenu('Scene')
        scene_menu.addAction('New Scene', self.new_scene)
        scene_menu.addAction('Save Scene', self.save_current_scene)
        scene_menu.addSeparator()
        
        self.scene_actions = []
        scene_menu.aboutToShow.connect(self.update_scene_menu)
        
    def update_scene_menu(self):
        # Clear existing scene actions
        for action in self.scene_actions:
            self.menuBar().actions()[2].menu().removeAction(action)
        self.scene_actions.clear()
        
        if self.project:
            for i, scene in enumerate(self.project.scenes):
                action = QAction(scene.name, self)
                action.triggered.connect(lambda checked, idx=i: self.load_scene(idx))
                self.scene_actions.append(action)
                self.menuBar().actions()[2].menu().addAction(action)
                
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        if not self.project:
            return
            
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                # Determine destination directory based on file type
                ext = os.path.splitext(path)[1].lower()
                dest_dir = 'Assets'
                
                if ext in ['.wav', '.mp3', '.ogg']:
                    dest_dir = 'Audio'
                elif ext == '.py':
                    dest_dir = 'Scripts'
                
                # Copy file to project
                dest_path = os.path.join(self.project.path, dest_dir, os.path.basename(path))
                
                try:
                    # Create destination directory if it doesn't exist
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    
                    # Copy file
                    import shutil
                    shutil.copy2(path, dest_path)
                    
                    # Update project assets
                    self.project.load_assets()
                    
                    # Show success message
                    self.statusBar().showMessage(f"Added {os.path.basename(path)} to project", 3000)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to add file: {str(e)}")
                    
    def new_project(self):
        path = QFileDialog.getSaveFileName(self, "New Project", "", "PyEngine Project (*.peproj)")[0]
        if path:
            if not path.endswith('.peproj'):
                path += '.peproj'
            self.project = Project(path)
            self.current_scene = self.project.current_scene
            self.update_project_view()
            self.statusBar().showMessage(f"Created new project: {self.project.name}", 3000)
            
    def open_project(self):
        path = QFileDialog.getOpenFileName(self, "Open Project", "", "PyEngine Project (*.peproj)")[0]
        if path and os.path.exists(path):
            self.project = Project(path)
            self.project.load_assets()
            self.current_scene = self.project.current_scene
            self.update_project_view()
            self.statusBar().showMessage(f"Opened project: {self.project.name}", 3000)
            
    def save_project(self):
        if self.project:
            self.project.save()
            if self.current_scene:
                self.project.save_scene(self.current_scene)
            self.statusBar().showMessage("Project saved", 3000)
            
    def save_current_scene(self):
        if self.project and self.current_scene:
            self.project.save_scene(self.current_scene)
            self.statusBar().showMessage(f"Scene '{self.current_scene.name}' saved", 3000)
            
    def new_scene(self):
        if not self.project:
            return
            
        name, ok = QInputDialog.getText(self, "New Scene", "Scene name:")
        if ok and name:
            scene = self.project.create_scene(name)
            self.current_scene = scene
            self.update_hierarchy()
            self.statusBar().showMessage(f"Created new scene: {name}", 3000)
            
    def load_scene(self, index: int):
        if self.project and 0 <= index < len(self.project.scenes):
            self.current_scene = self.project.scenes[index]
            self.project.current_scene = self.current_scene
            self.update_hierarchy()
            self.statusBar().showMessage(f"Loaded scene: {self.current_scene.name}", 3000)
            
    def update_project_view(self):
        if self.project:
            self.update_hierarchy()
            self.update_scene_menu()
            
    def update_hierarchy(self):
        # In a real implementation, we'd use a proper model for the hierarchy
        # For now, just clear and repopulate
        self.hierarchy.model().clear()
        
        if self.current_scene:
            for obj in self.current_scene.root_objects:
                self._add_object_to_hierarchy(obj)
                  
    def _add_object_to_hierarchy(self, obj: GameObject, parent_item=None):
        model = self.hierarchy.model()
        item = QStandardItem(obj.name)
        item.setData(obj, Qt.UserRole)
        if parent_item:
            parent_item.appendRow(item)
        else:
            model.appendRow(item)
        for child in obj.children:
            self._add_object_to_hierarchy(child, item)
              
        def select_object(self, obj: GameObject):
            # Find and select the object in the hierarchy
            model = self.hierarchy.model()
            self._select_object_in_hierarchy(model, obj)
            self.inspector.update_object(obj)
        
    def _select_object_in_hierarchy(self, parent, obj: GameObject):
        for row in range(parent.rowCount()):
            index = parent.index(row, 0)
            if index.data(Qt.UserRole) == obj:
                self.hierarchy.setCurrentIndex(index)
                return True
                
            if parent.hasChildren():
                found = self._select_object_in_hierarchy(parent.child(row), obj)
                if found:
                    return True
                    
        return False
        
    def create_empty_object(self):
        if self.current_scene:
            name, ok = QInputDialog.getText(self, "Create Empty", "Object name:", 
                                          QLineEdit.Normal, "GameObject")
            if ok and name:
                obj = GameObject(name)
                self.current_scene.add_object(obj)
                self.update_hierarchy()
                
    def create_3d_object(self, shape_type: str):
        if self.current_scene:
            name_map = {
                'cube': 'Cube',
                'sphere': 'Sphere',
                'plane': 'Plane',
                'capsule': 'Capsule',
                'cylinder': 'Cylinder'
            }
            name = name_map.get(shape_type, '3D Object')
            obj = GameObject(name)
            renderer = MeshRenderer()
            renderer.shape_type = shape_type
            obj.add_component(renderer)
            self.current_scene.add_object(obj)
            self.update_hierarchy()
            
    def open_script_editor(self, script: ScriptComponent):
        self.script_editor.open_script(script)
        self.bottom_dock.setCurrentWidget(self.script_editor)

# ---------------------------
# Main Application
# ---------------------------

def main():
    app = QApplication([])
    
    # Redirect stdout to console
    #console = ConsoleWidget()
    #sys.stdout = console
    #sys.stderr = console
    
    # Create editor window
    editor = EditorWindow()
    editor.show()
    
    app.exec_()
    
    # Cleanup
    if editor.ctx:
        editor.ctx.release()

if __name__ == "__main__":
    main()