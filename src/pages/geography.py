"""Geographic Analysis dashboard page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.charts import donut_chart, matrix_heatmap
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
from src.config import COLORS, MISSING_COUNTY, UNCLASSIFIED, ModuleConfig
from src.formatting import compact_number, compact_percent
from src.geography_map import (
    county_choropleth,
    load_kenya_boundaries,
    prepare_county_map_data,
)
from src.metrics import ranked_counts, safe_share


def _county_summary(geo_df: pd.DataFrame) -> pd.DataFrame:
    """Build a decision-useful county lookup table."""
    rows: list[dict[str, object]] = []
    total = len(geo_df)
    for county, group in geo_df.groupby("county_label", observed=True):
        top_chain = group["value_chain_label"].value_counts().index[0]
        domain_counts = group.loc[
            ~group["domain_label"].eq(UNCLASSIFIED), "domain_label"
        ].value_counts()
        top_domain = domain_counts.index[0] if not domain_counts.empty else UNCLASSIFIED
        classified = int((~group["domain_label"].eq(UNCLASSIFIED)).sum())
        rows.append(
            {
                "County": county,
                "Queries": len(group),
                "Share of geotagged": safe_share(len(group), total),
                "Leading value chain": top_chain,
                "Leading domain": top_domain,
                "Domain coverage": safe_share(classified, len(group)),
            }
        )
    return pd.DataFrame(rows).sort_values("Queries", ascending=False)


def render(df: pd.DataFrame, module: ModuleConfig) -> None:
    """Render county coverage, ranking, domain mix, and lookup."""
    page_header(
        "Geographic analysis",
        f"Compare {module.label.lower()} information needs across counties while keeping "
        "missing location metadata visible as a major analytical limitation.",
    )
    production_banner()
    if df.empty:
        empty_state("No records match the current global filters.")
        return

    missing_county = int(df["county_label"].eq(MISSING_COUNTY).sum())
    geo_df = df.loc[~df["county_label"].eq(MISSING_COUNTY)].copy()
    coverage = safe_share(len(geo_df), len(df))
    county_ranking = (
        ranked_counts(geo_df, "county_label", "County")
        if not geo_df.empty
        else pd.DataFrame()
    )
    top_county = county_ranking.iloc[0] if not county_ranking.empty else None

    metric_grid(
        [
            {
                "label": "Geotagged queries",
                "value": len(geo_df),
                "note": compact_percent(coverage) + " county coverage",
                "accent": "teal",
            },
            {
                "label": "Missing county",
                "value": missing_county,
                "note": compact_percent(safe_share(missing_county, len(df))),
                "accent": "gold",
            },
            {
                "label": "Counties represented",
                "value": geo_df["county_label"].nunique(),
                "note": "Within the current global filters",
                "accent": "blue",
            },
            {
                "label": "Most represented county",
                "value": str(top_county["County"]) if top_county is not None else "N/A",
                "note": (
                    f"{compact_number(top_county['Queries'])} geotagged queries"
                    if top_county is not None
                    else "No county-labelled records"
                ),
                "accent": "pink",
            },
        ],
        columns=4,
    )

    scope_note(
        f"<strong>Geographic limitation.</strong> County is missing for "
        f"{compact_percent(safe_share(missing_county, len(df)))} of the selected queries. "
        "The county map and heatmap use geotagged records only; missing records remain "
        "visible in the coverage KPI and donut. All 47 counties remain on the map, and "
        "neutral counties have no geotagged queries in the current selection.",
        kind="warning",
    )

    left, right = st.columns([0.72, 1.28], gap="large")
    with left:
        coverage_fig = donut_chart(
            ["County available", "County missing"],
            [len(geo_df), missing_county],
            "County metadata coverage",
            "Missing locations are retained as a visible data-quality category",
            colors=[COLORS["teal"], COLORS["gold"]],
            height=480,
        )
        chart(coverage_fig, f"{module.key}_geo_coverage_donut")
    with right:
        try:
            county_geojson, national_geojson = load_kenya_boundaries()
            ranking_for_map = (
                county_ranking
                if not county_ranking.empty
                else pd.DataFrame(columns=["County", "Queries"])
            )
            county_map_data, _ = prepare_county_map_data(
                ranking_for_map, county_geojson
            )
            county_fig = county_choropleth(
                county_map_data,
                county_geojson,
                national_geojson,
                "County representation",
                "Geotagged query volume by county; darker counties indicate higher "
                "volume",
                height=600,
            )
            chart(
                county_fig,
                f"{module.key}_geo_county_map",
                config={"scrollZoom": True},
            )
            st.caption(
                "Boundaries: [geoBoundaries gbOpen]"
                "(https://www.geoboundaries.org/) (2020, Public Domain)."
            )
        except (FileNotFoundError, ValueError, OSError) as exc:
            st.warning(
                "The Kenya county map could not be rendered. The remaining "
                "geographic analysis is still available.",
                icon="⚠️",
            )
            st.caption(str(exc))

    section_title(
        "County × domain heatmap",
        "Switch between raw volume and within-county composition. The latter is more "
        "appropriate for comparing knowledge-demand mix across differently sized counties.",
    )
    if geo_df.empty:
        empty_state("The county-domain matrix requires at least one geotagged record.")
    else:
        display_mode = st.radio(
            "Heatmap measure",
            ["Within-county share", "Query count"],
            horizontal=True,
            key=f"{module.key}_geo_heatmap_measure",
        )
        top_counties = geo_df["county_label"].value_counts().head(15).index
        heat_df = geo_df.loc[geo_df["county_label"].isin(top_counties)].copy()
        matrix = pd.crosstab(
            heat_df["county_label"],
            heat_df["domain_label"],
        )
        matrix = matrix.loc[
            heat_df["county_label"].value_counts().loc[matrix.index].sort_values().index
        ]
        if display_mode == "Within-county share":
            matrix = matrix.div(matrix.sum(axis=1), axis=0).fillna(0)
            percent = True
            subtitle = "Rows sum to 100%; top 15 counties by geotagged volume"
        else:
            percent = False
            subtitle = "Raw query counts; top 15 counties by geotagged volume"
        heatmap = matrix_heatmap(
            matrix,
            "County and primary-domain mix",
            subtitle,
            percent=percent,
            height=max(600, 30 * len(matrix) + 260),
        )
        chart(heatmap, f"{module.key}_geo_domain_heatmap")

    section_title(
        "County summary table",
        "Search and sort counties by query volume, leading value chain, leading domain, "
        "or classification coverage.",
    )
    if geo_df.empty:
        empty_state("No county summary is available for this selection.")
    else:
        summary = _county_summary(geo_df)
        summary["Queries"] = summary["Queries"].map(compact_number)
        summary["Share of geotagged"] = summary["Share of geotagged"].map(compact_percent)
        summary["Domain coverage"] = summary["Domain coverage"].map(compact_percent)
        table(summary, height=500)
        most = county_ranking.iloc[0]
        least = county_ranking.iloc[-1]
        scope_note(
            f"<strong>Representation range.</strong> {most['County']} has the largest "
            f"share of geotagged queries at {compact_percent(most['Share'])}, while "
            f"{least['County']} has the smallest at {compact_percent(least['Share'])}. "
            "These labels describe representation in this dataset only. County "
            "population or FarmerChat user denominators would be required to determine "
            "true overrepresentation or underrepresentation."
        )
