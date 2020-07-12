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
from os import chdir
from pathlib import Path
from typing import Mapping, Optional, Sequence

import pytest
from pydantic import SecretStr

from nasty_utils import ColoredBraceStyleAdapter, Config

_LOGGER = ColoredBraceStyleAdapter(getLogger(__name__))


def test_find_config_file(tmp_path: Path) -> None:
    cwd = Path.cwd()
    try:
        chdir(tmp_path)

        for directory in [".", "myconfigdir"]:
            Path.mkdir(tmp_path / ".config" / directory, parents=True, exist_ok=True)

            for name in ["conf", "myconfig.toml"]:
                with pytest.raises(FileNotFoundError):
                    Config.find_config_file(name, directory)

                with (tmp_path / ".config" / directory / name).open(
                    "w", encoding="UTF-8"
                ):
                    pass

                assert Config.find_config_file(name, directory)
    finally:
        chdir(cwd)


class MyInnerConfig(Config):
    host: str = "localhost"
    port: int = 9200
    user: str = "elastic"
    password: SecretStr = SecretStr("")
    path: Optional[Path] = None


class MyConfig(Config):
    name: str
    age: Optional[int] = None

    first_list: Sequence[int]
    second_list: Sequence[Path] = [Path("foo")]
    default_list: Sequence[str] = ["foo", "bar"]
    nested_list: Sequence[Sequence[int]]
    first_map: Mapping[str, int]
    second_map: Mapping[str, Path] = {"foo": Path("barr")}
    nested_map: Mapping[str, Mapping[str, int]]

    inner: MyInnerConfig


def test_load_from_config_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    with config_file.open("w", encoding="UTF-8") as fout:
        fout.write(
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
            """
        )

    config = MyConfig.load_from_config_file(config_file)

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


class InheritingConfig(MyConfig):
    foo: str


def test_inheriting_config() -> None:
    config = InheritingConfig.load_from_str(
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


class PathConfig(Config):
    path: Path


def test_path_config(tmp_path: Path) -> None:
    config_contents = """
        path = "${CONFIG_FILE}/test.path"
    """

    with pytest.raises(ValueError):
        PathConfig.load_from_str(config_contents)

    cwd = Path.cwd()
    try:
        chdir(tmp_path)

        Path.mkdir(tmp_path / ".config")
        with (tmp_path / ".config" / "config.toml").open("w", encoding="UTF-8") as fout:
            fout.write(config_contents)

        config = PathConfig.find_and_load_from_config_file("config.toml")
        _LOGGER.debug("Path when loading from file: '{}'", config.path)
        assert config.path.name == "test.path"
        assert config.path.parent.name == ".config"
        assert config.path.parent.parent.name == tmp_path.name
    finally:
        chdir(cwd)


class InnerOptionalConfig(Config):
    inner: Optional[MyInnerConfig] = None


def test_inner_optional_config() -> None:
    config = InnerOptionalConfig.load_from_str(
        """
        [inner]
        host = "localhost"
        """
    )
    assert config.inner is not None and config.inner.host == "localhost"

    config = InnerOptionalConfig.load_from_str("")
    assert config.inner is None


class InnerSequenceConfig(Config):
    inner: Sequence[MyInnerConfig] = []


def test_inner_sequence_config() -> None:
    config = InnerSequenceConfig.load_from_str(
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

    config = InnerSequenceConfig.load_from_str("")
    assert len(config.inner) == 0
