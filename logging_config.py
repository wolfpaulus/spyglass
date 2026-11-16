""" Application logging setup for Spyglass. """
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

logger = None


def setup_logging() -> None:
    """ Setup logging to a file in the user's home directory. """
    log_dir = Path.home() / "Library" / "Logs" / "Spyglass"
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_dir / "spyglass.log",
        maxBytes=1_000_000,
        backupCount=3,
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[handler],
    )


setup_logging()
logger = logging.getLogger("spyglass")
