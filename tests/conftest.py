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


from os import chdir
from pathlib import Path
from typing import Iterator

from _pytest.config import Config
from pytest import fixture

from nasty_utils import LoggingSettings


def pytest_configure(config: Config) -> None:
    LoggingSettings.setup_pytest_logging(config)


@fixture
def tmp_cwd(tmp_path: Path) -> Iterator[Path]:
    cwd = Path.cwd()
    try:
        chdir(tmp_path)
        yield tmp_path
    finally:
        chdir(cwd)
