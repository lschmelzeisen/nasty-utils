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

from typing import Any, Callable, Sequence, TypeVar, Union

_T_func = TypeVar("_T_func", bound=Callable[..., Any])

def session(
    python: Union[str, bool, Sequence[str]] = ..., reuse_env: bool = ...
) -> Callable[[_T_func], _T_func]: ...

class options:  # noqa: N801
    error_on_external_run = True
    reuse_existing_virtualenvs = True
    stop_on_first_error = True
