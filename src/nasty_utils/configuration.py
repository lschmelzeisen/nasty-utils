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
from pprint import pformat
from typing import AbstractSet, Mapping, Optional, Sequence, Type, TypeVar

import toml
from overrides import overrides
from pydantic import BaseModel, Extra, FilePath, validator
from pydantic.fields import ModelField
from xdg import XDG_CONFIG_DIRS, XDG_CONFIG_HOME

from nasty_utils.logging_ import ColoredBraceStyleAdapter

_LOGGER = ColoredBraceStyleAdapter(getLogger(__name__))

_T_Configuration = TypeVar("_T_Configuration", bound="Configuration")


class Configuration(BaseModel):
    class Config:  # Pydantic config, not related to this class's configuration nature.
        validate_all = True
        extra = Extra.forbid
        allow_mutation = False

    config_file: Optional[FilePath]

    # TODO: does probably not work with Path's in nested BaseModels.
    @validator("*", pre=True)
    def _expand_paths(
        cls,  # noqa: N805
        value: object,
        values: Mapping[str, object],
        field: ModelField,
    ) -> object:
        if not (
            # In >=3.7 typing.Sequence/Mapping is not a normal type.
            type(field.type_) == type(object)
            and issubclass(field.type_, Path)
            and value
        ):
            return value

        if isinstance(value, str) or isinstance(value, Path):
            v = str(value)
            if "{CONFIG_FILE}" in v:
                config_file = values.get("config_file")
                if not config_file:
                    raise ValueError(
                        "Can not use '{CONFIG_FILE}' placeholder in configuration not "
                        "loaded from a file."
                    )
                v = v.replace("{CONFIG_FILE}", str(Path(str(config_file)).parent))
            return v
        elif isinstance(value, Mapping):
            return {k: cls._expand_paths(v, values, field) for k, v in value.items()}
        elif isinstance(value, Sequence):
            return [cls._expand_paths(v, values, field) for v in value]
        elif isinstance(value, AbstractSet):
            return {cls._expand_paths(v, values, field) for v in value}
        else:
            raise TypeError(
                f"Path-container of type '{type(value).__name__}' not implemented yet."
            )

    @classmethod
    def can_default(cls) -> bool:
        for field in cls.__fields__.values():
            if field.required:
                return False
        return True

    @classmethod
    def find_config_file(cls, search_path: Path) -> Path:
        config_dirs = [Path.cwd() / ".config"]
        while config_dirs[-1].parent.parent != config_dirs[-1].parent:
            config_dirs.append(config_dirs[-1].parent.parent / ".config")

        config_dirs.append(XDG_CONFIG_HOME)
        config_dirs.extend(XDG_CONFIG_DIRS)

        for config_dir in config_dirs:
            path = config_dir / search_path
            if path.exists():
                return path

        raise FileNotFoundError(
            f"Could not find configuration file '{search_path}'. Checked at the "
            "following locations:\n"
            + "\n".join("- " + str(config_dir) for config_dir in config_dirs)
        )

    @classmethod
    def find_and_load_from_config_file(
        cls: Type[_T_Configuration], search_path: Path
    ) -> _T_Configuration:
        try:
            config_file = cls.find_config_file(search_path)
        except FileNotFoundError:
            if cls.can_default():
                _LOGGER.debug(
                    "Loading default {} since no config file was found...", cls.__name__
                )
                return cls()
            else:
                raise
        return cls.load_from_config_file(config_file)

    @classmethod
    def load_from_config_file(
        cls: Type[_T_Configuration], config_file: Path
    ) -> _T_Configuration:
        _LOGGER.debug("Loading {} from '{}'...", cls.__name__, config_file)
        return cls.load_from_str(
            config_file.read_text(encoding="UTF-8"), config_file=config_file
        )

    @classmethod
    def load_from_str(
        cls: Type[_T_Configuration],
        toml_str: str,
        *,
        config_file: Optional[Path] = None,
    ) -> _T_Configuration:
        config_dict = toml.loads(toml_str)
        config_dict["config_file"] = config_file
        return cls.parse_obj(config_dict)

    @overrides
    def __str__(self) -> str:
        formatted = pformat(self.dict(exclude={"config_file"}), indent=2)
        return f"{type(self).__name__}{{\n {formatted[len('{'):-len('}')]}\n}}"
