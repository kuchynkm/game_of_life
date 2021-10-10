import tkinter as Tkinter
import sys
from loguru import logger
from PIL import ImageTk, Image
from scipy.signal import convolve2d
import time
import threading
from queue import Queue
import numpy as np

from game_of_life.gui_elements import MenuBar, Grid


# logger level
logger.remove()
logger.add(sys.stderr, level="INFO")


# TODO move to config
GRID_SIZE = 1000
NUM_UNITS = 60
SLEEP_TIME = 50
BACKGROUND = "#ff00ff"
EDGE_COLOR = "grey"
CELL_COLOR = "#34aeeb"


class GUI:
    def __init__(self, master):
        self.master = master
        self.master.title(f"Game of Life")
        self.master.resizable(0, 0)

        # initialize widgets
        self.widgets = self.init_widgets()

        # canvas update related params
        self.cells = None
        self.last_time = None
        self.current_time = time.perf_counter()

    def init_widgets(self):
        widgets = dict()

        # menu bar
        widgets["menubar"] = MenuBar(self.master)

        # grid canvas
        widgets["grid"] = Grid(
            master=self.master,
            size=GRID_SIZE,
            num_units=NUM_UNITS,
            background="black",
            edge_color=EDGE_COLOR,
            highlightthickness=0
        )
        widgets["grid"].draw_grid()
        widgets["grid"].pack()

        return widgets

    def show_fps(self):
        self.last_time = self.current_time
        self.current_time = time.perf_counter()
        elapsed = self.current_time - self.last_time
        self.master.title(f"Game of Life ({int(1 / elapsed)} FPS)")

    def show_cells(self, cells):
        """Handle all cell images currently in the queue, if any."""
        self.show_fps()
        self.cells = cells
        self.widgets["grid"].draw_img(self.cells)


