"""App class."""
from loguru import logger
import numpy as np
import tkinter as tk
from tkinter import ttk
from scipy.signal import convolve2d

from game_of_life.gui_elements import MenuBar, Grid


# TODO move to config
GRID_SIZE = 1000
NUM_UNITS = 60
SLEEP_TIME = 50
BACKGROUND = "#ff00ff"
EDGE_COLOR = "grey"
CELL_COLOR = "#34aeeb"

from functools import wraps
from time import time, sleep

def timer(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print(f'{te - ts} sec')
        return result
    return wrap


class GameOfLifeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.bind("<KeyPress>", self.keypress_handler)
        # GUI widgets
        self.init_gui()
        self.update()

        # cells etc.
        self.kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]])
        self.new_cells = None
        self.cells = None
        self.img = None
        self.paused = False

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
        self.grid.bind("<Button-1>", self.change_cell_status)
        self.grid.bind("<B1-Motion>", self.change_cell_status)

    def init_game(self):
        self.new_cells = np.random.randint(2, size=(NUM_UNITS, NUM_UNITS))
        self.paused = False
        self.grid.show_grid()
        self.draw_cells()
        self.refresh()

    def keypress_handler(self, event):
        char = event.keysym.lower()
        logger.debug(f"{char} pressed ...")
        if char == 'p' or char == 'space':
            self.pause_game()
        elif char == 'r':
            self.restart_game()
        elif char == 'e':
            self.erase_cells()
        elif char == 'q' or char == 'escape':
            self.quit_game()
        elif char == 'n':
            self.next_step()
        else:
            logger.debug("<NO ACTION>")

    def pause_game(self):
        if self.paused:
            self.paused = False
            self.refresh()
            logger.debug("<UNPAUSED>")
        else:
            self.paused = True
            logger.debug("<PAUSED>")

    def quit_game(self):
        self.destroy()
        logger.debug("<QUIT>")

    def restart_game(self):
        self.paused = True
        # self.update_idletasks()
        self.init_game()
        logger.debug("<RESTART>")

    def erase_cells(self):
        self.paused = True
        self.new_cells *= 0
        self.draw_cells()
        logger.debug("<CELLS ERASED>")

    def next_step(self):
        self.paused = True
        self.single_step()

    def draw_cells(self):
        self.grid.show_cells(self.new_cells)

    def change_cell_status(self, event):
        i, j = self.grid.coords_to_grid_position(x=event.x, y=event.y)
        self.new_cells[i, j] += 1
        self.new_cells[i, j] %= 2
        self.draw_cells()

    def _count_neighbors(self):
        """Calculate number of alive neighbors for each cell in the matrix."""
        return convolve2d(self.cells, self.kernel, mode='same')

    def _update_cell_status(self):
        """Update cell's dead or alive status based on current status."""
        neighbors = self._count_neighbors()

        should_die = (self.cells == 1) & ((neighbors > 3) | (neighbors < 2))
        should_live = (self.cells == 0) & (neighbors == 3)

        self.new_cells[should_live] = 1
        self.new_cells[should_die] = 0

    def update_cells(self):
        self.cells = self.new_cells.copy()
        self._update_cell_status()
        # logger.debug("<CELLS UPDATED>")

    def single_step(self):
        self.grid.update_idletasks()
        sleep(0.025)
        self.update_cells()
        self.draw_cells()

    # @timer
    def refresh(self):
        if not self.paused:
            self.single_step()
            self.after(2, self.refresh)

