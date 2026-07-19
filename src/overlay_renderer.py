"""Overlay renderer – PIL-based HUD overlay compositing functions.

This module contains all rendering functions for the TeleM telemetry overlay:
charts, gauges, bars, text indicators, time blocks, and custom texts.

Every function is a pure transformation: parameters in, PIL.Image out.
"""

from __future__ import annotations

import math
from typing import Any, Optional

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    # Fallback if PIL is not available
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFilter = None  # type: ignore
    ImageFont = None  # type: ignore

# ── Font cache ──────────────────────────────────────────────────────────────

FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


# ── Helpers ─────────────────────────────────────────────────────────────────


def load_font_cache_small(size: int) -> Optional[ImageFont.ImageFont]:
    """Return the default PIL font at the given size (cached). Used for chart axis labels."""
    key = ("__builtin_default__", int(size))
    if key in FONT_CACHE:
        return FONT_CACHE[key]  # type: ignore[return-value]
    try:
        font = ImageFont.load_default()
        FONT_CACHE[key] = font
        return font
    except Exception:
        return None


def parse_hex_color(hex_str: Any) -> Optional[tuple[int, int, int]]:
    """Convert a hex colour string (e.g. '#FF3232' or 'FF3232') to an RGB tuple.
    Returns None on failure."""
    if not hex_str or not isinstance(hex_str, str):
        return None
    s = hex_str.strip().lstrip("#")
    try:
        if len(s) == 6:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        elif len(s) == 3:
            return (int(s[0], 16) * 17, int(s[1], 16) * 17, int(s[2], 16) * 17)
    except Exception:
        pass
    return None


def s(value: float, base: int) -> int:
    """Scale a relative value (0.0-1.0 range) to an absolute pixel size."""
    return max(1, int(round(value * base)))


