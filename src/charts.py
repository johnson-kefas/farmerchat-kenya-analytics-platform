"""Plotly chart builders with consistent publication-quality styling."""

from __future__ import annotations

from collections.abc import Iterable
from html import escape
import textwrap

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config import CATEGORY_PALETTE, COLORS, MONTH_ORDER
from src.formatting import compact_number, compact_tick_spec, wrap_label


FONT_STACK = "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"


def _wrapped_html(value: object, width: int) -> tuple[str, int]:
    """Wrap Plotly text on word boundaries and return its rendered line count."""
    lines = textwrap.wrap(
        str(value),
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [str(value)]
    return "<br>".join(escape(line) for line in lines), len(lines)


def apply_chart_style(
    fig: go.Figure,
    title: str,
    subtitle: str,
    *,
    height: int = 460,
    show_legend: bool = False,
    legend_orientation: str = "h",
) -> go.Figure:
    """Apply shared typography, spacing, backgrounds, and interaction defaults."""
    wrapped_title, title_lines = _wrapped_html(title, 44)
    title_text = wrapped_title
    subtitle_lines = 0
    if subtitle:
        wrapped_subtitle, subtitle_lines = _wrapped_html(subtitle, 58)
        title_text += (
            f"<br><span style='font-size:12px;color:{COLORS['muted']};"
            f"font-weight:400'>{wrapped_subtitle}</span>"
        )
    top_margin = 70 + (title_lines - 1) * 18 + subtitle_lines * 17
    fig.update_layout(
        title={
            "text": title_text,
            "x": 0,
            "xanchor": "left",
            "y": 0.965,
            "yanchor": "top",
            "font": {"size": 17, "color": COLORS["ink"], "family": FONT_STACK},
        },
        height=height,
        autosize=True,
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font={"family": FONT_STACK, "size": 12, "color": COLORS["ink"]},
        hoverlabel={
            "bgcolor": COLORS["ink"],
            "bordercolor": COLORS["ink"],
            "font": {"family": FONT_STACK, "size": 12, "color": "#FFFFFF"},
        },
        margin={"l": 30, "r": 28, "t": top_margin, "b": 54},
        showlegend=show_legend,
        legend={
            "orientation": legend_orientation,
            "yanchor": "top",
            "y": -0.12,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 11, "color": COLORS["muted"]},
            "title": {"text": ""},
            "bgcolor": "rgba(255,255,255,0)",
        },
        hovermode="closest",
        hoverdistance=40,
        uirevision="farmerchat-responsive",
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=True,
        linecolor=COLORS["grid"],
        tickfont={"color": COLORS["muted"]},
        title_font={"color": COLORS["muted"]},
        ticks="outside",
        tickcolor=COLORS["grid"],
        automargin=True,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=COLORS["grid"],
        gridwidth=1,
        zeroline=False,
        showline=True,
        linecolor=COLORS["grid"],
        tickfont={"color": COLORS["muted"]},
        title_font={"color": COLORS["muted"]},
        ticks="outside",
        tickcolor=COLORS["grid"],
        automargin=True,
    )
    return fig


def set_compact_axis(
    fig: go.Figure,
    maximum: float | int,
    *,
    axis: str = "y",
    minimum: float | int = 0,
) -> go.Figure:
    """Apply uppercase compact-number labels to one axis."""
    values, labels = compact_tick_spec(maximum, minimum)
    updater = {"tickmode": "array", "tickvals": values, "ticktext": labels}
    if axis == "x":
        fig.update_xaxes(**updater)
    else:
        fig.update_yaxes(**updater)
    return fig


