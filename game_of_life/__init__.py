import os
import sys
from configparser import ConfigParser
from loguru import logger

__version__ = '0.1.0'

# configuration file
relative_config_path = os.path.join("config", "config.ini")
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_config_path)
config = ConfigParser()
config.read(config_path)

# default configuration
relative_default_config_path = os.path.join("config", "default.ini")
default_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_default_config_path)
default_config = ConfigParser()
default_config.read(default_config_path)

# project toml file
relative_project_path = os.path.join("..", "pyproject.toml")
project_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_project_path)
project = ConfigParser()
project.read(project_path)

# logger
LOGGER_LEVEL = config["LOGGER"]["LEVEL"]
logger.remove()
logger.add(sys.stderr, level=LOGGER_LEVEL)
logger.info("read config from init ...")
