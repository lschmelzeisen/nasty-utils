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

from datetime import date, datetime, timedelta, tzinfo
from typing import Iterable, Optional

from nasty_utils.program import ArgumentError


def parse_yyyy_mm_dd(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return datetime.strptime(s, "%Y%m%d").date()


def parse_yyyy_mm_dd_arg(s: str) -> date:
    try:
        return parse_yyyy_mm_dd(s)
    except ValueError:
        raise ArgumentError(
            f"Can not parse date: '{s}'. Make sure it is in YYYY-MM-DD format."
        )


def format_yyyy_mm_dd(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def parse_yyyy_mm(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m").date()
    except ValueError:
        return datetime.strptime(s, "%Y%m").date()


def parse_yyyy_mm_arg(s: str) -> date:
    try:
        return parse_yyyy_mm(s)
    except ValueError:
        raise ArgumentError(
            f"Can not parse date: '{s}'. Make sure it is in YYYY-MM format."
        )


def format_yyyy_mm(d: date) -> str:
    return d.strftime("%Y-%m")


# Adapted from: https://stackoverflow.com/a/1060352/211404
def date_range(start_date: date, end_date: date) -> Iterable[date]:
    if start_date > end_date:
        raise ValueError(f"End date {start_date} before start date {end_date}.")

    current_date = start_date
    delta = timedelta(days=1)
    while current_date <= end_date:
        yield current_date
        current_date += delta


# See: https://stackoverflow.com/a/1937636/211404
def date_to_datetime(d: date, tzinfo_: Optional[tzinfo]) -> datetime:
    return datetime.combine(d, datetime.min.time(), tzinfo=tzinfo_)


def date_to_timestamp(d: date, tzinfo_: Optional[tzinfo]) -> float:
    return date_to_datetime(d, tzinfo_).timestamp()
