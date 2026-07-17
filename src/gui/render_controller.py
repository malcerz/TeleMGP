"""Render controller – orchestrates the FFmpeg rendering pipeline."""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional


class RenderController:
    """Orchestrates the FFmpeg-based HUD overlay rendering pipeline.

    Manages cancel events, progress callbacks, active process handles,
    and delegates to the main module's stream_overlay_to_ffmpeg / render_pipeline
    via injected function references.
    """

    def __init__(
        self,
        render_pipeline_fn: Optional[Callable] = None,
    ) -> None:
        self._render_pipeline_fn = render_pipeline_fn

        # State
        self.render_cancel_event = threading.Event()
        self._active_process: dict[str, Any] = {}
        self._render_executor: Any = None
        self.is_rendering: bool = False

        # UI references (set by HudTunerApp)
        self.render_button: Any = None
        self.render_progress: Any = None
        self.render_stats_label: Any = None

        # Callbacks
        self._on_finished: Optional[Callable[[dict[str, Any]], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

    def set_callbacks(
        self,
        on_finished: Optional[Callable[[dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Register render lifecycle callbacks."""
        self._on_finished = on_finished
        self._on_error = on_error

    def start_render(self, **kwargs: Any) -> None:
        """Start the render pipeline with the given arguments.

        This method is called by HudTunerApp with all the required parameters
        collected from the GUI state.
        """
        if self.is_rendering:
            return

        self.is_rendering = True
        self.render_cancel_event.clear()
        self._active_process = {}

        if self._render_pipeline_fn:
            # Run in a background thread to keep UI responsive
            def run_pipeline() -> None:
                try:
                    stats = self._render_pipeline_fn(
                        cancel_event=self.render_cancel_event,
                        active_process_holder=self._active_process,
                        progress_cb=self._on_progress,
                        **kwargs,
                    )
                    self.is_rendering = False
                    if self._on_finished and stats:
                        self._on_finished(stats)
                except Exception as exc:
                    self.is_rendering = False
                    if self._on_error:
                        self._on_error(str(exc))

            t = threading.Thread(target=run_pipeline, daemon=True)
            t.start()

    def cancel_render(self) -> None:
        """Signal cancellation of the current render."""
        self.render_cancel_event.set()
        proc_info = self._active_process.get("process")
        if proc_info is not None:
            try:
                proc_info.terminate()
            except Exception:
                pass
        self.is_rendering = False

    def _on_progress(self, value: float, text: str) -> None:
        """Update progress bar and stats label."""
        try:
            if self.render_progress is not None:
                self.render_progress["value"] = value
            if self.render_stats_label is not None:
                self.render_stats_label.config(text=text)
        except Exception:
            pass

    def reset(self) -> None:
        """Reset render state after completion or cancellation."""
        self.is_rendering = False
        self._active_process = {}
        self.render_cancel_event.clear()