def horizontal_bar(
    data: pd.DataFrame,
    category: str,
    value: str,
    title: str,
    subtitle: str,
    *,
    height: int = 520,
    color: str = COLORS["blue"],
    label_width: int = 30,
) -> go.Figure:
    """Build a sorted, compact-label horizontal bar chart."""
    ordered = data.sort_values(value, ascending=True).copy()
    labels = ordered[category].map(lambda item: wrap_label(item, label_width))
    compact_values = ordered[value].map(compact_number)
    fig = go.Figure(
        go.Bar(
            x=ordered[value],
            y=labels,
            orientation="h",
            marker={
                "color": color,
                "line": {"color": "rgba(24,34,48,0.35)", "width": 0.5},
            },
            text=compact_values,
            textposition="outside",
            textfont={"size": 11, "color": COLORS["muted"]},
            constraintext="none",
            cliponaxis=False,
            customdata=np.stack(
                [ordered[category].astype(str), compact_values.astype(str)], axis=-1
            ),
            hovertemplate="<b>%{customdata[0]}</b><br>Queries: %{customdata[1]}<extra></extra>",
        )
    )
    apply_chart_style(fig, title, subtitle, height=height)
    fig.update_layout(margin={"l": 34, "r": 78, "b": 54}, bargap=0.28)
    fig.update_xaxes(title="Queries", rangemode="tozero")
    fig.update_yaxes(title="", showgrid=False)
    return set_compact_axis(fig, ordered[value].max() if not ordered.empty else 0, axis="x")


def donut_chart(
    labels: Iterable[object],
    values: Iterable[float | int],
    title: str,
    subtitle: str,
    *,
    colors: list[str] | None = None,
    height: int = 420,
) -> go.Figure:
    """Build a restrained donut with compact hover values."""
    label_list = [str(value) for value in labels]
    value_list = list(values)
    compact_values = [compact_number(value) for value in value_list]
    fig = go.Figure(
        go.Pie(
            labels=label_list,
            values=value_list,
            hole=0.64,
            sort=False,
            marker={
                "colors": colors or CATEGORY_PALETTE[: len(label_list)],
                "line": {"color": "#FFFFFF", "width": 2},
            },
            textinfo="percent",
            textfont={"size": 12, "family": FONT_STACK},
            customdata=compact_values,
            hovertemplate="<b>%{label}</b><br>Queries: %{customdata}<br>Share: %{percent}<extra></extra>",
        )
    )
    apply_chart_style(fig, title, subtitle, height=height, show_legend=True)
    fig.update_layout(
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.08,
            "xanchor": "center",
            "x": 0.5,
            "font": {"size": 11, "color": COLORS["muted"]},
        },
        margin={"l": 24, "r": 24, "b": 84},
    )
    return fig


def treemap_chart(
    data: pd.DataFrame,
    path: list[str],
    value: str,
    title: str,
    subtitle: str,
    *,
    height: int = 560,
) -> go.Figure:
    """Build a bounded hierarchical treemap."""
    working = data.copy()
    working["_compact"] = working[value].map(compact_number)
    fig = px.treemap(
        working,
        path=path,
        values=value,
        color=path[0],
        color_discrete_sequence=CATEGORY_PALETTE,
        custom_data=["_compact"],
    )
    fig.update_traces(
        textinfo="label+percent parent",
        textfont={"size": 12, "family": FONT_STACK},
        marker={"line": {"color": "#FFFFFF", "width": 1.5}},
        hovertemplate="<b>%{label}</b><br>Queries: %{customdata[0]}<br>Share of parent: %{percentParent:.1%}<extra></extra>",
        root_color=COLORS["grey_light"],
    )
    apply_chart_style(fig, title, subtitle, height=height)
    fig.update_layout(margin={"l": 20, "r": 20, "b": 24})
    return fig


def sunburst_chart(
    data: pd.DataFrame,
    path: list[str],
    value: str,
    title: str,
    subtitle: str,
    *,
    height: int = 650,
) -> go.Figure:
    """Build a bounded hierarchy for domain-to-intent drill-down."""
    working = data.copy()
    working["_compact"] = working[value].map(compact_number)
    fig = px.sunburst(
        working,
        path=path,
        values=value,
        color=path[0],
        color_discrete_sequence=CATEGORY_PALETTE,
        custom_data=["_compact"],
    )
    fig.update_traces(
        insidetextorientation="auto",
        textfont={"family": FONT_STACK},
        marker={"line": {"color": "#FFFFFF", "width": 1.2}},
        hovertemplate="<b>%{label}</b><br>Queries: %{customdata[0]}<br>Share of parent: %{percentParent:.1%}<extra></extra>",
    )
    apply_chart_style(fig, title, subtitle, height=height)
    fig.update_layout(margin={"l": 20, "r": 20, "b": 24})
    return fig


