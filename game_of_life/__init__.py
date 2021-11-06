import os
import sys
from configparser import ConfigParser
from loguru import logger

__version__ = '0.1.0'

# absolute package directory
package_dir = os.path.dirname(os.path.abspath(__file__))

# configuration file
relative_config_path = os.path.join("config", "config.ini")
config_path = os.path.join(package_dir, relative_config_path)
config = ConfigParser()
config.read(config_path)

# default configuration
relative_default_config_path = os.path.join("config", "default.ini")
default_config_path = os.path.join(package_dir, relative_default_config_path)
default_config = ConfigParser()
default_config.read(default_config_path)

# project file
relative_project_path = os.path.join("..", "pyproject.toml")
project_path = os.path.join(package_dir, relative_project_path)
project = ConfigParser()
project.read(project_path)

# logger
LOGGER_LEVEL = config["LOGGER"]["LEVEL"]
logger.remove()
logger.add(sys.stderr, level=LOGGER_LEVEL)
logger.info("Game of Life being initalized ...")
