import contextvars
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

IS_TTY = sys.stderr.isatty()
logging_context = contextvars.ContextVar("logging_context", default={})


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        ctx = logging_context.get()
        record.context = f" | {ctx}" if ctx else ""
        return True


def configure_logging() -> None:
    if IS_TTY:
        # ANSI codes: \033[1m = bold, \033[2m = dim, \033[38;5;N = 256 color, \033[0m = reset
        handler = RichHandler(
            console=Console(width=120),
            markup=True,
            show_level=False,
            show_path=False,
            show_time=False,
        )
        fmt = "%(message)s%(context)s"
    else:
        handler = logging.StreamHandler(sys.stderr)
        fmt = "%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)s - %(message)s%(context)s"
    handler.addFilter(ContextFilter())
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=[handler], force=True)
