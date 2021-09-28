"""Cell class."""

class Cell:
    def __init__(self, position, state):
        self.position = position
        self.state = state

    def number_of_neighbours(self):
        return None