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

from logging import INFO, getLogger
from pathlib import Path
from sys import argv
from typing import Iterator, cast

from _pytest.logging import LogCaptureFixture
from colorlog import escape_codes
from tqdm import tqdm

from nasty_utils import (
    ColoredArgumentsFormatter,
    ColoredBraceStyleAdapter,
    DynamicFileHandler,
    TqdmAwareFileHandler,
)


def test_colored_brace_style_adapter(caplog: LogCaptureFixture) -> None:
    regular_logger = getLogger(__name__)
    adapted_logger = ColoredBraceStyleAdapter(regular_logger)
    adapted_logger.setLevel(INFO)

    regular_logger.info("foo %s bar", 45)
    adapted_logger.info("foo {} bar", 45)
    adapted_logger.debug("test")
    adapted_logger.info("test", extra={"foo": "bar"})

    assert len(caplog.records) == 3
    assert caplog.records[0].message == "foo 45 bar"
    assert caplog.records[1].message == "foo 45 bar"
    assert caplog.records[1].msg_color_fmt == (  # type: ignore
        "foo {color_before}45{color_after} bar"
    )
    assert caplog.records[2].foo == "bar"  # type: ignore


def test_colored_arguments_formatter(caplog: LogCaptureFixture) -> None:
    logger = ColoredBraceStyleAdapter(getLogger(__name__))
    logger.info("foo {} bar", 45)
    logger.info("test")

    formatter = ColoredArgumentsFormatter("{green}{message}", arg_color="white")
    assert formatter.format(
        caplog.records[0]
    ) == "{green}foo {reset}{white}45{reset}{green} bar{reset}".format(**escape_codes)
    assert formatter.format(caplog.records[1]) == "{green}test{reset}".format(
        **escape_codes
    )


def test_dynamic_file_handler(tmp_path: Path) -> None:
    handler = DynamicFileHandler(tmp_path / "{argv0}.log")
    assert Path(handler.baseFilename).name == Path(argv[0]).name + ".log"

    dest1 = tmp_path / "dest1.log"
    dest2 = tmp_path / "dest2.log"
    link = tmp_path / "link.log"
    assert not link.exists()
    DynamicFileHandler(dest1, symlink=link)
    assert link.resolve() == dest1
    DynamicFileHandler(dest2, symlink=link)
    assert link.resolve() == dest2


def test_tqdm_aware_file_handler(tmp_path: Path) -> None:
    file = tmp_path / "tqdm.log"
    TqdmAwareFileHandler(file, encoding="UTF-8")
    assert not file.read_text(encoding="UTF-8")
    next(iter(tqdm(cast(Iterator[None], [None]))))
    assert "0/1" in file.read_text(encoding="UTF-8")
