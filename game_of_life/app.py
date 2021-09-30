"""App class."""
from loguru import logger
import numpy as np
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk, Image
from scipy.signal import convolve2d

from game_of_life.gui_elements import MenuBar, Grid


# TODO move to config
GRID_SIZE = 720
NUM_UNITS = 75
BACKGROUND = "#ff00ff"
EDGE_COLOR = "grey"
CELL_COLOR = "#34aeeb"


class GameOfLifeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # GUI widgets
        self.init_gui()
        self.update()

        # cells etc.
        self.kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]])
        self.new_cells = None
        self.cells = None
        self.img = None

        self.init_game()

    def init_gui(self):
        # window settings
        self.title('Game of Life')
        self.resizable(0, 0)

        # file menu
        self.menu_bar = MenuBar(self)

        # grid canvas
        self.grid = Grid(
            master=self,
            size=GRID_SIZE,
            num_units=NUM_UNITS,
            background=BACKGROUND,
            edge_color=EDGE_COLOR,
            highlightthickness=0
        )
        self.grid.grid(row=0, column=0, columnspan=2)
        self.grid.pack()

    def init_game(self):
        self.new_cells = np.random.randint(2, size=(NUM_UNITS, NUM_UNITS))
        self.grid.show_grid()
        self.draw_cells()
        self.refresh()

    def draw_cells(self):
        image = Image.fromarray(255 * (1 - self.new_cells.astype(np.uint8)))
        image = image.resize((GRID_SIZE, GRID_SIZE), Image.NEAREST)
        self.img = ImageTk.PhotoImage(image)
        self.grid.itemconfig("cells", image=self.img)
        self.grid.tag_lower("cells")

    def count_neighbors(self):
        """Calculate number of alive neighbors for each cell in the matrix."""
        return convolve2d(self.cells, self.kernel, mode='same')

    def update_cell_status(self):
        """Update cell's dead or alive status based on current status."""
        neighbors = self.count_neighbors()

        should_die = (self.cells == 1) & ((neighbors > 3) | (neighbors < 2))
        should_live = (self.cells == 0) & (neighbors == 3)

        self.new_cells[should_live] = 1
        self.new_cells[should_die] = 0

    def update_cells(self):
        self.cells = self.new_cells.copy()
        self.update_cell_status()

    # @timer
    def refresh(self):
        self.update_cells()
        self.draw_cells()
        self.after(50, self.refresh)
