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

import argparse
from typing import Generic, Optional, Sequence, TypeVar

from nasty_utils.config import Config

_T_Config = TypeVar("_T_Config", bound=Optional[Config])


class CommandMeta:
    def __init__(
        self, *, name: str, aliases: Optional[Sequence[str]] = None, desc: str
    ):
        self.name = name
        self.aliases = aliases
        self.desc = desc


class Command(Generic[_T_Config]):
    @classmethod
    def meta(cls) -> CommandMeta:
        raise NotImplementedError()

    def __init__(self, args: argparse.Namespace, config: _T_Config):
        self._args = args
        self._config = config

    def run(self) -> None:
        pass
