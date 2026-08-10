"""EXIF / metadata analysis unit tests (roadmap Phase 11)."""

from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.TiffImagePlugin import IFDRational

from app.discovery.context.exif import ExifExtractor, ExifMetadata, GpsInfo


def _write_exif_jpeg(path: Path) -> None:
    image = Image.new("RGB", (16, 16), (200, 60, 60))
    exif = image.getexif()
    exif[0x010F] = "TestMake"
    exif[0x0110] = "TestModel 2"
    exif[0x0131] = "FancySoft 1.0"
    exif[0x0112] = 6
    exif[0x0132] = "2023:04:05 10:11:12"
    exif[0x9003] = "2023:04:05 10:11:12"
    exif[0x8825] = {
        0x0001: "N",
        0x0002: (IFDRational(9, 1), IFDRational(34, 1), IFDRational(50, 1)),
        0x0003: "E",
        0x0004: (IFDRational(76, 1), IFDRational(15, 1), IFDRational(0, 1)),
    }
    image.save(path, format="JPEG", exif=exif.tobytes())


def test_extract_reads_camera_timestamp_and_orientation(tmp_path: Path):
    path = tmp_path / "exif.jpg"
    _write_exif_jpeg(path)
    meta = ExifExtractor().extract(path)

    assert meta.camera == "TestMake TestModel 2"
    assert meta.software == "FancySoft 1.0"
    assert meta.orientation == 6
    assert meta.taken_at == datetime(2023, 4, 5, 10, 11, 12)
    assert meta.has_gps


def test_gps_converted_and_rounded_for_half_oriented(tmp_path: Path):
    path = tmp_path / "exif.jpg"
    _write_exif_jpeg(path)
    meta = ExifExtractor().extract(path)
    assert meta.gps is not None
    assert round(meta.gps.latitude, 2) == 9.58
    assert meta.public_location() is not None
    assert "!" not in meta.public_location()
    assert meta.public_location().startswith("9.58,")


def test_no_exif_returns_empty():
    assert ExifMetadata().is_empty()
    assert GpsInfo(None, None).is_complete() is False


def test_missing_and_broken_files_do_not_raise(tmp_path: Path):
    extractor = ExifExtractor()
    missing = extractor.extract(tmp_path / "nope.jpg")
    assert missing.is_empty()
    assert extractor.extract(tmp_path / "nope.jpg") is not None