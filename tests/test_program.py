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

from _pytest.capture import CaptureFixture
from overrides import overrides
from pydantic import ValidationError
from pytest import raises

from nasty_utils import (
    Argument,
    ArgumentGroup,
    Program,
    ProgramConfig,
    Settings,
    SettingsConfig,
)

_MY_GROUP = ArgumentGroup(name="My Group", description="my group desc")


class ArgParsingProgram(Program):
    class Config(ProgramConfig):
        title = "myprog"
        version = "0.0.0"
        description = "My program description."

    foo: str = "foo"
    bar: int = Argument(5, short_alias="b", description="my arg desc", group=_MY_GROUP)
    baz: int = Argument(alias="baz-alias", metavar="VALUE", group=_MY_GROUP)
    qux: bool


class ChildArgParsingProgram(ArgParsingProgram):
    @overrides
    def run(self) -> None:
        print(self.bar * self.baz)  # noqa: T001


def test_arg_parsing(capsys: CaptureFixture) -> None:
    with raises(SystemExit):  # Prints version string (for manual inspection).
        ArgParsingProgram.init("-v")

    with raises(SystemExit):  # Print help message (for manual inspection).
        ArgParsingProgram.init("-h")

    with raises(SystemExit):  # Argument baz-alias required.
        ArgParsingProgram.init()

    capsys.readouterr()
    args = ("--baz-alias", "10")
    prog = ArgParsingProgram.init(*args)
    assert tuple(prog.raw_args) == args
    assert isinstance(prog, ArgParsingProgram)
    assert prog.foo == "foo"
    assert prog.bar == 5
    assert prog.baz == 10
    assert not prog.qux
    prog.run()
    assert capsys.readouterr().out == ""

    with raises(SystemExit):  # Argument baz-alias validation failed.
        ArgParsingProgram.init("--baz-alias", "ten")

    capsys.readouterr()
    args = ("--foo", "fool", "-b", "6", "--baz-alias", "15", "--qux")
    prog = ChildArgParsingProgram.init(*args)
    assert tuple(prog.raw_args) == args
    assert isinstance(prog, ChildArgParsingProgram)
    assert prog.foo == "fool"
    assert prog.bar == 6
    assert prog.baz == 15
    assert prog.qux
    prog.run()
    assert capsys.readouterr().out == "90\n"


class ParentProgram(Program):
    in_file: Path
    out_file: Optional[Path] = None

    @overrides
    def run(self) -> None:
        print(ParentProgram.__name__)  # noqa: T001


class ChildProgram(ParentProgram):
    test_file: Path

    @overrides
    def run(self) -> None:
        print(ChildProgram.__name__)  # noqa: T001


class InheritedSubprogramsProgram(Program):
    class Config(ProgramConfig):
        subprograms = (ParentProgram, ChildProgram)


def test_inherited_subprograms(capsys: CaptureFixture) -> None:
    with raises(SystemExit):  # Command required.
        InheritedSubprogramsProgram.init()

    with raises(SystemExit):  # Argument in_file required.
        ParentProgram.init(ParentProgram.title())

    prog = InheritedSubprogramsProgram.init(
        ParentProgram.__name__, "--in_file", "in.file"
    )
    assert isinstance(prog, ParentProgram)
    assert prog.in_file == Path("in.file")
    assert prog.out_file is None
    prog.run()
    assert capsys.readouterr().out == ParentProgram.__name__ + "\n"

    with raises(SystemExit):  # Argument in_file missing.
        InheritedSubprogramsProgram.init(
            ChildProgram.__name__, "--test_file", "test.file"
        )

    prog = InheritedSubprogramsProgram.init(
        ChildProgram.__name__, "--in_file", "in.file", "--test_file", "test.file"
    )
    assert isinstance(prog, ChildProgram)
    assert prog.in_file == Path("in.file")
    assert prog.out_file is None
    assert prog.test_file == Path("test.file")
    prog.run()
    assert capsys.readouterr().out == ChildProgram.__name__ + "\n"


class FooProgram(Program):
    class Config(ProgramConfig):
        title = "foo"
        aliases = ("f",)


class BazProgram(Program):
    class Config(ProgramConfig):
        title = "baz"
        aliases = ("b",)


