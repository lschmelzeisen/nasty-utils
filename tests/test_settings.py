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

from logging import getLogger
from pathlib import Path
from typing import Mapping, Optional, Sequence

from pydantic import SecretStr
from pytest import raises

from nasty_utils import ColoredBraceStyleAdapter, Settings, SettingsConfig

_LOGGER = ColoredBraceStyleAdapter(getLogger(__name__))


def test_find_settings_file(tmp_cwd: Path) -> None:
    for directory in [Path("."), Path("mysettingsdir")]:
        settings_dir = Path(".config") / directory
        settings_dir.mkdir(exist_ok=True)

        for name in [Path("conf"), Path("mysettings.toml")]:

            class FindSettings(Settings):
                class Config(SettingsConfig):
                    search_path = directory / name

            with raises(FileNotFoundError):
                FindSettings.find_settings_file()

            (settings_dir / name).touch()

            assert FindSettings.find_settings_file()


class MyInnerSettings(Settings):
    host: str = "localhost"
    port: int = 9200
    user: str = "elastic"
    password: SecretStr = SecretStr("")
    path: Optional[Path] = None


class MySettings(Settings):
    name: str
    age: Optional[int] = None

    first_list: Sequence[int]
    second_list: Sequence[Path] = [Path("foo")]
    default_list: Sequence[str] = ["foo", "bar"]
    nested_list: Sequence[Sequence[int]]
    first_map: Mapping[str, int]
    second_map: Mapping[str, Path] = {"foo": Path("barr")}
    nested_map: Mapping[str, Mapping[str, int]]

    inner: MyInnerSettings


def test_load_from_settings_file(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.toml"
    settings_file.write_text(
        """
            name = "test"
            first_list = [ 1, 2, 3 ]
            second_list = [ "1", "2", "3" ]
            nested_list = [ [ 1, 2, 3 ], [ 4, 5, 6 ] ]
            first_map = { one = 1, two = 2 }
            second_map = { one = "1", two = "2" }
            nested_map = { one = { one = 11 }, two = { one = 21, two = 22 }}

            [inner]
            host = "localhost"
            port = 9200
            user = "test-user"
            password = "test-pass"
            path = "test.path"
        """,
        encoding="UTf-8",
    )

    settings = MySettings.load_from_settings_file(settings_file)

    assert settings.name == "test"
    assert settings.age is None

    assert settings.first_list == [1, 2, 3]
    assert settings.second_list == [Path("1"), Path("2"), Path("3")]
    assert settings.default_list == ["foo", "bar"]
    assert settings.nested_list == [[1, 2, 3], [4, 5, 6]]
    assert settings.first_map == {"one": 1, "two": 2}
    assert settings.second_map == {"one": Path("1"), "two": Path("2")}
    assert settings.nested_map == {"one": {"one": 11}, "two": {"one": 21, "two": 22}}

    assert settings.inner.host == "localhost"
    assert settings.inner.port == 9200
    assert settings.inner.user == "test-user"
    assert str(settings.inner.password) == "**********"
    assert settings.inner.password.get_secret_value() == "test-pass"
    assert settings.inner.path is not None and settings.inner.path.name == "test.path"


class InheritingSettings(MySettings):
    foo: str


def test_inheriting_settings() -> None:
    settings = InheritingSettings.load_from_str(
        """
        foo = "bar"

        name = "test"
        first_list = [ 1, 2, 3 ]
        nested_list = [ [ 1, 2, 3 ], [ 4, 5, 6 ] ]
        first_map = { one = 1, two = 2 }
        nested_map = { one = { one = 11 }, two = { one = 21, two = 22 }}

        [inner]
        """
    )
    assert settings.name == "test"
    assert settings.foo == "bar"


class PathSettings(Settings):
    class Config(SettingsConfig):
        search_path = Path("settings.toml")

    path: Path


def test_path_settings(tmp_cwd: Path) -> None:
    settings_contents = """
        path = "{SETTINGS_DIR}/test.path"
    """

    with raises(ValueError):
        PathSettings.load_from_str(settings_contents)

    settings_dir = Path(".config")
    settings_dir.mkdir()
    (settings_dir / "settings.toml").write_text(settings_contents, encoding="UTF-8")

    settings = PathSettings.find_and_load_from_settings_file()
    assert settings.path.name == "test.path"
    assert settings.path.parent.name == ".config"
    assert settings.path.parent.parent.resolve() == tmp_cwd


class InnerOptionalSettings(Settings):
    inner: Optional[MyInnerSettings] = None


def test_inner_optional_settings() -> None:
    settings = InnerOptionalSettings.load_from_str(
        """
        [inner]
        host = "localhost"
        """
    )
    assert settings.inner is not None and settings.inner.host == "localhost"

    settings = InnerOptionalSettings.load_from_str("")
    assert settings.inner is None


class InnerSequenceSettings(Settings):
    inner: Sequence[MyInnerSettings] = []


def test_inner_sequence_settings() -> None:
    settings = InnerSequenceSettings.load_from_str(
        """
        [[inner]]
        host = "localhost1"

        [[inner]]
        host = "localhost2"

        [[inner]]
        host = "localhost3"
        """
    )
    assert len(settings.inner) == 3
    for i in range(3):
        assert settings.inner[i].host == f"localhost{i+1}"

    settings = InnerSequenceSettings.load_from_str("")
    assert len(settings.inner) == 0


class CanNotDefaultSettings(Settings):
    class Config(SettingsConfig):
        search_path = Path("settings.toml")

    foo: int


class CanDefaultSettings(Settings):
    class Config(SettingsConfig):
        search_path = Path("settings.toml")

    foo: int = 5


def test_can_default_settings() -> None:
    assert not CanNotDefaultSettings.can_default()
    with raises(FileNotFoundError):
        CanNotDefaultSettings.find_and_load_from_settings_file()

    assert CanDefaultSettings.can_default()
    settings = CanDefaultSettings.find_and_load_from_settings_file()
    assert settings.foo == 5
