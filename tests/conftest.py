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

import logging

from _pytest.config import Config


def pytest_configure(config: Config) -> None:
    _configure_logging(config)
    _configure_pycharm(config)


def _configure_logging(config: Config) -> None:
    logging.addLevelName(logging.WARNING, "WARN")
    logging.addLevelName(logging.CRITICAL, "CRIT")

    config.option.log_level = "DEBUG"
    config.option.log_format = (
        "%(asctime)s %(levelname)-5.5s [ %(name)-31s ] %(message)s"
    )


def _configure_pycharm(config: Config) -> None:
    # When running pytest from PyCharm enable live cli logging so that we can click a
    # test case and see (only) its log output. When not using PyCharm, this
    # functionality is available via the html report.
    if config.pluginmanager.hasplugin("teamcity.pytest_plugin"):
        config.option.log_cli_level = "DEBUG"
