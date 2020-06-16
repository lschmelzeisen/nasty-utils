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

import toml
import typing_inspect

from nasty_utils._util.argparse_ import SingleMetavarHelpFormatter
from nasty_utils.config import Config
from nasty_utils.logging_ import ColoredBraceStyleAdapter
from nasty_utils.logging_config import LoggingConfig
from nasty_utils.typing_ import checked_cast

_LOGGER = ColoredBraceStyleAdapter(getLogger(__name__))

_T_Config = TypeVar("_T_Config", bound=Optional[Config])


class ArgumentGroup:
    def __init__(self, *, name: str, desc: Optional[str] = None):
        self.name = name
        self.desc = desc


class _Flag:
    def __init__(
        self,
        *,
        name: str,
        short_name: Optional[str] = None,
        desc: str,
        default: bool = False,
    ):
        self.name = name
        self.short_name = short_name
        self.desc = desc
        self.default = default


class _Argument:
    def __init__(
        self,
        *,
        name: str,
        short_name: Optional[str] = None,
        desc: str,
        metavar: Optional[str] = None,
        required: bool = False,
        default: Optional[object] = None,
        deserializer: Optional[Callable[[str], object]] = None,
    ):
        self.name = name
        self.short_name = short_name
        self.desc = desc
        self.metavar = metavar
        self.required = required
        self.default = default
        self.deserializer = deserializer

        if self.required and self.default:
            raise ValueError("Can not use required together with default.")


class ArgumentError(Exception):
    def __init__(self, message: str):
        self.message = message


if TYPE_CHECKING:
    Flag = Any
    Argument = Any
else:
    Flag = _Flag
    Argument = _Argument


class CommandMeta:
    def __init__(
        self, *, name: str, aliases: Optional[Sequence[str]] = None, desc: str
    ):
        self.name = name
        self.aliases = aliases
        self.desc = desc


class Command(Generic[_T_Config]):
    @classmethod
    def meta(cls) -> CommandMeta:
        raise NotImplementedError()

    def __init__(self, config: _T_Config):
        self.config = config

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
        self._raw_args = args
        self._parsed_args = self._load_args()
        self.config = self._load_config()
        self.command: Optional[Command[_T_Config]] = None
        self._parse_args()
        self._log_state()

        try:
            self.run()
        except ArgumentError as e:
            self._argparser.error(e.message)  # noqa: B306

        _LOGGER.debug("Done.")

    def run(self) -> None:
        if self.command:
            try:
                self.command.run()
            except ArgumentError as e:
                self._subparser_by_command_type[type(self.command)].error(
                    e.message  # noqa: B306
                )

    def _load_args(self) -> argparse.Namespace:
        self._argparser = ArgumentParser(
            prog=self._meta.name,
            description=self._meta.desc,
            add_help=False,
            formatter_class=SingleMetavarHelpFormatter,
        )
        self._setup_argparser(self._argparser, type(self))

        self._subparser_by_command_type: MutableMapping[
            Type[Command[_T_Config]], ArgumentParser
        ] = {}
        self._setup_subparsers(self._argparser, Command, name=self._meta.name, depth=0)

        return self._argparser.parse_args(self._raw_args)

    def _setup_argparser(  # noqa: C901
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

        for class_ in reversed(argument_holder.mro()):
            for name, meta in vars(class_).items():
                if isinstance(meta, ArgumentGroup):
                    g = argparser.add_argument_group(
                        title=meta.name, description=meta.desc
                    )

                if not (isinstance(meta, _Flag) or isinstance(meta, _Argument)):
                    continue

                type_ = cast(Optional[Type[Any]], class_.__annotations__.get(name))
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
                "The following commands  are available, each supporting the --help "
                "option."
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
                description=subcommand_meta.desc,
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

            self._setup_argparser(subparser, subcommand)

    def _load_config(self) -> _T_Config:
        if not issubclass(self._meta.config_type, Config):
            return cast(_T_Config, None)

        config_overwrite_path = cast(
            Optional[Path], getattr(self._parsed_args, "config", None)
        )
        config: Config
        if config_overwrite_path:
            config = self._meta.config_type.load_from_config_file(config_overwrite_path)
        else:
            config = self._meta.config_type.find_and_load_from_config_file(
                self._meta.config_file, self._meta.config_dir
            )

        return cast(_T_Config, config)

    def _parse_args(self) -> None:
        command_cls = cast(
            Optional[Type[Command[_T_Config]]],
            getattr(self._parsed_args, "command", None),
        )
        if command_cls:
            self.command = command_cls(self.config)

        argument_holder = self.command or self
        for class_ in reversed(type(argument_holder).mro()):
            for name, meta in vars(class_).items():
                if not (isinstance(meta, _Flag) or isinstance(meta, _Argument)):
                    continue

                raw_value = getattr(self._parsed_args, name)
                if isinstance(meta, _Flag):
                    setattr(argument_holder, name, bool(raw_value))
                elif isinstance(meta, _Argument):
                    type_ = cast(Type[Any], class_.__annotations__.get(name))
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

                    type_check_passed = False
                    if type_origin is Type:
                        type_check_passed = issubclass(value, type_args[0])
                    elif type_origin is Union:
                        type_check_passed = any(isinstance(value, t) for t in type_args)
                    elif type_origin is Callable:
                        type_check_passed = callable(value)
                    else:
                        type_check_passed = isinstance(value, type_)

                    if not type_check_passed:
                        raise ValueError(
                            f"Deserialized value {repr(value)} of argument {name} is "
                            f"not of type {type_}."
                        )

                    setattr(argument_holder, name, value)

    def _log_state(self) -> None:
        if isinstance(self.config, LoggingConfig):
            self.config.setup_logging()

        _LOGGER.debug("Running {} ({}):", self._meta.name, type(self))
        _LOGGER.debug("  Version: {}", self._meta.version)
        _LOGGER.debug("  Raw args: {}", list(self._raw_args))
        _LOGGER.debug("  Argparse args: {}", vars(self._parsed_args))

        if self.command:
            _LOGGER.debug("  Command: {} ({})", self.command.meta().name, self.command)

        _LOGGER.debug("  Parsed args:")
        argument_holder = self.command or self
        for class_ in reversed(type(argument_holder).mro()):
            for name, meta in vars(class_).items():
                if not (isinstance(meta, _Flag) or isinstance(meta, _Argument)):
                    continue
                _LOGGER.debug("    {} = {}", name, repr(getattr(argument_holder, name)))

        if self.config:
            _LOGGER.debug("  Config:")
            for line in toml.dumps(cast(Config, self.config).serialize()).splitlines():
                _LOGGER.debug("    {}", line)
