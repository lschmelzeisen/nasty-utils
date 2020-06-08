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

import logging
from datetime import datetime
from inspect import getfile
from logging import FileHandler, Formatter, Handler, LogRecord, StreamHandler, getLogger
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, TextIO, cast

from _pytest.config import Config as PytestConfig
from colorlog import ColoredFormatter
from tqdm import tqdm
from typing_extensions import Final

from nasty_utils.config import Config, ConfigAttr, ConfigSection
from nasty_utils.typing_ import checked_cast

_LOG_LEVELS: Final[Sequence[str]] = [
    "CRITICAL",
    "FATAL",
    "ERROR",
    "WARNING",
    "WARN",
    "INFO",
    "DEBUG",
    "NOTSET",
]


def log_level_num(log_level: str) -> int:
    log_level = log_level.upper()
    if log_level not in _LOG_LEVELS:
        raise ValueError(
            f"Not a valid log level: '{log_level}'. Valid values are: "
            f"{', '.join(_LOG_LEVELS)}."
        )
    return checked_cast(int, getattr(logging, log_level))


def log_level(log_level_num: int) -> str:
    for level in _LOG_LEVELS:
        if getattr(logging, level) == log_level_num:
            return level
    raise ValueError(f"Not a valid log level number: {log_level_num}.")


# See: https://stackoverflow.com/a/38739634/211404
class TqdmStreamHandler(StreamHandler):
    """Logging handler that prints log messages using tqdm.write().

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


class _LoggingSection(Config):
    date_format: str = ConfigAttr(default="%Y-%m-%d %H:%M:%S")

    cli: bool = ConfigAttr(default=True)
    cli_level: int = ConfigAttr(
        default=logging.INFO, deserializer=log_level_num, serializer=log_level
    )
    cli_format: str = ConfigAttr(default="{log_color}{message}")

    file: Optional[Path] = ConfigAttr(default=Path(".logs/{asctime}.log"))
    file_level: int = ConfigAttr(
        default=logging.DEBUG, deserializer=log_level_num, serializer=log_level
    )
    file_format: str = ConfigAttr(
        default="{asctime} {levelname:8} [ {name:46} ] {message}"
    )

    loggers: Mapping[str, int] = ConfigAttr(
        default={}, deserializer=log_level_num, serializer=log_level
    )


class LoggingConfig(Config):
    logging: _LoggingSection = ConfigSection()

    def setup_logging(self) -> None:
        root_logger = getLogger()
        root_logger.setLevel(logging.DEBUG)

        if self.logging.cli:
            cli_handler = TqdmStreamHandler()
            cli_handler.setFormatter(
                ColoredFormatter(
                    self.logging.cli_format, self.logging.date_format, style="{",
                )
            )
            cli_handler.setLevel(self.logging.cli_level)
            root_logger.addHandler(cli_handler)

        if self.logging.file:
            log_file = self.logging.file
            log_file = log_file.with_name(
                log_file.name.format(asctime=datetime.now().isoformat())
            )
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = FileHandler(log_file, encoding="UTF-8")
            file_handler.setFormatter(
                Formatter(self.logging.file_format, self.logging.date_format, style="{")
            )
            file_handler.setLevel(self.logging.file_level)
            root_logger.addHandler(file_handler)
            self._forward_tqdm_to_handler(file_handler)

            # If date formatting took place, create "current" symlink.
            if log_file != self.logging.file:
                symlink_file = log_file.with_name(
                    self.logging.file.name.format(asctime="current")
                )
                if symlink_file.is_symlink() or symlink_file.exists():
                    symlink_file.unlink()
                symlink_file.symlink_to(log_file.resolve())

        for logger, level in self.logging.loggers.items():
            getLogger(logger).setLevel(level)

    @staticmethod
    def _forward_tqdm_to_handler(handler: Handler) -> None:
        orig_refresh = tqdm.refresh

        def patched_refresh(
            tqdm_self: "tqdm[Any]",
            nolock: bool = False,
            lock_args: Optional[Any] = None,
        ) -> bool:
            result = orig_refresh(tqdm_self, nolock, lock_args)

            format_dict = tqdm_self.format_dict
            format_dict["ncols"] = 80
            progress_bar = tqdm_self.format_meter(**format_dict)

            handler.emit(
                LogRecord(
                    name="tqdm.std",
                    level=logging.DEBUG,
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

    def setup_pytest_logging(self, pytest_config: PytestConfig) -> None:
        logging.addLevelName(logging.WARNING, "WARN")
        logging.addLevelName(logging.CRITICAL, "CRIT")

        pytest_config.option.log_level = log_level(self.logging.file_level)
        pytest_config.option.log_format = self.logging.file_format

        # When running pytest from PyCharm enable live cli logging so that we can click
        # a test case and see (only) its log output. When not using PyCharm, this
        # functionality is available via the html report.
        if pytest_config.pluginmanager.hasplugin("teamcity.pytest_plugin"):
            pytest_config.option.log_cli_level = log_level(self.logging.file_level)
