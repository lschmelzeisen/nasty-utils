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
from argparse import ArgumentParser
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
    TypeVar,
    Union,
    cast,
)

from pydantic import BaseConfig, BaseModel, Extra, ValidationError
from pydantic.dataclasses import dataclass
from pydantic.fields import FieldInfo, ModelField, Undefined

from nasty_utils._util.argparse_ import SingleMetavarHelpFormatter
from nasty_utils.configuration import Configuration
from nasty_utils.logging_ import ColoredBraceStyleAdapter
from nasty_utils.logging_configuration import LoggingConfiguration
from nasty_utils.misc import get_qualified_name

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


class CommandConfig(BaseConfig):
    title: Optional[str] = None  # type: ignore
    aliases: Sequence[str] = ()
    description: Optional[str] = None


class Command(BaseModel):
    if TYPE_CHECKING:
        __config__: Type[CommandConfig] = CommandConfig

    prog: "Program"

    class Config(CommandConfig):
        validate_all = True
        extra = Extra.forbid

    @classmethod
    def title(cls) -> str:
        return cls.__config__.title or cls.__name__

    def run(self) -> None:
        pass


class ProgramConfig(BaseConfig):
    title: Optional[str] = None  # type: ignore
    version: Optional[str] = None
    description: Optional[str] = None
    config_search_path: Optional[Path] = None
    commands: Union[Sequence[Type[Command]], Mapping[Type[Command], Type[Command]]] = []


_T_Program = TypeVar("_T_Program", bound="Program")


