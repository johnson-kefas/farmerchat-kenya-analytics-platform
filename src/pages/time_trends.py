"""Time Trends dashboard page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.charts import (
    add_rain_season_bands,
    line_chart,
    monthly_heatmap,
    set_compact_axis,
    stacked_area_chart,
)
from src.components import (
    chart,
    empty_state,
    metric_grid,
    page_header,
    production_banner,
    scope_note,
    section_title,
    table,
)
from src.config import CATEGORY_PALETTE, ModuleConfig
from src.formatting import compact_number, compact_percent
from src.metrics import monthly_counts, monthly_domain_mix, monthly_signal_share, safe_share


def _seasonal_summary(
    df: pd.DataFrame,
    module: ModuleConfig,
) -> pd.DataFrame:
    """Summarize query volume and the three approved taxonomy signals by season."""
    signal_domains = tuple(
        (f"{label} share", domain) for label, domain in module.time_signals
    )
    rows: list[dict[str, object]] = []
    for phase, group in df.groupby("season_phase", observed=True):
        row: dict[str, object] = {
            "Seasonal window": phase,
            "Queries": len(group),
        }
        for label, domain in signal_domains:
            row[label] = safe_share(
                int(group["domain_label"].eq(domain).sum()),
                len(group),
            )
        rows.append(row)
    order = {
        "Before MAM": 1,
        "MAM long rains": 2,
        "Jun-Jul transition": 3,
        "Before OND": 4,
        "OND short rains": 5,
    }
    return (
        pd.DataFrame(rows)
        .assign(_order=lambda frame: frame["Seasonal window"].map(order))
        .sort_values("_order")
        .drop(columns="_order")
    )


def render(df: pd.DataFrame, module: ModuleConfig) -> None:
    """Render production-period trends and cautious seasonal signals."""
    page_header(
        "Time trends",
        (
            "Examine monthly movement, seasonality, and taxonomy-based livestock "
            "planning, management, and weather-risk signals using production data from "
            "2025–2026 only."
            if module.key == "livestock"
            else "Examine monthly movement, seasonality, and taxonomy-based planning, "
            "pest, and harvest signals using production data from 2025–2026 only."
        ),
    )
    production_banner()
    if df.empty:
        empty_state("No records match the current global filters.")
        return

    monthly = monthly_counts(df)
    peak = monthly.loc[monthly["Queries"].idxmax()]
    selected_years = sorted(df["year"].dropna().astype(int).unique().tolist())
    month_count = int(monthly["Month"].nunique())
    classified = int(df["domain_label"].ne("Unclassified").sum())

    metric_grid(
        [
            {
                "label": "Production-period queries",
                "value": len(df),
                "note": ", ".join(str(year) for year in selected_years),
                "accent": "blue",
            },
            {
                "label": "Months represented",
                "value": month_count,
                "note": "Selected continuous production window",
                "accent": "teal",
            },
            {
                "label": "Peak query month",
                "value": peak["Month"].strftime("%b %Y"),
                "note": f"{compact_number(peak['Queries'])} queries",
                "accent": "gold",
            },
            {
                "label": "Domain-classified queries",
                "value": classified,
                "note": compact_percent(safe_share(classified, len(df))),
                "accent": "pink",
            },
        ],
        columns=4,
    )

    scope_note(
        "<strong>Interpretation rule.</strong> MAM and OND bands are calendar context, "
        "not rainfall observations. Peaks aligned with these windows are described as "
        "patterns consistent with seasonal information demand, not proof of rainfall, "
        "disease outbreaks, or climate change.",
        kind="warning",
    )

    with st.expander("Year coverage and comparability", expanded=False):
        yearly = (
            df.groupby("year", observed=True)
            .agg(
                Queries=("query", "size"),
                Months=("month_period", "nunique"),
                First_month=("month_period", "min"),
                Last_month=("month_period", "max"),
            )
            .reset_index()
            .rename(columns={"year": "Year"})
        )
        yearly["Average per month"] = yearly["Queries"] / yearly["Months"]
        yearly["Queries"] = yearly["Queries"].map(compact_number)
        yearly["Average per month"] = yearly["Average per month"].map(compact_number)
        yearly["First month"] = yearly.pop("First_month").dt.strftime("%b %Y")
        yearly["Last month"] = yearly.pop("Last_month").dt.strftime("%b %Y")
        table(
            yearly[
                [
                    "Year",
                    "Queries",
                    "Months",
                    "Average per month",
                    "First month",
                    "Last month",
                ]
            ],
            height=180,
        )
        st.caption(
            "The annual totals should not be compared as complete calendar years when "
            "the selected year contains fewer than 12 observed months."
        )

    trend = line_chart(
        monthly,
        "Month",
        "Queries",
        "Monthly farmer query volume",
        "MAM and OND bands provide seasonal calendar context",
        height=520,
    )
    add_rain_season_bands(trend, selected_years)
    chart(trend, f"{module.key}_time_monthly_trend")
    if month_count < 8:
        st.caption(
            "The current filters leave fewer than eight monthly points. Interpret the "
            "line as a short period comparison rather than a stable trend."
        )

    section_title(
        "Monthly intensity",
        "The matrix makes month-to-month changes and incomplete year coverage easy to see.",
    )
    heatmap = monthly_heatmap(
        monthly,
        "Monthly query heatmap",
        "Every cell uses the filtered query count; blank production months appear as zero",
        height=380,
    )
    chart(heatmap, f"{module.key}_time_monthly_heatmap")

    section_title(
        "Domain mix over time",
        "The leading five classified domains are shown separately. Remaining and "
        "unclassified rows are grouped to keep the view readable.",
    )
    domain_mix = monthly_domain_mix(df)
    area = stacked_area_chart(
        domain_mix,
        "Month",
        "Queries",
        "Domain",
        "Monthly primary-domain composition",
        "Top five classified domains plus Other / unclassified",
        height=590,
    )
    add_rain_season_bands(area, selected_years)
    chart(area, f"{module.key}_time_domain_area")

    section_title(
        "Seasonal knowledge-demand signals",
        "Monthly shares normalize for large changes in total query volume. The signals "
        "use approved primary domains rather than keyword inference.",
    )
    signals = monthly_signal_share(df, module.time_signals)
    signal_labels = [label for label, _ in module.time_signals]
    signal_title = (
        ", ".join(signal_labels[:-1]) + f", and {signal_labels[-1]} shares"
    )
    signal_fig = line_chart(
        signals,
        "Month",
        "Share",
        signal_title,
        "Share of all selected queries in each month",
        color="Signal",
        height=560,
        percent_axis=True,
    )
    add_rain_season_bands(signal_fig, selected_years)
    chart(signal_fig, f"{module.key}_time_signal_share")

    seasonal = _seasonal_summary(df, module)
    section_title(
        "Seasonal comparison table",
        "Exact volumes and normalized taxonomy shares for the five calendar windows.",
    )
    seasonal_view = seasonal.copy()
    seasonal_view["Queries"] = seasonal_view["Queries"].map(compact_number)
    for column in [f"{label} share" for label in signal_labels]:
        seasonal_view[column] = seasonal_view[column].map(compact_percent)
    table(seasonal_view, height=360)

    observations: list[str] = []
    for signal in signal_labels:
        subset = signals.loc[signals["Signal"].eq(signal)]
        if not subset.empty:
            peak_row = subset.loc[subset["Share"].idxmax()]
            observations.append(
                f"{signal} peaks at {compact_percent(peak_row['Share'])} of monthly "
                f"queries in {peak_row['Month'].strftime('%b %Y')}"
            )
    scope_note(
        "<strong>Observed peaks.</strong> "
        + "; ".join(observations)
        + ". These are descriptive demand signals. External rainfall, agronomic, and "
        "outbreak data would be required for causal or climate-related conclusions."
    )
