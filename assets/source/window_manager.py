import pygame as pg
import OpenGL.GL as gl
import numpy as np

VERTEX_SHADER_SRC = """
#version 330 core
in vec2 position;
in vec2 texCoord;
out vec2 vTexCoord;
void main() {
    gl_Position = vec4(position, 0.0, 1.0);
    vTexCoord = texCoord;
}
"""

FRAGMENT_SHADER_SRC = """
#version 330 core
in vec2 vTexCoord;
out vec4 fragColor;
uniform sampler2D screenTexture;
void main() {
    fragColor = texture(screenTexture, vTexCoord);
}
"""

class WindowManager:
    def __init__(self, screen_width, screen_height, window_title, icon, use_opengl=True):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        self.use_opengl = use_opengl

        self.screen = pg.Surface((screen_width, screen_height))

        if use_opengl:
            pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
            pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, 3)
            pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, 3)
            self.window = pg.display.set_mode((1920, 1080), pg.DOUBLEBUF | pg.OPENGL | pg.RESIZABLE, vsync=1)

            self.real_mouse_get_pos = pg.mouse.get_pos
            pg.mouse.get_pos = self.scaled_mouse_pos

            self.init_gl()
            
        else:
            self.window = pg.display.set_mode((self.screen_width, self.screen_height), pg.DOUBLEBUF | pg.HWSURFACE | pg.RESIZABLE | pg.SCALED, vsync=1)

        pg.display.set_caption(window_title)
        pg.display.set_icon(icon)

    def scaled_mouse_pos(self):
        mx, my = self.real_mouse_get_pos()
        w, h = pg.display.get_window_size()
        return mx * self.screen_width / w, my * self.screen_height / h

    def init_gl(self):
        self.shader_program = gl.glCreateProgram()

        vs = gl.glCreateShader(gl.GL_VERTEX_SHADER)
        gl.glShaderSource(vs, VERTEX_SHADER_SRC)
        gl.glCompileShader(vs)
        if not gl.glGetShaderiv(vs, gl.GL_COMPILE_STATUS):
            print(gl.glGetShaderInfoLog(vs))

        fs = gl.glCreateShader(gl.GL_FRAGMENT_SHADER)
        gl.glShaderSource(fs, FRAGMENT_SHADER_SRC)
        gl.glCompileShader(fs)
        if not gl.glGetShaderiv(fs, gl.GL_COMPILE_STATUS):
            print(gl.glGetShaderInfoLog(fs))

        gl.glAttachShader(self.shader_program, vs)
        gl.glAttachShader(self.shader_program, fs)
        gl.glLinkProgram(self.shader_program)
        gl.glUseProgram(self.shader_program)
        gl.glDeleteShader(vs)
        gl.glDeleteShader(fs)

        quad = np.array([
            -1.0, -1.0, 0.0, 0.0,
             1.0, -1.0, 1.0, 0.0,
             1.0,  1.0, 1.0, 1.0,
            -1.0,  1.0, 0.0, 1.0
        ], dtype=np.float32)
        self.vao = gl.glGenVertexArrays(1)
        self.vbo = gl.glGenBuffers(1)
        self.ebo = gl.glGenBuffers(1)

        indices = np.array([0, 1, 2, 2, 3, 0], dtype=np.uint32)

        gl.glBindVertexArray(self.vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, quad.nbytes, quad, gl.GL_STATIC_DRAW)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, gl.GL_STATIC_DRAW)

        pos_loc = gl.glGetAttribLocation(self.shader_program, "position")
        tex_loc = gl.glGetAttribLocation(self.shader_program, "texCoord")
        
        gl.glVertexAttribPointer(pos_loc, 2, gl.GL_FLOAT, False, 16, gl.ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(pos_loc)
        gl.glVertexAttribPointer(tex_loc, 2, gl.GL_FLOAT, False, 16, gl.ctypes.c_void_p(8))
        gl.glEnableVertexAttribArray(tex_loc)

        self.screen_texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.screen_texture)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)

    def draw_scaled(self):
        if self.use_opengl:
            screen_data = pg.image.tobytes(self.screen, "RGBA", True)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.screen_texture)
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, self.screen_width, self.screen_height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, screen_data)
            gl.glClearColor(0, 0, 0, 1)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            gl.glUseProgram(self.shader_program)
            gl.glBindVertexArray(self.vao)
            gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
            
        else:
            self.window.blit(self.screen)