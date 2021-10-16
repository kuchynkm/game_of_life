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

# logger
LOGGER_LEVEL = config["LOGGER"]["LEVEL"]
logger.remove()
logger.add(sys.stderr, level=LOGGER_LEVEL)

logger.info("read config from init ...")
