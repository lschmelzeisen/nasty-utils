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

from logging import FileHandler, Handler
from sys import version_info
from typing import Sequence

from pytest import raises

from nasty_utils import checked_cast, safe_issubclass


def test_checked_cast() -> None:
    x: object = 5
    y: int = checked_cast(int, x)
    assert x == y

    with raises(AssertionError):
        checked_cast(int, 3.5)


def test_safe_issubclass() -> None:
    assert safe_issubclass(FileHandler, Handler)
    assert not safe_issubclass(Handler, FileHandler)

    if version_info >= (3, 7):
        with raises(TypeError):
            issubclass(Sequence[int], Sequence)
        assert not safe_issubclass(Sequence[int], Sequence)
