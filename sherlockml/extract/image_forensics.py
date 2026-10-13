"""Image forensics: hashes, EXIF/GPS, embedded text and appended data.

Covers the checks that come up constantly in OSINT and CTF forensics work:

* MD5/SHA-1/SHA-256 of the file (for evidence logs and hash lookups)
* real file type from magic bytes vs. the extension (renamed files)
* EXIF: camera, software, timestamps, and GPS converted to decimal
  coordinates with map links
* text hidden in metadata: PNG tEXt/zTXt/iTXt chunks, JPEG comments,
  XMP packets, Windows XP* tags and the EXIF UserComment
* data appended after the image's end marker (JPEG EOI / PNG IEND),
  including the type of any embedded file (zip, rar, png, ...)
* CTF flag patterns anywhere in the file or its decoded metadata

JPEG and PNG structure is walked directly, so pixel data is never decoded.
Pillow is only used to read EXIF tags and image dimensions.
"""

from __future__ import annotations

import hashlib
import zlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sherlockml.flags import compile_flag_patterns, find_flags

# Magic signatures checked at the start of a file and inside appended data.
SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"PK\x03\x04", "zip"),
    (b"Rar!\x1a\x07", "rar"),
    (b"7z\xbc\xaf\x27\x1c", "7z"),
    (b"%PDF", "pdf"),
    (b"\x1f\x8b", "gzip"),
    (b"BZh", "bzip2"),
    (b"\x7fELF", "elf"),
    (b"MZ", "exe"),
    (b"II*\x00", "tiff"),
    (b"MM\x00*", "tiff"),
    (b"BM", "bmp"),
)

# Types searched for inside appended data.  Short magics (MZ, BM, gzip)
# are left out: they occur by chance in compressed bytes.
_EMBEDDED_TYPES = {"jpeg", "png", "gif", "zip", "rar", "7z", "pdf", "elf"}

# Expected extensions per detected image type (camera RAW formats are TIFF)
_EXTENSIONS: dict[str, set[str]] = {
    "jpeg": {".jpg", ".jpeg", ".jpe", ".jfif"},
    "png": {".png"},
    "gif": {".gif"},
    "tiff": {".tif", ".tiff", ".dng", ".cr2", ".nef", ".arw"},
    "bmp": {".bmp", ".dib"},
    "webp": {".webp"},
    "heic": {".heic", ".heif"},
}

IMAGE_EXTENSIONS: frozenset[str] = frozenset(set().union(*_EXTENSIONS.values()))

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_XMP_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"
_MAX_TEXT = 4096          # chars kept per decoded metadata string
_MAX_INFLATE = 1 << 20    # cap on decompressed zTXt/iTXt (zip-bomb guard)

# EXIF IFD pointers and tags with special decoding
_EXIF_IFD, _GPS_IFD = 0x8769, 0x8825
_USER_COMMENT, _MAKER_NOTE = 0x9286, 0x927C
_XP_TAGS = {0x9C9B: "XPTitle", 0x9C9C: "XPComment", 0x9C9D: "XPAuthor",
            0x9C9E: "XPKeywords", 0x9C9F: "XPSubject"}
_TIMESTAMP_TAGS = ("DateTime", "DateTimeOriginal", "DateTimeDigitized")
_CAMERA_TAGS = {"Make": "make", "Model": "model", "LensModel": "lens",
                "Software": "software", "BodySerialNumber": "serial",
                "Artist": "artist", "Copyright": "copyright",
                "HostComputer": "host_computer"}


