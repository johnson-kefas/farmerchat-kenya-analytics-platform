"""Reusable Streamlit presentation components."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import PLOTLY_CONFIG
from src.formatting import compact_number

ACCENT_NAMES = {"blue", "teal", "gold", "pink", "grey"}


def load_css(css_path: Path) -> None:
    """Load local CSS into the Streamlit page."""
    st.html(f"<style>{css_path.read_text(encoding='utf-8')}</style>")


def page_header(title: str, description: str) -> None:
    """Render a consistent page title and purpose statement."""
    st.html(
        "".join(
            (
                '<header class="page-header">',
                '<p class="page-eyebrow">FarmerChat Kenya</p>',
                f'<h1 class="page-title">{escape(title)}</h1>',
                f'<p class="page-description">{escape(description)}</p>',
                "</header>",
            )
        )
    )


def production_banner() -> None:
    """Make the date restriction visible throughout the application."""
    st.html(
        "".join(
            (
                '<div class="production-banner">',
                '<div class="production-banner__period">',
                "<span>Reporting period</span>",
                "<strong>2025–2026</strong>",
                "</div>",
                "<p>2024 records were used only for system testing and are intentionally "
                "excluded before global filters are applied.</p>",
                "</div>",
            )
        )
    )


def scope_note(text: str, kind: str = "info") -> None:
    """Render a prominent analytical scope or quality note."""
    safe_kind = kind if kind in {"info", "warning"} else "info"
    label = "Context" if safe_kind == "info" else "Important"
    st.html(
        f'<div class="scope-note {safe_kind}">'
        f'<span class="scope-note__label">{label}</span>'
        f'<div class="scope-note__body">{text}</div>'
        "</div>"
    )


def _metric_card_markup(
    label: str,
    value: str | int | float,
    note: str,
    accent: str,
) -> str:
    """Build one compact card without Markdown-significant indentation."""
    rendered = compact_number(value) if isinstance(value, (int, float)) else value
    safe_accent = accent if accent in ACCENT_NAMES else "blue"
    value_class = " metric-value--text" if isinstance(value, str) else ""
    return (
        f'<article class="metric-card accent-{safe_accent}">'
        '<div class="metric-label">'
        f'<span aria-hidden="true"></span>{escape(str(label))}'
        "</div>"
        f'<div class="metric-value{value_class}">{escape(str(rendered))}</div>'
        f'<div class="metric-note">{escape(str(note))}</div>'
        "</article>"
    )


def metric_card(
    label: str,
    value: str | int | float,
    note: str = "",
    *,
    accent: str = "blue",
) -> None:
    """Render one responsive KPI card."""
    st.html(_metric_card_markup(label, value, note, accent))


def metric_grid(metrics: list[dict[str, object]], columns: int = 4) -> None:
    """Render container-aware KPI cards that reflow before text becomes cramped."""
    del columns
    cards = "".join(
        _metric_card_markup(
            label=str(metric["label"]),
            value=metric["value"],
            note=str(metric.get("note", "")),
            accent=str(metric.get("accent", "blue")),
        )
        for metric in metrics
    )
    st.html(f'<section class="metric-grid">{cards}</section>')


def chart(fig: go.Figure, key: str) -> None:
    """Render a responsive Plotly chart with export controls."""
    st.plotly_chart(
        fig,
        width="stretch",
        config=PLOTLY_CONFIG,
        key=key,
        theme=None,
    )


def table(
    frame: pd.DataFrame,
    *,
    height: int = 420,
    column_config: dict | None = None,
) -> None:
    """Render a searchable, bounded Streamlit table."""
    st.dataframe(
        frame,
        width="stretch",
        hide_index=True,
        height=height,
        column_config=column_config,
    )


def section_title(title: str, description: str = "") -> None:
    """Render a compact section heading."""
    st.html(f'<h2 class="section-title">{escape(title)}</h2>')
    if description:
        st.html(f'<p class="section-description">{escape(description)}</p>')


def empty_state(message: str) -> None:
    """Render a clear empty-filter state."""
    st.info(message, icon="ℹ️")


def app_footer(title: str, version: str, source_name: str) -> None:
    """Render a quiet, presentation-ready provenance footer."""
    st.html(
        '<footer class="app-footer">'
        f"<span>{escape(title)} · v{escape(version)}</span>"
        f"<span>Approved source: {escape(source_name)}</span>"
        "<span>Production period only</span>"
        "</footer>"
    )
