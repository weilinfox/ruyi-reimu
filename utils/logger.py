import logging

logger = logging.getLogger("ruyi-reimu")
logger.setLevel(logging.INFO)

logger.addHandler(logging.StreamHandler())
