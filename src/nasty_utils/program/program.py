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
from pathlib import Path
from typing import (
    Any,
    Generic,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
)

import typing_inspect

from nasty_utils._util.argparse_ import SingleMetavarHelpFormatter
from nasty_utils.config import Config
from nasty_utils.logging import LoggingConfig
from nasty_utils.program.argument import ArgumentGroup, _Argument, _Flag
from nasty_utils.program.command import Command
from nasty_utils.typing import checked_cast

_T_Config = TypeVar("_T_Config", bound=Optional[Config])


class ProgramMeta(Generic[_T_Config]):
    def __init__(
        self,
        *,
        name: str,
        version: str,
        desc: str,
        config_type: Type[_T_Config],
        config_file: str,
        config_dir: str,
        command_hierarchy: Optional[
            Mapping[Type[Command[_T_Config]], Sequence[Type[Command[_T_Config]]]]
        ],
    ):
        self.name = name
        self.version = version
        self.desc = desc
        self.config_type = config_type
        self.config_file = config_file
        self.config_dir = config_dir
        self.command_hierarchy = command_hierarchy


class Program(Generic[_T_Config]):
    @classmethod
    def meta(cls) -> ProgramMeta[_T_Config]:
        raise NotImplementedError()

    def __init__(self, *args: str):
        self._raw_args = args
        self._meta = self.meta()
        self._args = self._load_args()
        self._config = self._load_config()
        self._parse_args()

        if self._command:
            self._command.run()

    def _load_args(self) -> argparse.Namespace:
        argparser = ArgumentParser(
            prog=self._meta.name,
            description=self._meta.desc,
            add_help=False,
            formatter_class=SingleMetavarHelpFormatter,
        )
        self._setup_argparser(argparser, type(self))

        self._subparser_by_command_type: MutableMapping[
            Type[Command[_T_Config]], ArgumentParser
        ] = {}
        self._setup_subparsers(argparser, Command, name=self._meta.name, depth=0)

        return argparser.parse_args(self._raw_args)

    def _setup_argparser(
        self,
        argparser: ArgumentParser,
        argument_holder: Union[Type["Program[_T_Config]"], Type[Command[_T_Config]]],
    ) -> None:
        g = argparser.add_argument_group("General Arguments")

        # The following line & the add_help=False above is to be able to customize
        # the help message. See: https://stackoverflow.com/a/35848313/211404
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
            version="%(prog)s " + self._meta.version,
            help="Show program's version number and exit.",
        )

        if self._meta.config_type:
            g.add_argument(
                "--config",
                metavar="<CONFIG>",
                type=Path,
                help="Overwrite default config file path.",
            )

        for name, meta in vars(argument_holder).items():
            if isinstance(meta, ArgumentGroup):
                g = argparser.add_argument_group(title=meta.name, description=meta.desc)

            if not (isinstance(meta, _Flag) or isinstance(meta, _Argument)):
                continue

            type_ = cast(Optional[Type[Any]], argument_holder.__annotations__.get(name))
            if type_ is None:
                raise TypeError(
                    "Type annotation is required to use Flag()/Argument()."
                    f"It is missing for {name}."
                )

            opts = ["--" + meta.name]
            if meta.short_name:
                opts.insert(
                    0, "-" + meta.short_name,
                )

            if isinstance(meta, _Flag):
                if type_ is not bool:
                    raise TypeError(
                        f"Type annotation for Flag() must be bool, but is {type_}."
                    )
                g.add_argument(
                    *opts,
                    help=meta.desc,
                    action="store_true" if not meta.default else "store_false",
                    dest=name,
                )

            elif isinstance(meta, _Argument):
                g.add_argument(
                    *opts,
                    metavar=f"<{meta.metavar or meta.name.upper()}>",
                    help=meta.desc,
                    type=str,
                    required=meta.required,
                    dest=name,
                )

    def _setup_subparsers(
        self,
        argparser: ArgumentParser,
        command: Type[Command[_T_Config]],
        *,
        name: str,
        depth: int,
    ) -> None:
        subcommands = (self._meta.command_hierarchy or {}).get(command)
        if not subcommands:
            return

        title = depth * "sub" + "command"
        subparsers = argparser.add_subparsers(
            title=title[0].upper() + title[1:] + "s",
            description=(
                "The following commands (and abbreviations) are available, each "
                "supporting the help option."
            ),
            metavar="<" + title.upper() + ">",
            prog=name,
        )
        subparsers.required = True

        for subcommand in subcommands:
            subcommand_meta = subcommand.meta()
            subparser = subparsers.add_parser(
                name=subcommand_meta.name,
                aliases=subcommand_meta.aliases or [],
                help=subcommand_meta.desc,
                add_help=False,
                formatter_class=SingleMetavarHelpFormatter,
            )
            subparser.set_defaults(command=subcommand)
            self._subparser_by_command_type[subcommand] = subparser

            self._setup_subparsers(
                subparser,
                subcommand,
                name=name + " " + subcommand_meta.name,
                depth=depth + 1,
            )

            subcommand.setup_argparser(subparser)
            self._setup_argparser(subparser, subcommand)

    def _load_config(self) -> _T_Config:
        if not issubclass(self._meta.config_type, Config):
            return cast(_T_Config, None)

        config_overwrite_path = cast(
            Optional[Path], getattr(self._args, "config", None)
        )
        config: Config
        if config_overwrite_path:
            config = self._meta.config_type.load_from_config_file(config_overwrite_path)
        else:
            config = self._meta.config_type.find_and_load_from_config_file(
                self._meta.config_file, self._meta.config_dir
            )

        if isinstance(config, LoggingConfig):
            config.setup_logging()

        return cast(_T_Config, config)

    def _parse_args(self) -> None:
        command_cls = cast(
            Optional[Type[Command[_T_Config]]], getattr(self._args, "command", None)
        )
        if not command_cls:
            self._command = None
        else:
            self._command = command_cls(self._args, self._config)
            self._command.validate_arguments(
                self._subparser_by_command_type[command_cls]
            )

        argument_holder = self._command or self
        for name, meta in vars(type(argument_holder)).items():
            if not (isinstance(meta, _Flag) or isinstance(meta, _Argument)):
                continue

            raw_value = getattr(self._args, name)
            if isinstance(meta, _Flag):
                setattr(argument_holder, name, bool(raw_value))
            elif isinstance(meta, _Argument):
                type_ = cast(Type[Any], type(argument_holder).__annotations__.get(name))
                value: object
                if raw_value is None:
                    value = meta.default
                else:
                    deserializer = meta.deserializer or (lambda x: x)
                    value = deserializer(checked_cast(str, raw_value))

                type_origin = typing_inspect.get_origin(type_)
                type_args = typing_inspect.get_args(type_, evaluate=True)
                valid_types = (
                    type_args if type_origin is Union else (type_,)  # type: ignore
                )
                if not any(isinstance(value, t) for t in valid_types):
                    raise ValueError(
                        f"Deserialized value {repr(value)} is not of type {type_}."
                    )

                setattr(argument_holder, name, value)
