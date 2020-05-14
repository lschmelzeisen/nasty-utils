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
from typing import Any, Iterator

import pytest
from overrides import overrides
from typing_extensions import Final

from nasty_utils.logging import LoggingConfig, _level_num
from nasty_utils.program import Command, CommandMeta, Program, ProgramMeta
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
    @classmethod
    @overrides
    def meta(cls) -> CommandMeta:
        return CommandMeta(name="qqq", aliases=["q"], desc="qqq desc")


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


class NoCommandProgramm(Program[None]):
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
            assert prog._config.logging.level == _level_num("DEBUG")

    with change_dir(tmp_path / "b") as path:
        with _write_logging_config(path / "myprog.toml", "WARN"):
            prog = MyProgram("f", "--config", "myprog.toml")
            assert prog._config.logging.level == _level_num("WARN")

    with change_dir(tmp_path / "c") as path:
        with pytest.raises(FileNotFoundError):
            MyProgram("f")

    prog = NoConfigProgram("q")
    assert prog._config is None


def test_no_command_program() -> None:
    NoCommandProgramm()
