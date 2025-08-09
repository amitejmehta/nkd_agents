import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

IS_TTY = sys.stderr.isatty()
console = Console()


def setup_logging(level: int = logging.INFO) -> None:
    """Alternate between rich and basic logging based on IS_TTY."""
    if IS_TTY:
        handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            markup=True,
        )
        fmt = "%(message)s"
        datefmt = "[%X]"
    else:
        handler = logging.StreamHandler(sys.stderr)
        fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        handlers=[handler],
        force=True,  # override prior configs if any
    )
