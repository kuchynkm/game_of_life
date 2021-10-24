import tkinter
from typing import Any, Dict, List

from game_of_life import config, logger
from game_of_life.gui import GameOfLifeGUI
from game_of_life.processor import Processor, Message


class GameOfLife:

    def __init__(self, master: tkinter.Tk):
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
        self.master.bind("<KeyPress>", self.keypress_handler)

        # GUI setup
        self.gui = GameOfLifeGUI(master)
        self.gui.widgets["menubar"].file_menu.entryconfigure(0, command=self.restart_game)
        self.gui.widgets["menubar"].file_menu.entryconfigure(2, command=self.quit_game)
        self.gui.widgets["grid"].bind("<Button-1>", lambda x: self.edit_cell(x, alive=True))
        self.gui.widgets["grid"].bind("<B1-Motion>", lambda x: self.edit_cell(x, alive=True))
        self.gui.widgets["grid"].bind("<Button-3>", lambda x: self.edit_cell(x, alive=False))
        self.gui.widgets["grid"].bind("<B3-Motion>", lambda x: self.edit_cell(x, alive=False))
        self.gui.widgets["grid"].bind("<ButtonRelease-1>", self.process_shown)
        self.gui.widgets["grid"].bind("<ButtonRelease-3>", self.process_shown)
        self.gui_sleep = config.getint("APP", "GUI_SLEEP")
        self.gui_paused = False

        # processing 
        self.processor = Processor()
        self.shown = None

        # initialize game
        self.processor.send_message(Message.RANDOM_INIT)
        self.processor.start()
        self.master.after(100, self.periodic_gui_update)

    def keypress_handler(self, event):
        char = event.keysym.lower()
        logger.debug(f"{char} pressed ...")

        actions = {
            config["APP"]["PAUSE_GAME_KEY"]: self.pause_game,
            config["APP"]["RESTART_GAME_KEY"]: self.restart_game,
            config["APP"]["QUIT_GAME_KEY"]: self.quit_game,
            config["APP"]["NEXT_STEP_KEY"]: self.next_step,
            config["APP"]["ERASE_CELLS_KEY"]: self.erase_cells,
        }

        actions.get(char, lambda *args: None).__call__()

    def pause_game(self):
        if self.gui_paused:
            self.gui_paused = False
            logger.debug("<UNPAUSED>")
        else:
            self.gui_paused = True
            logger.debug("<PAUSED>")

    def quit_game(self):
        self.master.destroy()
        logger.debug("<QUIT>")

    def restart_game(self):
        self.processor.msg_queue.put(Message.RANDOM_INIT)
        self.processor.flush_processed()
        self.gui_paused = False
        logger.debug("<RESTART>")

    def erase_cells(self):
        self.processor.msg_queue.put(Message.CLEAN_INIT)
        self.processor.flush_processed()
        self.gui_paused = False
        logger.debug("<CELLS ERASED>")

    def next_step(self):
        self.gui_paused = True
        self.update_gui()

    def edit_cell(self, event, alive):
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

    def process_shown(self, event):
        self.processor.flush_processed()
        logger.debug(f"Processed imgs in queue: {self.processor.processed.qsize()}")
        self.processor.send_message(Message(self.shown))
        logger.debug("Inserted current gen msg in msg queue")

    def periodic_gui_update(self):
        if not self.gui_paused:
            self.update_gui()

        self.master.after(self.gui_sleep, self.periodic_gui_update)

    def update_gui(self):
        if not self.processor.processed.empty():
            logger.debug("processed not empty, showing img...")
            self.shown, cell_img = self.processor.get_processed()
            self.processor.processed.task_done()
            self.gui.show_cells(cell_img)
            logger.debug(f"{self.processor.processed.qsize()} processed imgs left in queue")
        else:
            logger.debug(f"processed empty: {self.processor.processed.qsize()}")
