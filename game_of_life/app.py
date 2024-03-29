import tkinter as tk

import numpy as np

from game_of_life import config, logger
from game_of_life.gui import GameOfLifeGUI
from game_of_life.processing import ProcessingThread, Message


# TODO clean up the unnecessary logging
class GameOfLife:

    def __init__(self, master: tk.Tk):
        """
        Start GUI and Processor (a worker thread) for computation of cell's next generations.
        App GUI is running in the main thread while heavy lifting is done in the worker thread.
        Processor contains two queues:

            * message queue  serving as a communication channel between main thread and worker thread; 

            * processed queue containing images to be displayed by GUI;

        Processor is responsible for reading the message queue and writing to processed queue.
        Main thread is only allowed to read from processed queue and adding to the message queue (in order to
        communicate with worker thread.
        """
        self.master = master
        self.master.bind("<KeyPress>", self._keypress_handler)

        # GUI setup
        self.gui = GameOfLifeGUI(master)
        self.gui.widgets["menubar"].file_menu.entryconfigure(0, command=self.restart_game)
        self.gui.widgets["grid"].bind("<Button-1>", lambda x: self._edit_cell(x, alive=True))
        self.gui.widgets["grid"].bind("<B1-Motion>", lambda x: self._edit_cell(x, alive=True))
        self.gui.widgets["grid"].bind("<Button-3>", lambda x: self._edit_cell(x, alive=False))
        self.gui.widgets["grid"].bind("<B3-Motion>", lambda x: self._edit_cell(x, alive=False))
        self.gui.widgets["grid"].bind("<ButtonRelease-1>", self._process_shown)
        self.gui.widgets["grid"].bind("<ButtonRelease-3>", self._process_shown)
        self.gui_sleep = int(1000 / config.getint("APP", "MAX_FPS"))
        self.gui_paused = False

        # processing 
        self.processor = ProcessingThread()
        self.shown: np.ndarray

        # initialize game
        self.processor.send_message(Message(Message.RANDOM_INIT))
        self.processor.start()
        self.master.after(100, self.periodic_gui_update)
        logger.info("Game of Life initialized ...")

    def _keypress_handler(self, event: tk.Event) -> None:
        """Handles key-press events."""
        char = event.keysym.lower()
        logger.debug(f"{char} pressed ...")

        actions = {
            config["APP"]["PAUSE_GAME_KEY"]: self.pause_game,
            config["APP"]["RESTART_GAME_KEY"]: self.restart_game,
            config["APP"]["NEXT_STEP_KEY"]: self._next_step,
            config["APP"]["ERASE_CELLS_KEY"]: self._erase_cells,
            config["APP"]["QUIT_GAME_KEY"]: self.gui.widgets["menubar"].exit_command,
            config["APP"]["SETTINGS_KEY"]: self.gui.widgets["menubar"].settings_command,
            config["APP"]["ABOUT_KEY"]: self.gui.widgets["menubar"].about_command,
        }

        actions.get(char, lambda *args: None).__call__()

    # def _apply_settings(self):
    #     self.gui.widgets["menubar"].

    def pause_game(self) -> None:
        """Pauses the game."""
        if self.gui_paused:
            self.gui_paused = False
            logger.debug("<UNPAUSED>")
        else:
            self.gui_paused = True
            logger.debug("<PAUSED>")

    def restart_game(self) -> None:
        """Restarts the game with random initial state."""
        self.processor.msg_queue.put(Message(Message.RANDOM_INIT))
        self.processor.flush_processed()
        self.gui_paused = False
        logger.debug("<RESTART>")

    def _erase_cells(self) -> None:
        """Erases all living cells in the game."""
        self.processor.msg_queue.put(Message(Message.CLEAN_INIT))
        self.processor.flush_processed()
        self.gui_paused = False
        logger.debug("<CELLS ERASED>")

    def _next_step(self) -> None:
        """Pauses the game and performs a single next step."""
        self.gui_paused = True
        self._update_gui()

    def _edit_cell(self, event: tk.Event, alive: bool) -> None:
        """Edits cell status at the given position."""
        self.gui_paused = True
        cell_array = self.shown

        i, j = self.gui.widgets["grid"].coords_to_grid_position(x=event.x, y=event.y)
        i, j = max(i, 0), max(j, 0)

        try:
            cell_array[i, j] = int(alive)
        except IndexError:
            logger.debug("Cursor outside of canvas.")

        self.shown = cell_array
        cells = self.processor.array_to_img(cell_array)
        self.gui.show_cells(cells)

    def _process_shown(self, event: tk.Event) -> None:
        """Puts currently shown image to the processing thread as a new initial state."""
        self.processor.flush_processed()
        logger.debug(f"Processed imgs in queue: {self.processor.processed.qsize()}")
        self.processor.send_message(Message(Message.IMG_UPDATE, self.shown))
        logger.debug("Inserted current gen msg in msg queue")

    def periodic_gui_update(self) -> None:
        """GUI update loop responsible for showing new cell generations."""
        if not self.gui_paused:
            self._update_gui()

        self.master.after(self.gui_sleep, self.periodic_gui_update)

    def _update_gui(self) -> None:
        """Performs a single step in the GUI update loop."""
        if not self.processor.processed.empty():
            logger.debug("processed not empty, showing img...")
            self.shown, cell_img = self.processor.get_processed()
            self.processor.processed.task_done()
            self.gui.show_cells(cell_img)
            logger.debug(f"{self.processor.processed.qsize()} processed imgs left in queue")
        else:
            logger.debug(f"processed empty: {self.processor.processed.qsize()}")
