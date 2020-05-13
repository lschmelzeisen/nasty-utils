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

from nasty_utils.config import Config, ConfigAttr, ConfigSection


class TestInnerConfig(Config):
    host: str = ConfigAttr(default="localhost")
    port: int = ConfigAttr(default=9200)
    user: str = ConfigAttr(default="elastic")
    password: str = ConfigAttr(default="", secret=True)
    path: Path = ConfigAttr(converter=Path)


class TestConfig(Config):
    name: str = ConfigAttr(required=True)
    inner: TestInnerConfig = ConfigSection()


def test_config(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    with config_file.open("w", encoding="UTF-8") as fout:
        fout.write(
            """
            name = "test"
            
            [inner]
            host = "localhost"
            port = 9200
            user = "test-user"
            password = "test-pass"
            path = "test.path"
            """
        )

    config = TestConfig.load(config_file)
    assert config.name == "test"
    assert config.inner.host == "localhost"
    assert config.inner.port == 9200
    assert config.inner.user == "test-user"
    assert config.inner.password == "test-pass"
    assert config.inner.path == Path("test.path")
