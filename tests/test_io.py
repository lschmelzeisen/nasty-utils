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

import bz2
import gzip
import lzma
from pathlib import Path
from typing import Optional, TextIO, cast

from typing_extensions import Protocol
from zstandard import ZstdCompressor

from nasty_utils import DecompressingTextIOWrapper


class _TOpenFunc(Protocol):
    def __call__(
        self, filename: Path, mode: str, encoding: Optional[str] = None
    ) -> TextIO:
        ...


def test_decompressing_text_io_wrapper(tmp_path: Path) -> None:
    content = "This is just\nsome test content.\n"
    content_len = len(content.encode(encoding="UTF-8"))

    file = tmp_path / "file.txt"
    file.write_text(content, encoding="UTF-8")

    for progress_bar in [True, False]:
        with DecompressingTextIOWrapper(
            file, encoding="UTF-8", progress_bar=progress_bar
        ) as fin:
            assert fin.size() == content_len
            assert fin.tell() == 0
            assert fin.read() == content
            assert fin.tell() == content_len

        with DecompressingTextIOWrapper(
            file, encoding="UTF-8", progress_bar=progress_bar
        ) as fin:
            newline_pos = content.index("\n") + 1
            assert fin.read(4) == "This"
            assert [content[4:newline_pos], content[newline_pos:]] == list(fin)

    for extension, open_func in [
        ("gz", cast(_TOpenFunc, gzip.open)),
        ("bz2", cast(_TOpenFunc, bz2.open)),
        ("xz", cast(_TOpenFunc, lzma.open)),
    ]:
        compressed_file = tmp_path / ("file." + extension)
        with open_func(compressed_file, "wt", encoding="UTF-8") as fout:
            fout.write(content)
        with DecompressingTextIOWrapper(compressed_file, encoding="UTF-8") as fin:
            assert fin.tell() == 0
            assert fin.read() == content
            assert fin.tell() > 0

    compressed_file = tmp_path / "file.zst"
    compressed_file.write_bytes(
        ZstdCompressor().compress(content.encode(encoding="UTF-8"))
    )
    with DecompressingTextIOWrapper(compressed_file, encoding="UTF-8") as fin:
        assert fin.tell() == 0
        assert fin.read() == content
        assert fin.tell() > 0
