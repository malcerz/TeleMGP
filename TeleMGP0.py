#!/usr/bin/env python3
"""TeleM – GoPro Telemetry Overlay Application (launcher).

Re-exports HudTunerApp from the refactored src.gui.hud_tuner_app module.
"""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.gui.hud_tuner_app import HudTunerApp, default_layout  # noqa: E402, F401
from src.overlay_renderer import render_preview  # noqa: E402, F401

# Re-export symbols for backward compatibility with tests
from src.telemetry_extract import (  # noqa: E402, F401
    ensure_records_list,
    extract_altitude_samples,
    extract_exposure_samples,
    extract_iso_samples,
    extract_speed_samples,
    extract_temperature_samples,
    extract_track_samples,
    find_gps_anchor,
    flatten_record,
    get_rotation_from_metadata,
    haversine_m,
    parse_exif_datetime,
)

if __name__ == "__main__":
    import tkinter as tk

    root = tk.Tk()
    app = HudTunerApp(root)
    root.mainloop()
