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

import re
from enum import Enum
from typing import Any, Sequence, Type, TypeVar


def get_qualified_name(cls: Type[Any]) -> str:
    return cls.__module__ + "." + cls.__name__


# Adapted from: https://stackoverflow.com/a/37697078/211404
def camel_case_split(s: str, remove_underscores: bool = True) -> Sequence[str]:
    if remove_underscores:
        s = s.replace("_", "")
    return re.sub("([A-Z][a-z]+)", r" \1", re.sub("([A-Z]+)", r" \1", s)).split()


_T_Enum = TypeVar("_T_Enum", bound=Enum)


# def parse_enum_arg(
#     s: str,
#     enum_cls: Type[_T_Enum],
#     *,
#     ignore_case: bool = False,
#     convert_camel_case_for_error: bool = False,
# ) -> _T_Enum:
#     for variant in enum_cls:
#         if (ignore_case and variant.name.upper() == s.upper()) or (variant.name == s):
#             return variant
#
#     enum_name = enum_cls.__name__
#     if convert_camel_case_for_error:
#         enum_name = " ".join(s.lower() for s in camel_case_split(enum_name))
#
#     valid_values = "', '".join(t.name for t in enum_cls)
#
#     raise ArgumentError(
#         f"Can not parse {enum_name} '{s}'. Valid values are: '{valid_values}'."
#     )
