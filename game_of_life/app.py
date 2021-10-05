import tkinter as Tkinter
from loguru import logger
from PIL import ImageTk, Image
from scipy.signal import convolve2d
import time
import threading
from queue import Queue
import numpy as np

from game_of_life.gui_elements import MenuBar, Grid


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

        # queues for cell generations
        self.to_process = Queue()
        self.processed = Queue(maxsize=100)

        # cell processing
        self.kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]])
        self.current_generation = None

        # worker thread
        self.worker_thread = threading.Thread(target=self.cell_processing, daemon=True)
        self.worker_running = True
        self.gui_paused = True
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
        self.to_process.put(self.RANDOM_INIT_MSG)
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
            self.to_process.put(np.random.randint(2, size=(NUM_UNITS, NUM_UNITS)))
        else:
            self.to_process.put(np.zeros(shape=(NUM_UNITS, NUM_UNITS)))

        # if not self.worker_running:
        #     self.worker_running = True
        #     self.worker_thread.start()

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
        self.clear_queue(self.processed)
        self.to_process.put(self.RANDOM_INIT_MSG)
        logger.debug("<RESTART>")

    def erase_cells(self):
        self.clear_queue(self.processed)
        self.to_process.put(self.INIT_MSG)
        logger.debug("<CELLS ERASED>")

    def next_step(self):
        self.gui_paused = True
        self.gui_update_step()

    @staticmethod
    def clear_queue(q):
        logger.debug(f"Clearing a queue from thread {threading.get_ident()} ...")
        with q.mutex:
            q.queue.clear()
            q.all_tasks_done.notify_all()
            q.unfinished_tasks = 0
        logger.debug("Queue clear")

    def clear_queues(self):
        logger.debug("Clear queues called")

        self.clear_queue(self.to_process)
        self.clear_queue(self.processed)
        logger.debug("Queues clear...")

    def edit_cell(self, event, alive):
        # TODO still freezing
        self.gui_paused = True
        self.to_process.put(self.PAUSE_MSG)
        self.clear_queue(self.processed)

        i, j = self.gui.widgets["grid"].coords_to_grid_position(x=event.x, y=event.y)
        if i >= 0 and j >= 0:
            try:
                self.current_generation[i, j] = int(alive)
            except IndexError:
                pass

        cells = self.array_to_img(self.current_generation)
        self.gui.show_cells(cells)
        print("len of processed:", self.processed.qsize())

    def current_generation_to_queue(self):
        self.to_process.put(self.CURRENT_GENERATION_MSG)
        self.clear_queue(self.processed)
        self.gui_paused = False

    def periodic_gui_update(self):
        # logger.debug("Periodic gui update called")
        if not self.gui_paused:
            self.gui_update_step()

        self.master.after(self.dt, self.periodic_gui_update)

    def cell_processing(self):
        logger.debug("Started cell processing ...")

        while self.worker_running:

            if not self.to_process.empty():
                self.processing_step()

            time.sleep(1e-3 * self.idle_period)

    def processing_step(self):
        # logger.debug("Processing step called")

        to_process = self.to_process.get(False)

        # TODO make this a message handler or something..
        if isinstance(to_process, str):
            if to_process == self.INIT_MSG:
                logger.debug("Received INIT MSG")
                # clear queue can be moved to init game since it's called only by worker
                self.clear_queue(self.to_process)
                self.init_game(random=False)
                return
            elif to_process == self.RANDOM_INIT_MSG:
                logger.debug("Received RANDOM INIT MSG")
                self.clear_queue(self.to_process)
                self.init_game(random=True)
                return
            elif to_process == self.CLEAR_QUEUES_MSG:
                logger.debug("Received CLEAR QUEUE MSG")
                self.clear_queue(self.to_process)
                return
            elif to_process == self.CURRENT_GENERATION_MSG:
                logger.debug("Received CURRENT GENERATION MSG")
                self.clear_queue(self.to_process)
                self.to_process.put(self.current_generation)
                print("len of to_process:", self.to_process.qsize())
                return
            elif to_process == self.PAUSE_MSG or self.processed.full():
                logger.debug("Either pause or processed queue is full.")
                return

        processed = to_process.copy()
        neighbors = convolve2d(to_process, self.kernel, mode='same')

        should_die = (to_process == 1) & ((neighbors > 3) | (neighbors < 2))
        should_live = (to_process == 0) & (neighbors == 3)

        processed[should_live] = 1
        processed[should_die] = 0

        cell_img = self.array_to_img(processed)

        self.processed.put((processed, cell_img))
        self.to_process.put(processed)

        logger.debug(f"to process, processed: {self.to_process.qsize()}, {self.processed.qsize()}")

    def gui_update_step(self):
        if not self.processed.empty():
            self.current_generation, cell_img = self.processed.get(False)
            self.gui.show_cells(cell_img)
            logger.debug(f"{self.processed.qsize()} processed imgs left in queue")

    def array_to_img(self, array):
        # logger.debug("array to img called")
        image = Image.fromarray(255 * (array.astype(np.uint8)))
        image = image.resize(size=(GRID_SIZE, GRID_SIZE), resample=Image.NEAREST)
        return ImageTk.PhotoImage(image)
