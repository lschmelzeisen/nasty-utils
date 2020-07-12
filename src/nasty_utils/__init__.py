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

from nasty_utils.config import Config
from nasty_utils.datetime_ import (
    date_range,
    date_to_datetime,
    date_to_timestamp,
    format_yyyy_mm,
    format_yyyy_mm_dd,
    parse_yyyy_mm,
    parse_yyyy_mm_arg,
    parse_yyyy_mm_dd,
    parse_yyyy_mm_dd_arg,
)
from nasty_utils.download import (
    FileNotOnServerError,
    download_file_with_progressbar,
    sha256sum,
)
from nasty_utils.io_ import DecompressingTextIOWrapper
from nasty_utils.logging_ import (
    ColoredArgumentsFormatter,
    ColoredBraceStyleAdapter,
    DynamicFileHandler,
    TqdmAwareFileHandler,
    TqdmAwareStreamHandler,
)
from nasty_utils.logging_config import DEFAULT_LOG_CONFIG, LoggingConfig
from nasty_utils.misc import camel_case_split, parse_enum_arg
from nasty_utils.program import (
    Argument,
    ArgumentError,
    ArgumentGroup,
    Command,
    CommandMeta,
    Flag,
    Program,
    ProgramMeta,
)
from nasty_utils.typing_ import checked_cast

__all__ = [
    "Config",
    "date_range",
    "date_to_datetime",
    "date_to_timestamp",
    "format_yyyy_mm",
    "format_yyyy_mm_dd",
    "parse_yyyy_mm",
    "parse_yyyy_mm_arg",
    "parse_yyyy_mm_dd",
    "parse_yyyy_mm_dd_arg",
    "FileNotOnServerError",
    "download_file_with_progressbar",
    "sha256sum",
    "DecompressingTextIOWrapper",
    "ColoredArgumentsFormatter",
    "ColoredBraceStyleAdapter",
    "DynamicFileHandler",
    "TqdmAwareFileHandler",
    "TqdmAwareStreamHandler",
    "DEFAULT_LOG_CONFIG",
    "LoggingConfig",
    "camel_case_split",
    "parse_enum_arg",
    "Argument",
    "ArgumentError",
    "ArgumentGroup",
    "Flag",
    "Command",
    "CommandMeta",
    "Program",
    "ProgramMeta",
    "checked_cast",
]

__version__ = "dev"
try:
    from nasty_utils._version import __version__  # type: ignore
except ImportError:
    pass

__version_info__ = tuple(
    (int(part) if part.isdigit() else part)
    for part in __version__.split(".", maxsplit=4)
)

# Don't show log messages in applications that don't configure logging.
# See https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())
