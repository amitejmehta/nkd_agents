import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

IS_TTY = sys.stderr.isatty()


def configure_logging(level: int = logging.INFO) -> None:
    """Convenience function to toggle Rich logging on/off based on IS_TTY."""
    if IS_TTY:
        handler = RichHandler(
            console=Console(),
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            markup=True,
        )
        fmt, datefmt = "%(message)s", "[%X]"

    else:
        handler = logging.StreamHandler(sys.stderr)
        fmt = "%(asctime)s | %(levelname)s   | %(name)s:%(funcName)s:%(lineno)s - %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        handlers=[handler],
        force=True,
    )

    if IS_TTY:
        logging.getLogger("httpx").setLevel(logging.WARNING)
