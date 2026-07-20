"""Layout manager – loading, saving and normalising HUD layout configurations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional


class LayoutManager:
    """Manages HUD layout configurations (JSON-based indicator definitions).

    Handles loading from def_layout.json, saving, migration between versions,
    and normalisation to the current default layout.
    """

    def __init__(
        self,
        default_layout_fn: Optional[Callable[[int, int], dict[str, Any]]] = None,
        normalize_layout_fn: Optional[
            Callable[[Path | str | None, int, int], dict[str, Any]]
        ] = None,
    ) -> None:
        self.layout: dict[str, Any] = {}
        self._default_layout_fn = default_layout_fn
        self._normalize_layout_fn = normalize_layout_fn

    # ------------------------------------------------------------------
    # Layout operations
    # ------------------------------------------------------------------

    def reset(self, video_width: int, video_height: int) -> dict[str, Any]:
        """Reset layout to defaults for the given video dimensions."""
        if self._default_layout_fn:
            self.layout = self._default_layout_fn(video_width, video_height)
        else:
            self.layout = {}
        return self.layout

    def load(
        self,
        layout_path: Path | str | None,
        video_width: int,
        video_height: int,
    ) -> dict[str, Any]:
        """Load a layout from a JSON file, merging with defaults.

        Args:
            layout_path: Path to the JSON layout file (may not exist).
            video_width: Video width in pixels (for relative positioning).
            video_height: Video height in pixels.

        Returns:
            The merged layout dict.
        """
        if self._normalize_layout_fn:
            self.layout = self._normalize_layout_fn(
                layout_path, video_width, video_height
            )
        else:
            self.layout = {}
        return self.layout

    def save(self, layout_path: Path | str) -> Path:
        """Save the current layout to a JSON file.

        Args:
            layout_path: Destination path.

        Returns:
            The path the layout was saved to.
        """
        path = Path(layout_path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.layout, f, indent=2, ensure_ascii=False)
        return path

    # ------------------------------------------------------------------
    # Indicator helpers
    # ------------------------------------------------------------------

    def get_indicator(self, key: str) -> dict[str, Any]:
        """Get a single indicator config by key."""
        return self.layout.get("indicators", {}).get(key, {})

    def set_indicator_source(self, key: str, source: str) -> None:
        """Set the telemetry source for a given indicator."""
        ind = self.layout.get("indicators", {}).get(key)
        if ind is not None:
            ind["source"] = source

    def set_indicators_source(
        self, keys: list[str], source: str
    ) -> None:
        """Set the telemetry source for multiple indicators at once."""
        for key in keys:
            self.set_indicator_source(key, source)

    def get_outline(self) -> int:
        """Get the global text outline width."""
        return self.layout.get("global", {}).get("text_outline", 3)

    def set_outline(self, value: int) -> None:
        """Set the global text outline width."""
        self.layout.setdefault("global", {})["text_outline"] = value

    def get_enabled_keys(self) -> list[str]:
        """Return list of enabled indicator keys."""
        inds = self.layout.get("indicators", {})
        return [k for k, v in inds.items() if v.get("enabled", True)]

    def get_smoothing(self) -> dict[str, Any]:
        """Get the smoothing configuration dict."""
        return self.layout.get("smoothing", {})

    # ------------------------------------------------------------------
    # Custom texts
    # ------------------------------------------------------------------

    def get_custom_texts(self) -> list[dict[str, Any]]:
        """Get the list of custom text overlays."""
        return self.layout.get("custom_texts", [])

    def add_custom_text(self) -> int:
        """Add a new default custom text entry. Returns its index."""
        texts = self.layout.setdefault("custom_texts", [])
        idx = len(texts) + 1
        texts.append({
            "enabled": True,
            "text": f"Custom {idx}",
            "x": 0.5,
            "y": 0.5,
            "font_size": 0.025,
            "color": "#FFFFFF",
            "rotation": 0,
        })
        return len(texts) - 1

    def remove_custom_text(self, index: int) -> None:
        """Remove a custom text by index."""
        texts = self.layout.get("custom_texts", [])
        if 0 <= index < len(texts):
            del texts[index]

    def update_indicator(self, key: str, updates: dict[str, Any]) -> None:
        """Update a single indicator's config."""
        ind = self.layout.setdefault("indicators", {}).get(key)
        if ind is not None:
            ind.update(updates)

    def disable_indicators_except(self, keep_keys: list[str]) -> None:
        """Disable all indicators except those in *keep_keys*."""
        inds = self.layout.get("indicators", {})
        for key in inds:
            if key not in keep_keys:
                inds[key]["enabled"] = False

    def get_builtin_keys(self, ext_fields: list[str]) -> list[str]:
        """Return indicator keys that are NOT in ext_fields and NOT fit_*."""
        inds = self.layout.get("indicators", {})
        return [k for k in inds if k not in ext_fields and not k.startswith("fit_")]

    def get_ext_keys(self, gpx_ext_fields: list[str], fit_ext_fields: list[str]) -> list[str]:
        """Return GPX + FIT extension keys."""
        return list(gpx_ext_fields) + list(fit_ext_fields)

    def update_custom_text(self, index: int, **kwargs: Any) -> None:
        """Update properties of a custom text entry."""
        texts = self.layout.get("custom_texts", [])
        if 0 <= index < len(texts):
            texts[index].update(kwargs)

