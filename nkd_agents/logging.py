import contextvars
import logging
import sys

IS_TTY = sys.stderr.isatty()
logging_context = contextvars.ContextVar("logging_context", default={})

COLOR, RESET = "\033[32m" if IS_TTY else "", "\033[0m"


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        ctx = logging_context.get()
        record.context = f" | {ctx}" if ctx else ""
        return True


def configure_logging() -> None:
    if IS_TTY:
        # ANSI codes: \033[1m = bold, \033[2m = dim, \033[38;5;N = 256 color, \033[0m = reset
        fmt = "\n\033[38;5;65m%(asctime)s\033[38;5;102m | %(levelname)s\033[0m\033[38;5;103m | %(name)s:%(funcName)s:%(lineno)s\033[38;5;255m - %(message)s\033[0m%(context)s"
        logging.getLogger("httpx").setLevel(logging.WARNING)

    else:
        fmt = "%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)s - %(message)s%(context)s"
    handler = logging.StreamHandler(sys.stderr)
    handler.addFilter(ContextFilter())
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=[handler], force=True)
