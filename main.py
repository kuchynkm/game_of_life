"""Main module."""
from tkinter import Tk
from game_of_life.app import GameOfLife

if __name__ == '__main__':
    root = Tk()
    client = GameOfLife(root)
    root.mainloop()

