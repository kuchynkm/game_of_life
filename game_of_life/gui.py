"""Tkinter GUI elements module."""
import tkinter as tk
from tkinter import Label, ttk
from typing import Any, Callable, Optional, Tuple
from loguru import logger
import numpy as np
from PIL import ImageTk, Image, ImageColor
import time
import webbrowser

from game_of_life import config, config_path, default_config, project


class MenuBar(tk.Menu):
    """Menu bar with file, settings and help menu."""
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)

        self.file_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Restart (R)")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit (Q)", command=self.exit_command)

        self.settings_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="Edit", menu=self.settings_menu)
        self.settings_menu.add_command(label="Preferences (S)", command=self.settings_command)

        self.help_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="Homepage", command=self.help_command)
        self.help_menu.add_command(label="About", command=self.about_command)

        master.config(menu=self)

    def exit_command(self) -> None:
        """Closes the game."""
        self.master.destroy()
        logger.debug("<QUIT>")

    def settings_command(self) -> None:
        settings = SettingsWindow(self.master)
        settings.grab_set()
        logger.debug("<PREFERENCES>")

    def help_command(self) -> None:
        url = project["tool.poetry"]["repository"].strip('""')
        webbrowser.open(url)
        logger.debug("<HELP>")

    def about_command(self) -> None:
        settings = AboutWindow(self.master)
        settings.grab_set()
        logger.debug("<ABOUT>")


class SettingsWindow(tk.Toplevel):
    """Settings window."""
    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.title("Settings")
        self.resizable(False, False)

        # settings
        self.settings = self._init_settings()

        # reset button
        self.reset_button = tk.Button(self, text="Reset", padx=20, command=self.reset_command)
        self.reset_button.grid(row=2, column=0, sticky=tk.W, padx=20, pady=10)
        
        # OK button
        self.ok_button = tk.Button(self, text="OK", padx=20, command=self.ok_command)
        self.ok_button.grid(row=2, column=1, sticky=tk.E, padx=10, pady=10)

        # Cancel button
        self.cancel_button = tk.Button(self, text="cancel", padx=10, command=self.cancel_command)
        self.cancel_button.grid(row=2, column=2,  sticky=tk.E, padx=10, pady=10)

    def _init_settings(self) -> dict:
        settings = dict()

        # Game settings
        game_settings = ttk.LabelFrame(self, text="Game")
        game_settings.grid(column=0, row=0, padx=20, pady=5, sticky=tk.W)
        # Number of units   
        settings["units"] = Option(game_settings, config_item=("GRID", "UNITS"), label="Number of units", validation_fn=int)
        settings["units"].grid(row=0, column=0, sticky=tk.EW)
        # FPS
        settings["fps"] = Option(game_settings, config_item=("APP", "MAX_FPS"), label="Maximum FPS", validation_fn=int)
        settings["fps"].grid(row=1, column=0, sticky=tk.EW)

        # Graphics settings
        graphics = ttk.LabelFrame(self, text="Graphics")
        graphics.grid(column=0, row=1, padx=20, pady=5, sticky=tk.W)
        # Alive cell color   
        settings["alive_cell_color"] = Option(graphics, config_item=("GRID", "FOREGROUND"), label="Alive cell color", validation_fn=ImageColor.getrgb)
        settings["alive_cell_color"].grid(row=0, column=0, sticky=tk.EW)     
        # Dead cell color
        settings["dead_cell_color"] = Option(graphics, config_item=("GRID", "BACKGROUND"), label="Dead cell color", validation_fn=ImageColor.getrgb)
        settings["dead_cell_color"].grid(row=1, column=0, sticky=tk.EW)  
        # Grid color
        settings["grid_color"] = Option(graphics, config_item=("GRID", "EDGE_COLOR"), label="Grid color", validation_fn=ImageColor.getrgb)
        settings["grid_color"].grid(row=2, column=0, sticky=tk.EW)    

        return settings

    def ok_command(self) -> None:
        """Saves the current configuration to config file and closed the settings window."""
        for _, setting in self.settings.items():
            try:
                setting.save_to_config()
            except ValueError as e:
                MessageWindow(self.master, msg_type="Error", msg=str(e))
                return

        msg = "New settings will take effect next time you open the application."
        MessageWindow(self.master, msg_type="Info", msg=str(msg))
        self.destroy()

    def cancel_command(self) -> None:
        """Discards changes and closes the settings window."""
        self.destroy()

    def reset_command(self) -> None:
        """Resets the settings to default and closes the settings window."""
        for _, setting in self.settings.items():
            setting.reset_default()
        logger.info("Config reset to default.")


class MessageWindow(tk.Toplevel):
    """Generic top-level window displaying a message."""
    def __init__(self, master: tk.Misc, msg_type: str, msg: str):
        super().__init__(master)
        self.title(msg_type)
        self.resizable(False, False)
        self.grab_set()

        self.label = Label(self, text=msg)
        self.label.grid(row=0, column=0, padx=20, pady=10)

        self.ok_button = tk.Button(self, text="OK", padx=20, command=self.destroy)
        self.ok_button.grid(row=1, column=0, padx=10, pady=10)


class AboutWindow(tk.Toplevel):
    """Window displaying basic info about the app."""
    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.title("About")
        self.geometry("250x200")
        self.resizable(False, False)
        self.grab_set()

        title_text = "Game of Life"
        title = ttk.Label(self, text=title_text, font=("Arial",16))
        title.grid(row = 0, column = 0, padx=30, pady=10, sticky=tk.W)

        info_text = self._generate_info()
        info = ttk.Label(self, text=info_text)
        info.grid(row = 2, column = 0, sticky=tk.W)

    def _generate_info(self) -> str:
        """Generates info string based on content of the project TOML file."""        
        # get author and email
        author_info = project["tool.poetry"]["authors"].strip('[""]')
        author_info = author_info.replace(">", "")
        author, email = author_info.split(" <")

        # get version
        version = project["tool.poetry"]["version"].strip('"')

        info_text = f"""
            Author: {author} \n
            Email: {email} \n
            Version: {version}
        """

        return info_text


