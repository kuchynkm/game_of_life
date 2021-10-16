"""Tkinter GUI elements module."""
import tkinter as tk
from tkinter import ttk
import numpy as np
from PIL import ImageTk, Image

class MenuBar(tk.Menu):
    def __init__(self, master):
        super().__init__(master)

        self.file_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Restart (R)", command=None)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit (Q)", command=None)

        self.settings_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="Settings", menu=self.settings_menu)
        self.settings_menu.add_command(label="Game settings", command=None)

        self.help_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="About", command=None)

        master.config(menu=self)

    def exit_command(self):
        pass

    def restart_command(self):
        pass

    def settings_command(self):
        pass

    def about_command(self):
        pass


class Grid(tk.Canvas):
    def __init__(self, master, size, num_units, background_color, foreground_color, edge_color, *args, **kwargs):
        super(Grid, self).__init__(master, width=size + 1, height=size + 1, *args, **kwargs)
        self.edge_color = edge_color
        self.num_units = num_units
        self.unit_size = size / num_units
        self.size = size
        self.background = np.dstack([
            np.ones((self.num_units, self.num_units)),
            np.ones((self.num_units, self.num_units)),
            np.ones((self.num_units, self.num_units))
        ]) * background_color
        self.foreground = np.dstack([
            np.ones((self.num_units, self.num_units)),
            np.ones((self.num_units, self.num_units)),
            np.ones((self.num_units, self.num_units))
        ]) * foreground_color
        self.cells = self.create_image(0, 0, anchor=tk.NW, image=None, tag="cells")
        self.cell_img = None

    def draw_grid(self):
        self.delete('grid')
        for unit in range(self.num_units):
            pos = unit * self.unit_size
            self.create_line(0, pos, self.size, pos, fill=self.edge_color, tag="grid")
            self.create_line(pos, 0, pos, self.size, fill=self.edge_color, tag="grid")

    def draw_array(self, cell_array):
        image = Image.fromarray(255 * (1 - cell_array.astype(np.uint8)))
        image = image.resize(size=(self.size, self.size), resample=Image.NEAREST)
        self.cell_img = ImageTk.PhotoImage(image)
        self.itemconfig("cells", image=self.cell_img)
        self.tag_lower("cells")

    def draw_img(self, cell_img):
        self.itemconfig("cells", image=cell_img)
        self.tag_lower("cells")

    def coords_to_grid_position(self, x, y):
        i = int(y // self.unit_size)
        j = int(x // self.unit_size)
        return i, j