class Program(BaseModel):
    # TODO: Add option to make commands optional if they exist?

    if TYPE_CHECKING:
        __config__: Type[ProgramConfig] = ProgramConfig

    raw_args: Sequence[str] = ()
    command: Optional[Command] = None

    class Config(ProgramConfig):
        validate_all = True
        extra = Extra.forbid

    @classmethod
    def title(cls) -> str:
        return cls.__config__.title or cls.__name__

    @classmethod
    def version(cls) -> str:
        return cls.__config__.version or "unversioned"

    @classmethod
    def config_type(cls) -> Optional[Type[Configuration]]:
        config_field = cls.__fields__.get("config")
        if not config_field:
            return None

        config_type: Type[Any] = config_field.outer_type_
        if issubclass(config_type, Configuration):
            return config_type

        raise TypeError(
            "If field `config` exists it must be annotated with a type that "
            "subclasses nasty_utils.Configuration."
        )

    @classmethod
    def config_search_path(cls) -> Path:
        return cls.__config__.config_search_path or Path(cls.title() + ".toml")

    @classmethod
    def commands(cls) -> Mapping[Type[Command], Sequence[Type[Command]]]:
        commands = cls.__config__.commands
        if isinstance(commands, Sequence):
            return {Command: commands}
        return {  # Yes, this has quadratic complexity, but kept for brevity.
            parent: [child for child, parent2 in commands.items() if parent2 == parent]
            for parent in set(commands.values())
        }

    @classmethod
    def init(cls: Type[_T_Program], *args: str) -> _T_Program:
        config_type = cls.config_type()
        if config_type and issubclass(config_type, LoggingConfiguration):
            config_type.setup_memory_logging()

        prog_argparser, command_argparsers = cls._setup_argparsers()
        parsed_args, command, config_overwrite_path = cls._parse_args(
            prog_argparser, args
        )
        config = cls._load_config(config_type, config_overwrite_path)

        prog_obj: MutableMapping[str, object] = {"raw_args": tuple(args)}
        if config_type:
            prog_obj["config"] = config
        if not command:
            prog_obj.update(parsed_args)

        try:
            prog = cls.parse_obj(prog_obj)
        except ValidationError as e:
            prog_argparser.error(str(e))

        if command:
            try:
                command_obj = dict(parsed_args, prog=prog)
                prog.command = command.parse_obj(command_obj)
            except ValidationError as e:
                command_argparsers[command].error(str(e))

        return prog

    @classmethod
    def _setup_args(
        cls, argparser: ArgumentParser, model: Union[Type["Program"], Type[Command]]
    ) -> None:
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
            version=f"{cls.title()} {cls.version()}",
            help="Show program's version string and exit.",
        )

        if "config" in cls.__fields__:
            g.add_argument(
                "--config",
                metavar="<CONFIG>",
                type=Path,
                help="Overwrite default config file path.",
            )

        for argument_group, fields in cls._get_argument_groups(model).items():
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
                else:
                    kwargs["type"] = str
                    kwargs["metavar"] = f"<{metavar}>"
                    kwargs["required"] = field.required
                    kwargs["default"] = ...

                g.add_argument(*args, **kwargs)

    @classmethod
    def _get_argument_groups(
        cls, model: Union[Type["Program"], Type[Command]]
    ) -> Mapping[Optional[ArgumentGroup], Sequence[ModelField]]:
        result: MutableMapping[Optional[ArgumentGroup], MutableSequence[ModelField]] = {
            None: []
        }

        for field_name, field in model.__fields__.items():
            if field_name in ["command", "config", "prog", "raw_args"]:
                continue

            argument_group = getattr(field.field_info, "group", None)
            result.setdefault(argument_group, []).append(field)

        return result

    @classmethod
    def _setup_argparsers(
        cls,
    ) -> Tuple[ArgumentParser, Mapping[Type[Command], ArgumentParser]]:
        prog_argparser = ArgumentParser(
            prog=cls.title(),
            description=cls.__config__.description,
            add_help=False,
            formatter_class=SingleMetavarHelpFormatter,
        )
        cls._setup_args(prog_argparser, cls)

        command_argparsers = cls._setup_command_argparsers(
            prog_argparser, Command, cls.commands(), name=cls.title(), depth=0
        )

        return prog_argparser, command_argparsers

    @classmethod
    def _setup_command_argparsers(
        cls,
        argparser: ArgumentParser,
        command: Type[Command],
        commands: Mapping[Type[Command], Sequence[Type[Command]]],
        *,
        name: str,
        depth: int,
    ) -> Mapping[Type[Command], ArgumentParser]:
        subcommands = commands.get(command)
        if not subcommands:
            return {}

        title = depth * "sub" + "command"
        subparsers = argparser.add_subparsers(
            title=title[0].upper() + title[1:] + "s",
            description=(
                "The following commands  are available, each supporting the --help "
                "option."
            ),
            metavar="<" + title.upper() + ">",
            prog=name,
        )
        subparsers.required = True

        command_argparsers: MutableMapping[Type[Command], ArgumentParser] = {}
        for subcommand in subcommands:
            subparser = subparsers.add_parser(
                name=subcommand.title(),
                aliases=subcommand.__config__.aliases,
                description=subcommand.__config__.description,
                help=subcommand.__config__.description,
                add_help=False,
                formatter_class=SingleMetavarHelpFormatter,
            )
            subparser.set_defaults(command=subcommand)
            cls._setup_args(subparser, subcommand)

            command_argparsers[subcommand] = subparser
            command_argparsers.update(
                cls._setup_command_argparsers(
                    subparser,
                    subcommand,
                    commands,
                    name=f"{name} {subcommand.title()}",
                    depth=depth + 1,
                )
            )

        return command_argparsers

    @classmethod
    def _parse_args(
        cls, argparser: ArgumentParser, args: Sequence[str]
    ) -> Tuple[Mapping[str, object], Type[Command], Path]:
        parsed_args = {
            arg_name: arg_value
            for arg_name, arg_value in vars(argparser.parse_args(args)).items()
            if arg_value is not ...
        }
        command = cast(Type[Command], parsed_args.pop("command", None))
        config_overwrite_path = cast(Path, parsed_args.pop("config", None))
        return parsed_args, command, config_overwrite_path

    @classmethod
    def _load_config(
        cls,
        config_type: Optional[Type[Configuration]],
        config_overwrite_path: Optional[Path],
    ) -> Optional[Configuration]:
        if not config_type:
            return None

        if config_overwrite_path:
            config = config_type.load_from_config_file(config_overwrite_path)
        else:
            config = config_type.find_and_load_from_config_file(
                cls.config_search_path()
            )

        if isinstance(config, LoggingConfiguration):
            config.setup_logging()

        return config

    def log(self) -> None:
        cls = type(self)
        _LOGGER.debug("Program: {} ({}):", cls.title(), get_qualified_name(cls))
        _LOGGER.debug("  Version: {}", cls.version())
        _LOGGER.debug("  Raw args: {}", list(self.raw_args))

        if not self.command:
            _LOGGER.debug("  Command: {}", None)
            for field_name, field_value in self.dict(
                exclude={"command", "config", "raw_args"}
            ).items():
                _LOGGER.debug("    {} = {}", field_name, field_value)

        else:
            _LOGGER.debug(
                "  Command: {} ({}):",
                self.command.title(),
                get_qualified_name(type(self.command)),
            )
            for field_name, field_value in self.command.dict(exclude={"prog"}).items():
                _LOGGER.debug("    {} = {}", field_name, field_value)

        config = cast(Optional[Configuration], getattr(self, "config", None))
        if config:
            _LOGGER.debug("  Config: {}", get_qualified_name(type(config)))
            for line in str(config).splitlines()[1:-1]:
                _LOGGER.debug("  {}", line)

    def run(self) -> None:
        self.log()
        if self.command:
            self.command.run()


Command.update_forward_refs()
