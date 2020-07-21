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

from datetime import date, datetime, timezone

from nasty_utils import (
    advance_date_by_month,
    date_range,
    date_to_datetime,
    date_to_timestamp,
    format_yyyy_mm,
    format_yyyy_mm_dd,
    parse_yyyy_mm,
    parse_yyyy_mm_dd,
)


def test_parse_yyyy_mm_dd() -> None:
    assert parse_yyyy_mm_dd("2020-03-05") == date(2020, 3, 5)
    assert parse_yyyy_mm_dd("2020-3-5") == date(2020, 3, 5)
    assert parse_yyyy_mm_dd("20200106") == date(2020, 1, 6)
    assert parse_yyyy_mm_dd("202016") == date(2020, 1, 6)


def test_format_yyyy_mm_dd() -> None:
    assert format_yyyy_mm_dd(date(2020, 3, 5)) == "2020-03-05"


def test_parse_yyyy_mm() -> None:
    assert parse_yyyy_mm("2020-03") == date(2020, 3, 1)
    assert parse_yyyy_mm("20203") == date(2020, 3, 1)


def test_format_yyyy_mm() -> None:
    assert format_yyyy_mm(date(2020, 3, 5)) == "2020-03"


def test_advance_date_by_months() -> None:
    assert advance_date_by_month(date(2020, 1, 1)) == date(2020, 2, 1)
    assert advance_date_by_month(date(2020, 1, 3)) == date(2020, 2, 3)
    assert advance_date_by_month(date(2020, 1, 31)) == date(2020, 2, 29)
    assert advance_date_by_month(date(2019, 1, 31)) == date(2019, 2, 28)
    assert advance_date_by_month(date(2020, 1, 31), num_months=2) == date(2020, 3, 31)
    assert advance_date_by_month(date(2020, 1, 31), num_months=3) == date(2020, 4, 30)


def test_date_range() -> None:
    assert list(date_range(date(2020, 1, 28), date(2020, 2, 3))) == [
        date(2020, 1, 28),
        date(2020, 1, 29),
        date(2020, 1, 30),
        date(2020, 1, 31),
        date(2020, 2, 1),
        date(2020, 2, 2),
        date(2020, 2, 3),
    ]


def test_date_to_datetime() -> None:
    assert date_to_datetime(date(2020, 3, 5), None) == datetime(2020, 3, 5)


def test_date_to_timestamp() -> None:
    assert date_to_timestamp(date(1970, 1, 1), timezone.utc) == 0
