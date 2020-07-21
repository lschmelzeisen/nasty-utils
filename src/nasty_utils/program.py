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

import argparse
from argparse import ArgumentParser, _SubParsersAction
from logging import getLogger
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Type,
    cast,
)

from pydantic import BaseConfig, BaseModel, Extra, ValidationError
from pydantic.dataclasses import dataclass
from pydantic.fields import FieldInfo, ModelField, Undefined

from nasty_utils._util.argparse_ import SingleMetavarHelpFormatter
from nasty_utils.logging_ import ColoredBraceStyleAdapter
from nasty_utils.logging_settings import LoggingSettings
from nasty_utils.misc import get_qualified_name
from nasty_utils.settings import Settings
from nasty_utils.typing_ import safe_issubclass

_LOGGER = ColoredBraceStyleAdapter(getLogger(__name__))


@dataclass(eq=True, frozen=True)
class ArgumentGroup:
    name: str
    description: Optional[str] = None


class ArgumentInfo(FieldInfo):
    __slots__ = FieldInfo.__slots__ + ("short_alias", "metavar", "group")

    def __init__(
        self,
        default: Any,
        short_alias: Optional[str],
        metavar: Optional[str],
        group: Optional[ArgumentGroup],
        **kwargs: Any,
    ):
        super().__init__(default, **kwargs)
        self.short_alias = short_alias
        self.metavar = metavar
        self.group = group


def Argument(  # noqa: N802
    default: Any = Undefined,
    *,
    default_factory: Optional[Callable[[], Any]] = None,
    alias: Optional[str] = None,
    short_alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    metavar: Optional[str] = None,
    group: Optional[ArgumentGroup] = None,
    const: Optional[bool] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    multiple_of: Optional[float] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    regex: Optional[str] = None,
    **extra: Any,
) -> Any:
    return ArgumentInfo(
        default,
        default_factory=default_factory,
        alias=alias,
        short_alias=short_alias,
        title=title,
        description=description,
        metavar=metavar,
        group=group,
        const=const,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        min_items=min_items,
        max_items=max_items,
        min_length=min_length,
        max_length=max_length,
        regex=regex,
        **extra,
    )


class ProgramConfig(BaseConfig):
    title: Optional[str] = None  # type: ignore
    aliases: Sequence[str] = ()
    version: Optional[str] = None
    description: Optional[str] = None
    subprograms: Sequence[Type["Program"]] = ()


