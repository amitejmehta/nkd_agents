from pydantic_settings import BaseSettings
from rich.console import Console


class RichLogger(Console):
    """RichLogger extends the Rich Console class to provide a logger interface."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._styles = {
            "debug": "[dim]{}[/dim]",
            "info": "{}",
            "warning": "[yellow]{}[/yellow]",
            "error": "[red]{}[/red]",
            "critical": "[bold red]{}[/bold red]",
        }

    def __getattr__(self, name: str):
        if name in self._styles:
            return lambda msg: self.print(self._styles[name].format(msg))
        return super().__getattribute__(name)


class AgentSettings(BaseSettings):
    @property
    def runtime_env(self):
        """Update this to be conditional based on your dev env's."""
        return "local"

    def get_logger(self):
        if self.runtime_env == "local":
            return RichLogger()
        else:
            from loguru import logger

            return logger


settings = AgentSettings()
logger = settings.get_logger()
