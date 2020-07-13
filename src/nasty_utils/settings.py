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
from pydantic import BaseConfig, BaseModel, Extra, FilePath, validator
from pydantic.fields import ModelField
from xdg import XDG_CONFIG_DIRS, XDG_CONFIG_HOME

from nasty_utils.logging_ import ColoredBraceStyleAdapter

_LOGGER = ColoredBraceStyleAdapter(getLogger(__name__))

_T_Settings = TypeVar("_T_Settings", bound="Settings")


class Settings(BaseModel):
    class Config(BaseConfig):
        validate_all = True
        extra = Extra.forbid
        allow_mutation = False

    settings_file: Optional[FilePath]

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
            if "{SETTINGS_DIR}" in v:
                settings_file = values.get("settings_file")
                if not settings_file:
                    raise ValueError(
                        "Can not use '{SETTINGS_DIR}' placeholder in settings not "
                        "loaded from a file."
                    )
                v = v.replace("{SETTINGS_DIR}", str(Path(str(settings_file)).parent))
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
    def find_settings_file(cls, search_path: Path) -> Path:
        settings_dirs = [Path.cwd() / ".config"]
        while settings_dirs[-1].parent.parent != settings_dirs[-1].parent:
            settings_dirs.append(settings_dirs[-1].parent.parent / ".config")

        settings_dirs.append(XDG_CONFIG_HOME)
        settings_dirs.extend(XDG_CONFIG_DIRS)

        for settings_dir in settings_dirs:
            path = settings_dir / search_path
            if path.exists():
                return path

        raise FileNotFoundError(
            f"Could not find settings file '{search_path}'. Checked at the "
            "following locations:\n"
            + "\n".join("- " + str(settings_dir) for settings_dir in settings_dirs)
        )

    @classmethod
    def find_and_load_from_settings_file(
        cls: Type[_T_Settings], search_path: Path
    ) -> _T_Settings:
        try:
            settings_file = cls.find_settings_file(search_path)
        except FileNotFoundError:
            if cls.can_default():
                _LOGGER.debug(
                    "Loading default {} since no settings file was found...",
                    cls.__name__,
                )
                return cls()
            else:
                raise
        return cls.load_from_settings_file(settings_file)

    @classmethod
    def load_from_settings_file(
        cls: Type[_T_Settings], settings_file: Path
    ) -> _T_Settings:
        _LOGGER.debug("Loading {} from '{}'...", cls.__name__, settings_file)
        return cls.load_from_str(
            settings_file.read_text(encoding="UTF-8"), settings_file=settings_file
        )

    @classmethod
    def load_from_str(
        cls: Type[_T_Settings], toml_str: str, *, settings_file: Optional[Path] = None,
    ) -> _T_Settings:
        settings_dict = toml.loads(toml_str)
        settings_dict["settings_file"] = settings_file
        return cls.parse_obj(settings_dict)

    @overrides
    def __str__(self) -> str:
        formatted = pformat(self.dict(exclude={"settings_file"}), indent=2)
        return f"{type(self).__name__}{{\n {formatted[len('{'):-len('}')]}\n}}"
