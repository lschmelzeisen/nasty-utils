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

import json
from pathlib import Path

import pytest

from nasty_utils import FileNotOnServerError, download_file_with_progressbar, sha256sum


def test_download_file_with_progressbar(tmp_path: Path) -> None:
    dest = tmp_path / "does-not-eixst.txt"
    with pytest.raises(FileNotOnServerError):
        download_file_with_progressbar(
            "https://example.org/" + dest.name, dest=dest, description=dest.name
        )
    assert not dest.exists()

    dest = tmp_path / "file_example_JSON_1kb.json"
    download_file_with_progressbar(
        "https://file-examples-com.github.io/uploads/2017/02/" + dest.name,
        dest=dest,
        description=dest.name,
    )

    # Validate download.
    with dest.open("r", encoding="UTF-8") as fin:
        content = json.load(fin)
        assert len(content["countries"]) == 246
        for country in content["countries"]:
            assert "name" in country and "isoCode" in country


def test_sha256sum(tmp_path: Path) -> None:
    file = tmp_path / "file"
    with file.open("w", encoding="UTF-8") as fout:
        fout.write("test\n")

    expected = "f2ca1bb6c7e907d06dafe4687e579fce76b37e4e93b7605022da52e6ccc26fd2"
    assert sha256sum(file) == expected
    with file.open("rb") as fin:
        assert sha256sum(fin) == expected
