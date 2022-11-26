import contextlib
import logging


# Loggers which have static levels regardless of debug or normal mode
LEVEL_OVERWRITES: dict[str, int] = {
    'discord': logging.INFO,
    'discord.state': logging.WARNING,
    'PIL': logging.INFO,
    'websockets': logging.INFO,
}


@contextlib.contextmanager
def setup_logging(*, process_ids: bool = False):
    """
    Context manager which sets up logging to stdout and shuts down logging on exit.

    Depending on the value of the MOUSEY_DEBUG environment value the log level will be set to INFO or DEBUG.

    Parameters
    ----------
    process_ids : bool
        Controls whether process IDs should be shown in the log. Defaults to False.
    """

    level: int = logging.INFO  # logging.DEBUG if DEBUG else logging.INFO

    if not process_ids:
        fmt: str = '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s'
    else:
        fmt: str = '[%(asctime)s] [%(process)d] [%(levelname)s] [%(name)s]: %(message)s'

    try:
        root: logging.Logger = logging.getLogger()
        root.setLevel(level)

        handler: logging.StreamHandler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt, datefmt='%Y-%m-%d %H:%M:%S'))

        root.addHandler(handler)

        for name, value in LEVEL_OVERWRITES.items():
            logging.getLogger(name).setLevel(value)

        yield
    finally:
        logging.shutdown()