class Option(tk.Frame):
    """Option as a pair composed of a label and an entry."""
    def __init__(self, master: tk.Misc, config_item: tuple, label: str, validation_fn: Optional[Callable] = None) -> None:
        super().__init__(master)
        self.master = master
        # pairing with an item in the config file
        self.conf_item = config_item
        self.validation_fn = validation_fn
        # label
        self.label = ttk.Label(self, text=label)
        self.label.grid(row=0, column=0, sticky=tk.W, padx=20, pady=10)
        # entry
        self.entry = ttk.Entry(self, width=8)
        self.entry.insert('0', config.get(*config_item))
        self.entry.grid(row=0, column=1, sticky=tk.E, padx=10)
        self.columnconfigure(1, weight=1)

    def get_value(self) -> Any:
        return self.entry.get()

    def save_to_config(self) -> None:
        if self.validation_fn is not None:
            try:
                value = self.entry.get()
                self.validation_fn(value)
            except ValueError:
                error_msg = "Value not supported."
                logger.error(error_msg)
                raise ValueError(error_msg)

        section, option = self.conf_item
        config.set(section, option, value=str(value))
        with open(config_path, 'w') as configfile:
            config.write(configfile)

        logger.debug(f"Saved {value} to {self.conf_item} option.")

    def reset_default(self) -> None:
        self.entry.delete(0, 'end')
        self.entry.insert('0', default_config.get(*self.conf_item))



class Grid(tk.Canvas):
    """Canvas displaying grid and alive/dead cells."""
    def __init__(
        self, 
        master: tk.Misc, 
        dim: int, 
        num_units: int, 
        background_color: tuple,  
        foreground_color: tuple, 
        edge_color: str, 
        *args: Any, **kwargs: Any
    ) -> None:
        super(Grid, self).__init__(master, width=dim + 1, height=dim + 1, *args, **kwargs)
        self.edge_color = edge_color
        self.num_units = num_units
        self.unit_size = dim / num_units
        self.dim = dim
        self.background = np.dstack([
            np.ones((self.num_units, self.num_units)),
            np.ones((self.num_units, self.num_units)),
            np.ones((self.num_units, self.num_units))
        ]) * background_color
        self.foreground = np.dstack([
            np.ones((self.num_units, self.num_units)),
            np.ones((self.num_units, self.num_units)),
            np.ones((self.num_units, self.num_units))
        ]) * foreground_color
        self.cells = self.create_image(0, 0, anchor=tk.NW, image=None, tag="cells")
        self.cell_img = None

    def draw_grid(self) -> None:
        self.delete('grid')
        for unit in range(self.num_units):
            pos = unit * self.unit_size
            self.create_line(0, pos, self.dim, pos, fill=self.edge_color, tag="grid")
            self.create_line(pos, 0, pos, self.dim, fill=self.edge_color, tag="grid")

    def draw_array(self, cell_array: np.ndarray) -> None:
        image = Image.fromarray(255 * (1 - cell_array.astype(np.uint8)))
        image = image.resize(size=(self.size, self.size), resample=Image.NEAREST)
        self.cell_img = ImageTk.PhotoImage(image)
        self.itemconfig("cells", image=self.cell_img)
        self.tag_lower("cells")

    def draw_img(self, cell_img: ImageTk.PhotoImage) -> None:
        self.itemconfig("cells", image=cell_img)
        self.tag_lower("cells")

    def coords_to_grid_position(self, x: int, y: int) -> Tuple[int, int]:
        i = int(y // self.unit_size)
        j = int(x // self.unit_size)
        return i, j



class GameOfLifeGUI:
    """GUI for the Game of Life."""
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title(f"Game of Life")
        self.master.iconphoto(True, tk.PhotoImage(file="game_of_life/resources/images/icon.png"))
        self.master.resizable(False, False)

        # initialize widgets
        self.widgets = self._init_widgets()

        # canvas update related params
        self.cells: tk.PhotoImage
        self.last_time: float
        self.current_time = time.perf_counter()

        logger.info("GUI initialized ...")

    def _init_widgets(self) -> dict:
        widgets = dict()

        # menu bar
        widgets["menubar"] = MenuBar(self.master)

        # grid canvas
        widgets["grid"] = Grid(
            master=self.master,
            dim=config.getint("GRID", "SIZE"),
            num_units=config.getint("GRID", "UNITS"),
            background_color=ImageColor.getrgb(config["GRID"]["BACKGROUND"]),
            foreground_color=ImageColor.getrgb(config["GRID"]["FOREGROUND"]),
            edge_color=config.get("GRID", "EDGE_COLOR"),
            highlightthickness=0
        )
        widgets["grid"].draw_grid()
        widgets["grid"].pack()

        return widgets

    def _show_fps(self) -> None:
        self.last_time = self.current_time
        self.current_time = time.perf_counter()
        elapsed = self.current_time - self.last_time
        self.master.title(f"Game of Life ({int(1 / elapsed)} FPS)")

    def show_cells(self, cells: tk.PhotoImage) -> None:
        """Handle all cell images currently in the queue, if any."""
        self._show_fps()
        self.cells = cells
        self.widgets["grid"].draw_img(self.cells)
