import pygame
from dataclasses import dataclass
from typing import List, Tuple
from math import sin, cos, pi
import wx
from win32api import GetSystemMetrics
import os
os.environ['SDL_VIDEO_WINDOW_POS'] = '%i,%i' % (0, 0)

@dataclass
class Coord:
    x: float = 0.0
    y: float = 0.0

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def clone(self):
        return Coord(self.x, self.y)


@dataclass
class Radius:
    value: float = 1
    thickness: float = 1


class Circle:
    def __init__(self, is_draw_circles: bool, angle: float, r: Radius, v: float):
        self.is_draw_circles = is_draw_circles

        self.center = Coord(0, 0)
        self.angle = angle
        self.angle_velocity = v
        self.r = r

        self.inner_pixels: List[Coord] = self.calc_pixels() if is_draw_circles else []
        self.pixels = self.inner_pixels[:]

    def set_center(self, center: Coord):
        self.center = center

    def calc_pixels(self):
        pixels: List[Coord] = []

        r_inner = self.r.value
        r_outer = self.r.value + self.r.thickness

        def larger_inner(p: Coord):
            return (p.x - self.center.x) ** 2 + (p.y - self.center.y) ** 2 > r_inner ** 2

        def smaller_outer(p: Coord):
            return (p.x - self.center.x) ** 2 + (p.y - self.center.y) ** 2 <= r_outer ** 2

        y = self.center.y - r_outer
        y_end = self.center.y + r_outer

        while y <= y_end:
            x = self.center.x - r_outer
            x_end = self.center.x + r_outer
            while x <= x_end:
                c = Coord(x, y)
                if larger_inner(c) and smaller_outer(c):
                    pixels.append(c)
                x += 1
            y += 1
        return pixels

    def add_angle_velocity(self, other_circle):
        self.angle_velocity += other_circle.angle_velocity

    def recalc_center(self, prev_circle):
        avg_r = 2*prev_circle.r.value + prev_circle.r.thickness
        avg_r /= 2

        self.center.x = int(prev_circle.center.x + avg_r * cos(self.angle/180*pi))
        self.center.y = int(prev_circle.center.y + avg_r * sin(self.angle/180*pi))

        if self.is_draw_circles:
            for i in range(len(self.inner_pixels)):
                new_pixel = self.inner_pixels[i].clone()
                new_pixel.x += self.center.x
                new_pixel.y += self.center.y
                self.pixels[i] = new_pixel

    def get_pixels(self):
        return self.pixels

    def update_angle(self):
        self.angle = (1 if self.angle >= 0 else -1) * (self.angle + self.angle_velocity) % 360


class DrawableSurface:
    def __init__(self, width, height):
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.width, self.height = width, height

    def draw_pixel(self, pos: Coord, color, brush_size: int = 1):
        pixels_offset = brush_size//2
        pix = pygame.PixelArray(self.surface)
        x, y = int(pos.x - pixels_offset), int(pos.y - pixels_offset)
        for row in range(y, y + brush_size + 1):
            for col in range(x, x + brush_size + 1):
                if 0 <= col < self.width and 0 <= row < self.height:
                    pix[col, row] = color


class GraphicWindow:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.surface = pygame.display.set_mode((self.width, self.height), pygame.SRCALPHA | pygame.FULLSCREEN)
        self.running = True

    def is_run(self):
        return self.running

    def flip(self):
        pygame.display.flip()
        self.surface.fill((0, 0, 0, 0))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif pygame.key.get_mods() & pygame.KMOD_CTRL and event.key == pygame.K_s:
                    self.running = False


class CirclesCollection:
    def __init__(self,
                 circles: List[Circle],
                 first_circle_center: Coord,
                 scene_width: int, scene_height: int,
                 brush_line_size: int,
                 circles_color: Tuple[int, int, int],
                 line_color: Tuple[int, int, int],
                 is_draw_circles: bool):

        self.circles: List[Circle] = circles
        self.line_points: List[Coord] = [Coord(-10000, -10000), Coord(-10000, -10000)]
        self.cur_point_index = 0
        self.first_circle_center = first_circle_center
        self.scene_width = scene_width
        self.scene_height = scene_height
        self.brush_line_size = brush_line_size
        self.circles_color = circles_color
        self.line_color = line_color
        self.is_draw_circles = is_draw_circles

        # Set main circle pos with help temp circle
        temp_circle = Circle(is_draw_circles, 0, Radius(1), 1)
        temp_circle.set_center(first_circle_center)
        circles[0].recalc_center(temp_circle)

        # Tie velocity of circles
        for i in range(1, len(circles)):
            circles[i].add_angle_velocity(circles[i - 1])

    def run(self):
        window = GraphicWindow(self.scene_width, self.scene_height)
        image_points = DrawableSurface(self.scene_width, self.scene_height)
        image_circles = DrawableSurface(self.scene_width, self.scene_height)
        image_points.surface.fill((0, 0, 0, 0))

        while window.is_run():
            window.handle_events()

            for i in range(1, len(self.circles)):
                self.circles[i].recalc_center(self.circles[i - 1])
            for circle in self.circles:
                circle.update_angle()

            if self.is_draw_circles:
                image_circles.surface.fill((0, 0, 0, 0))
                for circle in self.circles:
                    for pixel in circle.get_pixels():
                        image_circles.draw_pixel(pixel, (255, 255, 255))
                window.surface.blit(image_circles.surface, (0, 0))

            image_points.draw_pixel(self.circles[-1].center, self.line_color, self.brush_line_size)

            window.surface.blit(image_points.surface, (0, 0))
            if self.is_draw_circles:
                window.surface.blit(image_circles.surface, (0, 0))

            window.flip()

        pygame.quit()


