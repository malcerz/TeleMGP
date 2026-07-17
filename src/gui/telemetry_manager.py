"""Telemetry data manager – loads, caches and resolves telemetry data from
GPMF (ExifTool), GPX and FIT sources."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

# Import telemetry modules (with fallback stubs)
try:
    from telemetry_gpx import (
        find_gpx_for_video,
        parse_gpx,
        process_gpx,
        sync_gpx_to_video,
    )
    _GPX_AVAILABLE = True
except ImportError:
    _GPX_AVAILABLE = False

    def process_gpx(video_path, video_start_dt=None):  # noqa: E302
        return None

    def find_gpx_for_video(video_path):  # noqa: E302
        return None

    def parse_gpx(path):  # noqa: E302
        return None

    def sync_gpx_to_video(points, video_start_dt):  # noqa: E302
        return None, None, None, None, None, None, None


try:
    from telemetry_fit import (
        find_fit_for_video,
        parse_fit,
        process_fit,
        sync_fit_to_video,
    )
    _FIT_AVAILABLE = True
except ImportError:
    _FIT_AVAILABLE = False

    def process_fit(video_path, video_start_dt=None):  # noqa: E302
        return None

    def find_fit_for_video(video_path):  # noqa: E302
        return None

    def parse_fit(path):  # noqa: E302
        return None

    def sync_fit_to_video(points, video_start_dt):  # noqa: E302
        return None, None, None, None, None, None, None, None


# ---- Type aliases ----
Sample = tuple[datetime, float]
SampleList = list[Sample]


class TelemetryDataManager:
    """Manages all telemetry data loading, caching, and source-resolution.

    This class holds all sample data from GPMF (GoPro), GPX, and FIT sources
    and provides methods to resolve values with configurable priority (FIT > GPX > GPMF).
    """

    def __init__(
        self,
        extract_speed_fn: Optional[Callable] = None,
        extract_altitude_fn: Optional[Callable] = None,
        extract_track_fn: Optional[Callable] = None,
        extract_iso_fn: Optional[Callable] = None,
        extract_exposure_fn: Optional[Callable] = None,
        extract_temperature_fn: Optional[Callable] = None,
        smooth_fn: Optional[Callable] = None,
        interpolate_fn: Optional[Callable] = None,
        get_rotation_meta_fn: Optional[Callable] = None,
        get_container_rotation_fn: Optional[Callable] = None,
        find_meta_json_fn: Optional[Callable] = None,
        find_meta_json_write_fn: Optional[Callable] = None,
        load_telemetry_fn: Optional[Callable] = None,
        ensure_records_fn: Optional[Callable] = None,
        load_json_fallback_fn: Optional[Callable] = None,
        write_records_fn: Optional[Callable] = None,
    ) -> None:
        # GPMF samples
        self.records: list[dict] = []
        self.speed_samples: SampleList = []
        self.alt_samples: SampleList = []
        self.track_samples: SampleList = []
        self.iso_samples: SampleList = []
        self.exposure_samples: SampleList = []
        self.temperature_samples: SampleList = []

        # GPX samples
        self.gpx_speed_samples: SampleList = []
        self.gpx_alt_samples: SampleList = []
        self.gpx_track_samples: SampleList = []
        self.gpx_power_samples: SampleList = []
        self.gpx_atemp_samples: SampleList = []
        self.gpx_hr_samples: SampleList = []
        self.gpx_cad_samples: SampleList = []

        # FIT samples
        self.fit_speed_samples: SampleList = []
        self.fit_alt_samples: SampleList = []
        self.fit_track_samples: SampleList = []
        self.fit_power_samples: SampleList = []
        self.fit_atemp_samples: SampleList = []
        self.fit_hr_samples: SampleList = []
        self.fit_cad_samples: SampleList = []
        self.fit_battery_samples: SampleList = []

        # Metadata
        self.start_dt_utc: Optional[datetime] = None
        self.meta_path: Optional[Path] = None
        self.gpx_path: Optional[Path] = None  # manually selected GPX
        self.fit_path: Optional[Path] = None  # manually selected FIT
        self.video_path: Optional[Path] = None
        self.video_paths_to_process: list[Path] = []

        # Video info (set during loading)
        self.video_duration_s: float = 0.0
        self.fps: float = 30.0

        # Tool paths
        self.ffprobe_path: Any = None
        self.ffmpeg_exe: Any = None
        self.ffprobe_exe: Any = None
        self.exiftool_path: Any = None

        # Function references injected by HudTunerApp
        self._extract_speed = extract_speed_fn
        self._extract_altitude = extract_altitude_fn
        self._extract_track = extract_track_fn
        self._extract_iso = extract_iso_fn
        self._extract_exposure = extract_exposure_fn
        self._extract_temperature = extract_temperature_fn
        self._smooth_fn = smooth_fn
        self._interpolate_fn = interpolate_fn
        self._get_rotation_meta = get_rotation_meta_fn
        self._get_container_rotation = get_container_rotation_fn
        self._find_meta_json = find_meta_json_fn
        self._find_meta_json_write = find_meta_json_write_fn
        self._load_telemetry = load_telemetry_fn
        self._ensure_records = ensure_records_fn
        self._load_json_fallback = load_json_fallback_fn
        self._write_records = write_records_fn

        # Refresh / UI callbacks (set by HudTunerApp)
        self._on_telemetry_loaded: Optional[Callable[[], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_status: Optional[Callable[[str], None]] = None

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def set_callbacks(
        self,
        on_loaded: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Register callbacks for telemetry loading events."""
        self._on_telemetry_loaded = on_loaded
        self._on_error = on_error
        self._on_status = on_status

    def load_gpmf_records(self, records: list[dict]) -> None:
        """Set GPMF records and extract built-in samples (speed, alt, track, iso, exposure, temp)."""
        self.records = records

        if self._extract_speed:
            self.speed_samples = self._extract_speed(records)
        if self._extract_altitude:
            self.alt_samples = self._extract_altitude(records)
        if self._extract_track:
            self.track_samples = self._extract_track(records)
        if self._extract_iso:
            self.iso_samples = self._extract_iso(records)
        if self._extract_exposure:
            self.exposure_samples = self._extract_exposure(records)
        if self._extract_temperature:
            self.temperature_samples = self._extract_temperature(records)

    def _smooth(self, samples: SampleList, window: int = 5) -> SampleList:
        """Apply moving average smoothing to samples."""
        if self._smooth_fn:
            return self._smooth_fn(samples, "moving_average", window)
        return samples

    def load_gpx(
        self,
        video_path: Path | str,
        start_dt: Optional[datetime] = None,
        manual_path: Optional[Path] = None,
    ) -> bool:
        """Load and process GPX data. Returns True if data was loaded."""
        if not _GPX_AVAILABLE:
            return False

        if manual_path:
            gpx_result = self._load_gpx_manual(manual_path, start_dt)
        else:
            gpx_result = process_gpx(video_path, start_dt)

        if gpx_result is None:
            return False

        (gpx_speed, gpx_track, gpx_alt, gpx_power, gpx_atemp, gpx_hr, gpx_cad) = (
            gpx_result
        )

        if gpx_speed:
            self.gpx_speed_samples = self._smooth(gpx_speed)
        else:
            self.gpx_speed_samples = []
        self.gpx_track_samples = gpx_track or []
        self.gpx_alt_samples = self._smooth(gpx_alt) if gpx_alt else []
        self.gpx_power_samples = gpx_power or []
        self.gpx_atemp_samples = gpx_atemp or []
        self.gpx_hr_samples = gpx_hr or []
        self.gpx_cad_samples = gpx_cad or []

        if self.start_dt_utc is None and gpx_speed:
            self.start_dt_utc = gpx_speed[0][0]

        print(f"[TelemetryManager] GPX loaded: speed={len(self.gpx_speed_samples)}", flush=True)
        return True

    def _load_gpx_manual(
        self, gpx_path: Path, start_dt: Optional[datetime]
    ) -> Optional[Any]:
        """Load GPX from a manually selected file path."""
        try:
            _pts = parse_gpx(gpx_path)
            return sync_gpx_to_video(_pts, start_dt) if _pts else None
        except Exception as exc:
            print(f"[GPX] Error loading manually selected GPX: {exc}", flush=True)
            return None

    def load_fit(
        self,
        video_path: Path | str,
        start_dt: Optional[datetime] = None,
        manual_path: Optional[Path] = None,
    ) -> bool:
        """Load and process FIT data. Returns True if data was loaded."""
        if not _FIT_AVAILABLE:
            return False

        if manual_path:
            fit_result = self._load_fit_manual(manual_path, start_dt)
        else:
            fit_result = process_fit(video_path, start_dt)

        if fit_result is None:
            return False

        (
            fit_speed,
            fit_track,
            fit_alt,
            fit_power,
            fit_atemp,
            fit_hr,
            fit_cad,
            fit_battery,
        ) = fit_result

        self.fit_speed_samples = self._smooth(fit_speed) if fit_speed else []
        self.fit_track_samples = fit_track or []
        self.fit_alt_samples = self._smooth(fit_alt) if fit_alt else []
        self.fit_power_samples = fit_power or []
        self.fit_atemp_samples = fit_atemp or []
        self.fit_hr_samples = fit_hr or []
        self.fit_cad_samples = fit_cad or []
        self.fit_battery_samples = fit_battery or []

        if self.start_dt_utc is None and fit_speed:
            self.start_dt_utc = fit_speed[0][0]

        print(f"[TelemetryManager] FIT loaded: speed={len(self.fit_speed_samples)}", flush=True)
        return True

    def _load_fit_manual(
        self, fit_path: Path, start_dt: Optional[datetime]
    ) -> Optional[Any]:
        """Load FIT from a manually selected file path."""
        try:
            _pts = parse_fit(fit_path)
            return sync_fit_to_video(_pts, start_dt) if _pts else None
        except Exception as exc:
            print(f"[FIT] Error loading manually selected FIT: {exc}", flush=True)
            return None

    def clear_source(self, source: str) -> None:
        """Clear samples for a specific source type."""
        if source == "gpx":
            self.gpx_speed_samples.clear()
            self.gpx_alt_samples.clear()
            self.gpx_track_samples.clear()
            self.gpx_power_samples.clear()
            self.gpx_atemp_samples.clear()
            self.gpx_hr_samples.clear()
            self.gpx_cad_samples.clear()
            self.gpx_path = None
        elif source == "fit":
            self.fit_speed_samples.clear()
            self.fit_alt_samples.clear()
            self.fit_track_samples.clear()
            self.fit_power_samples.clear()
            self.fit_atemp_samples.clear()
            self.fit_hr_samples.clear()
            self.fit_cad_samples.clear()
            self.fit_battery_samples.clear()
            self.fit_path = None

    def clear_all(self) -> None:
        """Clear all telemetry data."""
        self.records.clear()
        self.speed_samples.clear()
        self.alt_samples.clear()
        self.track_samples.clear()
        self.iso_samples.clear()
        self.exposure_samples.clear()
        self.temperature_samples.clear()
        self.clear_source("gpx")
        self.clear_source("fit")
        self.start_dt_utc = None
        self.meta_path = None
        self.video_duration_s = 0.0

    # ------------------------------------------------------------------
    # Source resolution helpers
    # ------------------------------------------------------------------

    def get_samples_for_source(
        self, source_type: str
    ) -> tuple[SampleList, SampleList, SampleList]:
        """Return (speed_samples, track_samples, alt_samples) for the given source.

        Falls back to GPMF if the requested source has no data.
        """
        if source_type == "gpx":
            return (
                self.gpx_speed_samples or self.speed_samples,
                self.gpx_track_samples or self.track_samples,
                self.gpx_alt_samples or self.alt_samples,
            )
        if source_type == "fit":
            return (
                self.fit_speed_samples or self.speed_samples,
                self.fit_track_samples or self.track_samples,
                self.fit_alt_samples or self.alt_samples,
            )
        return (self.speed_samples, self.track_samples, self.alt_samples)

    def resolve_value(
        self, field_name: str, target_dt: datetime, prefer: str = "fit"
    ) -> Optional[float]:
        """Return an interpolated telemetry value for the given field at *target_dt*.

        Priority: *prefer* (fit/gpx) > the other external source > GPMF fallback.

        Args:
            field_name: One of 'speed', 'alt', 'dist', 'track', 'power', 'hr', 'cad',
                        'atemp', 'battery', 'iso', 'exposure', 'temperature'.
            target_dt: The datetime to interpolate at.
            prefer: Preferred source ('fit' or 'gpx').

        Returns:
            Scalar value (float or int) or None if no data is available.
        """
        samples = self._resolve_samples(field_name, prefer)
        if not samples:
            return None
        return self._interpolate(samples, target_dt)

    def resolve_samples(
        self, field_name: str, prefer: str = "fit"
    ) -> SampleList:
        """Return raw sample list for the given field with source priority.

        Args:
            field_name: One of 'speed', 'alt', 'dist', 'track', 'power', 'hr', 'cad',
                        'atemp', 'battery', 'iso', 'exposure', 'temperature'.
            prefer: Preferred source ('fit' or 'gpx').

        Returns:
            List of (datetime, value) tuples or empty list.
        """
        return self._resolve_samples(field_name, prefer)

    def _resolve_samples(self, field_name: str, prefer: str) -> SampleList:
        """Internal: resolve samples with priority prefer > other > GPMF."""
        alt_prefix = "gpx" if prefer == "fit" else "fit"

        pref = getattr(self, f"{prefer}_{field_name}_samples", []) or []
        alt = getattr(self, f"{alt_prefix}_{field_name}_samples", []) or []
        samples: SampleList = pref or alt

        # GPMF fallback for fields that have native GPMF samples
        if not samples and field_name in (
            "speed", "alt", "dist", "track", "iso", "exposure", "temperature"
        ):
            gpmf_attr = (
                "track_samples"
                if field_name in ("dist", "track")
                else f"{field_name}_samples"
            )
            samples = getattr(self, gpmf_attr, []) or []

        return samples

    def _interpolate(self, samples: SampleList, target_dt: datetime) -> Optional[float]:
        """Interpolate a value at *target_dt* from the sample list."""
        if self._interpolate_fn:
            return self._interpolate_fn(samples, target_dt)
        return None

    # ------------------------------------------------------------------
    # Rotation helpers
    # ------------------------------------------------------------------

    def get_rotation_from_metadata(self) -> int:
        """Determine rotation (0/90/180/270) from ExifTool metadata records."""
        if self._get_rotation_meta and self.records:
            return self._get_rotation_meta(self.records)
        return 0

    def get_container_rotation(self) -> int:
        """Read the 'rotate' tag from the MP4 container via ffprobe."""
        if self._get_container_rotation and self.ffprobe_exe and self.video_path:
            return self._get_container_rotation(
                self.ffprobe_exe, self.video_path
            )
        return 0

    # ------------------------------------------------------------------
    # Metadata JSON generation
    # ------------------------------------------------------------------

    def generate_meta_json(
        self,
        video_paths: Optional[list[Path]] = None,
        exiftool_path: str | Path = "exiftool",
        silent: bool = False,
    ) -> Optional[Path]:
        """Generate metadata JSON from video files using ExifTool.

        Returns the path to the generated JSON file, or None on failure.
        """
        paths = video_paths or self.video_paths_to_process
        video_path = paths[0] if paths else None
        if not video_path:
            return None

        # Look for existing metadata
        if self._find_meta_json:
            meta_candidate = self._find_meta_json(video_path)
            if meta_candidate.exists() and meta_candidate.stat().st_size > 0:
                self.meta_path = meta_candidate
                if self._load_json_fallback:
                    raw = self._load_json_fallback(meta_candidate)
                    if self._ensure_records:
                        records = self._ensure_records(raw)
                        if records:
                            self.load_gpmf_records(records)
                            if not silent:
                                print(
                                    f"[TelemetryManager] Loaded meta from {meta_candidate.name}",
                                    flush=True,
                                )
                            return meta_candidate

        # Generate via ExifTool
        if not silent and self._on_status:
            self._on_status("Generating metadata...")

        try:
            if self._load_telemetry:
                meta_json = self._load_telemetry(video_path, exiftool_path)
                if meta_json and self._ensure_records:
                    records = self._ensure_records(meta_json)
                    if self._find_meta_json_write:
                        out_path = self._find_meta_json_write(video_path)
                        if out_path and self._write_records:
                            self._write_records(out_path, records)
                            self.meta_path = out_path
                            self.load_gpmf_records(records)
                            if not silent:
                                print(
                                    f"[TelemetryManager] Generated meta at {out_path}",
                                    flush=True,
                                )
                            return out_path
        except Exception as exc:
            if not silent and self._on_error:
                self._on_error(f"Meta JSON error: {exc}")

        return None
