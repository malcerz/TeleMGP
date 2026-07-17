"""Property editor – builds and manages the indicator property editor panel."""

from __future__ import annotations

from typing import Any, Callable, Optional


class PropertyEditor:
    """Builds and manages the indicator property editor panel in the GUI.

    This class is responsible for creating the dynamic form that lets users
    tweak indicator properties (position, size, colour, font, source, etc.)
    and handles changes when the user modifies a property.
    """

    def __init__(
        self,
        build_property_editor_fn: Optional[Callable] = None,
    ) -> None:
        self._build_property_editor_fn = build_property_editor_fn

        # UI containers (set by HudTunerApp)
        self.props_container: Any = None  # tk.Frame (inner of ScrollableFrame)
        self.property_widgets: dict[str, Any] = {}
        self.edit_mode: str = "builtin"

        # Callbacks (set by HudTunerApp)
        self._on_change: Optional[Callable[[], None]] = None
        self._on_font_change: Optional[Callable[[], None]] = None
        self._on_outline_change: Optional[Callable[[], None]] = None

        # Layout reference (shared with HudTunerApp)
        self.layout: dict[str, Any] = {}

        # Selection state
        self.indicator_list: Any = None
        self.gpx_ext_list: Any = None
        self.custom_texts_list: Any = None

    def set_callbacks(
        self,
        on_change: Optional[Callable[[], None]] = None,
        on_font_change: Optional[Callable[[], None]] = None,
        on_outline_change: Optional[Callable[[], None]] = None,
    ) -> None:
        """Register callbacks for property changes."""
        self._on_change = on_change
        self._on_font_change = on_font_change
        self._on_outline_change = on_outline_change

    def rebuild(self) -> None:
        """Rebuild the property editor for the currently selected indicator."""
        if self._build_property_editor_fn:
            self._build_property_editor_fn()

    def select_builtin(self, event: Any = None) -> None:
        """Handle selection of a built-in indicator from the list."""
        self.edit_mode = "builtin"
        self.rebuild()

    def select_gpx_ext(self, event: Any = None) -> None:
        """Handle selection of a GPX extension indicator."""
        self.edit_mode = "gpx_ext"
        self.rebuild()

    def select_custom_text(self, event: Any = None) -> None:
        """Handle selection of a custom text overlay."""
        self.edit_mode = "custom_text"
        self.rebuild()

    def on_property_change(self, *args: Any) -> None:
        """Called when any property is modified by the user."""
        if self._on_change:
            self._on_change()
