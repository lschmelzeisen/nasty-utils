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

from nasty_utils.config import Config, ConfigAttr, ConfigSection
from nasty_utils.download import (
    FileNotOnServerError,
    download_file_with_progressbar,
    sha256sum,
)
from nasty_utils.io_ import DecompressingTextIOWrapper
from nasty_utils.logging_ import LoggingConfig, log_level, log_level_num
from nasty_utils.program.argument import Argument, ArgumentGroup, Flag
from nasty_utils.program.command import Command, CommandMeta
from nasty_utils.program.program import Program, ProgramMeta
from nasty_utils.typing_ import checked_cast

__all__ = [
    "Config",
    "ConfigAttr",
    "ConfigSection",
    "FileNotOnServerError",
    "download_file_with_progressbar",
    "sha256sum",
    "DecompressingTextIOWrapper",
    "LoggingConfig",
    "log_level",
    "log_level_num",
    "Argument",
    "ArgumentGroup",
    "Flag",
    "Command",
    "CommandMeta",
    "Program",
    "ProgramMeta",
    "checked_cast",
]

try:
    from nasty_utils._version import __version__  # type: ignore
except ImportError:
    __version__ = "dev"

__version_info__ = tuple(
    (int(part) if part.isdigit() else part)
    for part in __version__.split(".", maxsplit=4)
)

# Don't show log messages in applications that don't configure logging.
# See https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())
