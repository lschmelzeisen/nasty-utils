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

import string
from datetime import datetime
from inspect import getfile
from logging import DEBUG, FileHandler, Logger, LoggerAdapter, LogRecord, StreamHandler
from pathlib import Path
from sys import argv
from typing import (
    Any,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    TextIO,
    Tuple,
    Union,
    cast,
)

from colorlog import ColoredFormatter, escape_codes
from overrides import overrides
from tqdm import tqdm
from xdg import XDG_DATA_HOME


class _ColoredStringFormatter(string.Formatter):
    @overrides
    def format(*args: Any, **kwargs: Any) -> str:
        return (
            string.Formatter.format(*args, **kwargs)
            # The following is needed so that original parentheses in the result are
            # preserved after the formatting.
            .replace("{", "{{")
            .replace("}", "}}")
            .replace("{{color_before}}", "{color_before}")
            .replace("{{color_after}}", "{color_after}")
        )

    @overrides
    def format_field(self, value: object, format_spec: str) -> str:
        return (
            f"{{color_before}}{super().format_field(value, format_spec)}{{color_after}}"
        )


# See:
# https://docs.python.org/3/howto/logging-cookbook.html#use-of-alternative-formatting-styles
class ColoredBraceStyleAdapter(LoggerAdapter):
    @overrides
    def __init__(self, logger: Logger, extra: Optional[Mapping[str, object]] = None):
        super().__init__(logger, extra or {})

    @overrides
    def log(self, level: int, msg: object, *args: object, **kwargs: object) -> None:
        if self.isEnabledFor(level):
            msg_raw, log_kwargs = self.process(msg, kwargs)

            msg_color_fmt = _ColoredStringFormatter().format(msg_raw, *args, **kwargs)
            msg = msg_color_fmt.format(color_before="", color_after="")
            if "{color_before}" in msg_color_fmt:
                cast(MutableMapping[str, object], log_kwargs["extra"])[
                    "msg_color_fmt"
                ] = msg_color_fmt

            self.logger._log(level, msg, (), **log_kwargs)

    @overrides
    def process(
        self, msg: object, kwargs: MutableMapping[str, object]
    ) -> Tuple[object, MutableMapping[str, object]]:
        # Default LoggerAdapter.process() implementation is buggy and reuses same extra
        # dict for all LogRecords (also overrides potentially existing extra dict).
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        cast(MutableMapping[str, object], kwargs["extra"]).update(self.extra)
        return msg, kwargs


class ColoredArgumentsFormatter(ColoredFormatter):
    @overrides
    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = "%",
        log_colors: Optional[Mapping[str, str]] = None,
        reset: bool = True,
        secondary_log_colors: Optional[Mapping[str, Mapping[str, str]]] = None,
        arg_color: str = "white",
    ):
        if style != "{":
            raise NotImplementedError("style != '{' is not supported yet.")

        super().__init__(
            fmt=fmt,
            datefmt=datefmt,
            style=style,
            log_colors=log_colors,
            reset=reset,
            secondary_log_colors=secondary_log_colors,
        )

        self._arg_color = arg_color
        self._message_color_modifiers: Sequence[str] = []
        for (
            _literal_text,
            field_name,
            _format_spec,
            _conversion,
        ) in string.Formatter().parse(cast(str, self._fmt)):
            if not field_name:
                continue
            elif field_name == "message":
                break
            elif field_name == "reset":
                self._message_color_modifiers = []
            elif field_name.endswith("log_color"):
                self._message_color_modifiers.append(field_name)

    @overrides
    def format(self, record: LogRecord) -> str:
        orig_record_msg = record.msg
        msg_color_fmt = getattr(record, "msg_color_fmt", None)
        if msg_color_fmt:
            record.msg = msg_color_fmt

        result = super().format(record)
        if msg_color_fmt:
            # The following had to be duplicated from ColoredFormatter.format()
            # because there is no way to access the results from a subclass.
            colors = {"log_color": self.color(self.log_colors, record.levelname)}
            if self.secondary_log_colors:
                for name, log_colors in self.secondary_log_colors.items():
                    colors[name + "_log_color"] = self.color(
                        log_colors, record.levelname
                    )

            result = result.format(
                color_before=escape_codes["reset"] + escape_codes[self._arg_color],
                color_after=(
                    escape_codes["reset"]
                    + "".join(colors[c] for c in self._message_color_modifiers)
                ),
            )

        if msg_color_fmt:
            record.msg = orig_record_msg
        return result


# See: https://stackoverflow.com/a/38739634/211404
class TqdmAwareStreamHandler(StreamHandler):
    """Stream handler that prints log messages using tqdm.write().

    Necessary, so that log messages do not disrupt an active tqdm progress bar.
    """

    @overrides
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

    @overrides
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

    @overrides
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
