"""Kenya county boundary loading, matching, and interactive map construction."""

from __future__ import annotations

import json
import logging
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.charts import FONT_STACK, apply_chart_style
from src.config import COLORS, PROJECT_ROOT
from src.formatting import compact_number, compact_percent


LOGGER = logging.getLogger(__name__)

COUNTY_BOUNDARY_PATH = PROJECT_ROOT / "assets" / "geo" / "kenya_counties.geojson"
NATIONAL_BOUNDARY_PATH = (
    PROJECT_ROOT / "assets" / "geo" / "kenya_national_boundary.geojson"
)

# The boundary source uses two shortened/unhyphenated labels. Display aliases keep
# map tooltips aligned with the approved FarmerChat labels.
BOUNDARY_DISPLAY_NAMES = {
    "Taita Taveta": "Taita-Taveta",
    "Tharaka": "Tharaka-Nithi",
}

# Compact and alternative spellings found in Kenyan data systems. Punctuation,
# accents, case, whitespace, and a trailing "County" are handled generically.
COUNTY_ALIASES = {
    "elgeyomarakwet": "elgeyo marakwet",
    "homabay": "homa bay",
    "taitataveta": "taita taveta",
    "tanariver": "tana river",
    "tharakanithi": "tharaka nithi",
    "transnzoia": "trans nzoia",
    "uasingishu": "uasin gishu",
    "westpokot": "west pokot",
}

COUNTY_VOLUME_SCALE = [
    [0.00, "#D7ECE8"],
    [0.25, "#A9D2CC"],
    [0.50, "#73B1AA"],
    [0.75, "#3B8983"],
    [1.00, "#145B56"],
]

ZERO_COUNTY_COLOR = "#F2F4F7"
COUNTY_BORDER_COLOR = "#475467"
NATIONAL_BORDER_COLOR = COLORS["ink"]
KENYA_CENTER = {"lon": 37.91, "lat": 0.17}
KENYA_INITIAL_ZOOM = 4.95


