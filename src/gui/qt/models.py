"""Modele danych — struktury przekazywane między GUI a kontrolerem.

GUI operuje tylko na tych strukturach, nie zna szczegółów GPMF/GPX/FIT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DataStream:
    """Reprezentuje pojedynczy strumień danych telemetrycznych.

    Tworzony przez kontroler po analizie załadowanych danych.
    GUI używa go do dynamicznego tworzenia przycisków.
    """

    key: str            # unikalny identyfikator (np. "speed_text", "heart_rate")
    display_name: str   # nazwa wyświetlana (np. "Prędkość", "Heart Rate")
    source: str         # źródło: "gpmf", "gpx", "fit"
    category: str       # kategoria: "gps", "sensor", "camera", "other"
    unit: str = ""      # jednostka (np. "km/h", "bpm", "m")

    # Sugerowana forma wizualizacji
    suggested_form: str = "text"  # "text", "gauge", "bar", "chart", "map"

    # Liczba dostępnych próbek
    sample_count: int = 0

    # Zakres wartości [min, max]
    value_range: tuple[float, float] = (0.0, 100.0)


@dataclass
class FieldSchema:
    """Schema pojedynczego pola właściwości wskaźnika."""

    name: str           # nazwa pola (np. "font_size", "color", "min_val")
    field_type: str     # typ: "bool", "int", "float", "choice", "text", "color"
    label: str          # etykieta wyświetlana

    # Zakładka w panelu właściwości ("" = header nad zakładkami):
    tab: str = "Text"

    # Dla typów numerycznych:
    min_val: float | None = None
    max_val: float | None = None
    step: float | None = None

    # Dla typu choice:
    choices: list[str] | None = None


# ── Fabryki pól per-zakładka ────────────────────────────────────────────────

def _header_fields() -> list[FieldSchema]:
    """Pola zawsze widoczne nad zakładkami (pozycja, etykieta, rotacja)."""
    return [
        FieldSchema("size", "float", "Rozmiar", tab="",
                    min_val=0.01, max_val=0.5, step=0.001),
        FieldSchema("label", "text", "Etykieta", tab=""),
        FieldSchema("x", "float", "Pozycja X", tab="",
                    min_val=0.0, max_val=1.0, step=0.001),
        FieldSchema("y", "float", "Pozycja Y", tab="",
                    min_val=0.0, max_val=1.0, step=0.001),
        FieldSchema("rotation", "choice", "Rotacja", tab="",
                    choices=["0", "90", "180", "270"]),
    ]


def _form_field() -> list[FieldSchema]:
    """Pole wyboru formy – zawsze widoczne."""
    return [
        FieldSchema("form", "choice", "Forma", tab="",
                    choices=["text", "gauge", "bar", "chart",
                             "segment_bar", "map"]),
    ]


def _text_tab_fields(
    font_range=(0.005, 0.1), dist_range=(-2.0, 2.0), repo_range=(-0.3, 0.3),
) -> list[FieldSchema]:
    """Zakładka Text – rozmiar i pozycja tekstu wartości."""
    return [
        FieldSchema("font_size", "float", "Size",
                    tab="Text",
                    min_val=font_range[0], max_val=font_range[1], step=0.001),
        FieldSchema("text_distance", "float", "Distance",
                    tab="Text",
                    min_val=dist_range[0], max_val=dist_range[1], step=0.1),
        FieldSchema("decimals", "int", "Decimals",
                    tab="Text", min_val=0, max_val=3, step=1),
        FieldSchema("show_value", "bool", "Value", tab="Text"),
        FieldSchema("show_units", "bool", "Units", tab="Text"),
        FieldSchema("value_offset_y", "float", "Reposition",
                    tab="Text",
                    min_val=repo_range[0], max_val=repo_range[1], step=0.001),
    ]


def _labels_tab_fields() -> list[FieldSchema]:
    """Zakładka Labels – etykiety na osi."""
    return [
        FieldSchema("label_count", "int", "Number",
                    tab="Labels", min_val=2, max_val=21, step=1),
        FieldSchema("label_font_size", "float", "Size",
                    tab="Labels", min_val=1.0, max_val=10.0, step=0.1),
        FieldSchema("label_units", "bool", "Units", tab="Labels"),
        FieldSchema("show_average", "bool", "Average", tab="Labels"),
    ]


def _ticks_tab_fields() -> list[FieldSchema]:
    """Zakładka Ticks – podziałki."""
    return [
        FieldSchema("ticks", "int", "Tick",
                    tab="Ticks", min_val=0, max_val=20, step=1),
        FieldSchema("thickness", "int", "Width",
                    tab="Ticks", min_val=1, max_val=10, step=1),
    ]


def _gauge_tab_fields() -> list[FieldSchema]:
    """Zakładka Gauge – kropka kursora i pionowy bar."""
    return [
        FieldSchema("marker_size", "int", "Size",
                    tab="Gauge", min_val=3, max_val=20, step=1),
        FieldSchema("marker_color", "color", "Color", tab="Gauge"),
        FieldSchema("bar_width", "int", "Width",
                    tab="Gauge", min_val=1, max_val=10, step=1),
        FieldSchema("show_bar", "bool", "Bar", tab="Gauge"),
    ]


def _shape_tab_fields() -> list[FieldSchema]:
    """Zakładka Shape – pola specyficzne dla kształtu (rozmiar w headerze)."""
    return []


# ── Schematy per-typ wskaźnika ─────────────────────────────────────────────

def text_indicator_fields() -> list[FieldSchema]:
    """Text: tylko Text + Shape."""
    return (
        _header_fields() + _form_field()
        + _text_tab_fields() + _shape_tab_fields()
    )


def gauge_indicator_fields() -> list[FieldSchema]:
    """Gauge: Text, Labels, Ticks, Gauge, Shape."""
    return (
        _header_fields() + _form_field()
        + _text_tab_fields()
        + _labels_tab_fields()
        + _ticks_tab_fields()
        + _gauge_tab_fields()
        + _shape_tab_fields()
        + [FieldSchema("min_val", "float", "Minimum", tab="Ticks",
                       min_val=0, max_val=1000, step=1),
           FieldSchema("max_val", "float", "Maksimum", tab="Ticks",
                       min_val=1, max_val=10000, step=1)]
    )


def bar_indicator_fields() -> list[FieldSchema]:
    """Bar: to samo co gauge + range_labels."""
    return gauge_indicator_fields() + [
        FieldSchema("show_range_labels", "bool", "Pokaż zakres", tab="Text"),
        FieldSchema("range_label_offset_x", "float", "Offset X", tab="Text",
                    min_val=-0.2, max_val=0.2, step=0.001),
        FieldSchema("range_label_offset_y", "float", "Offset Y", tab="Text",
                    min_val=-0.2, max_val=0.2, step=0.001),
    ]


def chart_indicator_fields() -> list[FieldSchema]:
    """Chart: wszystkie 5 zakładek."""
    return (
        _header_fields() + _form_field()
        + _text_tab_fields()
        + _labels_tab_fields()
        + _ticks_tab_fields()
        + _gauge_tab_fields()
        + _shape_tab_fields()
        + [FieldSchema("min_val", "float", "Minimum", tab="Ticks",
                       min_val=0, max_val=1000, step=1),
           FieldSchema("max_val", "float", "Maksimum", tab="Ticks",
                       min_val=1, max_val=10000, step=1),
           FieldSchema("chart_color", "color", "Kolor linii", tab="Text"),
           FieldSchema("fill_color", "color", "Kolor wypełnienia", tab="Text"),
           FieldSchema("fill_alpha", "int", "Alfa", tab="Text",
                       min_val=0, max_val=255, step=5)]
    )


def segment_bar_indicator_fields() -> list[FieldSchema]:
    """SegmentBar: Text + Shape + specyficzne."""
    return (
        _header_fields() + _form_field()
        + _text_tab_fields()
        + _shape_tab_fields()
        + [FieldSchema("width", "int", "Szerokość", tab="Shape",
                       min_val=50, max_val=500, step=10),
           FieldSchema("height", "int", "Wysokość", tab="Shape",
                       min_val=20, max_val=200, step=5),
           FieldSchema("segments", "int", "Segmenty", tab="Shape",
                       min_val=2, max_val=50, step=1),
           FieldSchema("segment_gap", "int", "Odstęp", tab="Shape",
                       min_val=0, max_val=20, step=1),
           FieldSchema("segment_radius", "int", "Zaokrąglenie", tab="Shape",
                       min_val=0, max_val=20, step=1),
           FieldSchema("min_val", "float", "Minimum", tab="Ticks",
                       min_val=0, max_val=1000, step=1),
           FieldSchema("max_val", "float", "Maksimum", tab="Ticks",
                       min_val=1, max_val=10000, step=1),
           FieldSchema("show_min", "bool", "Pokaż minimum", tab="Text"),
           FieldSchema("show_max", "bool", "Pokaż maksimum", tab="Text"),
           FieldSchema("show_label", "bool", "Pokaż etykietę", tab="Text"),
           FieldSchema("direction", "choice", "Kierunek", tab="Shape",
                       choices=["horizontal", "vertical"]),
           FieldSchema("grow_height", "bool", "Rosnąca wys.", tab="Shape"),
           FieldSchema("inactive_alpha", "int", "Alfa nieakt.", tab="Shape",
                       min_val=20, max_val=255, step=5),
           FieldSchema("inactive_color", "color", "Kolor nieakt.", tab="Shape")]
    )


def map_indicator_fields() -> list[FieldSchema]:
    """Map: Text + Shape.  Dwa typy: podążająca (map) i statyczna (static_map)."""
    return (
        _header_fields()
        + [FieldSchema("form", "choice", "Typ mapy", tab="",
                       choices=["map", "static_map"])]
        + _text_tab_fields()
        + _shape_tab_fields()
        + [FieldSchema("zoom", "int", "Zoom", tab="Shape",
                       min_val=10, max_val=20, step=1),
           FieldSchema("map_style", "choice", "Styl mapy", tab="Shape",
                       choices=["light_all", "light_nolabels", "dark_all",
                                "dark_nolabels", "voyager_all", "voyager_nolabels"]),
           FieldSchema("marker_size", "int", "Znacznik", tab="Shape",
                       min_val=3, max_val=20, step=1),
           FieldSchema("marker_color", "color", "Kolor znacz.", tab="Shape")]
    )


# Mapa: forma → funkcja generująca schemat
FORM_SCHEMA_MAP: dict[str, callable] = {
    "text":        text_indicator_fields,
    "gauge":       gauge_indicator_fields,
    "bar":         bar_indicator_fields,
    "chart":       chart_indicator_fields,
    "segment_bar": segment_bar_indicator_fields,
    "map":         map_indicator_fields,
    "static_map":  map_indicator_fields,
}


def get_schema_for_form(form: str) -> list[FieldSchema]:
    """Zwraca schemat pól dla podanej formy wskaźnika."""
    fn = FORM_SCHEMA_MAP.get(form, text_indicator_fields)
    return fn()
