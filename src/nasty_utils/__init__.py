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


__version__ = "dev"
try:
    from nasty_utils._version import __version__  # type: ignore
except ImportError:
    pass

__version_info__ = tuple(
    (int(part) if part.isdigit() else part)
    for part in __version__.split(".", maxsplit=4)
)


import logging

from nasty_utils.datetime_ import (
    advance_date_by_month,
    date_range,
    date_to_datetime,
    date_to_timestamp,
    format_yyyy_mm,
    format_yyyy_mm_dd,
    parse_yyyy_mm,
    parse_yyyy_mm_dd,
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
from nasty_utils.logging_settings import DEFAULT_LOGGING_SETTINGS, LoggingSettings
from nasty_utils.misc import camel_case_split, get_qualified_name, lookup_qualified_name
from nasty_utils.program import (
    Argument,
    ArgumentGroup,
    ArgumentInfo,
    Program,
    ProgramConfig,
)
from nasty_utils.settings import Settings, SettingsConfig
from nasty_utils.typing_ import checked_cast, safe_issubclass

__all__ = [
    "advance_date_by_month",
    "date_range",
    "date_to_datetime",
    "date_to_timestamp",
    "format_yyyy_mm",
    "format_yyyy_mm_dd",
    "parse_yyyy_mm",
    "parse_yyyy_mm_dd",
    "FileNotOnServerError",
    "download_file_with_progressbar",
    "sha256sum",
    "DecompressingTextIOWrapper",
    "ColoredArgumentsFormatter",
    "ColoredBraceStyleAdapter",
    "DynamicFileHandler",
    "TqdmAwareFileHandler",
    "TqdmAwareStreamHandler",
    "DEFAULT_LOGGING_SETTINGS",
    "LoggingSettings",
    "camel_case_split",
    "get_qualified_name",
    "lookup_qualified_name",
    "Argument",
    "ArgumentGroup",
    "ArgumentInfo",
    "Program",
    "ProgramConfig",
    "Settings",
    "SettingsConfig",
    "checked_cast",
    "safe_issubclass",
]


# Don't show log messages in applications that don't configure logging.
# See https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())
