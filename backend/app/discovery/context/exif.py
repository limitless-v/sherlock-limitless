"""EXIF / metadata analysis (roadmap Phase 11).

Extracts non-sensitive local metadata (timestamp, camera, device, software,
orientation, presence of GPS). Precise GPS is never exposed automatically:
`ExifMetadata.public_location()` returns only an approximate rounded value.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

_TAG_MAKE = 0x010F
_TAG_MODEL = 0x0110
_TAG_SOFTWARE = 0x0131
_TAG_DATE_TIME = 0x0132
_TAG_ORIENTATION = 0x0112
_TAG_DATE_TIME_ORIGINAL = 0x9003
_TAG_GPS_IFD = 0x8825

_GPS_LAT_REF = 0x0001
_GPS_LAT = 0x0002
_GPS_LON_REF = 0x0003
_GPS_LON = 0x0004


@dataclass
class GpsInfo:
    latitude: float | None
    longitude: float | None

    def is_complete(self) -> bool:
        return self.latitude is not None and self.longitude is not None


@dataclass
class ExifMetadata:
    """Non-sensitive EXIF signals from an image."""

    taken_at: datetime | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    software: str | None = None
    orientation: int | None = None
    gps: GpsInfo | None = None
    raw_keys: set[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.raw_keys is None:
            self.raw_keys = set()

    @property
    def has_gps(self) -> bool:
        return self.gps is not None

    @property
    def camera(self) -> str | None:
        if self.camera_make and self.camera_model:
            return f"{self.camera_make} {self.camera_model}"
        return self.camera_make or self.camera_model

    def public_location(self) -> str | None:
        """Approximate location (2 decimal places ~ 1 km). Never raw GPS."""
        if not self.has_gps or self.gps is None or not self.gps.is_complete():
            return None
        lat = round(self.gps.latitude, 2)
        lon = round(self.gps.longitude, 2)
        return f"{lat:.2f}, {lon:.2f} (approx)"

    def is_empty(self) -> bool:
        return not any(
            [self.taken_at, self.camera_make, self.camera_model, self.software, self.orientation, self.gps]
        )


def _dms_to_decimal(value, ref: str) -> float | None:
    """Convert a (degrees, minutes, seconds) rational GPS value to decimal."""
    try:
        degrees, minutes, seconds = (float(part) for part in value)
    except (TypeError, ValueError):
        return None
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if ref in {"S", "W"}:
        decimal = -decimal
    return round(decimal, 6)


def _parse_exif_datetime(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


class ExifExtractor:
    """Gracefully extracts EXIF metadata; missing/invalid tags are ignored."""

    def has_exif(self, image_path: Path | str) -> bool:
        return not self.extract(image_path).is_empty()

    def extract(self, image_path: Path | str) -> ExifMetadata:
        try:
            with Image.open(image_path) as image:
                exif = image.getexif()
        except (OSError, ValueError):
            return ExifMetadata()
        if not exif:
            return ExifMetadata()

        taken_at = _parse_exif_datetime(exif.get(_TAG_DATE_TIME_ORIGINAL) or exif.get(_TAG_DATE_TIME))
        gps_info = self._extract_gps(exif)
        raw_keys = {TAGS.get(key, f"unknown_{key}") for key in exif}
        if gps_info is not None:
            raw_keys.add(GPSTAGS.get(_TAG_GPS_IFD, "gps"))
        return ExifMetadata(
            taken_at=taken_at,
            camera_make=exif.get(_TAG_MAKE),
            camera_model=exif.get(_TAG_MODEL),
            software=exif.get(_TAG_SOFTWARE),
            orientation=exif.get(_TAG_ORIENTATION),
            gps=gps_info,
            raw_keys=raw_keys,
        )

    @staticmethod
    def _extract_gps(exif) -> GpsInfo | None:
        try:
            gps = exif.get_ifd(_TAG_GPS_IFD)
        except (KeyError, OSError, ValueError):
            return None
        if not gps:
            return None
        lat = _dms_to_decimal(gps.get(_GPS_LAT), gps.get(_GPS_LAT_REF, ""))
        lon = _dms_to_decimal(gps.get(_GPS_LON), gps.get(_GPS_LON_REF, ""))
        if lat is None and lon is None:
            return None
        return GpsInfo(latitude=lat, longitude=lon)