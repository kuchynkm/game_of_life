"""Tkinter GUI elements module."""
import tkinter as tk
from tkinter import Label, ttk
from loguru import logger
import numpy as np
from PIL import ImageTk, Image, ImageColor
import time

from game_of_life import config 


class MenuBar(tk.Menu):
    """Menu bar with file, settings and help menu."""
    def __init__(self, master):
        super().__init__(master)

        self.file_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Restart (R)", command=None)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit (Q)", command=self.exit_command)

        self.settings_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="Settings", menu=self.settings_menu)
        self.settings_menu.add_command(label="Game settings", command=self.settings_command)

        self.help_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="About", command=None)

        master.config(menu=self)

    def exit_command(self):
        """Closes the game."""
        self.master.destroy()
        logger.debug("<QUIT>")

    def settings_command(self):
        logger.info("Opening settings ...")
        settings = SettingsWindow(self.master)
        settings.grab_set()

    def about_command(self):
        pass


class SettingsWindow(tk.Toplevel):
    """Settings window."""
    def __init__(self, master):
        super().__init__(master)
        self.title("Settings")
        self.geometry("400x300+250+250")
        self.resizable(False, False)
        label = Label(self, text="Settings")

        self.widgets = self._init_widgets()

    def _init_widgets(self):
        widgets = dict()

        # Number of units        
        widgets["units"] = tk.IntVar()
        widgets["units"].set(60)
        ttk.Label(self, text="Number of units").grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=20, pady=10)
        widgets["units_entry"] = ttk.Entry(self, width=6, textvariable= widgets["units"])
        widgets["units_entry"].grid(row=0, column=3, columnspan=2, sticky=tk.E, padx=10)

        # FPS
        widgets["fps"] = tk.IntVar()
        widgets["fps"].set(12)
        ttk.Label(self, text="FPS").grid(row=1, column=0, sticky=tk.W, padx=20, pady=10)
        widgets["fps_entry"] = ttk.Entry(self, width=6, textvariable=widgets["fps"])
        widgets["fps_entry"].grid(row=1, column=3, columnspan=2, sticky=tk.E, padx=10)

        # OK button
        widgets["ok_button"] = tk.Button(self, text="OK", command=self.ok_command)
        widgets["ok_button"].grid(row=10, column=2, columnspan=1, sticky=tk.E, padx=10)

        # Cancel button
        widgets["cancel_button"] = tk.Button(self, text="cancel", command=self.cancel_command)
        widgets["cancel_button"].grid(row=10, column=5, columnspan=1, sticky=tk.E, padx=10)



        return widgets

    def ok_command(self):
        pass

    def cancel_command(self):
        pass




class Grid(tk.Canvas):
    """Canvas displaying grid and alive/dead cells."""
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



class GameOfLifeGUI:
    """GUI for the Game of Life."""
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title(f"Game of Life")
        self.master.resizable(0, 0)

        # initialize widgets
        self.widgets = self._init_widgets()

        # canvas update related params
        self.cells = None
        self.last_time = None
        self.current_time = time.perf_counter()

        logger.info("GUI initialized ...")

    def _init_widgets(self):
        widgets = dict()

        # menu bar
        widgets["menubar"] = MenuBar(self.master)

        # grid canvas
        widgets["grid"] = Grid(
            master=self.master,
            size=config.getint("GRID", "SIZE"),
            num_units=config.getint("GRID", "UNITS"),
            background_color=ImageColor.getrgb(config["GRID"]["BACKGROUND"]),
            foreground_color=ImageColor.getrgb(config["GRID"]["FOREGROUND"]),
            edge_color=config.get("GRID", "EDGE_COLOR"),
            highlightthickness=0
        )
        widgets["grid"].draw_grid()
        widgets["grid"].pack()

        return widgets

    def _show_fps(self):
        self.last_time = self.current_time
        self.current_time = time.perf_counter()
        elapsed = self.current_time - self.last_time
        self.master.title(f"Game of Life ({int(1 / elapsed)} FPS)")

    def show_cells(self, cells):
        """Handle all cell images currently in the queue, if any."""
        self._show_fps()
        self.cells = cells
        self.widgets["grid"].draw_img(self.cells)
