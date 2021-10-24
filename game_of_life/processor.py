from queue import Queue
import threading
import time
from PIL import ImageTk, Image, ImageColor
from numpy.lib import isin
from scipy.signal import convolve2d
import numpy as np

from game_of_life import config, logger 


class Processor(threading.Thread):

    PAUSE_MSG = "PAUSE"
    INIT_MSG = "INIT"
    RANDOM_INIT_MSG = "RANDOM_INIT"
    CLEAR_QUEUES_MSG = "CLEAR_QUEUES"
    CURRENT_GENERATION_MSG = "CURRENT_GENERATION"

    def __init__(self):
        super().__init__(daemon=True)
        self.processing_paused: bool = True

        # queues
        self.msg_queue = Queue()
        self.processed = Queue(maxsize=50)

        # array processing objects
        self.kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]])
        self.size=config.getint("GRID", "SIZE")
        self.array_shape=(config.getint("GRID", "UNITS"), config.getint("GRID", "UNITS"))
        self.background_color=ImageColor.getrgb(config["GRID"]["BACKGROUND"])
        self.foreground_color=ImageColor.getrgb(config["GRID"]["FOREGROUND"])
        self.shown = None
        self.to_process = None

        self.sleep = config.getint("APP", "WORKER_SLEEP")
        logger.info("Processor initialized ...")

    def _init_processing(self, random: bool = True) -> None:
        if random:
            self.to_process = np.random.randint(2, size=self.array_shape)
        else:
            self.to_process = np.zeros(shape=self.array_shape)

        self.processing_paused = False

    def _handle_messages(self) -> None:
        msg = self.msg_queue.get(False)

        if not isinstance(msg, str):
            if isinstance(msg, np.ndarray):
                logger.debug("Received UPDATE TO_PROCESS MSG")
                logger.debug(f"len of processed and msg queue: {self.processed.qsize(), self.msg_queue.qsize()}")
                self.to_process = msg
                logger.debug("Array to_process updated")
                return
            else:
                logger.debug("Unknown type of MSG received.")

        if msg == self.INIT_MSG:
            logger.debug("Received INIT MSG")
            self._init_processing(random=False)
            return
        elif msg == self.RANDOM_INIT_MSG:
            logger.debug("Received RANDOM INIT MSG")
            self._init_processing(random=True)
            return
        elif msg == self.PAUSE_MSG:
            logger.debug("Received PAUSE MSG.")
            self.processing_paused = True
            return


    def process(self) -> None:
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

    def run(self) -> None:
        while True:
            logger.info("loop of worker ...")

            if not self.msg_queue.empty():
                logger.debug("calling msg handler")
                self._handle_messages()
            else:
                logger.debug("msg queue empty")
                self.process()
                logger.debug(f"msg queue, processed: {self.msg_queue.qsize()}, {self.processed.qsize()}")

            time.sleep(1e-3 * self.sleep)

    def send_message(self, msg: object) -> None:
        self.msg_queue.put(msg) 

    def get_processed(self) -> np.array:
        return self.processed.get(block=False)

    def flush_processed(self) -> None:
        self.clear_queue(self.processed)

    @staticmethod
    def clear_queue(q: Queue) -> None:
        logger.debug(f"Clearing queue {q} from thread {threading.get_ident()} ...")
        with q.mutex:
            q.queue.clear()
            q.all_tasks_done.notify_all()
            q.unfinished_tasks = 0
        logger.debug("Queue clear")

    def array_to_img(self, array: np.array) -> ImageTk.PhotoImage:
        # 2D array to RGB array
        background = self.background_color * (1 - array[:, :, None])
        foreground = self.foreground_color * array[:, :, None]
        array = background + foreground

        # array to image and resize
        image = Image.fromarray(array.astype(np.uint8))
        resized_image = image.resize(size=(self.size, self.size), resample=Image.NEAREST)
        return ImageTk.PhotoImage(resized_image)