class QuxProgram(Program):
    class Config(ProgramConfig):
        title = "qux"
        aliases = ("q", "u")


class BarProgram(Program):
    class Config(ProgramConfig):
        title = "bar"
        aliases = ("b",)
        subprograms = (BazProgram, QuxProgram)


class NestedSubprogramsProgram(Program):
    class Config(ProgramConfig):
        subprograms = (FooProgram, BarProgram)


def test_nested_subprograms() -> None:
    with raises(SystemExit):  # Print help message (for manual inspection).
        NestedSubprogramsProgram.init("-h")

    with raises(SystemExit):  # Print help message (for manual inspection).
        NestedSubprogramsProgram.init("foo", "-h")

    with raises(SystemExit):  # Print help message (for manual inspection).
        NestedSubprogramsProgram.init("bar", "-h")

    with raises(SystemExit):  # Command required.
        NestedSubprogramsProgram.init()

    prog = NestedSubprogramsProgram.init("foo")
    assert isinstance(prog, FooProgram)

    with raises(SystemExit):  # Subcommand required.
        NestedSubprogramsProgram.init("bar")

    prog = NestedSubprogramsProgram.init("bar", "baz")
    assert isinstance(prog, BazProgram)

    prog = NestedSubprogramsProgram.init("bar", "q")
    assert isinstance(prog, QuxProgram)

    prog = NestedSubprogramsProgram.init("bar", "u")
    assert isinstance(prog, QuxProgram)


class FooSettings(Settings):
    class Config(SettingsConfig):
        search_path = Path("foo.toml")

    n: float


class SettingsProgram(Program):
    settings: FooSettings


def test_settings(tmp_cwd: Path) -> None:
    with raises(FileNotFoundError):  # Settings file does not exist.
        SettingsProgram.init()

    settings_dir = Path(".config")
    settings_dir.mkdir()

    settings_file = settings_dir / "foo.toml"
    settings_file.touch()

    with raises(ValidationError):  # Settings contents are required.
        SettingsProgram.init()

    settings_file.write_text("n = 3.14", encoding="UTF-8")

    prog = SettingsProgram.init()
    assert isinstance(prog, SettingsProgram)
    assert isinstance(prog.settings, FooSettings)
    assert prog.settings.settings_file
    assert prog.settings.settings_file.resolve() == settings_file.resolve()
    assert prog.settings.n == 3.14

    settings_file = Path("overwrite.toml")
    settings_file.write_text("n = 10.0", encoding="UTF-8")

    prog = SettingsProgram.init("--settings", str(settings_file))
    assert isinstance(prog, SettingsProgram)
    assert isinstance(prog.settings, FooSettings)
    assert prog.settings.settings_file
    assert prog.settings.settings_file.resolve() == settings_file.resolve()
    assert prog.settings.n == 10.0


class BarSettings(Settings):
    m: int


class MultipleSettingsProgram(Program):
    foo: FooSettings
    bar: BarSettings = Argument(
        short_alias="b", description="Overwrite bar setting path."
    )

    @overrides
    def run(self) -> None:
        print(self.foo.n * self.bar.m)  # noqa: T001


def test_multiple_settings(tmp_path: Path, capsys: CaptureFixture) -> None:
    with raises(SystemExit):
        MultipleSettingsProgram.init("-h")

    foo_settings_file = tmp_path / "my-foo.toml"
    foo_settings_file.write_text("n = 3.5", encoding="UTF-8")

    bar_settings_file = tmp_path / "my-bar.toml"
    bar_settings_file.write_text("m = 4", encoding="UTF-8")

    capsys.readouterr()
    prog = MultipleSettingsProgram.init(
        "--foo", str(foo_settings_file), "-b", str(bar_settings_file)
    )
    assert isinstance(prog, MultipleSettingsProgram)
    assert isinstance(prog.foo, FooSettings)
    assert prog.foo.settings_file
    assert prog.foo.settings_file.resolve() == foo_settings_file.resolve()
    assert prog.foo.n == 3.5
    assert isinstance(prog.bar, BarSettings)
    assert prog.bar.settings_file
    assert prog.bar.settings_file.resolve() == bar_settings_file.resolve()
    assert prog.bar.m == 4
    prog.run()
    assert capsys.readouterr().out == "14.0\n"
