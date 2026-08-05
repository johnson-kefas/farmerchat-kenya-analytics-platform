"""Agricultural Domains dashboard page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.charts import donut_chart, horizontal_bar, treemap_chart
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
from src.config import COLORS, UNCLASSIFIED, ModuleConfig
from src.formatting import compact_number, compact_percent
from src.metrics import ranked_counts, safe_share, treemap_top_categories


def render(df: pd.DataFrame, module: ModuleConfig) -> None:
    """Render domain demand, coverage, and hierarchy."""
    page_header(
        "Agricultural domains",
        f"Show the approved {module.label.lower()} taxonomy domains that dominate farmer "
        "knowledge demand and separate classified records from no-match records.",
    )
    production_banner()
    if df.empty:
        empty_state("No records match the current global filters.")
        return

    ranking = ranked_counts(df, "domain_label", "Domain")
    classified = int((~df["domain_label"].eq(UNCLASSIFIED)).sum())
    unclassified = len(df) - classified
    classified_ranking = ranking.loc[~ranking["Domain"].eq(UNCLASSIFIED)]
    top = classified_ranking.iloc[0] if not classified_ranking.empty else None
    least = classified_ranking.iloc[-1] if not classified_ranking.empty else None

    metric_grid(
        [
            {
                "label": "Classified queries",
                "value": classified,
                "note": compact_percent(safe_share(classified, len(df))),
                "accent": "teal",
            },
            {
                "label": "Unclassified queries",
                "value": unclassified,
                "note": "No accepted primary domain",
                "accent": "gold",
            },
            {
                "label": "Most common domain",
                "value": str(top["Domain"]) if top is not None else "N/A",
                "note": (
                    f"{compact_number(top['Queries'])} classified queries"
                    if top is not None
                    else "No classified queries"
                ),
                "accent": "blue",
            },
            {
                "label": "Least common domain",
                "value": str(least["Domain"]) if least is not None else "N/A",
                "note": (
                    f"{compact_number(least['Queries'])} classified queries"
                    if least is not None
                    else "No classified queries"
                ),
                "accent": "pink",
            },
        ],
        columns=4,
    )

    examples = (
        "animal health, feeding, breeding, markets, or finance"
        if module.key == "livestock"
        else "soil, pests, markets, or finance"
    )
    scope_note(
        "<strong>Taxonomy fidelity.</strong> Domain names are used exactly as approved "
        "in <code>primary_domain</code>. The dashboard does not remap them into broader "
        f"labels such as {examples} because doing so would require a separate approved "
        "crosswalk. Detailed themes remain available in the subdomain drill-down."
    )

    left, right = st.columns([1.25, 0.75], gap="large")
    with left:
        domain_fig = horizontal_bar(
            ranking,
            "Domain",
            "Queries",
            "Primary domain demand",
            "All approved domains plus Unclassified",
            height=520,
        )
        chart(domain_fig, f"{module.key}_domain_ranking")
    with right:
        coverage_fig = donut_chart(
            ["Classified", "Unclassified"],
            [classified, unclassified],
            "Primary-domain coverage",
            "Share of selected queries with an accepted primary domain",
            colors=[COLORS["teal"], COLORS["grey"]],
            height=520,
        )
        chart(coverage_fig, f"{module.key}_domain_coverage_donut")

    section_title(
        "Domain and subdomain composition",
        "Area represents query volume. Smaller subdomains outside the leading 40 "
        "domain-subdomain combinations are grouped as Other.",
    )
    hierarchy = treemap_top_categories(
        df,
        "domain_label",
        "subdomain_label",
        top_n=40,
    ).rename(
        columns={
            "domain_label": "Domain",
            "subdomain_label": "Subdomain",
        }
    )
    tree = treemap_chart(
        hierarchy,
        ["Domain", "Subdomain"],
        "Queries",
        "Domain-to-subdomain hierarchy",
        "Approved primary taxonomy; area encodes query volume",
        height=640,
    )
    chart(tree, f"{module.key}_domain_treemap")

    section_title(
        "Domain summary",
        "Search and sort the complete domain ranking for exact lookup.",
    )
    summary_table = ranking.copy()
    summary_table["Queries"] = summary_table["Queries"].map(compact_number)
    summary_table["Share"] = summary_table["Share"].map(compact_percent)
    summary_table["Cumulative share"] = summary_table["Cumulative share"].map(
        compact_percent
    )
    table(
        summary_table[["Rank", "Domain", "Queries", "Share", "Cumulative share"]],
        height=420,
    )

    if len(classified_ranking) >= 3:
        leaders = classified_ranking.head(3)
        labels = ", ".join(
            f"{row['Domain']} ({compact_percent(row['Share'])})"
            for _, row in leaders.iterrows()
        )
        scope_note(
            f"<strong>Dominant concerns.</strong> The three largest approved domains "
            f"within the current filters are {labels}. These are observed query-demand "
            "shares, not estimates of agronomic prevalence."
        )
