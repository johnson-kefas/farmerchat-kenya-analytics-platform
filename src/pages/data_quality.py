"""Data Quality dashboard page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.charts import donut_chart, horizontal_bar, matrix_heatmap
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
from src.config import COLORS, ModuleConfig
from src.formatting import compact_number, compact_percent
from src.metrics import (
    missing_profile,
    missingness_by_year,
    quality_summary,
    safe_share,
)


def _quality_observations(summary: dict[str, float | int]) -> None:
    """Render concise, evidence-backed interpretation."""
    unique = int(summary["unique_rows"])
    county_rate = safe_share(summary["missing_county"], unique)
    unclassified_rate = safe_share(summary["unclassified_domain"], unique)
    near_rate = safe_share(summary["near_duplicate_rows"], unique)
    review_rate = safe_share(summary["review_required"], unique)
    scope_note(
        "<strong>Main interpretation risks.</strong> "
        f"County metadata is missing for {compact_percent(county_rate)} of the current "
        f"selection. Primary domain is unclassified for {compact_percent(unclassified_rate)}. "
        f"The conservative text-normalization check flags {compact_percent(near_rate)} as "
        f"potential near-duplicate rows, and {compact_percent(review_rate)} require at least "
        "one classification or scope review. These issues affect geographic and taxonomy "
        "interpretation more than the integrity of the approved query text.",
        kind="warning",
    )


def render(df: pd.DataFrame, module: ModuleConfig) -> None:
    """Render the data-quality view."""
    page_header(
        "Data quality",
        "Evaluate uniqueness, completeness, metadata coverage, and review requirements "
        f"within the approved {module.label.lower()} production-period records.",
    )
    production_banner()
    if df.empty:
        empty_state("No records match the current global filters.")
        return

    summary = quality_summary(df)
    metric_grid(
        [
            {
                "label": "Total source occurrences",
                "value": summary["original_occurrences"],
                "note": "Reconstructed from query_duplicate_count",
                "accent": "blue",
            },
            {
                "label": "Unique approved queries",
                "value": summary["unique_rows"],
                "note": "One retained row per approved query",
                "accent": "teal",
            },
            {
                "label": "Exact duplicates removed",
                "value": summary["duplicate_occurrences"],
                "note": compact_percent(summary["duplicate_share"]) + " of source occurrences",
                "accent": "gold",
            },
            {
                "label": "Potential near duplicates",
                "value": summary["near_duplicate_rows"],
                "note": "Conservative normalized-text proxy",
                "accent": "pink",
            },
            {
                "label": "Incomplete core records",
                "value": summary["incomplete_core"],
                "note": "Missing one or more required core fields",
                "accent": "teal",
            },
            {
                "label": "Unintelligible records",
                "value": summary["garbled"],
                "note": "query_is_garbled = True",
                "accent": "grey",
            },
            {
                "label": "Missing metadata",
                "value": summary["missing_metadata"],
                "note": "Missing country, county, date, or language",
                "accent": "gold",
            },
            {
                "label": "Missing county",
                "value": summary["missing_county"],
                "note": compact_percent(
                    safe_share(summary["missing_county"], summary["unique_rows"])
                )
                + " of filtered queries",
                "accent": "pink",
            },
            {
                "label": "Unclear asset names",
                "value": summary["unclear_asset"],
                "note": "Missing or explicit unclear-name sentinel",
                "accent": "teal",
            },
            {
                "label": "Records requiring review",
                "value": summary["review_required"],
                "note": (
                    f"Domain, {module.label.lower()}-scope, or garbled-text review"
                ),
                "accent": "blue",
            },
        ],
        columns=5,
    )

    review_description = (
        "possible livestock or non-crop records"
        if module.key == "crop"
        else "livestock scope-review records"
    )
    scope_note(
        "<strong>Metric definitions.</strong> Exact duplicates removed are reconstructed "
        "from the approved <code>query_duplicate_count</code> field. Potential near "
        "duplicates are retained queries that collide after case, punctuation, and "
        "whitespace normalization. The source has no definitive non-agricultural flag, "
        f"so the dashboard retains {compact_number(summary['scope_review_records'])} "
        f"{review_description} without reclassifying them."
    )

    left, right = st.columns([0.9, 1.1], gap="large")
    with left:
        duplicate_fig = donut_chart(
            ["Unique approved queries", "Exact duplicates removed"],
            [summary["unique_rows"], summary["duplicate_occurrences"]],
            "Uniqueness of source occurrences",
            "Reconstructed occurrence mix after approved query deduplication",
            colors=[COLORS["teal"], COLORS["gold"]],
        )
        chart(duplicate_fig, f"{module.key}_quality_duplicate_donut")
    with right:
        profile = missing_profile(df)
        missing_chart_data = profile.loc[profile["Missing"] > 0, ["Field", "Missing"]]
        if missing_chart_data.empty:
            empty_state("No missing values are present in the monitored fields.")
        else:
            missing_fig = horizontal_bar(
                missing_chart_data.head(10),
                "Field",
                "Missing",
                "Fields with the most missing values",
                "Counts within the current global filters",
                height=470,
                color=COLORS["gold"],
            )
            chart(missing_fig, f"{module.key}_quality_missing_bar")

    section_title(
        "Completeness by field and year",
        "The heatmap separates 2025 and 2026 so changes in coverage are visible. "
        "Primary taxonomy blanks represent classification coverage, not missing core data.",
    )
    yearly = missingness_by_year(df)
    if yearly.empty:
        empty_state("No yearly completeness profile is available for this selection.")
    else:
        matrix = yearly.pivot(index="Field", columns="Year", values="Missing rate").fillna(0)
        heatmap = matrix_heatmap(
            matrix,
            "Missing-value heatmap",
            "Cell values show the percentage missing within each selected production year",
            percent=True,
            height=560,
        )
        chart(heatmap, f"{module.key}_quality_missing_heatmap")

    section_title(
        "Data completeness matrix",
        "Search or sort the monitored fields to distinguish required data gaps from "
        "classification coverage gaps.",
    )
    profile_table = profile.copy()
    profile_table["Missing"] = profile_table["Missing"].map(compact_number)
    profile_table["Complete"] = profile_table["Complete"].map(compact_number)
    profile_table["Missing rate"] = profile_table["Missing rate"].map(compact_percent)
    profile_table["Completeness"] = profile_table["Completeness"].map(compact_percent)
    table(
        profile_table[
            [
                "Field",
                "Interpretation",
                "Complete",
                "Missing",
                "Completeness",
                "Missing rate",
            ]
        ],
        height=430,
    )

    _quality_observations(summary)

    section_title(
        "Review queue",
        "Use the search field to find a query, value chain, domain, or review reason. "
        "The table is limited to 250 rows for responsive browsing.",
    )
    search = st.text_input(
        "Search review records",
        placeholder="Search query text, value chain, domain, or review reason",
        key=f"{module.key}_quality_review_search",
    ).strip()
    review = df.loc[df["_review_required"]].copy()
    if search:
        searchable = (
            review[
                [
                    "query",
                    "value_chain_label",
                    "domain_label",
                    "domain_review_reason",
                    "scope_review_status",
                ]
            ]
            .astype("string")
            .fillna("")
            .agg(" | ".join, axis=1)
        )
        review = review.loc[searchable.str.contains(search, case=False, regex=False, na=False)]

    if review.empty:
        empty_state("No review records match the current filters and search.")
    else:
        view = review[
            [
                "_row_id",
                "query",
                "value_chain_label",
                "county_label",
                "classification_status",
                "domain_label",
                "domain_review_reason",
                "scope_review_status",
            ]
        ].head(250)
        view = view.rename(
            columns={
                "_row_id": "Record ID",
                "query": "Query",
                "value_chain_label": "Value chain",
                "county_label": "County",
                "classification_status": "Classification status",
                "domain_label": "Primary domain",
                "domain_review_reason": "Domain review reason",
                "scope_review_status": f"{module.label} review status",
            }
        )
        table(view, height=520)
        st.caption(
            f"Showing {compact_number(len(view))} of {compact_number(len(review))} "
            "matching review records."
        )
