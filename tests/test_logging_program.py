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
from multiprocessing import Process
from pathlib import Path
from time import sleep
from typing import Iterator, cast

from overrides import overrides
from pytest import mark
from tqdm import tqdm

import nasty_utils
from nasty_utils import (
    Argument,
    ColoredBraceStyleAdapter,
    Command,
    CommandConfig,
    LoggingSettings,
    Program,
    ProgramConfig,
)

_LOGGER = ColoredBraceStyleAdapter(getLogger(__name__))


class MyCommand(Command):
    class Config(CommandConfig):
        title = "my"
        description = "Description of my command."

    arg: int = Argument(0, short_alias="a", description="Description of my arg.")

    @overrides
    def run(self) -> None:
        _LOGGER.debug("before")

        for i in tqdm(cast(Iterator[int], range(3)), desc="Epoch"):
            _LOGGER.debug("foo {} bar".format(i))
            for _ in tqdm(
                cast(Iterator[int], range(30)), desc="Batch {}".format(i), leave=False
            ):
                sleep(0.01)

        _LOGGER.debug("after")
        _LOGGER.info("arg: '{}' {{{}}}", self.arg, bool(self.arg))

        _LOGGER.debug("debug")
        _LOGGER.info("info")
        _LOGGER.warning("warning")
        _LOGGER.error("error")
        _LOGGER.critical("critical")


class MyProgram(Program):
    class Config(ProgramConfig):
        title = "myprog"
        version = nasty_utils.__version__
        description = "Description of my program."
        commands = [MyCommand]

    settings: LoggingSettings


@mark.skip
def test_logging() -> None:
    settings_file = (
        Path(nasty_utils.__file__).parent.parent.parent / ".config" / "nasty.toml"
    )
    p = Process(
        target=lambda: MyProgram.init(
            "my", "--config", str(settings_file), "-a", "5"
        ).run()
    )
    p.start()
    p.join()


if __name__ == "__main__":
    test_logging()
