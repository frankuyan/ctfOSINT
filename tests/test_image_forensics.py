"""Tests for the image forensics module and the `exif` command.

Fixtures are generated with Pillow at test time; no binary files are
checked in.
"""

import io
import json
import zlib
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from PIL import Image, PngImagePlugin
from PIL.TiffImagePlugin import IFDRational

from sherlockml.cli import main
from sherlockml.config import Config
from sherlockml.extract.image_forensics import (
    _MAX_INFLATE,
    _inflate,
    _walk_jpeg,
    analyze_image,
    iter_image_files,
    sniff_type,
)


def _jpeg_bytes(exif: Image.Exif | None = None, comment: bytes | None = None) -> bytes:
    buf = io.BytesIO()
    kwargs = {}
    if exif is not None:
        kwargs["exif"] = exif
    if comment is not None:
        kwargs["comment"] = comment
    Image.new("RGB", (16, 8), "blue").save(buf, "JPEG", **kwargs)
    return buf.getvalue()


def _png_bytes(info: PngImagePlugin.PngInfo | None = None) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "green").save(buf, "PNG", pnginfo=info)
    return buf.getvalue()


def _png_chunk(ctype: bytes, body: bytes) -> bytes:
    crc = zlib.crc32(ctype + body).to_bytes(4, "big")
    return len(body).to_bytes(4, "big") + ctype + body + crc


@pytest.fixture
def geotagged_jpeg(tmp_path):
    """JPEG with camera, timestamps, southern/western GPS and hidden text."""
    exif = Image.Exif()
    exif[0x010F] = "Canon"
    exif[0x0110] = "EOS 5D"
    exif[0x0131] = "Adobe Photoshop 25.0"
    exif[0x9C9C] = "secret note".encode("utf-16-le") + b"\x00\x00"
    sub = exif.get_ifd(0x8769)
    sub[0x9003] = "2023:07:14 18:30:00"
    sub[0x9286] = b"ASCII\x00\x00\x00flag{user_comment}"
    gps = exif.get_ifd(0x8825)
    gps[1] = "S"
    gps[2] = (IFDRational(33), IFDRational(51), IFDRational(5400, 100))
    gps[3] = "W"
    gps[4] = (IFDRational(70), IFDRational(30), IFDRational(0))
    gps[5] = b"\x00"
    gps[6] = IFDRational(520)
    path = tmp_path / "photo.jpg"
    path.write_bytes(_jpeg_bytes(exif, comment=b"shot from the roof"))
    return path


class TestJpeg:
    def test_hashes_and_type(self, geotagged_jpeg):
        import hashlib

        report = analyze_image(geotagged_jpeg)
        data = geotagged_jpeg.read_bytes()
        assert report.sha256 == hashlib.sha256(data).hexdigest()
        assert report.md5 == hashlib.md5(data).hexdigest()
        assert report.detected_type == "jpeg"
        assert not report.extension_mismatch
        assert (report.width, report.height) == (16, 8)

    def test_camera_and_timestamps(self, geotagged_jpeg):
        report = analyze_image(geotagged_jpeg)
        assert report.camera == {
            "make": "Canon", "model": "EOS 5D", "software": "Adobe Photoshop 25.0",
        }
        assert report.timestamps["DateTimeOriginal"] == "2023:07:14 18:30:00"

    def test_gps_south_west_negative(self, geotagged_jpeg):
        gps = analyze_image(geotagged_jpeg).gps
        assert gps["latitude"] == pytest.approx(-33.865)
        assert gps["longitude"] == pytest.approx(-70.5)
        assert gps["altitude_m"] == 520.0
        assert "google.com/maps?q=-33.865,-70.5" in gps["google_maps"]

    def test_hidden_text_and_flags(self, geotagged_jpeg):
        report = analyze_image(geotagged_jpeg)
        assert report.text["XPComment"] == "secret note"
        assert report.text["UserComment"] == "flag{user_comment}"
        assert report.text["jpeg_comment"] == "shot from the roof"
        assert report.flags_found == ["flag{user_comment}"]

    def test_clean_file_has_no_trailing_data(self, geotagged_jpeg):
        assert analyze_image(geotagged_jpeg).trailing_data is None

    def test_appended_zip_detected(self, tmp_path):
        clean = _jpeg_bytes()
        path = tmp_path / "cat.jpg"
        path.write_bytes(clean + b"junk" + b"PK\x03\x04flag{appended}")
        report = analyze_image(path)
        assert report.trailing_data["offset"] == len(clean)
        assert report.trailing_data["size_bytes"] == 4 + 4 + len("flag{appended}")
        assert report.trailing_data["embedded_type"] == "zip"
        assert report.trailing_data["embedded_offset"] == len(clean) + 4
        assert "flag{appended}" in report.flags_found

    def test_eoi_inside_segment_or_scan_is_not_end(self):
        # APP2 payload contains FF D9 (as an EXIF thumbnail would); scan
        # data has a stuffed FF 00 and an RST marker.  Only the final
        # EOI ends the image.
        app2 = b"\xff\xe2" + (2 + 6).to_bytes(2, "big") + b"ab\xff\xd9cd"
        sos = b"\xff\xda" + (2 + 2).to_bytes(2, "big") + b"\x00\x00"
        scan = b"\x12\xff\x00\x34\xff\xd3\x56"
        jpeg = b"\xff\xd8" + app2 + sos + scan + b"\xff\xd9"
        assert _walk_jpeg(jpeg + b"TRAILER", {}) == len(jpeg)

    def test_untrusted_markup_does_not_break_cli(self, tmp_path):
        exif = Image.Exif()
        exif[0x010F] = "[bold]Evil[/i] [/]"
        path = tmp_path / "evil.jpg"
        path.write_bytes(_jpeg_bytes(exif))
        with patch("sherlockml.cli.load_config", return_value=Config()):
            result = CliRunner().invoke(main, ["exif", str(path)])
        assert result.exit_code == 0, result.output
        assert "[bold]Evil[/i] [/]" in result.output


