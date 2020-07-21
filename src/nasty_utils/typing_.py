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

from typing import Any, Tuple, Type, TypeVar, Union

_T_type = TypeVar("_T_type")


def checked_cast(type_: Type[_T_type], value: object) -> _T_type:
    assert isinstance(value, type_)
    return value


def safe_issubclass(
    cls: Any, classinfo: Union[Type[Any], Tuple[Type[Any], ...]]
) -> bool:
    """Variant of issubclass that can be used with typing.Sequence, etc."""
    try:
        return issubclass(cls, classinfo)
    except TypeError:
        return False