def load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a font from cache or disk. Falls back to default PIL font on failure."""
    key = (str(font_path), int(size))
    font = FONT_CACHE.get(key)
    if font is not None:
        return font
    try:
        font = ImageFont.truetype(str(font_path), size=int(size))
    except Exception:
        font = ImageFont.load_default()
    FONT_CACHE[key] = font
    return font


# ── Chart rendering ─────────────────────────────────────────────────────────


def generate_history_chart(
    history_values: list[float],
    width: int,
    height: int,
    line_color: tuple[int, int, int] = (255, 0, 0),
    line_thickness: int = 3,
    fill_alpha: int = 50,
    fill_color: Optional[tuple[int, int, int]] = None,
    current_index: Optional[int] = None,
    cursor_color: tuple[int, int, int] = (255, 255, 255),
    show_axes: bool = True,
    time_labels: Optional[list[str]] = None,
    value_labels: Optional[list[str]] = None,
    supersample: int = 1,
) -> Image.Image:
    """Generate a universal line chart with transparent fill, axes, and optional cursor.

    Args:
        history_values: Data points to plot.
        width: Output image width in pixels.
        height: Output image height in pixels.
        line_color: RGB tuple for the main line.
        line_thickness: Width of the main line.
        fill_alpha: Fill transparency (0-255).
        fill_color: Optional separate fill colour (defaults to line_color).
        current_index: Index of the cursor position (None = no cursor).
        cursor_color: RGB for the cursor line.
        show_axes: Whether to draw axes with labels.
        time_labels: 5 strings for X-axis labels.
        value_labels: Strings for Y-axis labels (defaults to [min, max]).
        supersample: Render at Nx resolution then downscale for anti-aliasing (1=off).

    Returns:
        RGBA PIL.Image.
    """
    ss = max(1, int(supersample))
    out_w, out_h = width, height
    width *= ss
    height *= ss
    line_thickness *= ss
    axis_left_margin = (50 if show_axes else 0) * ss
    axis_bottom_margin = (22 if show_axes else 0) * ss
    axis_top_margin = 4 * ss
    axis_right_margin = 4 * ss

    has_data = history_values and len(history_values) >= 2

    if has_data:
        min_val = float(min(history_values))
        max_val = float(max(history_values))
    else:
        min_val = 0.0
        max_val = 100.0
    val_range = max_val - min_val
    if val_range == 0:
        val_range = 1.0

    num_points = len(history_values) if has_data else 0

    plot_x1 = axis_left_margin
    plot_y1 = axis_top_margin
    plot_x2 = width - axis_right_margin
    plot_y2 = height - axis_bottom_margin
    plot_w = plot_x2 - plot_x1
    plot_h = plot_y2 - plot_y1
    if plot_w <= 0:
        plot_w = 1
    if plot_h <= 0:
        plot_h = 1

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if show_axes:
        axis_color = (180, 180, 180, 220)
        tick_color = (150, 150, 150, 200)
        label_color = (200, 200, 200, 240)

        draw.line((plot_x1, plot_y1, plot_x1, plot_y2), fill=axis_color, width=1)
        draw.line((plot_x1, plot_y2, plot_x2, plot_y2), fill=axis_color, width=1)

        try:
            font_axis = load_font_cache_small(10)
        except Exception:
            font_axis = None

        y_label_values = value_labels if value_labels else [f"{min_val:.0f}", f"{max_val:.0f}"]
        y_positions = [plot_y2, plot_y1]

        for i, (lbl, yp) in enumerate(zip(y_label_values, y_positions)):
            if font_axis:
                bbox = draw.textbbox((0, 0), lbl, font=font_axis)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            else:
                tw = len(lbl) * 6
                th = 10
            tx = plot_x1 - tw - 5
            ty = yp - th // 2
            if font_axis:
                draw.text((tx, ty), lbl, fill=label_color, font=font_axis)
            else:
                draw.text((tx, ty), lbl, fill=label_color)

        draw.line((plot_x1 - 4, plot_y2, plot_x1, plot_y2), fill=tick_color, width=1)
        draw.line((plot_x1 - 4, plot_y1, plot_x1, plot_y1), fill=tick_color, width=1)

        x_labels = time_labels if time_labels else ["0%", "25%", "50%", "75%", "100%"]
        for i, lbl in enumerate(x_labels):
            x = plot_x1 + (plot_w * i / max(1, len(x_labels) - 1))
            draw.line((x, plot_y2, x, plot_y2 + 4), fill=tick_color, width=1)
            if font_axis:
                bbox = draw.textbbox((0, 0), lbl, font=font_axis)
                tw = bbox[2] - bbox[0]
            else:
                tw = len(lbl) * 6
            tx = x - tw // 2
            ty = plot_y2 + 5
            if font_axis:
                draw.text((tx, ty), lbl, fill=label_color, font=font_axis)
            else:
                draw.text((tx, ty), lbl, fill=label_color)

    if not has_data:
        return img

    # Calculate point coordinates
    points: list[tuple[float, float]] = []
    for i, val in enumerate(history_values):
        x = plot_x1 + (i / (num_points - 1)) * plot_w
        v_margin = line_thickness + 1
        usable_h = plot_h - (2 * v_margin)
        y = plot_y2 - v_margin - ((val - min_val) / val_range) * usable_h
        points.append((x, y))

    # Fill under the line
    fill_polygon: list[tuple[float, float]] = list(points)
    fill_polygon.append((plot_x2, plot_y2))
    fill_polygon.append((plot_x1, plot_y2))
    actual_fill_rgb = fill_color if fill_color is not None else line_color
    actual_fill = (actual_fill_rgb[0], actual_fill_rgb[1], actual_fill_rgb[2], fill_alpha)

    fill_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    fill_draw = ImageDraw.Draw(fill_img)
    fill_draw.polygon(fill_polygon, fill=actual_fill)  # type: ignore[arg-type]
    img = Image.alpha_composite(img, fill_img)

    # Draw the line
    draw = ImageDraw.Draw(img)
    draw.line(points, fill=(line_color[0], line_color[1], line_color[2], 255), width=line_thickness, joint="round")

    # Draw cursor
    if current_index is not None and 0 <= current_index < num_points:
        cursor_x = points[current_index][0]
        draw.line(
            (cursor_x, plot_y1, cursor_x, plot_y2),
            fill=(cursor_color[0], cursor_color[1], cursor_color[2], 200),
            width=max(2, line_thickness),
        )
        py = points[current_index][1]
        dot_r = max(3, line_thickness + 1)
        draw.ellipse(
            (cursor_x - dot_r, py - dot_r, cursor_x + dot_r, py + dot_r),
            fill=(cursor_color[0], cursor_color[1], cursor_color[2], 255),
            outline=(line_color[0], line_color[1], line_color[2], 255),
        )

    if ss > 1:
        img = img.resize((out_w, out_h), Image.LANCZOS)
    return img


# ── Single-indicator rendering ──────────────────────────────────────────────


def render_custom_text(
    canvas_w: int, canvas_h: int, font_path: str, cfg: dict[str, Any],
    stroke_width: int = 2,
) -> tuple[Optional[Image.Image], int, int]:
    """Render a single custom text overlay.

    Args:
        canvas_w: Canvas width in pixels.
        canvas_h: Canvas height in pixels.
        font_path: Path to the TrueType font file.
        cfg: Dict with keys: enabled, text, x, y, rotation, font_size, color.
        stroke_width: Outline thickness in pixels (default 2).

    Returns:
        (overlay_img, px_x, px_y) or (None, 0, 0) if disabled.
    """
    if not cfg.get("enabled", True):
        return None, 0, 0
    text = str(cfg.get("text", ""))
    if not text:
        return None, 0, 0
    min_dim = min(canvas_w, canvas_h)
    font_size_px = max(8, int(round(cfg.get("font_size", 0.03) * min_dim)))
    font = load_font(font_path, font_size_px)
    color_hex = cfg.get("color", "#FFFFFF")
    rgb = parse_hex_color(color_hex)
    if rgb is None:
        rgb = (255, 255, 255)
    fill_color = (rgb[0], rgb[1], rgb[2], 255)
    tmp = Image.new("RGBA", (canvas_w, font_size_px * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tmp)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    overlay = Image.new("RGBA", (tw + 8, th + 8), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.text((4, 4), text, font=font, fill=fill_color, stroke_width=stroke_width, stroke_fill=(0, 0, 0, 200))
    px = int(round(cfg.get("x", 0.5) * canvas_w))
    py = int(round(cfg.get("y", 0.5) * canvas_h))
    return overlay, px, py


def rotated_paste(
    base_img: Image.Image,
    overlay: Image.Image,
    center_x: int,
    center_y: int,
    rotation: int,
) -> None:
    """Paste *overlay* onto *base_img* centred at (center_x, center_y) with rotation.
    Modifies base_img in place."""
    rotation = int(rotation) % 360
    if rotation == 90:
        overlay = overlay.transpose(Image.Transpose.ROTATE_90)
    elif rotation == 180:
        overlay = overlay.transpose(Image.Transpose.ROTATE_180)
    elif rotation == 270:
        overlay = overlay.transpose(Image.Transpose.ROTATE_270)
    x = int(round(center_x - overlay.width / 2))
    y = int(round(center_y - overlay.height / 2))
    base_img.alpha_composite(overlay, (x, y))


def render_time_block(
    canvas_w: int,
    canvas_h: int,
    layout: dict[str, Any],
    font_path: str,
    date_text: str,
    time_text: str,
) -> tuple[Optional[Image.Image], int, int]:
    """Render the date/time block indicator.

    Returns:
        (overlay_img, px_x, px_y) or (None, 0, 0) if disabled.
    """
    cfg = layout["indicators"]["time_block"]
    if not cfg.get("enabled", True):
        return None, 0, 0

    min_dim = min(canvas_w, canvas_h)
    outline_raw = int(layout["global"].get("text_outline", 3))
    outline = max(0, int(round(outline_raw * min_dim / 1000)))

    label_px = max(12, s(cfg["font_label"], min_dim))
    date_px = max(14, s(cfg["font_date"], min_dim))
    time_px = max(14, s(cfg["font_time"], min_dim))

    font_label = load_font(font_path, label_px)
    font_date = load_font(font_path, date_px)
    font_time = load_font(font_path, time_px)

    tmp = Image.new(
        "RGBA",
        (max(200, s(0.25, canvas_w)), max(100, s(0.12, canvas_h))),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(tmp)

    y = 0
    draw.text(
        (0, y),
        cfg.get("label", "Czas"),
        font=font_label,
        fill=(210, 210, 210, 255),
        stroke_width=outline,
        stroke_fill=(0, 0, 0, 255),
    )
    y += int(label_px * 1.3)

    draw.text(
        (0, y),
        date_text,
        font=font_date,
        fill=(255, 255, 255, 255),
        stroke_width=outline,
        stroke_fill=(0, 0, 0, 255),
    )
    y += int(date_px * 1.2)

    draw.text(
        (0, y),
        time_text,
        font=font_time,
        fill=(255, 255, 255, 255),
        stroke_width=outline,
        stroke_fill=(0, 0, 0, 255),
    )

    bbox = tmp.getbbox()
    if not bbox:
        return None, 0, 0

    return tmp.crop(bbox), s(cfg["x"], canvas_w), s(cfg["y"], canvas_h)


def render_value_indicator(
    canvas_w: int,
    canvas_h: int,
    layout: dict[str, Any],
    font_path: str,
    key: str,
    value: float,
    unit: str,
    label: str,
    cfg_override: Optional[dict[str, Any]] = None,
    formatted_val: Optional[str] = None,
    max_distance_m: Optional[float] = None,
    history_data: Optional[list[float] | dict[str, Any]] = None,
    current_position: Optional[float] = None,
) -> tuple[Optional[Image.Image], int, int, Optional[dict[str, Any]]]:
    """Render a single telemetry indicator (text, gauge, bar, or chart form).

    Args:
        canvas_w, canvas_h: Canvas dimensions.
        layout: Full HUD layout dict.
        font_path: Path to TrueType font.
        key: Indicator key (e.g. "speed_text").
        value: Current value to display.
        unit: Unit string (e.g. "km/h").
        label: Display label.
        cfg_override: Optional config override (uses layout config if None).
        formatted_val: Pre-formatted value string (auto-built if None).
        max_distance_m: Max distance for bar range labels.
        history_data: Chart data (list of floats or dict with 'values' key).
        current_position: 0.0-1.0 position for chart cursor.

    Returns:
        (overlay_img, px_x, px_y, extra_dict) or (None, 0, 0, None) if disabled.
    """
    cfg = cfg_override if cfg_override else layout["indicators"].get(key)
    if not cfg or not cfg.get("enabled", True):
        return None, 0, 0, None

    form = cfg.get("form", "text")
    _FORM_MAP = {"TEXT": "text", "SUWAK": "bar", "LICZNIK": "text"}
    form = _FORM_MAP.get(form, form)
    min_dim = min(canvas_w, canvas_h)
    outline_raw = int(layout["global"].get("text_outline", 3))
    outline = max(0, int(round(outline_raw * min_dim / 1000)))
    fs = max(8, s(cfg.get("font_size", 0.02), min_dim))
    font = load_font(font_path, fs)

    val_min = float(cfg.get("min_val", 0))
    val_max = float(cfg.get("max_val", 100))
    ticks = int(cfg.get("ticks", 0))
    # thickness: new format (1-10) → convert to old relative for s() scaling;
    # old format (< 1) → use as-is for backward compat
    _thickness_raw = float(cfg.get("thickness", 1))
    if _thickness_raw >= 1:
        _thickness_rel = _thickness_raw / 200.0
    else:
        _thickness_rel = _thickness_raw
    thickness = max(1, s(_thickness_rel, min_dim))
    size_px = s(cfg.get("size", 0.1), min_dim if form == "gauge" else canvas_w)

    if form == "text":
        v_str = formatted_val if formatted_val else f"{value:.1f} {unit}"
        txt = f"{label}: {v_str}" if label else v_str
        tmp = Image.new("RGBA", (canvas_w, fs * 3), (0, 0, 0, 0))
        draw = ImageDraw.Draw(tmp)
        draw.text(
            (0, 0),
            txt,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=outline,
            stroke_fill=(0, 0, 0, 255),
        )
        bbox = tmp.getbbox()
        if not bbox:
            return None, 0, 0, None
        return tmp.crop(bbox), s(cfg["x"], canvas_w), s(cfg["y"], canvas_h), None

    elif form == "bar":
        w, h = size_px, max(24, thickness * 6)
        img = Image.new("RGBA", (w + 40, h + 30), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        v_str = f"{value:.1f} {unit}"
        show_value = cfg.get("show_value", True)

        if label:
            draw.text(
                (20, 0),
                label,
                font=font,
                fill=(210, 210, 210, 255),
                stroke_width=outline,
                stroke_fill=(0, 0, 0, 255),
            )

        by = h - thickness - 5
        x1, x2 = 20, w + 20
        draw.line((x1, by, x2, by), fill=(160, 160, 160, 180), width=thickness)

        if ticks > 1:
            for i in range(ticks + 1):
                xt = x1 + (w * i / ticks)
                draw.line(
                    (xt, by - thickness, xt, by + thickness),
                    fill=(245, 245, 245, 220),
                    width=max(1, thickness // 4),
                )

        frac = max(0, min(1, (value - val_min) / (val_max - val_min))) if val_max > val_min else 0
        dot_x = x1 + frac * w
        dot_y = by

        draw.ellipse(
            (dot_x - thickness, dot_y - thickness, dot_x + thickness, dot_y + thickness),
            fill=(255, 50, 50, 255),
            outline=(255, 255, 255, 255),
        )
        extra = {
            "show_value": show_value,
            "value_text": v_str,
            "dot_x": dot_x,
            "dot_y": dot_y,
            "bar_w": w,
            "bar_h": h,
            "x1": x1,
            "x2": x2,
            "by": by,
            "show_range_labels": key == "dist_visual" and cfg.get("show_range_labels", False),
            "left_text": "0 km",
            "right_text": f"{max_distance_m / 1000.0:.1f} km" if max_distance_m is not None else "",
        }
        return img, s(cfg["x"], canvas_w), s(cfg["y"], canvas_h), extra

    elif form == "gauge":
        display_min = 0
        display_max = math.ceil(val_max / 10.0) * 10 if val_max > 0 else 10
        major_ticks_count = int(display_max / 10)
        if major_ticks_count < 1:
            major_ticks_count = 1
        sub_ticks_count = 10
        total_ticks = major_ticks_count * sub_ticks_count

        radius = size_px
        img_size = int(radius * 2.4)
        img = Image.new("RGBA", (img_size, img_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx = cy = img_size // 2
        start_deg, end_deg = 180, 360

        for i in range(total_ticks + 1):
            a = math.radians(start_deg + (end_deg - start_deg) * i / total_ticks)
            cos_a = math.cos(a)
            sin_a = math.sin(a)

            if i % sub_ticks_count == 0:
                tick_len = thickness
                tick_width = max(3, int(thickness // 3))
                tick_val = display_min + (display_max - display_min) * (i / total_ticks)
                txt_tick = f"{tick_val:.0f}"
                text_radius = radius - tick_len - (radius * 0.20)
                tx = cx + cos_a * text_radius
                ty = cy + sin_a * text_radius
                draw.text(
                    (tx, ty),
                    txt_tick,
                    font=font,
                    fill=(255, 255, 255, 240),
                    stroke_width=1,
                    stroke_fill=(0, 0, 0, 255),
                    anchor="mm",
                )
            elif i % (sub_ticks_count // 2) == 0:
                tick_len = thickness * 0.7
                tick_width = max(2, int(thickness // 4))
            else:
                tick_len = thickness * 0.4
                tick_width = max(1, int(thickness // 6))

            r_out = radius
            r_in = radius - tick_len
            draw.line(
                (
                    cx + cos_a * r_in,
                    cy + sin_a * r_in,
                    cx + cos_a * r_out,
                    cy + sin_a * r_out,
                ),
                fill=(240, 240, 240, 255),
                width=tick_width,
            )

        frac = (
            max(0, min(1, (value - display_min) / (display_max - display_min)))
            if display_max > display_min
            else 0
        )
        ang = math.radians(start_deg + (end_deg - start_deg) * frac)

        needle_r_out = radius + max(2, int(radius * 0.05))
        needle_r_in = radius - thickness - (radius * 0.40)

        draw.line(
            (
                cx + math.cos(ang) * needle_r_in,
                cy + math.sin(ang) * needle_r_in,
                cx + math.cos(ang) * needle_r_out,
                cy + math.sin(ang) * needle_r_out,
            ),
            fill=(220, 50, 50, 255),
            width=max(4, int(thickness // 2)),
        )

        if key == "speed_visual":
            if label:
                tw = draw.textbbox((0, 0), label, font=font)[2]
                draw.text(
                    (cx - tw // 2, cy + radius // 2),
                    label,
                    font=font,
                    fill=(255, 255, 255, 255),
                    stroke_width=outline,
                    stroke_fill=(0, 0, 0, 255),
                )
        else:
            txt_main = f"{value:.1f}"
            tw = draw.textbbox((0, 0), txt_main, font=font)[2]
            draw.text(
                (cx - tw // 2, cy + radius // 2),
                txt_main,
                font=font,
                fill=(255, 255, 255, 255),
                stroke_width=outline,
                stroke_fill=(0, 0, 0, 255),
            )

        # Drop shadow
        shadow_offset = max(2, int(radius * 0.025))
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        shadow.paste(img, (shadow_offset, shadow_offset))
        alpha = shadow.split()[3].point(lambda x: int(x * 0.35))
        alpha = alpha.filter(ImageFilter.GaussianBlur(radius=max(1, int(radius * 0.035))))
        shadow_rgba = Image.new("RGBA", img.size, (0, 0, 0, 0))
        shadow_rgba.putalpha(alpha)
        img = Image.alpha_composite(shadow_rgba, img)

        return img, s(cfg["x"], canvas_w), s(cfg["y"], canvas_h), None

    elif form == "chart":
        time_labels = None
        chart_vals = None
        if isinstance(history_data, dict):
            chart_vals = history_data.get("values", [])
            time_labels = history_data.get("time_labels")
        elif isinstance(history_data, list):
            chart_vals = history_data

        if not chart_vals or len(chart_vals) < 2:
            chart_vals = [value, value]

        ci = None
        if current_position is not None:
            ci = int(round(current_position * (len(chart_vals) - 1)))
            ci = max(0, min(len(chart_vals) - 1, ci))

        chart_w = size_px
        chart_h = max(40, int(chart_w * 0.4))

        custom_color = parse_hex_color(cfg.get("chart_color", ""))
        if custom_color:
            line_clr = custom_color
        elif "speed" in key or "cad" in key:
            line_clr = (255, 50, 50)
        elif "alt" in key:
            line_clr = (50, 200, 50)
        elif "dist" in key:
            line_clr = (50, 150, 255)
        elif "power" in key:
            line_clr = (255, 200, 50)
        elif "hr" in key:
            line_clr = (255, 50, 150)
        elif "battery" in key:
            line_clr = (50, 255, 50)
        else:
            line_clr = (200, 200, 200)

        chart_fill_alpha = int(cfg.get("fill_alpha", 40))
        chart_fill_color = parse_hex_color(cfg.get("fill_color", ""))

        chart_img = generate_history_chart(
            chart_vals,
            chart_w,
            chart_h,
            line_color=line_clr,
            line_thickness=max(1, int(float(cfg.get("thickness", 1)))),
            fill_alpha=chart_fill_alpha,
            fill_color=chart_fill_color,
            current_index=ci,
            cursor_color=(255, 255, 255),
            show_axes=True,
            time_labels=time_labels,
            supersample=2,
        )

        margin_top = fs + 8 if label else 0
        final_h = chart_h + margin_top + 4
        final_img = Image.new("RGBA", (chart_w + 8, final_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(final_img)

        if label:
            draw.text(
                (4, 0),
                label,
                font=font,
                fill=(210, 210, 210, 255),
                stroke_width=outline,
                stroke_fill=(0, 0, 0, 255),
            )

        final_img.paste(chart_img, (4, margin_top), chart_img)

        v_str = formatted_val if formatted_val else f"{value:.1f} {unit}"
        bbox = draw.textbbox((0, 0), v_str, font=font)
        vw = bbox[2] - bbox[0]
        draw.text(
            (chart_w - vw, 0),
            v_str,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=outline,
            stroke_fill=(0, 0, 0, 255),
        )

        return final_img, s(cfg["x"], canvas_w), s(cfg["y"], canvas_h), None

    return None, 0, 0, None


# ── Composite overlay rendering ─────────────────────────────────────────────


def compose_overlay(
    canvas_w: int,
    canvas_h: int,
    layout: dict[str, Any],
    font_path: str,
    date_text: str,
    time_text: str,
    speed_value: float,
    distance_m: float,
    max_distance_m: Optional[float] = None,
    alt_value: float = 0.0,
    min_alt: Optional[float] = None,
    max_alt: Optional[float] = None,
    iso_value: Optional[float] = None,
    exposure_value: Optional[float] = None,
    temp_value: Optional[float] = None,
    indicator_values: Optional[dict[str, float]] = None,
    max_speed_kmh: Optional[float] = None,
    power_value: Optional[float] = None,
    atemp_value: Optional[float] = None,
    hr_value: Optional[float] = None,
    cad_value: Optional[float] = None,
    battery_value: Optional[float] = None,
    _bboxes: Optional[dict[str, tuple[int, int, int, int]]] = None,
    chart_data: Optional[dict[str, list[float]]] = None,
    current_position: Optional[float] = None,
    extra_indicators: Optional[dict[str, tuple[float, str, str]]] = None,
) -> Image.Image:
    """Compose the complete HUD overlay image from all indicators.

    Each indicator is rendered according to its layout config and blended
    onto a transparent RGBA canvas.

    Args:
        canvas_w, canvas_h: Output image dimensions.
        layout: Full HUD layout dict.
        font_path: Path to TrueType font.
        date_text, time_text: Formatted date/time strings.
        speed_value, distance_m, alt_value: Primary telemetry values.
        indicator_values: Optional per-indicator value overrides (metres for dist).
        _bboxes: Optional dict to populate with indicator bounding boxes.
        chart_data: Optional dict of chart history {key: [values]}.
        current_position: 0.0-1.0 playback position for chart cursors.
        extra_indicators: Optional dict of dynamically discovered indicators
            {key: (value, unit, label)} (e.g. FIT fields).

    Returns:
        RGBA PIL.Image with all indicators composited.
    """
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    if _bboxes is None:
        _bboxes = {}

    # Time block
    tb, tbx, tby = render_time_block(canvas_w, canvas_h, layout, font_path, date_text, time_text)
    if tb:
        tb_rotation = layout["indicators"]["time_block"].get("rotation", 0)
        rotated_paste(img, tb, tbx + tb.width // 2, tby + tb.height // 2, tb_rotation)
        if tb_rotation == 90:
            _bboxes["time_block"] = (
                int(tbx - tb.height // 2),
                int(tby - tb.width // 2),
                tb.height,
                tb.width,
            )
        else:
            _bboxes["time_block"] = (
                int(tbx - tb.width // 2),
                int(tby - tb.height // 2),
                tb.width,
                tb.height,
            )

    if indicator_values is None:
        indicator_values = {}

    # All indicators to render
    indicator_defs = [
        ("speed_visual", speed_value, "km/h", ""),
        ("speed_text", speed_value, "km/h", ""),
        ("dist_visual", distance_m / 1000.0, "km", ""),
        ("dist_text", distance_m / 1000.0, "km", ""),
        ("alt_visual", alt_value, "m", "Alt"),
        ("alt_text", alt_value, "m", "Alt"),
        ("iso_text", iso_value if iso_value is not None else 0, "ISO", "ISO"),
        ("exposure_text", exposure_value if exposure_value is not None else 0, "", "Exp"),
        ("temp_text", temp_value if temp_value is not None else 0, "C", "Temp"),
        ("power_text", power_value if power_value is not None else 0, "W", "Moc"),
        ("atemp_text", atemp_value if atemp_value is not None else 0, "\u00b0C", "ATemp"),
        ("hr_text", hr_value if hr_value is not None else 0, "BPM", "HR"),
        ("cad_text", cad_value if cad_value is not None else 0, "RPM", "Cad"),
        ("battery_text", battery_value if battery_value is not None else 0, "%", "Bat"),
    ]

    for key, default_value, unit, default_label in indicator_defs:
        # Skip disabled indicators early
        ind_cfg_orig = layout["indicators"].get(key)
        if ind_cfg_orig and not ind_cfg_orig.get("enabled", True):
            continue
        if key in indicator_values:
            raw = indicator_values[key]
            if key in ("dist_visual", "dist_text"):
                value = raw / 1000.0
            else:
                value = raw
        else:
            value = float(default_value)

        current_cfg = layout["indicators"][key].copy()

        if key == "dist_visual" and max_distance_m is not None:
            current_cfg["max_val"] = max(current_cfg["min_val"] + 0.001, max_distance_m / 1000.0)

        if key == "speed_visual" and max_speed_kmh is not None:
            rounded = math.ceil(max_speed_kmh / 10.0) * 10
            current_cfg["max_val"] = max(current_cfg.get("min_val", 0) + 0.001, rounded)

        if key in ("alt_visual", "alt_text") and min_alt is not None and max_alt is not None:
            current_cfg["min_val"] = min_alt
            current_cfg["max_val"] = max(min_alt + 1.0, max_alt)

        label = current_cfg.get("label", default_label)

        # Build formatted value
        if key == "iso_text":
            fv = f"{int(value)}"
        elif key == "exposure_text":
            fv = f"1/{int(value)}" if value and int(value) > 0 else ""
        elif key == "temp_text":
            fv = f"{int(value)}\u00b0C"
        elif key == "power_text":
            fv = f"{int(value)}W"
        elif key == "atemp_text":
            fv = f"{int(value)}\u00b0C"
        elif key == "hr_text":
            fv = f"{int(value)} BPM"
        elif key == "cad_text":
            fv = f"{int(value)} RPM"
        elif key == "battery_text":
            fv = f"{int(value)}%"
        else:
            fv = None

        chart_vals = None
        if chart_data and key in chart_data:
            chart_vals = chart_data[key]

        res, rx, ry, extra = render_value_indicator(
            canvas_w,
            canvas_h,
            layout,
            font_path,
            key,
            value,
            unit,
            label,
            cfg_override=current_cfg,
            formatted_val=fv,
            max_distance_m=max_distance_m,
            history_data=chart_vals,
            current_position=current_position,
        )

        if res:
            rotation = layout["indicators"][key].get("rotation", 0)
            if layout["indicators"][key].get("form", "text") == "text":
                if rotation == 90:
                    rx = rx + res.height // 2
                else:
                    rx = rx + res.width // 2
            rotated_paste(img, res, rx, ry, rotation)

            if rotation == 90:
                _bboxes[key] = (
                    int(ry - res.height // 2),
                    int(rx - res.width // 2),
                    res.height,
                    res.width,
                )
            elif rotation == 180:
                _bboxes[key] = (
                    int(rx - res.width // 2),
                    int(ry - res.height // 2),
                    res.width,
                    res.height,
                )
            elif rotation == 270:
                _bboxes[key] = (
                    int(ry - res.width // 2),
                    int(rx - res.height // 2),
                    res.height,
                    res.width,
                )
            else:
                _bboxes[key] = (
                    int(rx - res.width // 2),
                    int(ry - res.height // 2),
                    res.width,
                    res.height,
                )

            draw = ImageDraw.Draw(img)
            cfg = current_cfg
            fs = max(10, int(s(cfg["font_size"], canvas_h)))
            font = load_font(font_path, fs)
            outline = max(1, fs // 12)

            if extra and extra.get("show_value") and key != "dist_visual":
                text = extra["value_text"]
                bbox = draw.textbbox((0, 0), text, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                ox = int(round(cfg.get("value_offset_x", 0.0) * canvas_w))
                oy = int(round(cfg.get("value_offset_y", 0.0) * canvas_h))
                if rotation == 90:
                    text_x = int(rx + res.height + 8 + ox)
                    text_y = int(ry + res.width / 2 - text_h / 2 + oy)
                else:
                    text_x = int(rx + extra["dot_x"] - text_w / 2 + ox)
                    text_y = int(ry + extra["dot_y"] - text_h - 8 + oy)
                draw.text(
                    (text_x, text_y),
                    text,
                    font=font,
                    fill=(255, 255, 255, 255),
                    stroke_width=outline,
                    stroke_fill=(0, 0, 0, 255),
                )

            if key in ("dist_visual", "alt_visual") and cfg.get("show_range_labels", False):
                left_text = (
                    f"{int(cfg.get('min_val', 0))} m"
                    if key == "alt_visual"
                    else "0 km"
                )
                right_text = (
                    f"{int(cfg.get('max_val', 500))} m"
                    if key == "alt_visual"
                    else (
                        f"{max_distance_m / 1000.0:.1f} km"
                        if max_distance_m is not None
                        else ""
                    )
                )
                rox = int(round(cfg.get("range_label_offset_x", 0.0) * canvas_w))
                roy = int(round(cfg.get("range_label_offset_y", 0.0) * canvas_h))
                rspreadx = int(round(cfg.get("range_label_spread_x", 0.0) * canvas_w))

                left_bbox = draw.textbbox((0, 0), left_text, font=font)
                left_w = left_bbox[2] - left_bbox[0]
                left_h = left_bbox[3] - left_bbox[1]
                if right_text:
                    right_bbox = draw.textbbox((0, 0), right_text, font=font)
                    right_w = right_bbox[2] - right_bbox[0]
                    right_h = right_bbox[3] - right_bbox[1]
                else:
                    right_w = right_h = 0

                if rotation == 90:
                    left_x = int(rx - left_w - 8 + rox)
                    left_y = int(ry + res.width - left_h / 2 + roy)
                    draw.text(
                        (left_x, left_y),
                        left_text,
                        font=font,
                        fill=(220, 220, 220, 255),
                        stroke_width=outline,
                        stroke_fill=(0, 0, 0, 255),
                    )
                    if right_text:
                        right_x = int(rx - right_w - 8 + rox)
                        right_y = int(ry - right_h / 2 + roy - rspreadx)
                        draw.text(
                            (right_x, right_y),
                            right_text,
                            font=font,
                            fill=(220, 220, 220, 255),
                            stroke_width=outline,
                            stroke_fill=(0, 0, 0, 255),
                        )
                else:
                    left_y = int(ry + extra["by"] + 4 + roy)
                    draw.text(
                        (int(rx + extra["x1"] + rox), left_y),
                        left_text,
                        font=font,
                        fill=(220, 220, 220, 255),
                        stroke_width=outline,
                        stroke_fill=(0, 0, 0, 255),
                    )
                    if right_text:
                        draw.text(
                            (int(rx + extra["x2"] - right_w + rox + rspreadx), left_y),
                            right_text,
                            font=font,
                            fill=(220, 220, 220, 255),
                            stroke_width=outline,
                            stroke_fill=(0, 0, 0, 255),
                        )

    # ── Extra indicators (dynamically discovered, e.g. FIT fields) ──
    if extra_indicators:
        for key, (value, unit, label) in extra_indicators.items():
            if key not in layout["indicators"]:
                continue
            current_cfg = layout["indicators"][key].copy()
            if not current_cfg.get("enabled", True):
                continue
            label = current_cfg.get("label", label)
            fv = f"{value:.1f} {unit}" if unit else f"{value:.1f}"
            chart_vals = chart_data.get(key) if chart_data else None
            res, rx, ry, _extra = render_value_indicator(
                canvas_w, canvas_h, layout, font_path,
                key, value, unit, label,
                cfg_override=current_cfg,
                formatted_val=fv,
                history_data=chart_vals,
                current_position=current_position,
            )
            if res:
                rotation = current_cfg.get("rotation", 0)
                if current_cfg.get("form", "text") == "text":
                    if rotation == 90:
                        rx = rx + res.height // 2
                    else:
                        rx = rx + res.width // 2
                rotated_paste(img, res, rx, ry, rotation)
                _bboxes[key] = (int(rx - res.width // 2), int(ry - res.height // 2), res.width, res.height)

    # Custom texts – use resolution-scaled outline
    ct_outline = max(0, int(round(
        int(layout.get("global", {}).get("text_outline", 3)) * min(canvas_w, canvas_h) / 1000
    )))
    for ct_cfg in layout.get("custom_texts", []):
        ct_res, ctx, cty = render_custom_text(canvas_w, canvas_h, font_path, ct_cfg, stroke_width=ct_outline)
        if ct_res:
            ct_rotation = int(ct_cfg.get("rotation", 0))
            rotated_paste(img, ct_res, ctx, cty, ct_rotation)

    return img


def render_preview(
    src_img: Image.Image,
    layout: dict[str, Any],
    font_path: str,
    date_text: str,
    time_text: str,
    speed_value: float,
    distance_m: float,
    max_distance_m: Optional[float] = None,
    alt_value: float = 0.0,
    min_alt: Optional[float] = None,
    max_alt: Optional[float] = None,
    iso_value: Optional[float] = None,
    exposure_value: Optional[float] = None,
    temp_value: Optional[float] = None,
    indicator_values: Optional[dict[str, float]] = None,
    max_speed_kmh: Optional[float] = None,
    power_value: Optional[float] = None,
    atemp_value: Optional[float] = None,
    hr_value: Optional[float] = None,
    cad_value: Optional[float] = None,
    battery_value: Optional[float] = None,
    _bboxes: Optional[dict[str, tuple[int, int, int, int]]] = None,
    chart_data: Optional[dict[str, list[float]]] = None,
    current_position: Optional[float] = None,
    extra_indicators: Optional[dict[str, tuple[float, str, str]]] = None,
) -> Image.Image:
    """Render a preview image: source frame with HUD overlay composited on top."""
    # Avoid a full-resolution copy if the image is already RGBA
    img = src_img if src_img.mode == "RGBA" else src_img.convert("RGBA")
    img = img.copy()
    w, h = img.size
    if _bboxes is None:
        _bboxes = {}
    overlay = compose_overlay(
        w,
        h,
        layout,
        font_path,
        date_text,
        time_text,
        speed_value,
        distance_m,
        max_distance_m,
        alt_value,
        min_alt,
        max_alt,
        iso_value,
        exposure_value,
        temp_value,
        indicator_values=indicator_values,
        max_speed_kmh=max_speed_kmh,
        power_value=power_value,
        atemp_value=atemp_value,
        hr_value=hr_value,
        cad_value=cad_value,
        battery_value=battery_value,
        _bboxes=_bboxes,
        chart_data=chart_data,
        current_position=current_position,
        extra_indicators=extra_indicators,
    )
    img.alpha_composite(overlay)
    return img
