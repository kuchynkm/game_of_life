import time
import threading
from queue import Queue
from PIL import ImageTk, Image, ImageColor
from scipy.signal import convolve2d
import numpy as np

from game_of_life import config, logger
from game_of_life.gui_elements import MenuBar, Grid


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

        # GUI setup
        self.gui = GUI(master)
        self.gui.widgets["menubar"].file_menu.entryconfigure(0, command=self.restart_game)
        self.gui.widgets["menubar"].file_menu.entryconfigure(2, command=self.quit_game)
        self.gui.widgets["grid"].bind("<Button-1>", lambda x: self.edit_cell(x, alive=True))
        self.gui.widgets["grid"].bind("<B1-Motion>", lambda x: self.edit_cell(x, alive=True))
        self.gui.widgets["grid"].bind("<Button-3>", lambda x: self.edit_cell(x, alive=False))
        self.gui.widgets["grid"].bind("<B3-Motion>", lambda x: self.edit_cell(x, alive=False))
        self.gui.widgets["grid"].bind("<ButtonRelease-1>", lambda x: self.current_generation_to_queue())
        self.gui.widgets["grid"].bind("<ButtonRelease-3>", lambda x: self.current_generation_to_queue())
        self.gui_sleep = config.getint("APP", "GUI_SLEEP")
        self.num_units = self.gui.widgets["grid"].num_units
        self.grid_size = self.gui.widgets["grid"].size

        # cell processing
        self.kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]])
        self.shown = None
        self.to_process = None

        # threading queues
        self.msg_queue = Queue()
        self.processed = Queue(maxsize=50)

        # worker thread
        self.worker_thread = threading.Thread(target=self.worker_tasks, daemon=True)
        self.worker_running = True
        self.gui_paused = True
        self.processing_paused = False
        self.worker_sleep = config.getint("APP", "WORKER_SLEEP")

        # initialize game
        self.msg_queue.put(self.RANDOM_INIT_MSG)
        self.worker_thread.start()
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

    def init_game(self, random=True):
        self.gui_paused = True

        if random:
            self.to_process = np.random.randint(2, size=(self.num_units, self.num_units))
        else:
            self.to_process = np.zeros(shape=(self.num_units, self.num_units))

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
        i, j = max(i, 0), max(j, 0)

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

        self.master.after(self.gui_sleep, self.periodic_gui_update)

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

            time.sleep(1e-3 * self.worker_sleep)

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

            # get image to process
            to_process = self.to_process
            processed = to_process.copy()

            # calcualte number of cell neighbours
            neighbors = convolve2d(to_process, self.kernel, mode='same')
            logger.debug("convolved")

            # apply rules of life
            should_die = (to_process == 1) & ((neighbors > 3) | (neighbors < 2))
            should_live = (to_process == 0) & (neighbors == 3)
            processed[should_live] = 1
            processed[should_die] = 0
            logger.debug("rules applied")

            # convert array to image and put in processed queue
            cell_img = self.array_to_img(processed)
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

    def array_to_img(self, array):
        # 2D array to RGB array
        background = self.gui.widgets["grid"].background * (1 - array[:, :, None])
        foreground = self.gui.widgets["grid"].foreground * array[:, :, None]
        array = background + foreground

        # array to image and resize
        image = Image.fromarray(array.astype(np.uint8))
        resized_image = image.resize(size=(self.grid_size, self.grid_size), resample=Image.NEAREST)
        return ImageTk.PhotoImage(resized_image)
