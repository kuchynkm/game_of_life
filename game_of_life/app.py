"""App class."""
from loguru import logger
import numpy as np
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk, Image

from game_of_life.gui_elements import MenuBar, Grid


# TODO move to config
GRID_SIZE = 600
NUM_UNITS = 50
BACKGROUND = "white"
EDGE_COLOR = "silver"
CELL_COLOR = "black"


class GameOfLifeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # GUI widgets
        self.init_gui()
        self.init_cells()
        self.refresh()
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
        self.grid.pack()
        self.grid.grid(row=0, column=0, columnspan=2)

    def init_cells(self):
        self.new_cells = np.random.randint(2, size=(NUM_UNITS, NUM_UNITS))
        self.draw_cells()

    def draw_cells(self):
        image = Image.fromarray(255 * (1 - self.new_cells.astype(np.uint8)))
        image = image.resize((GRID_SIZE, GRID_SIZE), Image.NEAREST)
        self.img = ImageTk.PhotoImage(image)
        self.grid.create_image(0, 0, anchor=tk.NW, image=self.img)

    def count_cell_neighbors(self, row, col):
        total = 0

        for i in range(-1, 2):
            for j in range(-1, 2):
                neighbor_row = (row + i + NUM_UNITS) % NUM_UNITS
                neighbor_col = (col + j + NUM_UNITS) % NUM_UNITS
                total += self.cells[neighbor_row, neighbor_col]

        total -= self.cells[row, col]

        return total

    def update_cell_status(self, row, col):

        num_neighbors = self.count_cell_neighbors(row, col)

        if self.cells[row, col]:
            # cell is alive
            if num_neighbors < 2 or num_neighbors > 3:
                # cell should die
                self.new_cells[row, col] = 0
        else:
            # cell is dead
            if num_neighbors == 3:
                self.new_cells[row, col] = 1

    def update_cells(self):
        self.cells = self.new_cells.copy()

        for row in range(self.cells.shape[0]):
            for col in range(self.cells.shape[1]):
                self.update_cell_status(row, col)

    # @timer
    def refresh(self):
        self.update_cells()
        self.draw_cells()
        self.after(50, self.refresh)