@dataclass
class ImageReport:
    """Forensic findings for one file."""
    path: str
    size_bytes: int
    md5: str
    sha1: str
    sha256: str
    detected_type: str | None = None
    extension: str = ""
    extension_mismatch: bool = False
    width: int | None = None
    height: int | None = None
    camera: dict[str, str] = field(default_factory=dict)
    timestamps: dict[str, str] = field(default_factory=dict)
    gps: dict[str, Any] | None = None
    exif: dict[str, Any] = field(default_factory=dict)
    text: dict[str, str] = field(default_factory=dict)
    png_chunks: list[str] = field(default_factory=list)
    trailing_data: dict[str, Any] | None = None
    flags_found: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def findings(self) -> list[str]:
        """Short human-readable list of the things worth a closer look."""
        notes = []
        if self.extension_mismatch:
            notes.append(f"extension {self.extension or '(none)'} but content is {self.detected_type}")
        if self.gps:
            notes.append(f"GPS {self.gps['latitude']}, {self.gps['longitude']}")
        if self.trailing_data:
            kind = self.trailing_data.get("embedded_type") or "unknown data"
            notes.append(f"{self.trailing_data['size_bytes']} bytes appended after end of image ({kind})")
        if self.text:
            notes.append(f"embedded text: {', '.join(sorted(self.text))}")
        if self.flags_found:
            notes.append(f"{len(self.flags_found)} flag(s)")
        return notes

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["findings"] = self.findings
        return data


def sniff_type(data: bytes) -> str | None:
    """Identify a file type from its leading magic bytes."""
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heix", b"mif1", b"msf1"):
        return "heic"
    for magic, kind in SIGNATURES:
        if data.startswith(magic):
            return kind
    return None


def _clip(text: str) -> str:
    text = text.replace("\x00", "").strip()
    return text if len(text) <= _MAX_TEXT else text[:_MAX_TEXT] + "…"


def _inflate(data: bytes) -> bytes:
    """zlib-decompress at most _MAX_INFLATE bytes."""
    try:
        return zlib.decompressobj().decompress(data, _MAX_INFLATE)
    except zlib.error:
        return b""


# --- Container walkers -------------------------------------------------------

def _walk_jpeg(data: bytes, text: dict[str, str]) -> int | None:
    """Walk JPEG segments; collect COM/XMP text and return the end offset.

    Segment lengths are followed (so an EXIF thumbnail's own EOI inside
    APP1 is skipped), and entropy-coded scan data is scanned for the next
    real marker, ignoring stuffed 0xFF00 bytes and RSTn markers.
    """
    if not data.startswith(b"\xff\xd8"):
        return None
    i, n = 2, len(data)
    comments: list[str] = []
    while i < n - 1:
        if data[i] != 0xFF:
            return None
        marker = data[i + 1]
        if marker == 0xFF:          # fill byte
            i += 1
            continue
        if marker == 0xD9:          # EOI
            end = i + 2
            break
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:   # standalone markers
            i += 2
            continue
        if i + 4 > n:
            return None
        length = int.from_bytes(data[i + 2:i + 4], "big")
        payload = data[i + 4:i + 2 + length]
        if marker == 0xFE:
            comments.append(payload.decode("utf-8", errors="replace"))
        elif marker == 0xE1 and payload.startswith(_XMP_HEADER):
            text["xmp"] = _clip(payload[len(_XMP_HEADER):].decode("utf-8", errors="replace"))
        i += 2 + length
        if marker == 0xDA:          # SOS: skip entropy-coded data
            while True:
                j = data.find(b"\xff", i, n - 1)
                if j == -1:
                    i = n
                    break
                following = data[j + 1]
                if following == 0x00 or 0xD0 <= following <= 0xD7:
                    i = j + 2       # stuffed byte or restart marker
                    continue
                i = j
                break
    else:
        end = None
    if comments:
        text["jpeg_comment"] = _clip("\n".join(comments))
    return end


def _walk_png(data: bytes, text: dict[str, str], chunks: list[str]) -> int | None:
    """Walk PNG chunks; collect text chunks and return the offset after IEND."""
    if not data.startswith(_PNG_SIGNATURE):
        return None
    i, n = len(_PNG_SIGNATURE), len(data)
    while i + 8 <= n:
        length = int.from_bytes(data[i:i + 4], "big")
        ctype = data[i + 4:i + 8].decode("latin-1")
        body = data[i + 8:i + 8 + length]
        if ctype not in chunks:
            chunks.append(ctype)
        key, _, rest = body.partition(b"\x00")
        name = key.decode("latin-1", errors="replace")
        if ctype == "tEXt":
            text[f"png:{name}"] = _clip(rest.decode("latin-1"))
        elif ctype == "zTXt":
            text[f"png:{name}"] = _clip(_inflate(rest[1:]).decode("latin-1"))
        elif ctype == "iTXt" and len(rest) >= 2:
            compressed = rest[0] == 1
            _lang, _, rest2 = rest[2:].partition(b"\x00")
            _translated, _, value = rest2.partition(b"\x00")
            if compressed:
                value = _inflate(value)
            text[f"png:{name}"] = _clip(value.decode("utf-8", errors="replace"))
        i += 12 + length
        if ctype == "IEND":
            return i
    return None


