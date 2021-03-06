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

import enum
from enum import Enum

from nasty_utils import camel_case_split, get_qualified_name, lookup_qualified_name


def test_get_qualified_name() -> None:
    assert get_qualified_name(Enum) == "enum.Enum"


def test_lookup_qualified_name() -> None:
    assert lookup_qualified_name("enum.Enum") == Enum


def test_camel_case_split() -> None:
    assert camel_case_split("camelCaseTest123") == ["camel", "Case", "Test123"]
    assert camel_case_split("CamelCaseTest123") == ["Camel", "Case", "Test123"]
    assert camel_case_split("_camel_CaseTest123") == ["camel", "Case", "Test123"]
    assert camel_case_split("_camel_CaseTest123", remove_underscores=False) == [
        "_camel_",
        "Case",
        "Test123",
    ]
    assert camel_case_split("CamelCaseXYZ") == ["Camel", "Case", "XYZ"]
    assert camel_case_split("XYZCamelCase") == ["XYZ", "Camel", "Case"]
    assert camel_case_split("XYZ") == ["XYZ"]
    assert camel_case_split("IPAddress") == ["IP", "Address"]


class MyEnum(Enum):
    A = enum.auto()
    B = enum.auto()
