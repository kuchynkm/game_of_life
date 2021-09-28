"""Main module."""
from loguru import logger
from game_of_life.app import GameOfLifeApp

if __name__ == '__main__':
    logger.info("Running main ...")

    win = GameOfLifeApp()
    win.mainloop()
