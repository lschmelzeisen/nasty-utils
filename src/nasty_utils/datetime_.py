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

from datetime import date, datetime, timedelta
from typing import Iterable

from nasty_utils.program import ArgumentError


def parse_yyyy_mm_dd(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


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
    return datetime.strptime(s, "%Y-%m").date()


def parse_yyyy_mm_arg(s: str) -> date:
    try:
        return parse_yyyy_mm(s)
    except ValueError:
        raise ArgumentError(
            f"Can not parse date: '{s}'. Make sure it is in YYYY-MM format."
        )


def format_yyyy_mm(d: date) -> str:
    return d.strftime("%Y-%m")


def advance_date_by_months(num_months: int, current_date: date) -> date:
    if num_months < 0:
        raise ValueError(f"Negative number of months {num_months}.")

    result = current_date
    for _ in range(num_months):
        result += timedelta(days=32)  # Enough days to surely reach next month.
        result = result.replace(day=1)
    return result


# Adapted from: https://stackoverflow.com/a/1060352/211404
def date_range(start_date: date, end_date: date) -> Iterable[date]:
    if start_date > end_date:
        raise ValueError(f"End date {start_date} before start date {end_date}.")

    current_date = start_date
    delta = timedelta(days=1)
    while current_date <= end_date:
        yield current_date
        current_date += delta