def normalise_county_name(value: object) -> str:
    """Return a stable county matching key without changing display labels."""
    if value is None or value is pd.NA:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii").casefold().strip()
    text = text.replace("&", " and ")
    text = re.sub(r"['’`]", "", text)
    text = re.sub(r"\bcounty\s+of\b", " ", text)
    text = re.sub(r"\b(county|city)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    key = re.sub(r"\s+", " ", text).strip()
    return COUNTY_ALIASES.get(key.replace(" ", ""), key)


def _read_geojson(path: str, modified_time_ns: int) -> dict[str, Any]:
    """Read a local GeoJSON file with cache invalidation."""
    del modified_time_ns
    with Path(path).open("r", encoding="utf-8") as source:
        payload = json.load(source)
    if payload.get("type") != "FeatureCollection":
        raise ValueError(f"Boundary file is not a GeoJSON FeatureCollection: {path}")
    return payload


@st.cache_data(show_spinner=False)
def _load_county_geojson(path: str, modified_time_ns: int) -> dict[str, Any]:
    """Load and validate the 47 individual county geometries."""
    payload = _read_geojson(path, modified_time_ns)
    features = payload.get("features", [])
    if len(features) != 47:
        raise ValueError(
            "The Kenya county boundary file must contain exactly 47 county features."
        )

    names: list[str] = []
    for feature in features:
        geometry_type = (feature.get("geometry") or {}).get("type")
        if geometry_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError(
                "Every Kenya county feature must use Polygon or MultiPolygon geometry."
            )
        properties = feature.setdefault("properties", {})
        boundary_name = str(
            properties.get("shapeName")
            or properties.get("county")
            or properties.get("NAME_1")
            or ""
        ).strip()
        display_name = BOUNDARY_DISPLAY_NAMES.get(boundary_name, boundary_name)
        if not display_name:
            raise ValueError("A Kenya county boundary feature has no county name.")
        properties["dashboard_county"] = display_name
        properties["dashboard_county_key"] = normalise_county_name(display_name)
        names.append(display_name)

    if len(set(names)) != 47:
        raise ValueError("Kenya county boundary names must be unique.")
    return payload


@st.cache_data(show_spinner=False)
def _load_national_geojson(path: str, modified_time_ns: int) -> dict[str, Any]:
    """Load the separate Kenya national outline geometry."""
    payload = _read_geojson(path, modified_time_ns)
    features = payload.get("features", [])
    if len(features) != 1:
        raise ValueError("The Kenya national boundary file must contain one feature.")
    geometry_type = (features[0].get("geometry") or {}).get("type")
    if geometry_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("The Kenya national boundary must be Polygon or MultiPolygon.")
    return payload


def load_kenya_boundaries() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return cached county polygons and the separate national outline."""
    for path in (COUNTY_BOUNDARY_PATH, NATIONAL_BOUNDARY_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Required Kenya boundary file not found: {path}")
    counties = _load_county_geojson(
        str(COUNTY_BOUNDARY_PATH), COUNTY_BOUNDARY_PATH.stat().st_mtime_ns
    )
    national = _load_national_geojson(
        str(NATIONAL_BOUNDARY_PATH), NATIONAL_BOUNDARY_PATH.stat().st_mtime_ns
    )
    return counties, national


def prepare_county_map_data(
    county_ranking: pd.DataFrame,
    county_geojson: dict[str, Any],
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    """Join filtered query counts to all 47 counties and retain explicit zeroes."""
    required = {"County", "Queries"}
    missing = sorted(required.difference(county_ranking.columns))
    if missing:
        raise ValueError(f"County ranking is missing fields: {', '.join(missing)}")

    boundary_rows: list[dict[str, str]] = []
    for feature in county_geojson.get("features", []):
        properties = feature.get("properties", {})
        county = str(properties.get("dashboard_county", "")).strip()
        key = str(properties.get("dashboard_county_key", "")).strip()
        if county and key:
            boundary_rows.append({"County": county, "county_key": key})
    boundaries = pd.DataFrame(boundary_rows)
    if len(boundaries) != 47:
        raise ValueError("The county map join requires exactly 47 named boundaries.")
    if boundaries["county_key"].duplicated().any():
        raise ValueError("County names are ambiguous after normalisation.")

    source = county_ranking.loc[:, ["County", "Queries"]].copy()
    source["County"] = source["County"].astype("string").str.strip()
    source["Queries"] = (
        pd.to_numeric(source["Queries"], errors="coerce").fillna(0).clip(lower=0)
    )
    source["county_key"] = source["County"].map(normalise_county_name)
    source = source.loc[source["county_key"].ne("")].copy()

    boundary_keys = set(boundaries["county_key"])
    unmatched = tuple(
        sorted(
            source.loc[~source["county_key"].isin(boundary_keys), "County"]
            .dropna()
            .astype(str)
            .unique()
        )
    )
    if unmatched:
        LOGGER.warning(
            "County map could not match %d dataset label(s): %s",
            len(unmatched),
            ", ".join(unmatched),
        )

    matched_source = source.loc[source["county_key"].isin(boundary_keys)]
    aggregated = (
        matched_source.groupby("county_key", as_index=False, observed=True)["Queries"]
        .sum()
        .sort_values(["Queries", "county_key"], ascending=[False, True])
        .reset_index(drop=True)
    )
    total_queries = float(aggregated["Queries"].sum()) if not aggregated.empty else 0.0
    aggregated["Share"] = (
        aggregated["Queries"] / total_queries if total_queries else 0.0
    )
    aggregated["Rank"] = pd.RangeIndex(start=1, stop=len(aggregated) + 1)

    mapped = boundaries.merge(aggregated, on="county_key", how="left")
    mapped["Queries"] = mapped["Queries"].fillna(0).round().astype("int64")
    mapped["Share"] = mapped["Share"].fillna(0.0).astype(float)
    mapped["Rank"] = mapped["Rank"].astype("Int64")
    mapped["Has data"] = mapped["Queries"].gt(0)
    mapped["Colour value"] = np.log1p(mapped["Queries"].astype(float))
    return mapped.sort_values("County").reset_index(drop=True), unmatched


def _county_hover_data(data: pd.DataFrame) -> np.ndarray:
    """Return exact, presentation-ready county tooltip fields."""
    ranks = data["Rank"].map(
        lambda value: "N/A" if pd.isna(value) else f"#{int(value)}"
    )
    return np.stack(
        [
            data["County"].astype(str),
            data["Queries"].map(lambda value: f"{int(value):,}"),
            data["Share"].map(compact_percent),
            ranks,
        ],
        axis=-1,
    )


def _volume_tick_spec(maximum: int) -> tuple[list[float], list[str]]:
    """Return log positions labelled with the underlying query counts."""
    if maximum <= 1:
        actual = np.array([1], dtype=int)
    else:
        actual = np.unique(np.rint(np.geomspace(1, maximum, 6)).astype(int))
        actual = np.unique(np.append(actual, maximum))
    return np.log1p(actual).tolist(), [compact_number(value) for value in actual]


def _outline_coordinates(
    geojson: dict[str, Any],
) -> tuple[list[float | None], list[float | None]]:
    """Flatten outer Polygon and MultiPolygon rings for the national outline."""
    longitudes: list[float | None] = []
    latitudes: list[float | None] = []
    for feature in geojson.get("features", []):
        geometry = feature.get("geometry") or {}
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates") or []
        polygons = [coordinates] if geometry_type == "Polygon" else coordinates
        if geometry_type not in {"Polygon", "MultiPolygon"}:
            continue
        for polygon in polygons:
            if not polygon:
                continue
            for longitude, latitude, *_ in polygon[0]:
                longitudes.append(float(longitude))
                latitudes.append(float(latitude))
            longitudes.append(None)
            latitudes.append(None)
    return longitudes, latitudes


def county_choropleth(
    data: pd.DataFrame,
    county_geojson: dict[str, Any],
    national_geojson: dict[str, Any],
    title: str,
    subtitle: str,
    *,
    height: int = 600,
) -> go.Figure:
    """Build a 47-county MapLibre choropleth with a neutral zero state."""
    if len(data) != 47:
        raise ValueError("The county choropleth requires exactly 47 county rows.")

    zero_counties = data.loc[~data["Has data"]].copy()
    represented = data.loc[data["Has data"]].copy()
    fig = go.Figure()

    if not zero_counties.empty:
        fig.add_trace(
            go.Choroplethmap(
                geojson=county_geojson,
                featureidkey="properties.dashboard_county",
                locations=zero_counties["County"],
                z=np.zeros(len(zero_counties)),
                zmin=0,
                zmax=1,
                colorscale=[[0, ZERO_COUNTY_COLOR], [1, ZERO_COUNTY_COLOR]],
                showscale=False,
                marker={
                    "line": {"color": COUNTY_BORDER_COLOR, "width": 1.15}
                },
                customdata=_county_hover_data(zero_counties),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>Queries: 0"
                    "<br>No geotagged queries<extra></extra>"
                ),
                name="No queries",
                showlegend=False,
            )
        )

    if not represented.empty:
        maximum = int(represented["Queries"].max())
        tick_values, tick_labels = _volume_tick_spec(maximum)
        fig.add_trace(
            go.Choroplethmap(
                geojson=county_geojson,
                featureidkey="properties.dashboard_county",
                locations=represented["County"],
                z=represented["Colour value"],
                zmin=0,
                zmax=math.log1p(maximum),
                colorscale=COUNTY_VOLUME_SCALE,
                showscale=True,
                marker={
                    "line": {"color": COUNTY_BORDER_COLOR, "width": 1.15}
                },
                colorbar={
                    "title": {"text": "Queries<br>(log scale)", "side": "top"},
                    "tickmode": "array",
                    "tickvals": tick_values,
                    "ticktext": tick_labels,
                    "len": 0.68,
                    "thickness": 14,
                    "x": 1.01,
                    "y": 0.50,
                    "outlinewidth": 0,
                    "tickfont": {"size": 10, "color": COLORS["muted"]},
                },
                customdata=_county_hover_data(represented),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>Queries: %{customdata[1]}"
                    "<br>Share: %{customdata[2]}<br>Rank: %{customdata[3]}"
                    "<extra></extra>"
                ),
                name="Query volume",
                showlegend=False,
            )
        )

    outline_lon, outline_lat = _outline_coordinates(national_geojson)
    fig.add_trace(
        go.Scattermap(
            lon=outline_lon,
            lat=outline_lat,
            mode="lines",
            line={"color": NATIONAL_BORDER_COLOR, "width": 2.2},
            hoverinfo="skip",
            showlegend=False,
            name="Kenya national boundary",
        )
    )

    apply_chart_style(fig, title, subtitle, height=height)
    fig.update_layout(
        margin={"l": 6, "r": 92, "b": 58},
        map={
            "style": "white-bg",
            "center": KENYA_CENTER,
            "zoom": KENYA_INITIAL_ZOOM,
            "bearing": 0,
            "pitch": 0,
            "uirevision": "kenya-county-map-v4.2.0",
        },
    )
    fig.add_annotation(
        x=0,
        y=-0.045,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="bottom",
        text=(
            f"<span style='color:{ZERO_COUNTY_COLOR}'>■</span> "
            f"<span style='color:{COLORS['muted']}'>Neutral = no geotagged queries; "
            "colour scale shows actual counts on a logarithmic range</span>"
        ),
        showarrow=False,
        font={"family": FONT_STACK, "size": 10},
    )
    return fig
