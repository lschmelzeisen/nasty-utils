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

from typing import (
    Any,
    ContextManager,
    Generic,
    Optional,
    Pattern,
    Tuple,
    Type,
    TypeVar,
    Union,
)

_T_exp = TypeVar("_T_exp", bound=BaseException)

class _pytest:  # noqa: N801
    class _code:  # noqa: N801
        class ExceptionInfo(Generic[_T_exp]):
            value: _T_exp

def raises(  # noqa: F811
    expected_exception: Union[Type[_T_exp], Tuple[Type[_T_exp], ...]],
    *args: Any,
    match: Optional[Union[str, Pattern[Any]]] = ...,
    **kwargs: Any,
) -> ContextManager[_pytest._code.ExceptionInfo[_T_exp]]: ...
