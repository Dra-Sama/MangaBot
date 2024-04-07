from loguru import logger
from config import env_vars
import sys

logger.remove(0)
logger.add(sys.stdout, level=env_vars.get("LOG_LEVEL", "INFO"))
