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

from logging import Logger, getLogger
from os import chdir
from pathlib import Path
from typing import Mapping, Optional, Sequence

import pytest
import toml
from typing_extensions import Final

from nasty_utils.config import Config, ConfigAttr, ConfigSection

_LOGGER: Final[Logger] = getLogger(__name__)


class MyInnerConfig(Config):
    host: str = ConfigAttr(default="localhost")
    port: int = ConfigAttr(default=9200)
    user: str = ConfigAttr(default="elastic")
    password: str = ConfigAttr(default="", secret=True)
    path: Path = ConfigAttr(deserializer=Path, serializer=str)


class MyConfig(Config):
    name: str = ConfigAttr(required=True)
    age: Optional[int] = ConfigAttr()

    first_list: Sequence[int] = ConfigAttr(required=True)
    second_list: Sequence[Path] = ConfigAttr(deserializer=Path, serializer=str)
    default_list: Sequence[str] = ConfigAttr(default=["foo", "bar"])
    nested_list: Sequence[Sequence[int]] = ConfigAttr(required=True)
    first_map: Mapping[str, int] = ConfigAttr(required=True)
    second_map: Mapping[str, Path] = ConfigAttr(
        default={"foo": Path("barr")}, deserializer=Path, serializer=str
    )
    nested_map: Mapping[str, Mapping[str, int]] = ConfigAttr(required=True)

    inner: MyInnerConfig = ConfigSection()


def test_config_load(tmp_path: Path) -> None:
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

    config = MyConfig.load(config_file)

    for line in str(config).splitlines():
        _LOGGER.debug(line)

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
    assert config.inner.password == "test-pass"
    assert config.inner.path == Path("test.path")

    config_file = tmp_path / "config2.toml"
    with config_file.open("w", encoding="UTF-8") as fout:
        toml.dump(config.serialize(), fout)

    config2 = MyConfig.load(config_file)
    assert config.serialize() == config2.serialize()


def test_find_file(tmp_path: Path) -> None:
    cwd = Path.cwd()
    try:
        chdir(tmp_path)

        for directory in [".", "myconfigdir"]:
            Path.mkdir(tmp_path / ".config" / directory, parents=True, exist_ok=True)

            for name in ["conf", "myconfig.toml"]:
                with pytest.raises(FileNotFoundError):
                    Config.find_file(name, directory)

                with (tmp_path / ".config" / directory / name).open(
                    "w", encoding="UTF-8"
                ):
                    pass

        assert Config.find_file(name, directory)
    finally:
        chdir(cwd)
