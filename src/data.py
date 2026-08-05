"""Dataset loading, preparation, filtering, and export."""

from __future__ import annotations

import gzip
import io
import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.config import (
    CONFIDENCE_LABELS,
    CORE_REQUIRED_FIELDS,
    CROP_MODULE,
    METADATA_FIELDS,
    MISSING_COUNTY,
    MODULES,
    ModuleConfig,
    PRODUCTION_YEARS,
    SEASON_PHASES,
    UNCLASSIFIED,
)


def resolve_data_path(module: ModuleConfig = CROP_MODULE) -> Path:
    """Resolve a module-specific environment override before the packaged path."""
    override = os.getenv(module.data_env_var, "").strip()
    if module.key == CROP_MODULE.key and not override:
        override = os.getenv("FARMERCHAT_DATA_PATH", "").strip()
    return Path(override).expanduser() if override else module.default_data_path


def _blank_or_missing(series: pd.Series) -> pd.Series:
    """Identify null, empty, and common missing-value sentinels."""
    text = series.astype("string").str.strip().str.casefold()
    return series.isna() | text.isin({"", "na", "n/a", "none", "null"})


def prepare_dataframe(
    df: pd.DataFrame,
    module: ModuleConfig = CROP_MODULE,
) -> pd.DataFrame:
    """Add shared dashboard fields without altering approved source columns."""
    missing = sorted(set(module.source_columns).difference(df.columns))
    if missing:
        raise ValueError(
            f"Required {module.label.lower()} columns are missing: {', '.join(missing)}"
        )

    prepared = df.copy()
    prepared["_row_id"] = pd.RangeIndex(start=1, stop=len(prepared) + 1)
    prepared["_module_key"] = module.key
    prepared["month_period"] = pd.to_datetime(
        prepared["query_year_month"].astype("string") + "-01",
        errors="coerce",
    )
    prepared["year"] = prepared["month_period"].dt.year.astype("Int64")
    prepared["month_number"] = prepared["month_period"].dt.month.astype("Int64")
    prepared["month_label"] = prepared["month_period"].dt.strftime("%b")
    prepared["season_phase"] = prepared["month_number"].map(SEASON_PHASES)

    prepared["county_label"] = (
        prepared["user_geo_level2"].astype("string").str.strip().fillna(MISSING_COUNTY)
    )
    prepared.loc[prepared["county_label"].eq(""), "county_label"] = MISSING_COUNTY
    prepared["asset_type_label"] = (
        prepared["asset_type"]
        .astype("string")
        .str.strip()
        .str.casefold()
        .map(module.asset_type_map)
        .fillna("Unclear asset type")
    )
    prepared["value_chain_label"] = (
        prepared["value_chain"].astype("string").str.strip().fillna("Unclear value chain")
    )
    prepared.loc[prepared["value_chain_label"].eq(""), "value_chain_label"] = (
        "Unclear value chain"
    )
    prepared["domain_label"] = (
        prepared["primary_domain"].astype("string").str.strip().fillna(UNCLASSIFIED)
    )
    prepared.loc[prepared["domain_label"].eq(""), "domain_label"] = UNCLASSIFIED
    prepared["subdomain_label"] = (
        prepared["primary_subdomain"].astype("string").str.strip().fillna(UNCLASSIFIED)
    )
    prepared.loc[prepared["subdomain_label"].eq(""), "subdomain_label"] = UNCLASSIFIED
    prepared["intent_label"] = (
        prepared["primary_farmer_intent"]
        .astype("string")
        .str.strip()
        .fillna(UNCLASSIFIED)
    )
    prepared.loc[prepared["intent_label"].eq(""), "intent_label"] = UNCLASSIFIED
    prepared["confidence_label"] = (
        prepared["domain_confidence"]
        .astype("string")
        .str.strip()
        .str.casefold()
        .map(CONFIDENCE_LABELS)
        .fillna(UNCLASSIFIED)
    )

    required_missing = pd.DataFrame(
        {field: _blank_or_missing(prepared[field]) for field in CORE_REQUIRED_FIELDS}
    )
    metadata_missing = pd.DataFrame(
        {field: _blank_or_missing(prepared[field]) for field in METADATA_FIELDS}
    )
    prepared["_incomplete_core"] = required_missing.any(axis=1)
    prepared["_missing_metadata"] = metadata_missing.any(axis=1)
    prepared["_missing_county"] = prepared["county_label"].eq(MISSING_COUNTY)

    asset_text = prepared["asset_name"].astype("string").str.strip().str.casefold()
    prepared["_unclear_asset"] = prepared["asset_name"].isna() | asset_text.isin(
        {
            "",
            "unknown",
            "unclear",
            "unspecified",
            "unidentified",
            "not applicable",
            "n/a",
            "none",
        }
    )

    normalized_query = (
        prepared["query"]
        .astype("string")
        .str.normalize("NFKC")
        .str.casefold()
        .str.replace(r"[^\w\s]", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    prepared["_query_norm_hash"] = pd.util.hash_pandas_object(
        normalized_query, index=False
    ).astype("uint64")

    prepared["cooccurrence_components"] = prepared[module.component_column]
    prepared["scope_review_flag"] = (
        prepared[module.review_flag_column].fillna(False).astype(bool)
    )
    prepared["scope_review_status"] = prepared[module.review_status_column]
    prepared["_review_required"] = (
        prepared["domain_review_flag"].fillna(False).astype(bool)
        | prepared["scope_review_flag"]
        | prepared["query_is_garbled"].fillna(False).astype(bool)
    )

    return prepared


@st.cache_data(show_spinner="Loading the approved FarmerChat dataset...")
def load_dataset(path: str, modified_time_ns: int, module_key: str) -> pd.DataFrame:
    """Load and prepare one authoritative CSV with cache invalidation."""
    del modified_time_ns
    module = MODULES[module_key]
    frame = pd.read_csv(path, low_memory=False)
    return prepare_dataframe(frame, module)


def load_approved_dataset(
    path: Path,
    module: ModuleConfig = CROP_MODULE,
) -> pd.DataFrame:
    """Validate a module source path and load its prepared dataframe."""
    if not path.exists():
        raise FileNotFoundError(
            f"Approved {module.label.lower()} dataset not found at {path}. "
            f"Set {module.data_env_var} to the CSV location."
        )
    return load_dataset(
        str(path.resolve()),
        path.stat().st_mtime_ns,
        module.key,
    )


def production_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the non-negotiable 2025-2026 production-period rule."""
    return df.loc[df["year"].isin(PRODUCTION_YEARS)].copy()


def apply_filters(df: pd.DataFrame, filters: dict[str, list[Any]]) -> pd.DataFrame:
    """Apply all global filters consistently."""
    mask = pd.Series(True, index=df.index)
    mapping = {
        "years": "year",
        "counties": "county_label",
        "asset_types": "asset_type_label",
        "value_chains": "value_chain_label",
        "domains": "domain_label",
        "subdomains": "subdomain_label",
        "intents": "intent_label",
        "confidence_levels": "confidence_label",
    }
    for key, column in mapping.items():
        selected = filters.get(key, [])
        if selected:
            mask &= df[column].isin(selected)
    return df.loc[mask].copy()


def export_filtered_data(
    df: pd.DataFrame,
    module: ModuleConfig = CROP_MODULE,
    compressed: bool = True,
) -> bytes:
    """Serialize filtered approved columns, excluding dashboard-only fields."""
    available = [column for column in module.source_columns if column in df.columns]
    if not compressed:
        return df.loc[:, available].to_csv(index=False).encode("utf-8")

    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=6) as gzip_file:
        with io.TextIOWrapper(gzip_file, encoding="utf-8", newline="") as text_file:
            df.loc[:, available].to_csv(text_file, index=False)
    return buffer.getvalue()