def sankey_chart(
    pairs: pd.DataFrame,
    title: str,
    subtitle: str,
    *,
    height: int = 600,
) -> go.Figure:
    """Build a two-column Sankey for co-occurring intercrop components."""
    sources = sorted(pairs["Source"].unique())
    targets = sorted(pairs["Target"].unique())
    nodes = [f"{item} · A" for item in sources] + [f"{item} · B" for item in targets]
    labels = sources + targets
    source_index = {name: index for index, name in enumerate(sources)}
    target_index = {
        name: len(sources) + index for index, name in enumerate(targets)
    }
    colors = [
        COLORS["blue_light"] if index < len(sources) else COLORS["gold_light"]
        for index in range(len(nodes))
    ]
    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node={
                "label": labels,
                "color": colors,
                "line": {"color": COLORS["grey"], "width": 0.6},
                "pad": 14,
                "thickness": 16,
            },
            link={
                "source": [source_index[value] for value in pairs["Source"]],
                "target": [target_index[value] for value in pairs["Target"]],
                "value": pairs["Queries"].tolist(),
                "color": "rgba(37,99,235,0.22)",
                "customdata": pairs["Queries"].map(compact_number),
                "hovertemplate": "%{source.label} + %{target.label}<br>Queries: %{customdata}<extra></extra>",
            },
        )
    )
    apply_chart_style(fig, title, subtitle, height=height)
    fig.update_layout(margin={"l": 30, "r": 30, "b": 34})
    return fig


def line_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    subtitle: str,
    *,
    color: str | None = None,
    height: int = 470,
    percent_axis: bool = False,
) -> go.Figure:
    """Build a line chart with compact tooltips and optional series grouping."""
    working = data.copy()
    working["_compact"] = (
        working[y].map(lambda value: f"{value:.1%}")
        if percent_axis
        else working[y].map(compact_number)
    )
    if color:
        fig = px.line(
            working,
            x=x,
            y=y,
            color=color,
            markers=True,
            color_discrete_sequence=CATEGORY_PALETTE,
            custom_data=["_compact"],
        )
        show_legend = True
    else:
        fig = px.line(
            working,
            x=x,
            y=y,
            markers=True,
            custom_data=["_compact"],
        )
        fig.update_traces(line={"color": COLORS["blue"], "width": 2.5})
        show_legend = False
    fig.update_traces(
        marker={"size": 6, "line": {"width": 1.5, "color": "#FFFFFF"}},
        hovertemplate="%{x|%b %Y}<br>Value: %{customdata[0]}<extra></extra>",
    )
    apply_chart_style(fig, title, subtitle, height=height, show_legend=show_legend)
    fig.update_xaxes(title="", tickformat="%b<br>%Y")
    if percent_axis:
        fig.update_yaxes(title="Share of monthly queries", tickformat=".0%")
    else:
        fig.update_yaxes(title="Queries", rangemode="tozero")
        set_compact_axis(fig, working[y].max() if not working.empty else 0)
    return fig


def stacked_area_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    color: str,
    title: str,
    subtitle: str,
    *,
    height: int = 540,
) -> go.Figure:
    """Build a stacked-area composition trend."""
    working = data.copy()
    working["_compact"] = working[y].map(compact_number)
    fig = px.area(
        working,
        x=x,
        y=y,
        color=color,
        color_discrete_sequence=CATEGORY_PALETTE,
        custom_data=["_compact"],
    )
    fig.update_traces(
        line={"width": 0.8, "color": "rgba(23,32,51,0.45)"},
        hovertemplate="%{x|%b %Y}<br>Queries: %{customdata[0]}<extra></extra>",
    )
    apply_chart_style(fig, title, subtitle, height=height, show_legend=True)
    fig.update_xaxes(title="", tickformat="%b<br>%Y")
    fig.update_yaxes(title="Queries", rangemode="tozero")
    return set_compact_axis(
        fig,
        working.groupby(x, observed=True)[y].sum().max() if not working.empty else 0,
    )


