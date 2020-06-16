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

from logging import getLogger
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
from xdg import XDG_CONFIG_DIRS, XDG_CONFIG_HOME

from nasty_utils.logging_ import ColoredBraceStyleAdapter
from nasty_utils.typing_ import checked_cast

_LOGGER = ColoredBraceStyleAdapter(getLogger(__name__))


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

    def __init__(self, *, config_file: Optional[Path] = None, **kwargs: object):
        self._config_file = config_file

        for class_ in reversed(type(self).mro()):
            for name, meta in vars(class_).items():
                if not (
                    isinstance(meta, _ConfigAttr) or isinstance(meta, _ConfigSection)
                ):
                    continue

                type_ = cast(Optional[Type[Any]], class_.__annotations__.get(name))
                if type_ is None:
                    raise TypeError(
                        "Type annotation is required to use "
                        f"ConfigAttr()/ConfigSection(). It is missing for {name}."
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
                    raw_value, attr.deserializer, type_
                )
            except Exception as e:
                raise ValueError(
                    f"Config attribute {name} can not be deserialized to {type_}."
                    f" Raw value is '{raw_value}' of type {type(raw_value)}.",
                    e,
                )

        setattr(self, name, value)

    def _deserialize_and_verify_type(
        self,
        raw_value: object,
        deserializer: Optional[Callable[[object], object]],
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
                self._deserialize_and_verify_type(x, deserializer, inner_type)
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
                k: self._deserialize_and_verify_type(v, deserializer, inner_type)
                for k, v in raw_value.items()
            }

        valid_types = type_args if type_origin is Union else (type_,)  # type: ignore
        if deserializer is not None:
            value = deserializer(raw_value)
        elif any(issubclass(t, Path) for t in valid_types):
            value = Path(checked_cast(str, raw_value))
            if not value.is_absolute() and self._config_file:
                value = self._config_file.parent / value
        else:
            value = raw_value

        if not any(isinstance(value, t) for t in valid_types):
            raise ValueError(
                f"Deserialized value {repr(value)} is not of type {type_}."
            )

        return value

    def _config_section(
        self, name: str, _section: _ConfigSection, type_: Type[Any], raw_value: object
    ) -> None:
        try:
            setattr(self, name, self._deserialize_section(raw_value, type_))
        except Exception as e:
            raise ValueError(
                f"Config section {name} can not be deserialized to {type_}."
                f" Raw value is '{raw_value}' of type {type(raw_value)}.",
                e,
            )

    def _deserialize_section(self, raw_value: object, type_: Type[Any]) -> object:
        type_origin = typing_inspect.get_origin(type_)
        type_args = typing_inspect.get_args(type_, evaluate=True)

        if (
            type_origin
            and type_origin is not Union  # type: ignore
            and issubclass(type_origin, Sequence)
        ):
            if raw_value is None:
                return []
            if not isinstance(raw_value, Sequence):
                raise ValueError(f"Expected a sequence but found a {type(raw_value)}.")
            return [self._deserialize_section(x, type_args[0]) for x in raw_value]

        if type_origin is Union:  # type: ignore
            if raw_value is None:
                return None
            type_ = type_args[0]

        if not issubclass(type_, Config):
            raise TypeError(
                "Type annotation for ConfigSection() values must be a subclass of "
                f"Config or a Optional or Sequence of that. It was {type_}."
            )

        if not isinstance(raw_value, Mapping):
            raise ValueError(f"Expected a TOML-table, not a {type(raw_value)}.")

        return type_(config_file=self._config_file, **raw_value)

    @classmethod
    def load_from_str(
        cls: Type[_T_Config], toml_str: str, *, config_file: Optional[Path] = None
    ) -> _T_Config:
        return cls(config_file=config_file, **toml.loads(toml_str))

    @classmethod
    def load_from_config_file(cls: Type[_T_Config], config_file: Path) -> _T_Config:
        _LOGGER.debug("Loading {} from '{}'...", cls.__name__, config_file)
        with config_file.open(encoding="UTF-8") as fin:
            return cls.load_from_str(fin.read(), config_file=config_file)

    @classmethod
    def find_config_file(cls, name: str, directory: str = ".") -> Path:
        config_dirs = [Path.cwd() / ".config"]
        while config_dirs[-1].parent.parent != config_dirs[-1].parent:
            config_dirs.append(config_dirs[-1].parent.parent / ".config")

        config_dirs.append(XDG_CONFIG_HOME)
        config_dirs.extend(XDG_CONFIG_DIRS)

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
        config_file = cls.find_config_file(name, directory)
        return cls.load_from_config_file(config_file)

    def __str__(self) -> str:
        dict_str = "\n".join(
            "  " + line for line in toml.dumps(self.serialize()).splitlines()
        )
        return f"{type(self).__name__}{{\n{dict_str}\n}}"

    def serialize(self) -> Mapping[str, object]:
        result: MutableMapping[str, object] = {}
        for class_ in reversed(type(self).mro()):
            for name, meta in vars(class_).items():
                if isinstance(meta, _ConfigAttr):
                    result[name] = (
                        self._serialize_value(getattr(self, name), meta.serializer)
                        if not meta.secret
                        else "<secret>"
                    )

                elif isinstance(meta, _ConfigSection):
                    result[name] = self._serialize_section(getattr(self, name))
        return result

    @classmethod
    def _serialize_value(
        cls, value: object, serializer: Optional[Callable[[object], object]]
    ) -> object:
        if isinstance(value, Sequence) and not isinstance(value, str):
            return [cls._serialize_value(x, serializer) for x in value]
        elif isinstance(value, Mapping):
            return {k: cls._serialize_value(v, serializer) for k, v in value.items()}
        elif serializer is not None:
            return serializer(value)
        elif value is None:
            return None
        elif isinstance(value, Path):
            return str(value)
        else:
            return value

    @classmethod
    def _serialize_section(cls, value: object) -> object:
        if value is None:
            return None
        elif isinstance(value, Sequence):
            return [cls._serialize_section(x) for x in value]
        else:
            return checked_cast(Config, value).serialize()
