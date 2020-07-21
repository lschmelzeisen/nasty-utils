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
from importlib import import_module
from typing import Any, Sequence, Type


def get_qualified_name(cls: Type[Any]) -> str:
    return cls.__module__ + "." + cls.__name__


def lookup_qualified_name(name: str) -> object:
    if "." not in name:
        raise ValueError(f"Not a valid fully-qualified name: '{name}'")
    module_name, member_name = name.rsplit(".", maxsplit=1)
    module = import_module(module_name)
    member = getattr(module, member_name, None)
    if member is None:
        raise ValueError(f"Could not find member '{member_name}' in module '{module}'.")
    return member


# Adapted from: https://stackoverflow.com/a/37697078/211404
def camel_case_split(s: str, remove_underscores: bool = True) -> Sequence[str]:
    if remove_underscores:
        s = s.replace("_", "")
    return re.sub("([A-Z][a-z]+)", r" \1", re.sub("([A-Z]+)", r" \1", s)).split()
