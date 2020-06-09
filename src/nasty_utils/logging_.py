#
# Copyright 2019-2020 Lukas Schmelzeisen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from datetime import datetime
from inspect import getfile
from logging import DEBUG, FileHandler, LogRecord, StreamHandler
from logging.config import dictConfig
from pathlib import Path
from sys import argv
from typing import TYPE_CHECKING, Any, Mapping, Optional, TextIO, Union, cast

from tqdm import tqdm
from typing_extensions import Final
from xdg import XDG_DATA_HOME

from nasty_utils.config import Config, ConfigAttr

if TYPE_CHECKING:
    from _pytest.config import Config as PytestConfig

DEFAULT_LOG_FORMAT: Final[str] = "{asctime} {levelname:8} [ {name:42} ] {message}"
DEFAULT_LOG_CONFIG: Final[Mapping[str, object]] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colored": {
            "()": "colorlog.ColoredFormatter",
            "format": "{log_color}{message}",
            "style": "{",
        },
        "detailed": {"format": DEFAULT_LOG_FORMAT, "style": "{"},
    },
    "handlers": {
        "console": {
            "class": "nasty_utils.TqdmAwareStreamHandler",
            "level": "INFO",
            "formatter": "colored",
        },
        "file": {
            "class": "nasty_utils.TqdmAwareFileHandler",
            "formatter": "detailed",
            "filename": "{XDG_DATA_HOME}/logs/{argv0}-{asctime:%Y%m%d-%H%M%S}.log",
            "encoding": "UTF-8",
            "symlink": "{XDG_DATA_HOME}/logs/{argv0}-current.log",
        },
    },
    "root": {"level": "DEBUG", "handlers": ["console", "file"]},
}


# See: https://stackoverflow.com/a/38739634/211404
class TqdmAwareStreamHandler(StreamHandler):
    """Stream handler that prints log messages using tqdm.write().

    Necessary, so that log messages do not disrupt an active tqdm progress bar.
    """

    def emit(self, record: LogRecord) -> None:
        try:
            msg = self.format(record)
            tqdm.write(msg, file=cast(TextIO, self.stream))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)


class DynamicFileHandler(FileHandler):
    """File handler allowing to include format placeholders in the filename.

    Also capable to create a symlink to the resulting file.
    """

    def __init__(
        self,
        filename: Union[str, Path],
        mode: str = "a",
        encoding: Optional[str] = None,
        delay: bool = False,
        symlink: Union[None, str, Path] = None,
    ):
        now = datetime.now()
        filename_args = {
            "asctime": now,
            "msecs": now.microsecond / 1000,
            "argv0": Path(argv[0]).name,
            "XDG_DATA_HOME": XDG_DATA_HOME,
        }
        parsed_filename = Path(str(filename).format(**filename_args))
        parsed_filename.parent.mkdir(parents=True, exist_ok=True)

        super().__init__(parsed_filename, mode, encoding, delay)

        if symlink:
            parsed_symlink = Path(str(symlink).format(**filename_args))
            if parsed_symlink.is_symlink() or parsed_symlink.exists():
                parsed_symlink.unlink()
            parsed_symlink.symlink_to(parsed_filename.resolve())


class TqdmAwareFileHandler(DynamicFileHandler):
    """File handler that prints tqdm progress bars to the log file.

    Necessary, so that tqdm progress bars occur in the log file but without the ascii
    control characters.
    """

    def __init__(
        self,
        filename: Union[str, Path],
        mode: str = "a",
        encoding: Optional[str] = None,
        delay: bool = False,
        symlink: Union[None, str, Path] = None,
    ):
        super().__init__(filename, mode, encoding, delay, symlink)

        orig_refresh = tqdm.refresh

        def patched_refresh(
            tqdm_self: "tqdm[Any]",
            nolock: bool = False,
            lock_args: Optional[Any] = None,
        ) -> bool:
            result = orig_refresh(tqdm_self, nolock, lock_args)

            format_dict = cast(
                Mapping[str, object], dict(tqdm_self.format_dict, ncols=80)
            )
            progress_bar = tqdm_self.format_meter(**format_dict)

            self.emit(
                LogRecord(
                    name="tqdm.std",
                    level=DEBUG,
                    pathname=getfile(tqdm),
                    lineno=-1,
                    msg=progress_bar,
                    args=(),
                    exc_info=None,
                )
            )

            return result

        # No way to type the following yet, see:
        # https://github.com/python/mypy/issues/2427
        tqdm.refresh = patched_refresh  # type: ignore


class LoggingConfig(Config):
    logging: Mapping[str, object] = ConfigAttr(default=DEFAULT_LOG_CONFIG)

    def setup_logging(self) -> None:
        dictConfig(dict(self.logging))

    @classmethod
    def setup_pytest_logging(
        cls,
        pytest_config: "PytestConfig",
        *,
        level: str = "DEBUG",
        format_: str = DEFAULT_LOG_FORMAT,
    ) -> None:
        pytest_config.option.log_level = level
        pytest_config.option.log_format = format_

        # When running pytest from PyCharm enable live cli logging so that we can click
        # a test case and see (only) its log output. When not using PyCharm, this
        # functionality is available via the html report.
        if pytest_config.pluginmanager.hasplugin("teamcity.pytest_plugin"):
            pytest_config.option.log_cli_level = level
