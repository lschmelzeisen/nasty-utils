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
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import (
    Generic,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
    cast,
)

from nasty_utils._util.argparse_ import SingleMetavarHelpFormatter
from nasty_utils.config import Config
from nasty_utils.logging import LoggingConfig

# TODO: program without commands

_T_Config = TypeVar("_T_Config", bound=Optional[Config])


class CommandMeta:
    def __init__(self, *, name: str, aliases: Sequence[str], desc: str):
        self.name = name
        self.aliases = aliases
        self.desc = desc


class Command(Generic[_T_Config]):
    @classmethod
    def meta(cls) -> CommandMeta:
        raise NotImplementedError()

    @classmethod
    def setup_argparser(cls, argparser: ArgumentParser) -> None:
        pass

    def __init__(self, args: argparse.Namespace, config: _T_Config):
        self._args = args
        self._config = config

    def validate_arguments(self, argparser: ArgumentParser) -> None:
        pass

    def run(self) -> None:
        pass


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
        self._meta = self.meta()
        self._args = self._load_args(args)
        self._config = self._load_config()
        self._run_command()

    def _load_args(self, args: Sequence[str]) -> argparse.Namespace:
        argparser = ArgumentParser(
            prog=self._meta.name,
            description=self._meta.desc,
            add_help=False,
            formatter_class=SingleMetavarHelpFormatter,
        )
        self._setup_argparser(argparser)

        self._subparser_by_command_type: MutableMapping[
            Type[Command[_T_Config]], ArgumentParser
        ] = {}
        self._setup_subparsers(argparser, Command, name=self._meta.name, depth=0)

        return argparser.parse_args(args)

    def _setup_argparser(self, argparser: ArgumentParser) -> None:
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
                aliases=subcommand_meta.aliases,
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
            self._setup_argparser(subparser)

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

    def _run_command(self) -> None:
        command_cls = cast(
            Optional[Type[Command[_T_Config]]], getattr(self._args, "command", None)
        )
        if not command_cls:
            return

        command = command_cls(self._args, self._config)
        command.validate_arguments(self._subparser_by_command_type[command_cls])
        command.run()
