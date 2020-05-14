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


from contextlib import contextmanager
from logging import Logger, getLogger
from pathlib import Path
from typing import Any, Iterator, Optional, cast

import pytest
from overrides import overrides
from typing_extensions import Final

from nasty_utils.logging import LoggingConfig, log_level_num
from nasty_utils.program.argument import Argument, Flag
from nasty_utils.program.command import Command, CommandMeta
from nasty_utils.program.program import Program, ProgramMeta
from tests._util.path import change_dir

_LOGGER: Final[Logger] = getLogger(__name__)


class FooCommand(Command[LoggingConfig]):
    @classmethod
    @overrides
    def meta(cls) -> CommandMeta:
        return CommandMeta(name="foo", aliases=["f"], desc="foo desc")


class BarCommand(Command[LoggingConfig]):
    @classmethod
    @overrides
    def meta(cls) -> CommandMeta:
        return CommandMeta(name="bar", aliases=["b"], desc="bar desc")


class BazCommand(Command[LoggingConfig]):
    @classmethod
    @overrides
    def meta(cls) -> CommandMeta:
        return CommandMeta(name="baz", aliases=["b"], desc="baz desc")


class QuxCommand(Command[LoggingConfig]):
    @classmethod
    @overrides
    def meta(cls) -> CommandMeta:
        return CommandMeta(name="qux", aliases=["q"], desc="qux desc")


class MyProgram(Program[LoggingConfig]):
    @classmethod
    @overrides
    def meta(cls) -> ProgramMeta[LoggingConfig]:
        return ProgramMeta(
            name="myprog",
            version="0.1.0",
            desc="myprog desc",
            config_type=LoggingConfig,
            config_file="myprog.toml",
            config_dir=".",
            command_hierarchy={
                Command: [FooCommand, BarCommand],
                BarCommand: [BazCommand, QuxCommand],
            },
        )


class QqqCommand(Command[None]):
    in_file: Path = Argument(
        name="in-file",
        short_name="i",
        metavar="FILE",
        desc="Input file.",
        required=True,
        deserializer=Path,
    )
    out_file: Optional[Path] = Argument(
        name="out-file", metavar="File", desc="Output file", deserializer=Path
    )

    @classmethod
    @overrides
    def meta(cls) -> CommandMeta:
        return CommandMeta(name="qqq", desc="qqq desc")


class NoConfigProgram(Program[None]):
    @classmethod
    @overrides
    def meta(cls) -> ProgramMeta[None]:
        return ProgramMeta(
            name="noconf",
            version="0.1.0",
            desc="noconf desc",
            config_type=type(None),
            config_file="",
            config_dir="",
            command_hierarchy={Command: [QqqCommand]},
        )


class NoCommandProgram(Program[None]):
    verbose: bool = Flag(name="verbose", desc="Verbose desc.")

    @classmethod
    @overrides
    def meta(cls) -> ProgramMeta[None]:
        return ProgramMeta(
            name="nocomm",
            version="0.1.0",
            desc="nocomm desc",
            config_type=type(None),
            config_file="",
            config_dir="",
            command_hierarchy=None,
        )


@contextmanager
def _write_logging_config(config_file: Path, level: str) -> Iterator[None]:
    Path.mkdir(config_file.parent, exist_ok=True, parents=True)
    with config_file.open("w", encoding="UTF-8") as fout:
        fout.write(
            f"""
            [logging]
            level = "{level}"
            """
        )

    try:
        yield None
    finally:
        Path.unlink(config_file)


def test_program_config(tmp_path: Path) -> None:
    prog: Program[Any]
    with change_dir(tmp_path / "a") as path:
        with _write_logging_config(path / ".config" / "myprog.toml", "DEBUG"):
            prog = MyProgram("f")
            assert prog._config.logging.level == log_level_num("DEBUG")

    with change_dir(tmp_path / "b") as path:
        with _write_logging_config(path / "myprog.toml", "WARN"):
            prog = MyProgram("f", "--config", "myprog.toml")
            assert prog._config.logging.level == log_level_num("WARN")

    with change_dir(tmp_path / "c") as path:
        with pytest.raises(FileNotFoundError):
            MyProgram("f")

    prog = NoConfigProgram("qqq", "-i", "file.txt")
    assert prog._config is None


def test_no_command_program() -> None:
    NoCommandProgram()


def test_program_help() -> None:
    with pytest.raises(SystemExit) as e:
        NoConfigProgram("qqq", "-h")
    assert e.value.code == 0

    with pytest.raises(SystemExit) as e:
        NoCommandProgram("-h")
    assert e.value.code == 0


def test_program_arguments() -> None:
    prog: Program[Any]

    prog = NoConfigProgram("qqq", "-i", "file.txt")
    assert cast(QqqCommand, prog._command).in_file == Path("file.txt")
    assert cast(QqqCommand, prog._command).out_file is None

    prog = NoConfigProgram("qqq", "-i", "file.txt", "--out-file", "file.csv")
    assert cast(QqqCommand, prog._command).in_file == Path("file.txt")
    assert cast(QqqCommand, prog._command).out_file == Path("file.csv")

    prog = NoCommandProgram()
    assert prog.verbose is False

    prog = NoCommandProgram("--verbose")
    assert prog.verbose is True
