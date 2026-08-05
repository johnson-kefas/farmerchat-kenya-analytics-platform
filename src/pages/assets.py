"""Asset Type Analysis dashboard page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.charts import (
    donut_chart,
    horizontal_bar,
    sankey_chart,
    treemap_chart,
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
from src.config import COLORS, ModuleConfig
from src.formatting import compact_number, compact_percent
from src.metrics import (
    cooccurrence_pairs,
    ranked_counts,
    safe_share,
    treemap_top_categories,
)


def render(df: pd.DataFrame, module: ModuleConfig) -> None:
    """Render asset composition, ranking, hierarchy, and co-occurrence."""
    is_livestock = module.key == "livestock"
    page_header(
        "Livestock value chain analysis" if is_livestock else "Asset type analysis",
        (
            "Identify the livestock value chains generating the most questions, "
            "examine mixed-livestock combinations, and make the long tail visible."
            if is_livestock
            else "Identify the crop value chains generating the most questions, "
            "examine intercropping combinations, and make the long tail visible."
        ),
    )
    production_banner()
    if df.empty:
        empty_state("No records match the current global filters.")
        return

    ranking = ranked_counts(df, "value_chain_label", "Value chain")
    asset_mix = ranked_counts(df, "asset_type_label", "Asset type")
    top = ranking.iloc[0]
    mixed_count = int(df["asset_type_label"].eq(module.mixed_asset_label).sum())

    metric_grid(
        [
            {
                "label": f"Filtered {module.label.lower()} queries",
                "value": len(df),
                "note": "Approved production-period rows",
                "accent": "blue",
            },
            {
                "label": "Distinct value chains",
                "value": df["value_chain_label"].nunique(),
                "note": (
                    "Single and approved mixed livestock value chains"
                    if is_livestock
                    else "Single crops and approved intercrops"
                ),
                "accent": "teal",
            },
            {
                "label": "Leading value chain",
                "value": str(top["Value chain"]).title(),
                "note": f"{compact_number(top['Queries'])} queries · "
                f"{compact_percent(top['Share'])}",
                "accent": "gold",
            },
            {
                "label": (
                    "Mixed livestock queries" if is_livestock else "Intercrop queries"
                ),
                "value": mixed_count,
                "note": compact_percent(safe_share(mixed_count, len(df))),
                "accent": "pink",
            },
        ],
        columns=4,
    )

    if is_livestock:
        scope_note(
            "<strong>Taxonomy fidelity.</strong> Livestock categories and value chains "
            "are used exactly as approved in the source. Terms such as dairy are not "
            "inferred from cattle records, and mixed livestock is identified only from "
            "the approved mixed-livestock fields.",
            kind="warning",
        )
    else:
        scope_note(
            "<strong>Source scope.</strong> The approved file is crop-specific. It "
            "contains single-crop and intercrop records, but no livestock, mixed "
            "crop-livestock, or general-agriculture asset categories. Those comparisons "
            "are therefore not estimated in this dashboard.",
            kind="warning",
        )

    left, right = st.columns([0.72, 1.28], gap="large")
    with left:
        mix_fig = donut_chart(
            asset_mix["Asset type"],
            asset_mix["Queries"],
            "Asset-type composition",
            (
                "Single-livestock and mixed-livestock query share"
                if is_livestock
                else "Single-crop and intercrop query share"
            ),
            colors=[COLORS["blue"], COLORS["gold"]],
            height=450,
        )
        chart(mix_fig, f"{module.key}_asset_mix_donut")
    with right:
        top_n = min(20, len(ranking))
        rank_fig = horizontal_bar(
            ranking.head(top_n),
            "Value chain",
            "Queries",
            f"Top {top_n} value chains",
            "Ranked by approved farmer query volume",
            height=600,
        )
        chart(rank_fig, f"{module.key}_asset_value_chain_ranking")

    section_title(
        "Value-chain hierarchy",
        "The treemap retains the leading value chains and groups the remaining long "
        "tail into Other within each asset type.",
    )
    hierarchy = treemap_top_categories(
        df,
        "asset_type_label",
        "value_chain_label",
        top_n=35,
    )
    hierarchy = hierarchy.rename(
        columns={
            "asset_type_label": "Asset type",
            "value_chain_label": "Value chain",
        }
    )
    tree = treemap_chart(
        hierarchy,
        ["Asset type", "Value chain"],
        "Queries",
        "Value-chain composition",
        "Area represents query volume; categories outside the leading 35 are grouped",
        height=620,
    )
    chart(tree, f"{module.key}_asset_treemap")

    section_title(
        "Co-occurring value chains",
        (
            "Links show the most frequent component pairs within approved mixed "
            "livestock questions. Multi-livestock combinations contribute all unordered "
            "component pairs."
            if is_livestock
            else "Links show the most frequent component pairs within approved "
            "intercrop queries. Multi-crop combinations contribute all unordered "
            "component pairs."
        ),
    )
    pairs = cooccurrence_pairs(
        df,
        top_n=20,
        mixed_asset_label=module.mixed_asset_label,
    )
    if pairs.empty:
        empty_state(
            f"No {module.mixed_asset_label.lower()} co-occurrence pairs remain after "
            "the current global filters."
        )
    else:
        sankey = sankey_chart(
            pairs,
            (
                "Leading livestock co-occurrences"
                if is_livestock
                else "Leading intercrop co-occurrences"
            ),
            "Top 20 component pairs by query volume",
            height=660,
        )
        chart(sankey, f"{module.key}_asset_cooccurrence_sankey")

    section_title(
        "Long-tail explorer",
        "Search, sort, and inspect every value chain. Shares use the current filtered "
        "query total as the denominator.",
    )
    long_tail = ranking.copy()
    long_tail["Queries"] = long_tail["Queries"].map(compact_number)
    long_tail["Share"] = long_tail["Share"].map(compact_percent)
    long_tail["Cumulative share"] = long_tail["Cumulative share"].map(compact_percent)
    table(
        long_tail[["Rank", "Value chain", "Queries", "Share", "Cumulative share"]],
        height=520,
    )

    top_10_share = ranking.head(10)["Share"].sum()
    outside_top_20 = max(len(ranking) - 20, 0)
    scope_note(
        f"The top 10 value chains account for <strong>{compact_percent(top_10_share)}</strong> "
        f"of selected queries. <strong>{compact_number(outside_top_20)}</strong> value "
        "chains sit outside the top 20, showing the scale of the long tail."
    )
