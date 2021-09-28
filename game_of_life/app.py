"""App class."""
from loguru import logger
import numpy as np
import tkinter as tk
from tkinter import ttk

from game_of_life.gui_elements import MenuBar, Grid


# TODO move to config
GRID_SIZE = 600
NUM_UNITS = 20
BACKGROUND = "white"
EDGE_COLOR = "silver"
CELL_COLOR = "black"


class GameOfLifeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # GUI widgets
        self.init_gui()
        self.init_cells()
        self.update()

    def init_gui(self):
        # window settings
        self.title('Game of Life')
        self.resizable(0, 0)

        # file menu
        self.menu_bar = MenuBar(self)

        # canvas
        self.grid = Grid(
            master=self,
            size=GRID_SIZE,
            num_units=NUM_UNITS,
            background=BACKGROUND,
            edge_color=EDGE_COLOR,
            highlightthickness=0
        )
        self.grid.grid(row=0, column=0, columnspan=2)
        self.grid.show_grid()

    def init_cells(self):
        self.cells = np.random.randint(2, size=(NUM_UNITS, NUM_UNITS))
        self.draw_cells()

    def draw_cells(self):
        """Draws current state of cells."""
        for row in range(NUM_UNITS):
            for col in range(NUM_UNITS):
                if self.cells[row, col] == 1:
                    self.grid.draw_unit(row, col, color=CELL_COLOR)

    def refresh(self, *args, **kwargs):
        pass


