"""Preview canvas widget – manages the video preview, seek bar, and tick labels."""

from __future__ import annotations

from typing import Any, Callable, Optional


class PreviewCanvas:
    """Manages the video preview display, seek slider, and time-axis tick labels.

    Delegates rendering to the main module's compose_overlay / render_preview functions
    via injected callbacks.
    """

    def __init__(
        self,
        render_preview_fn: Optional[Callable] = None,
        format_time_fn: Optional[Callable[[float], str]] = None,
    ) -> None:
        self._render_preview_fn = render_preview_fn
        self._format_time_fn = format_time_fn

        # State (set by HudTunerApp)
        self.src_img: Any = None
        self.indicator_bboxes: dict[str, tuple[int, int, int, int]] = {}
        self.layout: dict[str, Any] = {}
        self.font_path: str = ""
        self.speed_samples: list = []
        self.track_samples: list = []
        self.alt_samples: list = []
        self.video_duration_s: float = 0.0
        self.fps: float = 30.0

        # For seek bar
        self.seek_var: Any = None  # tk.DoubleVar
        self.tick_canvas: Any = None  # tk.Canvas

        # For refresh scheduling
        self._refresh_after_id: Any = None
        self._schedule_cb: Optional[Callable[[], None]] = None

    def set_schedule_callback(self, cb: Callable[[], None]) -> None:
        """Set the callback for scheduling a refresh."""
        self._schedule_cb = cb

    def schedule_refresh(self, delay_ms: int = 60) -> None:
        """Debounced refresh scheduling."""
        if self._schedule_cb:
            self._schedule_cb()

    def format_time(self, total_sec: float) -> str:
        """Format seconds to HH:MM:SS or MM:SS."""
        if self._format_time_fn:
            return self._format_time_fn(total_sec)
        total_sec_int = int(total_sec)
        if total_sec_int >= 3600:
            return (
                f"{total_sec_int // 3600}:"
                f"{(total_sec_int % 3600) // 60:02d}:"
                f"{total_sec_int % 60:02d}"
            )
        return f"{total_sec_int // 60:02d}:{total_sec_int % 60:02d}"

    def draw_tick_labels(self) -> None:
        """Draw time-axis tick marks and labels on the tick canvas."""
        c = self.tick_canvas
        if c is None:
            return
        c.delete("all")
        cw = c.winfo_width()
        if cw < 10:
            return
        total = 0
        if self.seek_var is not None:
            try:
                total = int(
                    c.master.winfo_children()[0].cget("to")
                    if hasattr(c.master, "winfo_children")
                    else 0
                )
            except (ValueError, AttributeError):
                pass
        if total <= 0:
            return

        # Determine tick spacing
        if total <= 60:
            step = 10
        elif total <= 300:
            step = 30
        elif total <= 1800:
            step = 120
        elif total <= 7200:
            step = 600
        else:
            step = 1800

        ch = c.winfo_height() if c.winfo_height() > 10 else 20
        for t in range(0, total + 1, step):
            x = int(t / total * cw)
            c.create_line(x, ch - 8, x, ch - 2, fill="#888")
            c.create_text(x, ch - 10, text=self.format_time(float(t)),
                          anchor="s", fill="#aaa", font=("", 7))
