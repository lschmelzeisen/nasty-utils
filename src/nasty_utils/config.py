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
from pydantic import BaseModel, FilePath, validator
from pydantic.fields import ModelField
from xdg import XDG_CONFIG_DIRS, XDG_CONFIG_HOME

from nasty_utils.logging_ import ColoredBraceStyleAdapter

_LOGGER = ColoredBraceStyleAdapter(getLogger(__name__))

_T_Config = TypeVar("_T_Config", bound="Config")


class Config(BaseModel):
    class Config:  # Pydantic configuration, not related to this class's config nature.
        validate_all = True
        allow_mutation = False

    config_file: Optional[FilePath]

    @validator("*", pre=True)
    def _expand_paths(
        cls,  # noqa: N805
        value: object,
        values: Mapping[str, object],
        field: ModelField,
    ) -> object:
        if not (issubclass(field.type_, Path) and value):
            return value

        if isinstance(value, str) or isinstance(value, Path):
            v = str(value)
            if "${CONFIG_FILE}" in v:
                config_file = values.get("config_file")
                if not config_file:
                    raise ValueError(
                        "Can not use '${CONFIG_FILE}' placeholder in configuration not "
                        "loaded from a file."
                    )
                v = v.replace("${CONFIG_FILE}", str(Path(str(config_file)).parent))
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

    @classmethod
    def load_from_config_file(cls: Type[_T_Config], config_file: Path) -> _T_Config:
        _LOGGER.debug("Loading {} from '{}'...", cls.__name__, config_file)
        with config_file.open(encoding="UTF-8") as fin:
            return cls.load_from_str(fin.read(), config_file=config_file)

    @classmethod
    def load_from_str(
        cls: Type[_T_Config], toml_str: str, *, config_file: Optional[Path] = None
    ) -> _T_Config:
        config_dict = toml.loads(toml_str)
        config_dict["config_file"] = config_file
        return cls.parse_obj(config_dict)

    @overrides
    def __str__(self) -> str:
        formatted = pformat(self.dict(exclude={"config_file"}), indent=2)
        return f"{type(self).__name__}{{\n {formatted[len('{'):-len('}')]}\n}}"
