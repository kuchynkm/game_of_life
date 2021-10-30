from queue import Queue
import threading
import time
from typing import Any, Optional
from PIL import ImageTk, Image, ImageColor
from scipy.signal import convolve2d
import numpy as np

from game_of_life import config, logger 


class Message:
    """Message objects to be send to Processor thread via message queue."""
    CLEAN_INIT = object()
    RANDOM_INIT = object()
    PAUSE = object()
    IMG_UPDATE = object()

    def __init__(self, type: object, content: Optional[np.ndarray] = None):
        self.type = type
        self.content = content


class ProcessingThread(threading.Thread):
    """Thread responsible for processing arrays during calculation of next generation of cells."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.processing_paused: bool = True

        # queues
        self.msg_queue: Queue = Queue()
        self.processed: Queue =  Queue(maxsize=50)

        # array processing objects
        self.kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]])
        self.array_size = config.getint("GRID", "SIZE")
        self.array_shape=(config.getint("GRID", "UNITS"), config.getint("GRID", "UNITS"))
        self.background_color=ImageColor.getrgb(config["GRID"]["BACKGROUND"])
        self.foreground_color=ImageColor.getrgb(config["GRID"]["FOREGROUND"])
        self.to_process: np.ndarray

        self.sleep = config.getint("APP", "WORKER_SLEEP")
        logger.info("Processing thread initialized ...")

    def _init_processing(self, random: bool = True) -> None:
        """Initializes starting cell generation, either random or empty."""
        if random:
            self.to_process = np.random.randint(2, size=self.array_shape)
        else:
            self.to_process = np.zeros(shape=self.array_shape)

        self.processing_paused = False

    def _handle_messages(self) -> None:
        """Handles messages coming via message queue."""
        msg = self.msg_queue.get(False)

        if msg.type == Message.CLEAN_INIT:
            logger.debug("Received INIT MSG")
            self._init_processing(random=False)
        elif msg.type == Message.RANDOM_INIT:
            logger.debug("Received RANDOM INIT MSG")
            self._init_processing(random=True)
        elif msg.type == Message.PAUSE:
            logger.debug("Received PAUSE MSG.")
            self.processing_paused = True
        elif msg.type == Message.IMG_UPDATE:
            logger.debug("Received IMG UPDATE MSG")
            logger.debug(f"len of processed and msg queue: {self.processed.qsize(), self.msg_queue.qsize()}")
            self.to_process = msg.content
            logger.debug("Array to_process updated")
        else:
            logger.warning("Received unknown type of message.")

    def _process(self) -> None:
        """Performs calculation of next cell generation and puts it to processed queue."""
        if not self.processed.full() and not self.processing_paused:
            logger.debug("Starting processing ...")

            # get image to process
            to_process = self.to_process
            processed = to_process.copy()

            # calcualte number of cell neighbours
            neighbors = convolve2d(to_process, self.kernel, mode='same')
            # logger.debug("convolved")

            # apply rules of life
            should_die = (to_process == 1) & ((neighbors > 3) | (neighbors < 2))
            should_live = (to_process == 0) & (neighbors == 3)
            processed[should_live] = 1
            processed[should_die] = 0
            # logger.debug("rules applied")

            # convert array to image and put in processed queue
            cell_img = self.array_to_img(processed)
            self.processed.put((processed, cell_img), block=False)
            self.to_process = processed

    def run(self) -> None:
        while True:
            logger.debug("loop of worker ...")

            if not self.msg_queue.empty():
                logger.debug("calling msg handler")
                self._handle_messages()
            else:
                logger.debug("msg queue empty")
                self._process()
                logger.debug(f"msg queue, processed: {self.msg_queue.qsize()}, {self.processed.qsize()}")

            time.sleep(1e-3 * self.sleep)

    def send_message(self, msg: Message) -> None:
        """Sends messages to processing thread."""
        self.msg_queue.put(msg) 

    def get_processed(self) -> Any:
        """Returns next item in processed queue."""
        return self.processed.get(block=False)

    def flush_processed(self) -> None:
        """Deletes content of tthe processed queue."""
        self._clear_queue(self.processed)

    @staticmethod
    def _clear_queue(q: Queue) -> None:
        """Clears a queue."""
        logger.debug(f"Clearing queue {q} from thread {threading.get_ident()} ...")
        with q.mutex:
            q.queue.clear()
            q.all_tasks_done.notify_all()
            q.unfinished_tasks = 0
        logger.debug("Queue clear")

    def array_to_img(self, array: np.ndarray) -> ImageTk.PhotoImage:
        """Conversion of array to image that will be displayed by GUI."""
        # 2D array to RGB array
        background = self.background_color * (1 - array[:, :, None])
        foreground = self.foreground_color * array[:, :, None]
        array = background + foreground

        # array to image and resize
        image = Image.fromarray(array.astype(np.uint8))
        resized_image = image.resize(size=(self.array_size, self.array_size), resample=Image.NEAREST)
        return ImageTk.PhotoImage(resized_image)