class Program(BaseModel):
    if TYPE_CHECKING:
        __config__: Type[ProgramConfig] = ProgramConfig

    class Config(ProgramConfig):
        validate_all = True
        extra = Extra.forbid

    raw_args: Sequence[str] = ()

    @classmethod
    def title(cls) -> str:
        return cls.__config__.title or cls.__name__

    @classmethod
    def version(cls) -> str:
        return cls.__config__.version or "unversioned"

    @classmethod
    def init(cls, *args: str) -> "Program":
        LoggingSettings.setup_memory_logging_handler()

        argparsers = cls._setup_argparsers()
        parsed_args, program_type = cls._parse_args(argparsers[cls], args)

        # Final logging has been configured in cls._parse_args().
        LoggingSettings.remove_memory_logging_handler()

        try:
            program = program_type.parse_obj(dict(parsed_args, raw_args=tuple(args)))
        except ValidationError as e:
            argparsers[program_type].error(str(e))

        program.log()
        return program

    @classmethod
    def _setup_argparsers(
        cls,
        *,
        parent_subparsers: Optional[_SubParsersAction] = None,
        prefix: str = "",
        depth: int = 0,
        version_str: Optional[str] = None,
    ) -> Mapping[Type["Program"], ArgumentParser]:
        prog = prefix + cls.title()
        if cls.__config__.version:
            version_str = prog + " " + cls.__config__.version
        elif not version_str:
            version_str = prog + " unversioned"

        if not parent_subparsers:
            argparser = ArgumentParser(
                prog=cls.title(),
                description=cls.__config__.description,
                add_help=False,
                formatter_class=SingleMetavarHelpFormatter,
            )
        else:
            argparser = parent_subparsers.add_parser(
                name=cls.title(),
                aliases=cls.__config__.aliases,
                description=cls.__config__.description,
                help=cls.__config__.description,
                add_help=False,
                formatter_class=SingleMetavarHelpFormatter,
            )
        cls._setup_args(argparser, version_str=version_str)

        argparsers = {cls: argparser}

        if cls.__config__.subprograms:
            metavar = depth * "SUB" + "COMMAND"
            subparsers = argparser.add_subparsers(
                title=metavar[0] + metavar[1:].lower() + "s",
                description=(
                    "The following commands  are available, each supporting the --help "
                    "option."
                ),
                metavar="<" + metavar + ">",
                prog=prog,
            )
            subparsers.required = True

            for subprogram in cls.__config__.subprograms:
                argparsers.update(
                    subprogram._setup_argparsers(
                        parent_subparsers=subparsers,
                        prefix=prog + " ",
                        depth=depth + 1,
                        version_str=version_str,
                    )
                )

        return argparsers

    @classmethod
    def _setup_args(cls, argparser: ArgumentParser, *, version_str: str) -> None:
        argparser.set_defaults(program_type=cls)

        g = argparser.add_argument_group("General Arguments")

        # The following and the add_help=False of ArgumentParser() are s to customize
        # the help's help. See: https://stackoverflow.com/a/35848313/211404
        g.add_argument(
            "-h",
            "--help",
            action="help",
            default=argparse.SUPPRESS,
            help="Show this help message and exit.",
        )

        g.add_argument(
            "-v",
            "--version",
            action="version",
            version=version_str,
            help="Show program's version string and exit.",
        )

        for argument_group, fields in cls._get_argument_groups().items():
            if argument_group:
                g = argparser.add_argument_group(
                    title=argument_group.name, description=argument_group.description
                )

            for field in fields:
                args = ["--" + field.alias]
                metavar = field.alias.upper()
                if isinstance(field.field_info, ArgumentInfo):
                    if field.field_info.short_alias:
                        args.insert(0, "-" + field.field_info.short_alias)
                    if field.field_info.metavar:
                        metavar = field.field_info.metavar

                kwargs = {
                    "help": field.field_info.description,
                    "dest": field.field_info.alias,
                }
                if field.outer_type_ is bool:
                    kwargs["action"] = "store_false" if field.default else "store_true"
                elif safe_issubclass(field.outer_type_, Settings):
                    kwargs["type"] = Path
                    kwargs["metavar"] = f"<{metavar}>"
                else:
                    kwargs["type"] = str
                    kwargs["metavar"] = f"<{metavar}>"
                    kwargs["required"] = field.required
                    kwargs["default"] = ...

                g.add_argument(*args, **kwargs)

    @classmethod
    def _get_argument_groups(
        cls,
    ) -> Mapping[Optional[ArgumentGroup], Sequence[ModelField]]:
        result: MutableMapping[Optional[ArgumentGroup], MutableSequence[ModelField]] = {
            None: []
        }

        for field_name, field in cls.__fields__.items():
            if field_name in ("raw_args",):
                continue

            argument_group = None
            if isinstance(field.field_info, ArgumentInfo):
                argument_group = field.field_info.group
            result.setdefault(argument_group, []).append(field)

        return result

    @classmethod
    def _parse_args(
        cls, argparser: ArgumentParser, args: Sequence[str]
    ) -> Tuple[Mapping[str, object], Type["Program"]]:
        parsed_args: MutableMapping[str, object] = {
            arg_name: arg_value
            for arg_name, arg_value in vars(argparser.parse_args(args)).items()
            if arg_value is not ...
        }

        program_type = cast(Type[Program], parsed_args.pop("program_type"))

        for field in program_type.__fields__.values():
            if safe_issubclass(field.outer_type_, Settings):
                settings_file = cast(Optional[Path], parsed_args.pop(field.alias, None))

                if settings_file:
                    settings = field.outer_type_.load_from_settings_file(settings_file)
                else:
                    settings = field.outer_type_.find_and_load_from_settings_file()

                if isinstance(settings, LoggingSettings):
                    settings.setup_logging()

                parsed_args[field.alias] = settings

        return parsed_args, program_type

    def log(self) -> None:
        cls = type(self)
        _LOGGER.debug("Program: {} ({}):", cls.title(), get_qualified_name(cls))
        _LOGGER.debug("  Version: {}", cls.__config__.version)
        _LOGGER.debug("  Raw args: {}", list(self.raw_args))

        _LOGGER.debug("  Args:")
        for field_name in self.__fields__.keys():
            if field_name in ("raw_args",):
                continue

            field_value = getattr(self, field_name)
            if isinstance(field_value, Settings):
                _LOGGER.debug(
                    "    {} = {}", field_name, get_qualified_name(type(field_value))
                )
                for line in str(field_value).splitlines()[1:-1]:
                    _LOGGER.debug("    {}", line)

            else:
                _LOGGER.debug("    {} = {}", field_name, field_value)

    def run(self) -> None:
        pass
