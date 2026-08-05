"""Subdomain Analysis dashboard page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.charts import horizontal_bar, sunburst_chart
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
from src.config import UNCLASSIFIED, ModuleConfig
from src.formatting import compact_number, compact_percent
from src.metrics import ranked_counts, safe_share


def _hierarchy_data(df: pd.DataFrame, limit: int = 45) -> pd.DataFrame:
    """Bound the intent hierarchy while retaining exact counts."""
    grouped = (
        df.groupby(
            ["domain_label", "subdomain_label", "intent_label"],
            observed=True,
            dropna=False,
        )
        .size()
        .reset_index(name="Queries")
        .sort_values("Queries", ascending=False)
    )
    return grouped.head(limit).rename(
        columns={
            "domain_label": "Domain",
            "subdomain_label": "Subdomain",
            "intent_label": "Farmer intent",
        }
    )


def render(df: pd.DataFrame, module: ModuleConfig) -> None:
    """Render interactive domain-to-subdomain drill-down."""
    page_header(
        "Subdomain analysis",
        f"Drill from a parent {module.label.lower()} domain into its specific topics and "
        "farmer intents while retaining the approved taxonomy hierarchy.",
    )
    production_banner()
    if df.empty:
        empty_state("No records match the current global filters.")
        return

    domain_counts = df["domain_label"].value_counts()
    domain_options = domain_counts.index.tolist()
    classified_options = [value for value in domain_options if value != UNCLASSIFIED]
    default_domain = classified_options[0] if classified_options else domain_options[0]
    selected_domain = st.selectbox(
        "Drill down by parent domain",
        domain_options,
        index=domain_options.index(default_domain),
        key=f"{module.key}_subdomain_parent_drilldown",
        help="This control operates inside the current global filter selection.",
    )
    domain_df = df.loc[df["domain_label"].eq(selected_domain)].copy()
    if domain_df.empty:
        empty_state("The selected parent domain has no records.")
        return

    subdomain_ranking = ranked_counts(
        domain_df,
        "subdomain_label",
        "Subdomain",
    )
    intent_ranking = ranked_counts(domain_df, "intent_label", "Farmer intent")
    top_subdomain = subdomain_ranking.iloc[0]
    top_intent = intent_ranking.iloc[0]
    classified_subdomain = int(
        (~domain_df["subdomain_label"].eq(UNCLASSIFIED)).sum()
    )

    metric_grid(
        [
            {
                "label": "Selected domain queries",
                "value": len(domain_df),
                "note": selected_domain,
                "accent": "blue",
            },
            {
                "label": "Distinct subdomains",
                "value": int(
                    domain_df.loc[
                        ~domain_df["subdomain_label"].eq(UNCLASSIFIED),
                        "subdomain_label",
                    ].nunique()
                ),
                "note": compact_percent(
                    safe_share(classified_subdomain, len(domain_df))
                )
                + " have a classified subdomain",
                "accent": "teal",
            },
            {
                "label": "Leading subdomain",
                "value": str(top_subdomain["Subdomain"]),
                "note": f"{compact_number(top_subdomain['Queries'])} queries",
                "accent": "gold",
            },
            {
                "label": "Leading farmer intent",
                "value": str(top_intent["Farmer intent"]),
                "note": f"{compact_number(top_intent['Queries'])} queries",
                "accent": "pink",
            },
        ],
        columns=4,
    )

    top_n = min(20, len(subdomain_ranking))
    ranking_fig = horizontal_bar(
        subdomain_ranking.head(top_n),
        "Subdomain",
        "Queries",
        f"Subdomains within {selected_domain}",
        f"Top {top_n} topics ranked by query volume",
        height=max(520, 28 * top_n + 160),
        label_width=34,
    )
    chart(ranking_fig, f"{module.key}_subdomain_ranking")

    section_title(
        "Interactive taxonomy hierarchy",
        "Click a sunburst segment to focus on a domain, subdomain, or farmer intent. "
        "The chart is limited to the 45 largest intent paths for legibility.",
    )
    hierarchy = _hierarchy_data(domain_df)
    if hierarchy.empty:
        empty_state("No taxonomy hierarchy is available for this selection.")
    else:
        sunburst = sunburst_chart(
            hierarchy,
            ["Domain", "Subdomain", "Farmer intent"],
            "Queries",
            "Domain → subdomain → farmer intent",
            f"Leading approved intent paths within {selected_domain}",
            height=700,
        )
        chart(sunburst, f"{module.key}_subdomain_sunburst")

    section_title(
        "Subdomain and intent explorer",
        "Use the tabs to switch between complete subdomain rankings and the leading "
        "farmer intents for the selected parent domain.",
    )
    tab_subdomains, tab_intents = st.tabs(["Subdomains", "Farmer intents"])
    with tab_subdomains:
        view = subdomain_ranking.copy()
        view["Queries"] = view["Queries"].map(compact_number)
        view["Share"] = view["Share"].map(compact_percent)
        view["Cumulative share"] = view["Cumulative share"].map(compact_percent)
        table(
            view[["Rank", "Subdomain", "Queries", "Share", "Cumulative share"]],
            height=480,
        )
    with tab_intents:
        view = intent_ranking.copy()
        view["Queries"] = view["Queries"].map(compact_number)
        view["Share"] = view["Share"].map(compact_percent)
        view["Cumulative share"] = view["Cumulative share"].map(compact_percent)
        table(
            view[["Rank", "Farmer intent", "Queries", "Share", "Cumulative share"]],
            height=480,
        )

    scope_note(
        "The drill-down uses the selected primary domain, primary subdomain, and "
        "primary farmer intent. Secondary intent fields are intentionally excluded so "
        "query rows are not counted more than once in the main hierarchy."
    )
