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

from logging import NOTSET, getLogger
from logging.config import dictConfig
from logging.handlers import MemoryHandler
from sys import maxsize
from typing import Mapping

from _pytest.config import Config as PytestConfig

from nasty_utils.configuration import Configuration

DEFAULT_LOGGING_CONFIGURATION: Mapping[str, object] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colored": {
            "()": "nasty_utils.ColoredArgumentsFormatter",
            "format": "{log_color}{message}",
            "style": "{",
            "arg_color": "reset",
        },
        "json": {
            "()": "jsonlog.JSONFormatter",
            "keys": [
                "timestamp",
                "levelno",
                "level",
                "message",
                "name",
                "pathname",
                "lineno",
                "thread",
                "threadName",
                "process",
                "processName",
                "traceback",
            ],
            "timespec": "milliseconds",
        },
    },
    "handlers": {
        "console": {
            "class": "nasty_utils.TqdmAwareStreamHandler",
            "level": "INFO",
            "formatter": "colored",
        },
        "file": {
            "class": "nasty_utils.TqdmAwareFileHandler",
            "formatter": "json",
            "filename": "{XDG_DATA_HOME}/logs/{argv0}-{asctime:%Y%m%d-%H%M%S}.log",
            "encoding": "UTF-8",
            "symlink": "{XDG_DATA_HOME}/logs/{argv0}-current.log",
        },
    },
    "root": {"level": "DEBUG", "handlers": ["console", "file"]},
}


class LoggingConfiguration(Configuration):
    logging: dict = dict(DEFAULT_LOGGING_CONFIGURATION)  # type: ignore

    @classmethod
    def setup_memory_logging(cls) -> None:
        root = getLogger()
        root.setLevel(NOTSET)
        root.addHandler(MemoryHandler(capacity=maxsize, flushLevel=maxsize))

    def setup_logging(self) -> None:
        root = getLogger()

        buffer = []
        for handler in root.handlers:
            if isinstance(handler, MemoryHandler):
                buffer = handler.buffer
                root.removeHandler(handler)
                break

        dictConfig(dict(self.logging))

        for record in buffer:
            for handler in root.handlers:
                if record.levelno >= handler.level:
                    handler.handle(record)

    @classmethod
    def setup_pytest_logging(
        cls,
        pytest_config: PytestConfig,
        *,
        level: str = "DEBUG",
        format_: str = (
            "%(asctime)s,%(msecs)03.f %(levelname).1s [ %(name)-42s ] %(message)s"
        ),
    ) -> None:
        pytest_config.option.log_level = level
        pytest_config.option.log_format = format_
        pytest_config.option.log_date_format = "%Y-%m-%dT%H:%M:%S"

        # When running pytest from PyCharm enable live cli logging so that we can click
        # a test case and see (only) its log output. When not using PyCharm, this
        # functionality is available via the html report.
        if pytest_config.pluginmanager.hasplugin(
            "teamcity.pytest_plugin"
        ):  # pragma: no cover
            pytest_config.option.log_cli_level = level