def monthly_heatmap(
    data: pd.DataFrame,
    title: str,
    subtitle: str,
    *,
    height: int = 360,
) -> go.Figure:
    """Build a year-by-month heatmap with compact cell labels."""
    working = data.copy()
    working["Year"] = working["Month"].dt.year
    working["Month label"] = working["Month"].dt.strftime("%b")
    pivot = (
        working.pivot(index="Year", columns="Month label", values="Queries")
        .reindex(columns=MONTH_ORDER)
        .fillna(0)
    )
    text = np.vectorize(compact_number)(pivot.values)
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=[str(year) for year in pivot.index],
            colorscale=[
                [0.0, "#EFF5FF"],
                [0.5, "#8DB4FF"],
                [1.0, COLORS["blue_dark"]],
            ],
            text=text,
            texttemplate="%{text}",
            customdata=text,
            hovertemplate="<b>%{y} %{x}</b><br>Queries: %{customdata}<extra></extra>",
            colorbar={"title": "Queries", "thickness": 12, "len": 0.75},
        )
    )
    apply_chart_style(fig, title, subtitle, height=height)
    fig.update_xaxes(title="", showgrid=False, side="bottom")
    fig.update_yaxes(title="", showgrid=False, autorange="reversed")
    fig.update_layout(margin={"l": 32, "r": 64, "b": 46})
    return fig


def matrix_heatmap(
    matrix: pd.DataFrame,
    title: str,
    subtitle: str,
    *,
    percent: bool = False,
    height: int = 620,
) -> go.Figure:
    """Build a categorical matrix heatmap."""
    values = matrix.values
    text = (
        np.vectorize(lambda value: f"{value:.0%}")(values)
        if percent
        else np.vectorize(compact_number)(values)
    )
    fig = go.Figure(
        go.Heatmap(
            z=values,
            x=[wrap_label(value, 18) for value in matrix.columns],
            y=[wrap_label(value, 24) for value in matrix.index],
            colorscale=[
                [0.0, "#F7FAFF"],
                [0.5, "#AFC8F7"],
                [1.0, COLORS["blue_dark"]],
            ],
            customdata=text,
            hovertemplate="<b>%{y}</b><br>%{x}: %{customdata}<extra></extra>",
            colorbar={
                "title": "Share" if percent else "Queries",
                "tickformat": ".0%" if percent else None,
                "thickness": 12,
            },
        )
    )
    apply_chart_style(fig, title, subtitle, height=height)
    fig.update_xaxes(title="", showgrid=False)
    fig.update_yaxes(title="", showgrid=False)
    fig.update_layout(margin={"l": 48, "r": 72, "b": 98})
    return fig


def add_rain_season_bands(fig: go.Figure, years: Iterable[int]) -> go.Figure:
    """Add restrained MAM and OND reference bands as contextual guides."""
    unique_years = sorted({int(year) for year in years if pd.notna(year)})
    for index, year in enumerate(unique_years):
        fig.add_vrect(
            x0=f"{year}-03-01",
            x1=f"{year}-06-01",
            fillcolor=COLORS["blue_light"],
            opacity=0.28,
            line_width=0,
            annotation_text="MAM" if index == 0 else "",
            annotation_position="top left",
        )
        fig.add_vrect(
            x0=f"{year}-10-01",
            x1=f"{year + 1}-01-01",
            fillcolor=COLORS["gold_light"],
            opacity=0.30,
            line_width=0,
            annotation_text="OND" if index == 0 else "",
            annotation_position="top left",
        )
    return fig