class TestPng:
    def test_text_chunks(self, tmp_path):
        info = PngImagePlugin.PngInfo()
        info.add_text("Author", "plain text")
        info.add_text("Comment", "flag{ztxt_hidden}", zip=True)
        info.add_itxt("Description", "ünïcode itxt", lang="en", tkey="Desc")
        path = tmp_path / "pic.png"
        path.write_bytes(_png_bytes(info))
        report = analyze_image(path)
        assert report.text["png:Author"] == "plain text"
        assert report.text["png:Comment"] == "flag{ztxt_hidden}"
        assert report.text["png:Description"] == "ünïcode itxt"
        # zTXt content is compressed on disk: only found via decoding
        assert report.flags_found == ["flag{ztxt_hidden}"]
        assert {"IHDR", "tEXt", "zTXt", "iTXt", "IDAT", "IEND"} <= set(report.png_chunks)

    def test_custom_chunk_listed(self, tmp_path):
        data = _png_bytes()
        iend = data.rindex(b"IEND") - 4
        data = data[:iend] + _png_chunks_custom() + data[iend:]
        path = tmp_path / "custom.png"
        path.write_bytes(data)
        assert "flAg" in analyze_image(path).png_chunks

    def test_data_after_iend(self, tmp_path):
        clean = _png_bytes()
        path = tmp_path / "pic.png"
        path.write_bytes(clean + b"\x89PNG\r\n\x1a\nsecond image")
        report = analyze_image(path)
        assert report.trailing_data["offset"] == len(clean)
        assert report.trailing_data["embedded_type"] == "png"

    def test_inflate_is_capped(self):
        bomb = zlib.compress(b"\x00" * (_MAX_INFLATE * 4))
        assert len(_inflate(bomb)) == _MAX_INFLATE


def _png_chunks_custom() -> bytes:
    return _png_chunk(b"flAg", b"private data")


class TestFileType:
    def test_png_named_jpg_is_mismatch(self, tmp_path):
        path = tmp_path / "really_png.jpg"
        path.write_bytes(_png_bytes())
        report = analyze_image(path)
        assert report.detected_type == "png"
        assert report.extension_mismatch
        assert report.findings[0].startswith("extension .jpg but content is png")

    def test_zip_named_png_is_mismatch(self, tmp_path):
        path = tmp_path / "archive.png"
        path.write_bytes(b"PK\x03\x04" + b"\x00" * 30)
        report = analyze_image(path)
        assert report.detected_type == "zip"
        assert report.extension_mismatch

    def test_non_image(self, tmp_path):
        path = tmp_path / "notes.txt"
        path.write_text("just text with flag{in_plain_text}")
        report = analyze_image(path)
        assert report.detected_type is None
        assert not report.extension_mismatch
        assert report.error == "Not a recognised image format"
        assert report.flags_found == ["flag{in_plain_text}"]

    @pytest.mark.parametrize("head,kind", [
        (b"\xff\xd8\xff\xe0", "jpeg"),
        (b"GIF89a", "gif"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "webp"),
        (b"%PDF-1.7", "pdf"),
        (b"hello", None),
    ])
    def test_sniff(self, head, kind):
        assert sniff_type(head) == kind


class TestDirectoryScan:
    def test_finds_images_by_extension_and_magic(self, tmp_path):
        (tmp_path / "a.jpg").write_bytes(_jpeg_bytes())
        (tmp_path / "renamed").write_bytes(_png_bytes())
        (tmp_path / "notes.txt").write_text("hello")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.png").write_bytes(_png_bytes())

        flat = {p.name for p in iter_image_files([tmp_path])}
        assert flat == {"a.jpg", "renamed"}
        deep = {p.name for p in iter_image_files([tmp_path], recursive=True)}
        assert deep == {"a.jpg", "renamed", "b.png"}

    def test_cli_writes_json(self, tmp_path, geotagged_jpeg):
        out = tmp_path / "report.json"
        with patch("sherlockml.cli.load_config", return_value=Config()):
            result = CliRunner().invoke(main, ["exif", str(geotagged_jpeg), "-o", str(out)])
        assert result.exit_code == 0, result.output
        assert "GPS:" in result.output and "flag{user_comment}" in result.output
        (entry,) = json.loads(out.read_text())
        assert entry["gps"]["latitude"] == pytest.approx(-33.865)
        assert entry["findings"]
