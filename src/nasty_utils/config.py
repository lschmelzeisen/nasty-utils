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
from os import environ
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
    cast,
)

import toml
import typing_inspect
from typing_extensions import Final

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


class _ConfigSection:
    pass


if TYPE_CHECKING:
    ConfigAttr = Any
    ConfigSection = Any
else:
    ConfigAttr = _ConfigAttr
    ConfigSection = _ConfigSection

_T_Config = TypeVar("_T_Config", bound="Config")


class Config:
    # TODO: warn about unused attribute in config file.

    def __init__(self, **kwargs: Mapping[str, object]):
        for name, meta in vars(type(self)).items():
            type_ = cast(Type[Any], self.__annotations__.get(name))
            raw_value = kwargs.get(name)

            if isinstance(meta, _ConfigAttr):
                self._config_atttr(name, meta, type_, raw_value)
            elif isinstance(meta, _ConfigSection):
                self._config_section(name, meta, type_, raw_value)

    def _config_atttr(
        self, name: str, attr: _ConfigAttr, type_: Type[Any], raw_value: object
    ) -> None:
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

        types: Sequence[Type[Any]] = [
            *typing_inspect.get_args(type_, evaluate=True),
            typing_inspect.get_origin(type_),
            type_,
        ]
        if not any(isinstance(value, t) for t in filter(None, types)):
            raise ValueError(
                f"Config attribute {name} is not of correct type {type_}."
                f" Raw value is '{raw_value}' of type {type(raw_value)}.",
            )

        setattr(self, name, value)

    def _config_section(
        self, name: str, _section: _ConfigSection, type_: Type[Any], raw_value: object
    ) -> None:
        assert isinstance(raw_value, Mapping)
        setattr(self, name, type_(**raw_value))

    @classmethod
    def load(cls: Type[_T_Config], path: Path) -> _T_Config:
        _LOGGER.debug(f"Loading {cls.__name__} from '{path}'...")
        with path.open(encoding="UTF-8") as fin:
            raw_config = toml.load(fin)

        return cls(**raw_config)

    @classmethod
    def find_file(cls, name: str, directory: str = ".") -> Path:
        xdg_config_home = environ.get("XDG_CONFIG_HOME")
        xdg_config_dirs = environ.get("XDG_CONFIG_DIRS")

        config_dirs = [
            Path.cwd() / ".config",
            Path(xdg_config_home) if xdg_config_home is not None else None,
            Path.home() / ".config",
            Path(xdg_config_dirs) if xdg_config_dirs is not None else None,
        ]

        for config_dir in filter(None, config_dirs):
            path = config_dir / directory / name
            if path.exists():
                return path

        raise FileNotFoundError(
            f"Could not find config file '{directory}/{name}'. Checked at the "
            "following locations:\n"
            + "\n".join("- " + str(config_dir) for config_dir in config_dirs)
        )

    @classmethod
    def find_and_load_file(
        cls: Type[_T_Config], name: str, directory: str = "."
    ) -> _T_Config:
        return cls.load(cls.find_file(name, directory))

    def __str__(self) -> str:
        dict_str = "\n".join(
            "  " + line for line in toml.dumps(self._to_dict()).splitlines()
        )
        return f"{type(self).__name__}{{\n{dict_str}}}"

    def _to_dict(self) -> Mapping[str, object]:
        result: MutableMapping[str, object] = {}
        for name, meta in vars(type(self)).items():
            if isinstance(meta, _ConfigAttr):
                if meta.secret:
                    result[name] = "<secret>"
                else:
                    result[name] = getattr(self, name)
            elif isinstance(meta, _ConfigSection):
                result[name] = cast(Config, getattr(self, name))._to_dict()
        return result