class InitEditor(wx.Frame):
    def __init__(self, parent, init_code, screen_size, click_handler):
        wx.Frame.__init__(self, parent)

        self.panel = wx.Panel(self)

        font = wx.Font()
        font.SetPointSize(int(16 * screen_size[0] / 1920 + 1))
        font.MakeBold()
        font.SetFaceName("Consolas")

        self.button = wx.Button(self.panel, label=" S t a r t ")
        self.button.SetFont(font)

        text_edit_size = (int(4*screen_size[0]//7), int(4*screen_size[1]//7))
        self.text_edit = wx.TextCtrl(self.panel, size=text_edit_size, style=wx.TE_MULTILINE)
        self.text_edit.SetValue(init_code)
        self.text_edit.SetFont(font)

        # Set sizer for the frame, so we can change frame size to match widgets
        self.windowSizer = wx.BoxSizer()
        self.windowSizer.Add(self.panel, 1, wx.ALL | wx.EXPAND)

        # Set sizer for the panel content
        self.sizer = wx.GridBagSizer(5, 5)
        self.sizer.Add(self.text_edit, (0, 0))
        self.sizer.Add(self.button, (1, 0), (3, 0), flag=wx.EXPAND)

        # Set simple sizer for a nice border
        self.border = wx.BoxSizer()
        self.border.Add(self.sizer, 1, wx.ALL | wx.EXPAND, 5)

        # Use the sizers
        self.panel.SetSizerAndFit(self.border)
        self.SetSizerAndFit(self.windowSizer)

        # Set event handlers
        self.text_edit.Bind(wx.EVT_KEY_DOWN, self.handler_key)
        self.button.Bind(wx.EVT_BUTTON, self.handler_ok)
        self.click_handler = click_handler

    def handler_ok(self, e):
        self.click_handler(self.text_edit.GetValue())

    def handler_key(self, event):
        keycode = event.GetKeyCode()
        ctrl_down = event.CmdDown()
        if ctrl_down and keycode == ord('S'):
            exit()
        event.Skip()

class GUI:
    def execute_gui_code(self, user_code):
        self.gui_globals = {'Circle': Circle, 'List': List, 'Coord': Coord, 'R': Radius}
        exec(user_code, self.gui_globals)

        self.circles_collection = CirclesCollection(
            self.gui_globals['circles'],
            self.gui_globals['main_circle_pos'],
            self.gui_globals['w'],
            self.gui_globals['h'],
            self.gui_globals['brush_size'],
            self.gui_globals['circles_color'],
            self.gui_globals['line_color'],
            self.gui_globals['is_draw_circles']
        )
        self.circles_collection.run()

    def __init__(self):
        w, h = GetSystemMetrics(0), GetSystemMetrics(1)

        params = [
            [f'w, h                = {w}, {h}'                , '\t# Размеры экрана'],
            [f'main_circle_pos     = Coord(w*0.5, h*0.5)'     , '\t# Позиция первой окружности'],
            [f'brush_size          = 5'                       , '\t# Размер кисти линии'],
            [f'circles_color       = (255, 255, 255)'         , '\t# Цвет кругов в RGB'],
            [f'line_color          = (155, 10, 20)'          , '\t# Цвет линии в RGB'],
            [f'idc=is_draw_circles = False'                   , '\t# Рисовать окружности'],
        ]

        # Align comments with max length of param line
        max_len = 0
        for s_list in params:
            max_len = max(len(s_list[0]), max_len)

        init_code = ''
        for s_list in params:
            spaces = ''.join([' ' for _ in range(max_len - len(s_list[0]) + 2)])
            init_code += s_list[0] + spaces + s_list[1] + '\n'

        init_code += f'''   
        s = 1 # Масштаб
        z = min(w, h) * 0.1 # Размер части экрана
        a = 90 # Начальный поворот всех окружностей 
        circles: List[Circle] = [
            # Добавь или удали строчку - добавишь или удалишь окружность
            # R(радиус, толщина)
            # v - скорость поворота следующего круга

            Circle(idc, a, R(s * z\t), v = 5\t),
            Circle(idc, a, R(s * z\t), v = -5\t),
            Circle(idc, a, R(s * z\t), v = 0\t),
            Circle(idc, a, R(s * z\t), v = -115\t),
            Circle(idc, a, R(s * z\t), v = 0\t),
            Circle(idc, a, R(s * z\t), v = 50\t),
            Circle(idc, a, R(s * z\t), v = 0\t),
            Circle(idc, a, R(s * z\t), v = 90\t),
            Circle(idc, a, R(s * z\t), v = -120\t),
            Circle(idc, a, R(s * z\t), v = 0\t),
            Circle(idc, a, R(s * z\t), v = -0.05\t),
            Circle(idc, a, R(s * z\t), v = 0.05\t),
            Circle(idc, a, R(s * z\t), v = 0\t),
            Circle(idc, a, R(s * z\t), v = 60\t),
            Circle(idc, a, R(s * z\t), v = -15\t),
            Circle(idc, a, R(s * z\t), v = 0.05\t),
            Circle(idc, a, R(s * 10\t), v = -0.05\t),
            Circle(idc, a, R(s * 10\t), v = 0\t),
            Circle(idc, a, R(s * 10\t), v = 0.15\t),
            Circle(idc, a, R(s * 10\t), v = 0\t),
            
        ]
        '''.replace("        ", "")

        self.gui_globals = {}
        self.circles_collection = None

        self.app = wx.App(False)
        self.frame = InitEditor(
            None, init_code, (w, h),
            lambda user_code: self.execute_gui_code(user_code)
        )
        self.frame.SetTitle("Circles")

    def run(self):
        self.frame.Show()
        self.app.MainLoop()


def main():
    GUI().run()


if __name__ == '__main__':
    main()
