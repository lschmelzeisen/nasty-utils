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

from logging import Logger, getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional, Type, TypeVar, cast

import toml
from typing_extensions import Final
from typing_inspect import get_origin

_LOGGER: Final[Logger] = getLogger(__name__)


class _ConfigAttr:
    def __init__(
        self,
        *,
        required: bool = False,
        default: Optional[object] = None,
        secret: bool = False,
        converter: Optional[Callable[[object], object]] = None,
    ):
        self.required = required
        self.default = default
        self.secret = secret
        self.converter = converter


if TYPE_CHECKING:
    ConfigAttr = Any
else:
    ConfigAttr = _ConfigAttr

_T_Config = TypeVar("_T_Config", bound="Config")


class Config:
    # TODO: warn about unused attribute in config file.

    def __init__(self, **kwargs: Mapping[str, object]):
        for name, attr in vars(type(self)).items():
            if not isinstance(attr, _ConfigAttr):
                continue

            type_ = cast(Type[Any], self.__annotations__.get(name))
            raw_value = kwargs.get(name)

            if raw_value is None:
                if attr.required:
                    raise ValueError(
                        f"Config attribute {name} does not exist but is required."
                    )
                value = attr.default

            elif attr.converter:
                try:
                    value = attr.converter(raw_value)
                except Exception as e:
                    raise ValueError(
                        f"Config attribute {name} can not be converted to type {type_}."
                        f" Raw value is '{raw_value}' of type {type(raw_value)}.",
                        e,
                    )

            else:
                value = raw_value

            if not isinstance(value, get_origin(type_) or type_):
                raise ValueError(
                    f"Config attribute {name} is not of correct type {type_}."
                    f" Raw value is '{raw_value}' of type {type(raw_value)}.",
                )

            setattr(self, name, value)

    @classmethod
    def load(cls: Type[_T_Config], path: Path) -> _T_Config:
        _LOGGER.debug(f"Loading {cls.__name__} from '{path}'...")
        with path.open(encoding="UTF-8") as fin:
            raw_config = toml.load(fin)

        return cls(**raw_config)

    # TODO: implement get correct path

    def __str__(self) -> str:
        return (
            type(self).__name__
            + "{\n"
            + "\n".join(
                "  " + line for line in toml.dumps(self._to_dict()).splitlines()
            )
            + "\n}"
        )

    def _to_dict(self) -> Mapping[str, object]:
        result = {}
        for name, attr in vars(type(self)).items():
            if not isinstance(attr, _ConfigAttr):
                continue
            if attr.secret:
                result[name] = "<secret>"
            else:
                result[name] = getattr(self, name)
        return result