class GameOfLife:

    PAUSE_MSG = "PAUSE"
    INIT_MSG = "INIT"
    RANDOM_INIT_MSG = "RANDOM_INIT"
    CLEAR_QUEUES_MSG = "CLEAR_QUEUES"
    CURRENT_GENERATION_MSG = "CURRENT_GENERATION"

    def __init__(self, master):
        """
        Start the GUI and a worker thread for calculations of cell's next generations.
        App GUI is running in the main thread while heavy lifting is done in the worker thread.
        There are two queues:

            * to_process queue with cell arrays to be processed (calculation of new generation
            from the current one and conversion to image);

            * processed queue containing images to be displayed by GUI;

        Worker thread is responsible for reading and writing to to_process queue and writing to processed queue.
        Main thread is only allowed to read from processed queue and writin to to_process queue (in order to
        communicate with worker thread.
        """
        self.master = master
        self.master.bind("<KeyPress>", self.keypress_handler)

        # threading queues
        self.msg_queue = Queue()
        self.processed = Queue(maxsize=50)

        # cell processing
        self.kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]])
        self.shown = None
        self.to_process = None

        # worker thread
        self.worker_thread = threading.Thread(target=self.worker_tasks, daemon=True)
        self.worker_running = True
        self.gui_paused = True
        self.processing_paused = False
        self.idle_period = 5

        # GUI setup
        self.gui = GUI(master)
        self.gui.widgets["menubar"].file_menu.entryconfigure(0, command=self.restart_game)
        self.gui.widgets["menubar"].file_menu.entryconfigure(2, command=self.quit_game)
        self.gui.widgets["grid"].bind("<Button-1>", lambda x: self.edit_cell(x, alive=True))
        self.gui.widgets["grid"].bind("<B1-Motion>", lambda x: self.edit_cell(x, alive=True))
        self.gui.widgets["grid"].bind("<Button-3>", lambda x: self.edit_cell(x, alive=False))
        self.gui.widgets["grid"].bind("<B3-Motion>", lambda x: self.edit_cell(x, alive=False))
        self.gui.widgets["grid"].bind("<Button-2>", lambda x: self.pause_game())
        self.gui.widgets["grid"].bind("<ButtonRelease-1>", lambda x: self.current_generation_to_queue())
        self.dt = 50

        # initialize game
        self.msg_queue.put(self.RANDOM_INIT_MSG)
        self.worker_thread.start()
        self.master.after(100, self.periodic_gui_update)

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

    def init_game(self, random=True):
        self.gui_paused = True

        if random:
            self.to_process = np.random.randint(2, size=(NUM_UNITS, NUM_UNITS))
        else:
            self.to_process = np.zeros(shape=(NUM_UNITS, NUM_UNITS))

        self.gui_paused = False

    def pause_game(self):
        if self.gui_paused:
            self.gui_paused = False
            logger.debug("<UNPAUSED>")
        else:
            self.gui_paused = True
            logger.debug("<PAUSED>")

    def quit_game(self):
        self.worker_running = False
        self.master.destroy()
        logger.debug("<QUIT>")

    def restart_game(self):
        self.msg_queue.put(self.RANDOM_INIT_MSG, block=False)
        self.clear_queue(self.processed)
        logger.debug("<RESTART>")

    def erase_cells(self):
        self.msg_queue.put(self.INIT_MSG, block=False)
        self.clear_queue(self.processed)
        logger.debug("<CELLS ERASED>")

    def next_step(self):
        self.gui_paused = True
        self.gui_update_step()

    @staticmethod
    def clear_queue(q):
        logger.debug(f"Clearing queue {q} from thread {threading.get_ident()} ...")
        with q.mutex:
            q.queue.clear()
            q.all_tasks_done.notify_all()
            q.unfinished_tasks = 0
        logger.debug("Queue clear")

    def edit_cell(self, event, alive):
        self.gui_paused = True
        cell_array = self.shown

        i, j = self.gui.widgets["grid"].coords_to_grid_position(x=event.x, y=event.y)
        if i >= 0 and j >= 0:
            try:
                cell_array[i, j] = int(alive)
            except IndexError:
                pass

        self.shown = cell_array
        cells = self.array_to_img(cell_array)
        self.gui.show_cells(cells)

    def current_generation_to_queue(self):
        self.clear_queue(self.processed)
        logger.debug(f"Processed imgs in queue: {self.processed.qsize()}")
        self.msg_queue.put(self.CURRENT_GENERATION_MSG)
        logger.debug("Inserted current gen msg in msg queue")

    def periodic_gui_update(self):
        if not self.gui_paused:
            self.gui_update_step()

        self.master.after(self.dt, self.periodic_gui_update)
        # self.master.after(500, self.periodic_gui_update)

    def worker_tasks(self):

        while self.worker_running:
            logger.info("loop of worker ...")

            if not self.msg_queue.empty():
                logger.debug("calling msg handler")
                self.msg_handler()
            else:
                logger.debug("to_process empty")
                self.process_array()
                logger.debug(f"to process, processed: {self.msg_queue.qsize()}, {self.processed.qsize()}")

            time.sleep(1e-3 * self.idle_period)
            # time.sleep(0.3)

    def msg_handler(self):
        msg = self.msg_queue.get(False)

        if msg == self.INIT_MSG:
            logger.debug("Received INIT MSG")
            self.init_game(random=False)
            return
        elif msg == self.RANDOM_INIT_MSG:
            logger.debug("Received RANDOM INIT MSG")
            self.init_game(random=True)
            return
        elif msg == self.CURRENT_GENERATION_MSG:
            logger.debug("Received CURRENT GENERATION MSG")
            logger.debug(f"len of processed and msg queue: {self.processed.qsize(), self.msg_queue.qsize()}")
            self.to_process = self.shown
            logger.debug("Array to process updated")
            return
        elif msg == self.PAUSE_MSG:
            logger.debug("Received PAUSE MSG.")
            self.processing_paused = True
            return

    def process_array(self):
        if not self.processed.full() and not self.processing_paused:
            logger.debug("Starting processing ...")

            to_process = self.to_process
            processed = to_process.copy()
            neighbors = convolve2d(to_process, self.kernel, mode='same')
            logger.debug("convolved")

            should_die = (to_process == 1) & ((neighbors > 3) | (neighbors < 2))
            should_live = (to_process == 0) & (neighbors == 3)

            processed[should_live] = 1
            processed[should_die] = 0
            logger.debug("rules applied")

            cell_img = self.array_to_img(processed)
            logger.debug("array to img done")

            self.processed.put((processed, cell_img), block=False)
            self.to_process = processed

    def gui_update_step(self):
        if not self.processed.empty():
            logger.debug("processed not empty, showing img...")
            self.shown, cell_img = self.processed.get(block=False)
            self.processed.task_done()
            self.gui.show_cells(cell_img)
            logger.debug(f"{self.processed.qsize()} processed imgs left in queue")
        else:
            logger.debug(f"processed empty: {self.processed.qsize()}")
            # logger.debug(f"worker is running: {self.worker_running}")
            # logger.debug(f"worker thread alive {self.worker_thread.is_alive()}")

    def array_to_img(self, array):
        image = Image.fromarray(255 * (array.astype(np.uint8)))
        resized_image = image.resize(size=(GRID_SIZE, GRID_SIZE), resample=Image.NEAREST)
        # image = ImageTk.PhotoImage(image)
        return ImageTk.PhotoImage(resized_image)
