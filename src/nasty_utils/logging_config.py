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

from logging.config import dictConfig
from typing import TYPE_CHECKING, Mapping

from typing_extensions import Final

from nasty_utils.config import Config, ConfigAttr

if TYPE_CHECKING:
    from _pytest.config import Config as PytestConfig

DEFAULT_LOG_FORMAT: Final[str] = "{asctime} {levelname:8} [ {name:42} ] {message}"
DEFAULT_LOG_CONFIG: Final[Mapping[str, object]] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colored": {
            "()": "nasty_utils.ColoredArgumentsFormatter",
            "format": "{log_color}{message}",
            "style": "{",
            "arg_color": "reset",
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
