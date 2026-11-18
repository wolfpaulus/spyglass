""" Spyglass: Keeping an eye on your containers. """
__author__ = "Wolf Paulus"
__copyright__ = "Copyright 2026, wolfpaulus.com"
__license__ = "MIT License"
__version__ = "1.0.1"
__email__ = "wolf@paulus.com"

import subprocess
import time

from logging_config import logger
from container_manager import check


def wait_for_container(timeout: int = 60) -> bool:
    """Wait until the Apple Container service is available."""
    deadline = time.monotonic() + timeout  # seconds
    while remaining := deadline - time.monotonic():
        if remaining <= 0:
            break
        try:
            subprocess.run(
                ["container", "list"],
                check=True,
                capture_output=True,
                timeout=min(5, remaining),
            )
            return True
        except (subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
                FileNotFoundError):
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(2, remaining))

    return False


def main() -> None:
    """ Main function to check for updates and recreate containers if needed. """
    if not wait_for_container():
        if logger:
            logger.error("Apple Container service is unavailable after waiting.")
        raise SystemExit("Apple Container service unavailable.")

    check()


if __name__ == "__main__":
    main()
