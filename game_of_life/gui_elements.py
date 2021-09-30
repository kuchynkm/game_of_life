"""Tkinter GUI elements module."""
import tkinter as tk
from tkinter import ttk


class MenuBar(tk.Menu):
    def __init__(self, master):
        super().__init__(master)

        self.file_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Restart (R)", command=None)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit (Q)", command=None)

        self.settings_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="Settings", menu=self.settings_menu)
        self.settings_menu.add_command(label="Game settings", command=None)

        self.help_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="About", command=None)

        master.config(menu=self)

    def exit_command(self):
        pass

    def restart_command(self):
        pass

    def settings_command(self):
        pass

    def about_command(self):
        pass


class Slider(ttk.Scale):
    """Custom slider with integer resolution."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, command=self._value_changed, **kwargs)

    def _value_changed(self, new_value):
        new_value = int(float(new_value))
        self.winfo_toplevel().globalsetvar(self.cget('variable'), new_value)


class RgbFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        colors = ("Red", "Green", "Blue")
        self.rgb_values = {c: tk.IntVar() for c in colors}
        self.rgb_labels = {c: ttk.Label(self, textvariable=self.rgb_values[c]) for c in colors}
        self.rgb_sliders = {
            c: Slider(
                self,
                from_=0, to=255,
                orient=tk.HORIZONTAL,
                length=255,
                variable=self.rgb_values[c]
            ) for c in colors}

        for row, c in zip(range(1, 4), colors):
            ttk.Label(self, text=c).grid(row=row, column=0, sticky=tk.E, padx=10)
            self.rgb_sliders[c].grid(row=row, column=1, sticky=tk.W)
            self.rgb_labels[c].grid(row=row, column=2, sticky=tk.E, padx=10)
            self.rgb_labels[c].grid(row=row, column=2, sticky=tk.E, padx=10)


class EntryFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        # Julia set constant
        self.re_c = tk.DoubleVar()
        ttk.Label(self, text="Constant C").grid(row=0, column=0, sticky=tk.W, padx=10)
        self.re_c_entry = ttk.Entry(self, width=12, textvariable=self.re_c)
        self.re_c_entry.grid(row=0, column=1)

        self.im_c = tk.DoubleVar()
        ttk.Label(self, text=" + i ").grid(row=0, column=2)
        self.im_c_entry = ttk.Entry(self, width=12, textvariable=self.im_c)
        self.im_c_entry.grid(row=0, column=3)

        # origin
        self.re_origin = tk.DoubleVar()
        self.im_origin = tk.DoubleVar()
        ttk.Label(self, text="Origin").grid(row=1, column=0, sticky=tk.E, padx=10)
        self.re_origin_entry = ttk.Entry(self, width=12, textvariable=self.re_origin)
        self.re_origin_entry.grid(row=1, column=1)
        ttk.Label(self, text=" + i ").grid(row=1, column=2)
        self.im_origin_entry = ttk.Entry(self, width=12, textvariable=self.im_origin)
        self.im_origin_entry.grid(row=1, column=3)

        # zoom
        self.zoom = tk.DoubleVar()
        ttk.Label(self, text="Zoom").grid(row=2, column=0, sticky=tk.E, padx=10)
        self.zoom_entry = ttk.Entry(self, width=6, textvariable=self.zoom)
        self.zoom_entry.grid(row=2, column=1, columnspan=3, sticky=tk.W)


class Grid(tk.Canvas):
    def __init__(self, master, size, num_units, background, edge_color, *args, **kwargs):
        super(Grid, self).__init__(master, width=size + 1, height=size + 1, *args, **kwargs)
        self.background = background
        self.edge_color = edge_color
        self.num_units = num_units
        self.unit_size = size / num_units
        self.cells = self.create_image(0, 0, anchor=tk.NW, image=None, tag="cells")

    def show_grid(self):

        for row in range(self.num_units):
            self.draw_h_line(row)
            self.draw_v_line(row)

    def draw_h_line(self, row):

        x1, x2 = 0, self.winfo_width()
        y1 = row * self.unit_size
        y2 = y1

        self.create_line(x1, y1, x2, y2, fill=self.edge_color, tag="grid")
        # self.create_line(x1, y1, x2, y2, fill=self.edge_color, tag=f"h_line_{row}")


    def draw_v_line(self, col):

        y1, y2 = 0, self.winfo_height()
        x1 = col * self.unit_size
        x2 = x1

        self.create_line(x1, y1, x2, y2, fill=self.edge_color, tag=f"grid")
        # self.create_line(x1, y1, x2, y2, fill=self.edge_color, tag=f"v_line_{col}")