def _trailing(data: bytes, end: int | None) -> dict[str, Any] | None:
    if end is None or end >= len(data):
        return None
    extra = data[end:]
    embedded = None
    for magic, kind in SIGNATURES:
        if kind not in _EMBEDDED_TYPES:
            continue
        pos = extra.find(magic)
        if pos != -1 and (embedded is None or pos < embedded[0]):
            embedded = (pos, kind)
    return {
        "offset": end,
        "size_bytes": len(extra),
        "sha256": hashlib.sha256(extra).hexdigest(),
        "embedded_type": embedded[1] if embedded else None,
        "embedded_offset": end + embedded[0] if embedded else None,
        "preview": "".join(chr(b) if 32 <= b < 127 else "." for b in extra[:64]),
    }


# --- EXIF ---------------------------------------------------------------------

def _bytes_repr(value: bytes) -> str:
    """Printable text if ``value`` is text, else a short hex summary."""
    try:
        text = value.rstrip(b"\x00").decode("utf-8")
        if all(c.isprintable() or c.isspace() for c in text):
            return _clip(text)
    except UnicodeDecodeError:
        pass
    return f"<{len(value)} bytes: {value[:32].hex()}>"


def _json_safe(value: Any) -> Any:
    from PIL.TiffImagePlugin import IFDRational

    if isinstance(value, IFDRational):
        return None if value.denominator == 0 else round(float(value), 6)
    if isinstance(value, (tuple, list)):
        return [_json_safe(v) for v in value]
    if isinstance(value, bytes):
        return _bytes_repr(value)
    if isinstance(value, str):
        return _clip(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _clip(str(value))


def _decode_tag(tag: int, value: Any) -> Any:
    if tag in _XP_TAGS and isinstance(value, (bytes, tuple)):
        raw = bytes(value)
        return _clip(raw.decode("utf-16-le", errors="replace"))
    if tag == _USER_COMMENT and isinstance(value, bytes):
        prefix, body = value[:8], value[8:]
        if prefix.startswith(b"UNICODE"):
            return _clip(body.decode("utf-16", errors="replace"))
        return _clip(body.decode("latin-1"))
    if tag == _MAKER_NOTE and isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    return _json_safe(value)


def _gps_decimal(dms: Any, ref: Any) -> float | None:
    try:
        degrees, minutes, seconds = (float(x) for x in dms)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    value = degrees + minutes / 60 + seconds / 3600
    if str(ref).strip().upper() in ("S", "W"):
        value = -value
    return round(value, 6)


def _parse_gps(gps_ifd: dict[int, Any]) -> dict[str, Any] | None:
    lat = _gps_decimal(gps_ifd.get(2), gps_ifd.get(1))
    lon = _gps_decimal(gps_ifd.get(4), gps_ifd.get(3))
    if lat is None or lon is None:
        return None
    gps: dict[str, Any] = {
        "latitude": lat,
        "longitude": lon,
        "google_maps": f"https://www.google.com/maps?q={lat},{lon}",
        "openstreetmap": f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=17/{lat}/{lon}",
    }
    if 6 in gps_ifd:
        try:
            altitude = float(gps_ifd[6])
            if gps_ifd.get(5) in (1, b"\x01"):
                altitude = -altitude
            gps["altitude_m"] = round(altitude, 2)
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    if 29 in gps_ifd:
        gps["timestamp_utc"] = str(gps_ifd[29])
        if 7 in gps_ifd:
            try:
                h, m, s = (float(x) for x in gps_ifd[7])
                gps["timestamp_utc"] += f" {int(h):02d}:{int(m):02d}:{s:05.2f}"
            except (TypeError, ValueError, ZeroDivisionError):
                pass
    return gps


def _read_exif(path: Path, report: ImageReport) -> None:
    from PIL import ExifTags, Image, UnidentifiedImageError

    try:
        with Image.open(path) as img:
            report.width, report.height = img.size
            exif = img.getexif()
            tags: dict[str, Any] = {}
            for tag, value in exif.items():
                if tag in (_EXIF_IFD, _GPS_IFD):
                    continue
                tags[ExifTags.TAGS.get(tag, f"0x{tag:04x}")] = _decode_tag(tag, value)
            for tag, value in exif.get_ifd(_EXIF_IFD).items():
                tags[ExifTags.TAGS.get(tag, f"0x{tag:04x}")] = _decode_tag(tag, value)
            gps_ifd = dict(exif.get_ifd(_GPS_IFD))
    except UnidentifiedImageError as e:
        report.error = f"Could not read image metadata: {e}"
        return
    except Exception as e:  # noqa: BLE001 - hostile files can trip any parser error
        report.error = f"Could not read image metadata ({type(e).__name__}): {e}"
        return

    for name in _XP_TAGS.values():
        if name in tags:
            report.text[name] = tags[name]
    if tags.get("UserComment"):
        report.text["UserComment"] = tags["UserComment"]
    report.exif = tags
    report.camera = {
        key: str(tags[tag]) for tag, key in _CAMERA_TAGS.items() if tags.get(tag)
    }
    report.timestamps = {name: str(tags[name]) for name in _TIMESTAMP_TAGS if tags.get(name)}
    if gps_ifd:
        report.gps = _parse_gps(gps_ifd)
        report.exif["GPSInfo"] = {
            ExifTags.GPSTAGS.get(k, str(k)): _decode_tag(k, v) for k, v in gps_ifd.items()
        }


# --- Public API ---------------------------------------------------------------

def analyze_image(
    path: Path | str,
    flag_patterns: list[str] | None = None,
) -> ImageReport:
    """Run every check on one file and return the findings."""
    path = Path(path)
    data = path.read_bytes()
    report = ImageReport(
        path=str(path),
        size_bytes=len(data),
        md5=hashlib.md5(data, usedforsecurity=False).hexdigest(),
        sha1=hashlib.sha1(data, usedforsecurity=False).hexdigest(),
        sha256=hashlib.sha256(data).hexdigest(),
        detected_type=sniff_type(data),
        extension=path.suffix.lower(),
    )
    if report.detected_type in _EXTENSIONS:
        # An image saved under the wrong image extension (or none)
        report.extension_mismatch = report.extension not in _EXTENSIONS[report.detected_type]
    elif report.detected_type is not None:
        # Named like an image but actually e.g. a zip or PDF
        report.extension_mismatch = report.extension in IMAGE_EXTENSIONS

    end = None
    if report.detected_type == "jpeg":
        end = _walk_jpeg(data, report.text)
    elif report.detected_type == "png":
        end = _walk_png(data, report.text, report.png_chunks)
    report.trailing_data = _trailing(data, end)

    if report.detected_type in _EXTENSIONS:
        _read_exif(path, report)
    elif report.detected_type is None:
        report.error = "Not a recognised image format"

    # Flags anywhere: raw bytes (as latin-1 so every byte maps to a char)
    # plus decoded metadata, which catches UTF-16 XP tags and zTXt content.
    patterns = compile_flag_patterns(flag_patterns)
    haystacks = [data.decode("latin-1"), *report.text.values()]
    for hay in haystacks:
        for flag in find_flags(hay, patterns):
            if flag not in report.flags_found:
                report.flags_found.append(flag)
    return report


def iter_image_files(paths: list[Path], recursive: bool = False) -> list[Path]:
    """Expand directories into the image files they contain.

    Files named explicitly are always included; inside directories a file
    is included if its extension looks like an image or its magic bytes do
    (so renamed images are not missed).
    """
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            candidates = p.rglob("*") if recursive else p.iterdir()
            for f in sorted(candidates):
                if not f.is_file():
                    continue
                if f.suffix.lower() in IMAGE_EXTENSIONS:
                    files.append(f)
                    continue
                try:
                    with f.open("rb") as fh:
                        head = fh.read(16)
                except OSError:
                    continue
                if sniff_type(head) in _EXTENSIONS:
                    files.append(f)
        else:
            files.append(p)
    return files
