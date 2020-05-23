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
from typing import Any, Callable, Iterator, Optional, cast

import pytest
from _pytest.capture import CaptureFixture
from overrides import overrides
from typing_extensions import Final

from nasty_utils import (
    Argument,
    ArgumentError,
    ArgumentGroup,
    Command,
    CommandMeta,
    Flag,
    LoggingConfig,
    Program,
    ProgramMeta,
    log_level_num,
)
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
    _in_out_group = ArgumentGroup(
        name="Input/Output", desc="Input and output arguments."
    )
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


class InheritingCommand(QqqCommand):
    test_file: Path = Argument(
        required=True,
        name="test-file",
        metavar="File",
        desc="Test file",
        deserializer=Path,
    )

    @classmethod
    @overrides
    def meta(cls) -> CommandMeta:
        return CommandMeta(name="inheriting", desc="inheriting desc")


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
            command_hierarchy={Command: [QqqCommand, InheritingCommand]},
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


class ErrorProgram(Program[None]):
    digit: int = Argument(
        name="digit",
        desc="digit desc",
        metavar="DIGIT",
        required=True,
        deserializer=int,
    )

    @classmethod
    @overrides
    def meta(cls) -> ProgramMeta[None]:
        return ProgramMeta(
            name="errorprog",
            version="0.1.0",
            desc="errorprog desc",
            config_type=type(None),
            config_file="",
            config_dir="",
            command_hierarchy=None,
        )

    def run(self) -> None:
        if not 0 < self.digit < 10:
            raise ArgumentError(f"Expected a digit (0-9), received: {self.digit}")


class ErrorCommand(Command[None]):
    digit: int = Argument(
        name="digit",
        desc="digit desc",
        metavar="DIGIT",
        required=True,
        deserializer=int,
    )

    @classmethod
    @overrides
    def meta(cls) -> CommandMeta:
        return CommandMeta(name="errorcomm", desc="errorcomm desc")

    def run(self) -> None:
        if not 0 < self.digit < 10:
            raise ArgumentError(f"Expected a digit (0-9), received: {self.digit}")


class ErrorCommandProgram(Program[None]):
    @classmethod
    @overrides
    def meta(cls) -> ProgramMeta[None]:
        return ProgramMeta(
            name="errorprog",
            version="0.1.0",
            desc="errorprog desc",
            config_type=type(None),
            config_file="",
            config_dir="",
            command_hierarchy={Command: [ErrorCommand]},
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
            assert prog.config.logging.level == log_level_num("DEBUG")

    with change_dir(tmp_path / "b") as path:
        with _write_logging_config(path / "myprog.toml", "WARN"):
            prog = MyProgram("f", "--config", "myprog.toml")
            assert prog.config.logging.level == log_level_num("WARN")

    with change_dir(tmp_path / "c"):
        with pytest.raises(FileNotFoundError):
            MyProgram("f")

    prog = NoConfigProgram("qqq", "-i", "file.txt")
    assert prog.config is None


def test_no_command_program() -> None:
    NoCommandProgram()


def test_program_help(capsys: CaptureFixture) -> None:
    # This test doesn't really assert anything. Its goal is to produce nice logging
    # output to manually look at.

    def _log_capsys() -> None:
        for line in capsys.readouterr().out.splitlines():
            _LOGGER.info(line)

    def _log_separator() -> None:
        _LOGGER.info(80 * "-")

    with pytest.raises(SystemExit) as e:
        NoConfigProgram("-h")
    assert e.value.code == 0

    _log_capsys()
    _log_separator()

    with pytest.raises(SystemExit) as e:
        NoConfigProgram("inheriting", "-h")
    assert e.value.code == 0

    _log_capsys()
    _log_separator()

    with pytest.raises(SystemExit) as e:
        NoCommandProgram("-h")
    assert e.value.code == 0

    _log_capsys()


def test_program_arguments() -> None:
    prog: Program[Any]

    prog = NoConfigProgram("qqq", "-i", "file.txt")
    assert cast(QqqCommand, prog.command).in_file == Path("file.txt")
    assert cast(QqqCommand, prog.command).out_file is None

    prog = NoConfigProgram("qqq", "-i", "file.txt", "--out-file", "file.csv")
    assert cast(QqqCommand, prog.command).in_file == Path("file.txt")
    assert cast(QqqCommand, prog.command).out_file == Path("file.csv")

    with pytest.raises(SystemExit) as e:
        # Note that this will log an error to stderr. This is to be expected.
        NoConfigProgram("inheriting", "-i", "file.txt", "--out-file", "file.csv")
    assert e.value.code == 2  # argparse exit code in case of command failure.

    prog = NoConfigProgram(
        "inheriting",
        "-i",
        "file.txt",
        "--out-file",
        "file.csv",
        "--test-file",
        "file.test",
    )
    assert cast(InheritingCommand, prog.command).in_file == Path("file.txt")
    assert cast(InheritingCommand, prog.command).out_file == Path("file.csv")
    assert cast(InheritingCommand, prog.command).test_file == Path("file.test")

    prog = NoCommandProgram()
    assert prog.verbose is False

    prog = NoCommandProgram("--verbose")
    assert prog.verbose is True


def test_argument_error(capsys: CaptureFixture) -> None:
    def _assert_outerr(callback: Callable[[], Program[Any]], msg_part: str) -> None:
        with pytest.raises(SystemExit) as e:
            callback()
        assert e.value.code == 2  # argparse exit code in case of command failure.

        outerr = capsys.readouterr()
        assert not outerr.out

        assert msg_part in outerr.err

        for line in outerr.err.splitlines():
            _LOGGER.info(line)

    prog: Program[Any]

    _assert_outerr(lambda: ErrorProgram(), f"{ErrorProgram.meta().name}: error")

    prog = ErrorProgram("--digit", "1")
    assert prog.digit == 1

    _assert_outerr(
        lambda: ErrorProgram("--digit", "10"), f"{ErrorProgram.meta().name}: error"
    )

    _assert_outerr(
        lambda: ErrorCommandProgram("errorcomm"),
        f"{ErrorCommandProgram.meta().name} {ErrorCommand.meta().name}: error",
    )

    prog = ErrorCommandProgram("errorcomm", "--digit", "1")
    assert cast(ErrorCommand, prog.command).digit == 1

    _assert_outerr(
        lambda: ErrorCommandProgram("errorcomm", "--digit", "10"),
        f"{ErrorCommandProgram.meta().name} {ErrorCommand.meta().name}: error",
    )
