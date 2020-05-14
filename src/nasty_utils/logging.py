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
from logging import getLogger
from typing import Mapping, Sequence

from _pytest.config import Config as PytestConfig
from typing_extensions import Final

from nasty_utils.config import Config, ConfigAttr, ConfigSection
from nasty_utils.typing import checked_cast

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
    raise ValueError(f"Not a valid log level number: {'level_num'}.")


class LoggingConfigSection(Config):
    format: str = ConfigAttr(
        default="%(asctime)s %(levelname)1.1s [ %(name)-31s ] %(message)s"
    )
    level: int = ConfigAttr(
        default="INFO", deserializer=log_level_num, serializer=log_level
    )
    loggers: Mapping[str, int] = ConfigAttr(
        default={}, deserializer=log_level_num, serializer=log_level
    )


class LoggingConfig(Config):
    logging: LoggingConfigSection = ConfigSection()

    def setup_logging(self) -> None:
        logging.basicConfig(format=self.logging.format, level=self.logging.level)
        for logger, level in self.logging.loggers.items():
            getLogger(logger).setLevel(level)

    def setup_pytest_logging(self, pytest_config: PytestConfig) -> None:
        logging.addLevelName(logging.WARNING, "WARN")
        logging.addLevelName(logging.CRITICAL, "CRIT")

        pytest_config.option.log_level = log_level(self.logging.level)
        pytest_config.option.log_format = self.logging.format

        # When running pytest from PyCharm enable live cli logging so that we can click
        # a test case and see (only) its log output. When not using PyCharm, this
        # functionality is available via the html report.
        if pytest_config.pluginmanager.hasplugin("teamcity.pytest_plugin"):
            pytest_config.option.log_cli_level = log_level(self.logging.level)
