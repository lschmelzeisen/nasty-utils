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

from pathlib import Path
from typing import Optional

from pydantic import ValidationError
from pytest import raises

from nasty_utils import Argument, ArgumentGroup, Command, Program, Settings

_MY_GROUP = ArgumentGroup(name="My Group", description="my group desc")


class ArgProgram(Program):
    class Config:
        title = "myprog"
        version = "0.0.0"
        description = "My program description."

    foo: str = "foo"
    bar: int = Argument(5, short_alias="b", description="my arg desc", group=_MY_GROUP)
    baz: int = Argument(alias="baz-alias", metavar="VALUE", group=_MY_GROUP)
    qux: bool


def test_arg_program() -> None:
    with raises(SystemExit):  # Prints version string (for manual inspection).
        ArgProgram.init("-v")

    with raises(SystemExit):  # Print help message (for manual inspection).
        ArgProgram.init("-h")

    with raises(SystemExit):  # Argument baz-alias required.
        ArgProgram.init()

    args = ("--baz-alias", "10")
    prog = ArgProgram.init(*args)
    assert tuple(prog.raw_args) == args
    assert prog.foo == "foo"
    assert prog.bar == 5
    assert prog.baz == 10
    assert not prog.qux

    with raises(SystemExit):  # Argument baz-alias validation failed.
        ArgProgram.init("--baz-alias", "ten")

    args = ("--foo", "fool", "-b", "6", "--baz-alias", "15", "--qux")
    prog = ArgProgram.init(*args)
    assert tuple(prog.raw_args) == args
    assert prog.foo == "fool"
    assert prog.bar == 6
    assert prog.baz == 15
    assert prog.qux


class ArgCommand(Command):
    foo: int


class ArgCommandProgram(Program):
    class Config:
        commands = [ArgCommand]


def test_arg_command_program() -> None:
    with raises(SystemExit):  # Argument foo required.
        ArgCommandProgram.init("MyCommand")

    prog = ArgCommandProgram.init(ArgCommand.__name__, "--foo", "3")
    assert isinstance(prog.command, ArgCommand)
    assert prog.command.foo == 3

    with raises(SystemExit):  # Argument foo validation error.
        ArgCommandProgram.init(ArgCommand.__name__, "--foo", "three")


class FooCommand(Command):
    prog: "SubcommandProgram"

    class Config:
        title = "foo"
        aliases = ("f",)


class BarCommand(Command):
    class Config:
        title = "bar"
        aliases = ("b",)


class BazCommand(Command):
    class Config:
        title = "baz"
        aliases = ("b",)


class QuxCommand(Command):
    class Config:
        title = "qux"
        aliases = ("q", "u")


class SubcommandProgram(Program):
    class Config:
        commands = {
            FooCommand: Command,
            BarCommand: Command,
            BazCommand: BarCommand,
            QuxCommand: BarCommand,
        }


FooCommand.update_forward_refs()


def test_subcommand_program() -> None:
    with raises(SystemExit):  # Print help message (for manual inspection).
        SubcommandProgram.init("-h")

    with raises(SystemExit):  # Print help message (for manual inspection).
        SubcommandProgram.init("foo", "-h")

    with raises(SystemExit):  # Print help message (for manual inspection).
        SubcommandProgram.init("bar", "-h")

    with raises(SystemExit):  # Command required.
        SubcommandProgram.init()

    prog = SubcommandProgram.init("foo")
    assert isinstance(prog.command, FooCommand)

    with raises(SystemExit):  # Subcommand required.
        SubcommandProgram.init("bar")

    prog = SubcommandProgram.init("bar", "baz")
    assert isinstance(prog.command, BazCommand)

    prog = SubcommandProgram.init("bar", "qux")
    assert isinstance(prog.command, QuxCommand)


class ParenCommand(Command):
    in_file: Path
    out_file: Optional[Path] = None


class ChildCommand(ParenCommand):
    test_file: Path


class SuclassCommandProgram(Program):
    class Config:
        commands = [ParenCommand, ChildCommand]


def test_subclass_command_program() -> None:
    prog = SuclassCommandProgram.init(ParenCommand.__name__, "--in_file", "in.file")
    assert isinstance(prog.command, ParenCommand)
    assert prog.command.in_file == Path("in.file")
    assert prog.command.out_file is None

    with raises(SystemExit):  # Argument in_file missing.
        SuclassCommandProgram.init(ChildCommand.__name__, "--test_file", "test.file")

    prog = SuclassCommandProgram.init(
        ChildCommand.__name__, "--in_file", "in.file", "--test_file", "test.file"
    )
    assert isinstance(prog.command, ChildCommand)
    assert prog.command.in_file == Path("in.file")
    assert prog.command.out_file is None
    assert prog.command.test_file == Path("test.file")


class MySettings(Settings):
    n: float


class MySettingsProgram(Program):
    settings: MySettings


def test_my_settings_program(tmp_cwd: Path) -> None:
    with raises(FileNotFoundError):  # Settings file does not exist.
        MySettingsProgram.init()

    settings_dir = Path(".config")
    settings_dir.mkdir()

    settings_file = settings_dir / (MySettingsProgram.__name__ + ".toml")
    settings_file.touch()

    with raises(ValidationError):  # Settings contents are required.
        MySettingsProgram.init()

    settings_file.write_text("n = 3.14", encoding="UTF-8")

    prog = MySettingsProgram.init()
    assert isinstance(prog.settings, MySettings)
    assert prog.settings.n == 3.14

    settings_file = Path("alt-settings.toml")
    settings_file.write_text("n = 10.0", encoding="UTF-8")

    prog = MySettingsProgram.init("--config", str(settings_file))
    assert isinstance(prog.settings, MySettings)
    assert prog.settings.n == 10.0
