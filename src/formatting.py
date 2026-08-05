"""Formatting helpers used by cards, charts, and tables."""

from __future__ import annotations

import math
import textwrap
from typing import Iterable

import numpy as np


def compact_number(value: float | int | None, decimals: int = 1) -> str:
    """Format a number with K, M, B, or T suffixes."""
    if value is None:
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if math.isnan(number):
        return "N/A"

    sign = "-" if number < 0 else ""
    number = abs(number)
    suffixes = (
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    )
    for threshold, suffix in suffixes:
        if number >= threshold:
            scaled = number / threshold
            precision = 0 if scaled >= 100 else decimals
            rendered = f"{scaled:.{precision}f}"
            if "." in rendered:
                rendered = rendered.rstrip("0").rstrip(".")
            return f"{sign}{rendered}{suffix}"

    if number.is_integer():
        return f"{sign}{int(number)}"
    rendered = f"{number:.{decimals}f}"
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return f"{sign}{rendered}"


def compact_percent(value: float | int | None, decimals: int = 1) -> str:
    """Format a proportion as a percentage."""
    if value is None:
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if math.isnan(number):
        return "N/A"
    return f"{number * 100:.{decimals}f}%"


def wrap_label(value: object, width: int = 28) -> str:
    """Wrap long category labels without cutting words."""
    text = str(value)
    return "<br>".join(textwrap.wrap(text, width=width)) or text


def compact_tick_spec(
    maximum: float | int,
    minimum: float | int = 0,
    target_ticks: int = 5,
) -> tuple[list[float], list[str]]:
    """Return readable tick positions and compact labels."""
    try:
        high = float(maximum)
        low = float(minimum)
    except (TypeError, ValueError):
        return [], []
    if not np.isfinite(high) or high <= low:
        return [low], [compact_number(low)]

    span = high - low
    raw_step = span / max(target_ticks, 1)
    magnitude = 10 ** math.floor(math.log10(raw_step)) if raw_step else 1
    normalized = raw_step / magnitude
    if normalized <= 1:
        nice = 1
    elif normalized <= 2:
        nice = 2
    elif normalized <= 5:
        nice = 5
    else:
        nice = 10
    step = nice * magnitude
    start = math.floor(low / step) * step
    end = math.ceil(high / step) * step
    values = np.arange(start, end + step * 0.5, step).tolist()
    return values, [compact_number(value) for value in values]


def compact_series(values: Iterable[float | int]) -> list[str]:
    """Apply compact formatting to a sequence."""
    return [compact_number(value) for value in values]
