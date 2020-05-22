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

from datetime import date, datetime

from nasty_utils.program import ArgumentError


def yyyy_mm_dd_deserializer(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def yyyy_mm_dd_arg_deserializer(s: str) -> date:
    try:
        return yyyy_mm_dd_deserializer(s)
    except ValueError:
        raise ArgumentError(
            f"Can not parse date: '{s}'. Make sure it is in YYYY-MM-DD format."
        )


def yyyy_mm_dd_serializer(d: date) -> str:
    return d.strftime("%Y-%m-%d")
