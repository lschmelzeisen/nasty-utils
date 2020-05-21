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
    Union,
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
        deserializer: Optional[Callable[[Any], object]] = None,
        serializer: Optional[Callable[[Any], object]] = None,
    ):
        self.required = required
        self.default = default
        self.secret = secret
        self.deserializer = deserializer
        self.serializer = serializer

        if self.required and self.default:
            raise ValueError("Can not use required together with default.")


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

    def __init__(self, **kwargs: object):
        for name, meta in vars(type(self)).items():
            if not (isinstance(meta, _ConfigAttr) or isinstance(meta, _ConfigSection)):
                continue

            type_ = cast(Optional[Type[Any]], self.__annotations__.get(name))
            if type_ is None:
                raise TypeError(
                    "Type annotation is required to use ConfigAttr()/ConfigSection(). "
                    f"It is missing for {name}."
                )
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
        else:
            try:
                value = self._deserialize_and_verify_type(
                    raw_value, attr.deserializer or (lambda x: x), type_
                )
            except Exception as e:
                raise ValueError(
                    f"Config attribute {name} can not be deserialized to {type_}."
                    f" Raw value is '{raw_value}' of type {type(raw_value)}.",
                    e,
                )

        setattr(self, name, value)

    @classmethod
    def _deserialize_and_verify_type(
        cls,
        raw_value: object,
        deserializer: Callable[[object], object],
        type_: Type[Any],
    ) -> object:
        type_origin = typing_inspect.get_origin(type_)
        type_args = typing_inspect.get_args(type_, evaluate=True)

        if (
            type_origin
            and type_origin is not Union  # type: ignore
            and issubclass(type_origin, Sequence)
        ):
            if not isinstance(raw_value, Sequence):
                raise ValueError(f"Expected a sequence but found a {type(raw_value)}.")

            inner_type = type_args[0] if len(type_args) else object

            return [
                cls._deserialize_and_verify_type(x, deserializer, inner_type)
                for x in raw_value
            ]

        elif (
            type_origin
            and type_origin is not Union  # type: ignore
            and issubclass(type_origin, Mapping)
        ):
            if not isinstance(raw_value, Mapping):
                raise ValueError(f"Expected a Mapping but found a {type(raw_value)}.")

            if len(type_args) and type_args[0] is not str:
                raise TypeError()
            inner_type = type_args[1] if len(type_args) else object

            return {
                k: cls._deserialize_and_verify_type(v, deserializer, inner_type)
                for k, v in raw_value.items()
            }

        value = deserializer(raw_value)

        valid_types = type_args if type_origin is Union else (type_,)  # type: ignore
        if not any(isinstance(value, t) for t in valid_types):
            raise ValueError(
                f"Deserialized value {repr(value)} is not of type {type_}."
            )

        return value

    def _config_section(
        self, name: str, _section: _ConfigSection, type_: Type[Any], raw_value: object
    ) -> None:
        if not isinstance(raw_value, Mapping):
            raise ValueError(
                f"Expected {name} to be a TOML-table, not a {type(raw_value)}."
            )
        setattr(self, name, type_(**raw_value))

    @classmethod
    def load_from_str(cls: Type[_T_Config], toml_str: str) -> _T_Config:
        return cls(**toml.loads(toml_str))

    @classmethod
    def load_from_config_file(cls: Type[_T_Config], config_file: Path) -> _T_Config:
        _LOGGER.debug(f"Loading {cls.__name__} from '{config_file}'...")
        with config_file.open(encoding="UTF-8") as fin:
            return cls.load_from_str(fin.read())

    @classmethod
    def find_config_file(cls, name: str, directory: str = ".") -> Path:
        xdg_config_home = environ.get("XDG_CONFIG_HOME")
        xdg_config_dirs = environ.get("XDG_CONFIG_DIRS")

        config_dirs = [Path.cwd() / ".config"]
        while config_dirs[-1].parent.parent != config_dirs[-1].parent:
            config_dirs.append(config_dirs[-1].parent.parent / ".config")

        if xdg_config_home is not None:
            config_dirs.append(Path(xdg_config_home))
        config_dirs.append(Path.home() / ".config")
        if xdg_config_dirs is not None:
            config_dirs.append(Path(xdg_config_dirs))

        for config_dir in config_dirs:
            path = config_dir / directory / name
            if path.exists():
                return path

        raise FileNotFoundError(
            f"Could not find config file '{directory}/{name}'. Checked at the "
            "following locations:\n"
            + "\n".join("- " + str(config_dir) for config_dir in config_dirs)
        )

    @classmethod
    def find_and_load_from_config_file(
        cls: Type[_T_Config], name: str, directory: str = "."
    ) -> _T_Config:
        return cls.load_from_config_file(cls.find_config_file(name, directory))

    def __str__(self) -> str:
        dict_str = "\n".join(
            "  " + line for line in toml.dumps(self.serialize()).splitlines()
        )
        return f"{type(self).__name__}{{\n{dict_str}\n}}"

    def serialize(self) -> Mapping[str, object]:
        result: MutableMapping[str, object] = {}
        for name, meta in vars(type(self)).items():
            if isinstance(meta, _ConfigAttr):
                result[name] = (
                    self._serialize_value(
                        getattr(self, name), meta.serializer or (lambda x: x)
                    )
                    if not meta.secret
                    else "<secret>"
                )

            elif isinstance(meta, _ConfigSection):
                result[name] = cast(Config, getattr(self, name)).serialize()
        return result

    @classmethod
    def _serialize_value(
        cls, value: object, serializer: Callable[[object], object]
    ) -> object:
        if isinstance(value, Sequence) and not isinstance(value, str):
            return [cls._serialize_value(x, serializer) for x in value]
        elif isinstance(value, Mapping):
            return {k: cls._serialize_value(v, serializer) for k, v in value.items()}
        elif value is None:
            return None
        else:
            return serializer(value)
