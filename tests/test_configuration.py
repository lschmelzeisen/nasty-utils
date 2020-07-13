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

from nasty_utils import ColoredBraceStyleAdapter, Configuration

_LOGGER = ColoredBraceStyleAdapter(getLogger(__name__))


def test_find_config_file(tmp_cwd: Path) -> None:
    for directory in [Path("."), Path("myconfigdir")]:
        config_dir = Path(".config") / directory
        config_dir.mkdir(exist_ok=True)

        for name in [Path("conf"), Path("myconfig.toml")]:
            with raises(FileNotFoundError):
                Configuration.find_config_file(directory / name)

            (config_dir / name).touch()

            assert Configuration.find_config_file(directory / name)


class MyInnerConfiguration(Configuration):
    host: str = "localhost"
    port: int = 9200
    user: str = "elastic"
    password: SecretStr = SecretStr("")
    path: Optional[Path] = None


class MyConfiguration(Configuration):
    name: str
    age: Optional[int] = None

    first_list: Sequence[int]
    second_list: Sequence[Path] = [Path("foo")]
    default_list: Sequence[str] = ["foo", "bar"]
    nested_list: Sequence[Sequence[int]]
    first_map: Mapping[str, int]
    second_map: Mapping[str, Path] = {"foo": Path("barr")}
    nested_map: Mapping[str, Mapping[str, int]]

    inner: MyInnerConfiguration


def test_load_from_config_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
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

    config = MyConfiguration.load_from_config_file(config_file)

    assert config.name == "test"
    assert config.age is None

    assert config.first_list == [1, 2, 3]
    assert config.second_list == [Path("1"), Path("2"), Path("3")]
    assert config.default_list == ["foo", "bar"]
    assert config.nested_list == [[1, 2, 3], [4, 5, 6]]
    assert config.first_map == {"one": 1, "two": 2}
    assert config.second_map == {"one": Path("1"), "two": Path("2")}
    assert config.nested_map == {"one": {"one": 11}, "two": {"one": 21, "two": 22}}

    assert config.inner.host == "localhost"
    assert config.inner.port == 9200
    assert config.inner.user == "test-user"
    assert str(config.inner.password) == "**********"
    assert config.inner.password.get_secret_value() == "test-pass"
    assert config.inner.path is not None and config.inner.path.name == "test.path"


class InheritingConfiguration(MyConfiguration):
    foo: str


def test_inheriting_configuration() -> None:
    config = InheritingConfiguration.load_from_str(
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
    assert config.name == "test"
    assert config.foo == "bar"


class PathConfiguration(Configuration):
    path: Path


def test_path_configuration(tmp_cwd: Path) -> None:
    config_contents = """
        path = "{CONFIG_FILE}/test.path"
    """

    with raises(ValueError):
        PathConfiguration.load_from_str(config_contents)

    config_dir = Path(".config")
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(config_contents, encoding="UTF-8")

    config = PathConfiguration.find_and_load_from_config_file(Path("config.toml"))
    assert config.path.name == "test.path"
    assert config.path.parent.name == ".config"
    assert config.path.parent.parent.resolve() == tmp_cwd


class InnerOptionalConfiguration(Configuration):
    inner: Optional[MyInnerConfiguration] = None


def test_inner_optional_configuration() -> None:
    config = InnerOptionalConfiguration.load_from_str(
        """
        [inner]
        host = "localhost"
        """
    )
    assert config.inner is not None and config.inner.host == "localhost"

    config = InnerOptionalConfiguration.load_from_str("")
    assert config.inner is None


class InnerSequenceConfiguration(Configuration):
    inner: Sequence[MyInnerConfiguration] = []


def test_inner_sequence_configuration() -> None:
    config = InnerSequenceConfiguration.load_from_str(
        """
        [[inner]]
        host = "localhost1"

        [[inner]]
        host = "localhost2"

        [[inner]]
        host = "localhost3"
        """
    )
    assert len(config.inner) == 3
    for i in range(3):
        assert config.inner[i].host == f"localhost{i+1}"

    config = InnerSequenceConfiguration.load_from_str("")
    assert len(config.inner) == 0


class CanNotDefaultConfiguration(Configuration):
    foo: int


class CanDefaultConfiguration(Configuration):
    foo: int = 5


def test_can_default_configuration() -> None:
    path = Path("config.toml")

    assert not CanNotDefaultConfiguration.can_default()
    with raises(FileNotFoundError):
        CanNotDefaultConfiguration.find_and_load_from_config_file(path)

    assert CanDefaultConfiguration.can_default()
    config = CanDefaultConfiguration.find_and_load_from_config_file(path)
    assert config.foo == 5
