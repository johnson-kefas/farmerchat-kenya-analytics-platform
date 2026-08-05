"""Reusable dashboard calculations."""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from src.config import FIELD_INTERPRETATIONS, QUALITY_FIELDS, UNCLASSIFIED


def safe_share(numerator: float | int, denominator: float | int) -> float:
    """Return a proportion without raising on empty filters."""
    return float(numerator) / float(denominator) if denominator else 0.0


def quality_summary(df: pd.DataFrame) -> dict[str, float | int]:
    """Calculate traceable quality metrics for the filtered query rows."""
    unique_rows = int(len(df))
    original_occurrences = int(df["query_duplicate_count"].fillna(1).clip(lower=1).sum())
    duplicate_occurrences = max(original_occurrences - unique_rows, 0)
    near_duplicate_rows = int(df["_query_norm_hash"].duplicated(keep=False).sum())
    scope_review_records = int(df["scope_review_flag"].fillna(False).sum())
    return {
        "unique_rows": unique_rows,
        "original_occurrences": original_occurrences,
        "duplicate_occurrences": duplicate_occurrences,
        "duplicate_share": safe_share(duplicate_occurrences, original_occurrences),
        "near_duplicate_rows": near_duplicate_rows,
        "incomplete_core": int(df["_incomplete_core"].sum()),
        "garbled": int(df["query_is_garbled"].fillna(False).sum()),
        "missing_metadata": int(df["_missing_metadata"].sum()),
        "missing_county": int(df["_missing_county"].sum()),
        "unclear_asset": int(df["_unclear_asset"].sum()),
        "scope_review_records": scope_review_records,
        "possible_out_of_scope": scope_review_records,
        "review_required": int(df["_review_required"].sum()),
        "unclassified_domain": int(df["domain_label"].eq(UNCLASSIFIED).sum()),
    }


def missing_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Profile missingness for fields used by dashboard interpretation."""
    rows: list[dict[str, object]] = []
    total = len(df)
    for field, label in QUALITY_FIELDS.items():
        series = df[field]
        text = series.astype("string").str.strip().str.casefold()
        missing = int((series.isna() | text.isin({"", "na", "n/a", "none", "null"})).sum())
        rows.append(
            {
                "Field": label,
                "Missing": missing,
                "Missing rate": safe_share(missing, total),
                "Complete": total - missing,
                "Completeness": safe_share(total - missing, total),
                "Interpretation": FIELD_INTERPRETATIONS[label],
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["Missing rate", "Field"], ascending=[False, True]
    )


def missingness_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """Return a tidy field-by-year missingness matrix."""
    records: list[dict[str, object]] = []
    for year, group in df.groupby("year", observed=True):
        profile = missing_profile(group)
        for _, row in profile.iterrows():
            records.append(
                {
                    "Year": int(year),
                    "Field": row["Field"],
                    "Missing rate": row["Missing rate"],
                }
            )
    return pd.DataFrame(records)


def ranked_counts(
    df: pd.DataFrame,
    column: str,
    label_name: str,
    top_n: int | None = None,
) -> pd.DataFrame:
    """Return sorted counts, shares, rank, and cumulative share."""
    counts = (
        df[column]
        .value_counts(dropna=False)
        .rename_axis(label_name)
        .reset_index(name="Queries")
    )
    counts["Share"] = counts["Queries"] / counts["Queries"].sum() if len(df) else 0.0
    counts["Rank"] = np.arange(1, len(counts) + 1)
    counts["Cumulative share"] = counts["Share"].cumsum()
    return counts.head(top_n) if top_n else counts


def cooccurrence_pairs(
    df: pd.DataFrame,
    top_n: int = 20,
    mixed_asset_label: str = "Intercrop",
) -> pd.DataFrame:
    """Count unordered component pairs in approved mixed-asset records."""
    values = df.loc[
        df["asset_type_label"].eq(mixed_asset_label), "cooccurrence_components"
    ].dropna()
    pair_counts: dict[tuple[str, str], int] = {}
    for value in values.astype(str):
        components = sorted(
            {
                component.strip()
                for component in value.split("+")
                if component.strip()
            }
        )
        for left, right in combinations(components, 2):
            pair_counts[(left, right)] = pair_counts.get((left, right), 0) + 1

    if not pair_counts:
        return pd.DataFrame(columns=["Source", "Target", "Queries"])
    result = pd.DataFrame(
        [
            {"Source": left, "Target": right, "Queries": count}
            for (left, right), count in pair_counts.items()
        ]
    )
    return result.sort_values(
        ["Queries", "Source", "Target"], ascending=[False, True, True]
    ).head(top_n)


def treemap_top_categories(
    df: pd.DataFrame,
    parent_col: str,
    child_col: str,
    top_n: int = 30,
) -> pd.DataFrame:
    """Aggregate a hierarchy and group small children into Other."""
    grouped = (
        df.groupby([parent_col, child_col], dropna=False, observed=True)
        .size()
        .reset_index(name="Queries")
        .sort_values("Queries", ascending=False)
    )
    if len(grouped) <= top_n:
        return grouped
    top = grouped.head(top_n).copy()
    other = grouped.iloc[top_n:].groupby(parent_col, observed=True)["Queries"].sum()
    other_rows = pd.DataFrame(
        {
            parent_col: other.index,
            child_col: "Other",
            "Queries": other.values,
        }
    )
    return pd.concat([top, other_rows], ignore_index=True)


def monthly_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Return a complete monthly series within the selected period."""
    if df.empty:
        return pd.DataFrame(columns=["Month", "Queries"])
    monthly = (
        df.groupby("month_period", observed=True)
        .size()
        .rename("Queries")
        .sort_index()
    )
    full_index = pd.date_range(
        monthly.index.min(), monthly.index.max(), freq="MS"
    )
    return (
        monthly.reindex(full_index, fill_value=0)
        .rename_axis("Month")
        .reset_index()
    )


def monthly_domain_mix(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Return monthly query counts for the leading domains plus Other."""
    if df.empty:
        return pd.DataFrame(columns=["Month", "Domain", "Queries"])
    top_domains = (
        df.loc[~df["domain_label"].eq(UNCLASSIFIED), "domain_label"]
        .value_counts()
        .head(top_n)
        .index
    )
    working = df.loc[:, ["month_period", "domain_label"]].copy()
    working["Domain"] = working["domain_label"].where(
        working["domain_label"].isin(top_domains), "Other / unclassified"
    )
    return (
        working.groupby(["month_period", "Domain"], observed=True)
        .size()
        .rename("Queries")
        .reset_index()
        .rename(columns={"month_period": "Month"})
    )


def monthly_signal_share(
    df: pd.DataFrame,
    signals: tuple[tuple[str, str], ...],
) -> pd.DataFrame:
    """Calculate monthly shares for approved module-specific domain signals."""
    if df.empty:
        return pd.DataFrame(columns=["Month", "Signal", "Share", "Queries", "Total"])

    total = df.groupby("month_period", observed=True).size().rename("Total")
    records: list[pd.DataFrame] = []
    for label, domain in signals:
        counts = (
            df.loc[df["domain_label"].eq(domain)]
            .groupby("month_period", observed=True)
            .size()
            .rename("Queries")
        )
        joined = pd.concat([total, counts], axis=1).fillna(0).reset_index()
        joined["Signal"] = label
        joined["Share"] = joined["Queries"] / joined["Total"]
        records.append(
            joined.rename(columns={"month_period": "Month"})[
                ["Month", "Signal", "Share", "Queries", "Total"]
            ]
        )
    return pd.concat(records, ignore_index=True)
