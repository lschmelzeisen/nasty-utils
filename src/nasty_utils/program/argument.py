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

from typing import TYPE_CHECKING, Any, Callable, Optional


class ArgumentGroup:
    def __init__(self, *, name: str, desc: str):
        self.name = name
        self.desc = desc


class _Flag:
    def __init__(
        self,
        *,
        name: str,
        short_name: Optional[str] = None,
        desc: str,
        default: bool = False,
    ):
        self.name = name
        self.short_name = short_name
        self.desc = desc
        self.default = default


class _Argument:
    def __init__(
        self,
        *,
        name: str,
        short_name: Optional[str] = None,
        desc: str,
        metavar: Optional[str] = None,
        required: bool = False,
        default: Optional[object] = None,
        deserializer: Optional[Callable[[str], object]] = None,
    ):
        self.name = name
        self.short_name = short_name
        self.desc = desc
        self.metavar = metavar
        self.required = required
        self.default = default
        self.deserializer = deserializer

        if self.required and self.default:
            raise ValueError("Can not use required together with default.")


if TYPE_CHECKING:
    Flag = Any
    Argument = Any
else:
    Flag = _Flag
    Argument = _Argument
