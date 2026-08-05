"""Sidebar module navigation, global filters, and filtered-data export."""

from __future__ import annotations

import streamlit as st

from src.config import (
    APP_VERSION,
    DEFAULT_MODULE_KEY,
    MODULE_OPTIONS,
    MODULES,
    ModuleConfig,
    PRODUCTION_YEARS,
)
from src.data import export_filtered_data
from src.formatting import compact_number


FILTER_NAMES = (
    "filter_years",
    "filter_counties",
    "filter_asset_types",
    "filter_value_chains",
    "filter_domains",
    "filter_subdomains",
    "filter_intents",
    "filter_confidence_levels",
)


def _sorted_options(values) -> list:
    return sorted(
        values.dropna().unique().tolist(),
        key=lambda value: str(value).casefold(),
    )


def _widget_key(module: ModuleConfig, name: str) -> str:
    """Namespace widget state so module switches never leak filter selections."""
    return f"{module.key}_{name}"


def render_module_selector() -> ModuleConfig:
    """Render the shared product brand and top-level analytics module switch."""
    current_key = st.session_state.get("analytics_module", DEFAULT_MODULE_KEY)
    current = MODULES.get(current_key, MODULES[DEFAULT_MODULE_KEY])
    with st.sidebar:
        st.html(
            '<div class="sidebar-brand">'
            '<span class="sidebar-brand__mark">FC</span>'
            "<div>"
            "<strong>FarmerChat Kenya</strong>"
            f"<span>{current.sidebar_subtitle}</span>"
            "</div>"
            "</div>"
        )
        st.caption(f"Analytics platform v{APP_VERSION}")
        st.html('<h2 class="sidebar-heading module-heading">Analytics module</h2>')
        selected_key = st.radio(
            "Analytics module",
            MODULE_OPTIONS,
            format_func=lambda key: MODULES[key].label,
            key="analytics_module",
            horizontal=True,
            label_visibility="collapsed",
        )
    return MODULES[selected_key]


def render_sidebar(base_df, module: ModuleConfig):
    """Render module-aware navigation and dashboard-wide filters."""
    labels_by_key = dict(module.page_options)
    labels = [label for _, label in module.page_options]
    with st.sidebar:
        st.divider()
        selected_label = st.radio(
            "Explore",
            labels,
            key=_widget_key(module, "dashboard_page"),
        )
        page_key = next(
            key for key, label in labels_by_key.items() if label == selected_label
        )

        st.divider()
        st.html('<h2 class="sidebar-heading">Filter dashboard</h2>')
        st.caption("Selections apply to every page. Blank fields include all values.")

        if st.button(
            "Reset filters",
            width="stretch",
            type="secondary",
            key=_widget_key(module, "reset_filters"),
        ):
            for name in FILTER_NAMES:
                st.session_state.pop(_widget_key(module, name), None)
            st.rerun()

        years = st.multiselect(
            "Year",
            list(PRODUCTION_YEARS),
            default=list(PRODUCTION_YEARS),
            key=_widget_key(module, "filter_years"),
            help="Only 2025 and 2026 are available. The 2024 test period is excluded.",
        )
        counties = st.multiselect(
            "County",
            _sorted_options(base_df["county_label"]),
            key=_widget_key(module, "filter_counties"),
        )
        asset_type_label = (
            "Livestock Type" if module.key == "livestock" else "Asset Type"
        )
        asset_types = st.multiselect(
            asset_type_label,
            _sorted_options(base_df["asset_type_label"]),
            key=_widget_key(module, "filter_asset_types"),
        )
        value_chains = st.multiselect(
            "Value Chain",
            _sorted_options(base_df["value_chain_label"]),
            key=_widget_key(module, "filter_value_chains"),
            help="Type in the box to search the approved value-chain list.",
        )
        domains = st.multiselect(
            "Domain",
            _sorted_options(base_df["domain_label"]),
            key=_widget_key(module, "filter_domains"),
        )
        subdomains = st.multiselect(
            "Subdomain",
            _sorted_options(base_df["subdomain_label"]),
            key=_widget_key(module, "filter_subdomains"),
        )

        intents: list = []
        confidence_levels: list = []
        if module.key == "livestock":
            intents = st.multiselect(
                "Intent",
                _sorted_options(base_df["intent_label"]),
                key=_widget_key(module, "filter_intents"),
            )
            confidence_levels = st.multiselect(
                "Confidence Level",
                _sorted_options(base_df["confidence_label"]),
                key=_widget_key(module, "filter_confidence_levels"),
            )

    return page_key, {
        "years": years,
        "counties": counties,
        "asset_types": asset_types,
        "value_chains": value_chains,
        "domains": domains,
        "subdomains": subdomains,
        "intents": intents,
        "confidence_levels": confidence_levels,
    }


def render_export(filtered_df, module: ModuleConfig) -> None:
    """Offer an explicit, lazy export for the active module."""
    with st.sidebar:
        st.divider()
        st.markdown("### Filter result")
        st.html(f'<div class="sidebar-count">{compact_number(len(filtered_df))}</div>')
        st.caption(f"approved {module.label.lower()} query rows")

        with st.expander("Download filtered data"):
            export_format = st.radio(
                "Format",
                ["Compressed CSV (.csv.gz)", "CSV (.csv)"],
                help="Compressed CSV is recommended for large selections.",
                key=_widget_key(module, "export_format"),
            )
            if st.checkbox(
                "Prepare the current filtered selection",
                key=_widget_key(module, "prepare_download"),
                help="Large selections can take a few seconds to prepare.",
            ):
                compressed = export_format.startswith("Compressed")
                with st.spinner("Preparing filtered data..."):
                    payload = export_filtered_data(
                        filtered_df,
                        module,
                        compressed=compressed,
                    )
                extension = "csv.gz" if compressed else "csv"
                mime = "application/gzip" if compressed else "text/csv"
                st.download_button(
                    "Download filtered dataset",
                    data=payload,
                    file_name=(
                        f"farmerchat_{module.key}_filtered_2025_2026.{extension}"
                    ),
                    mime=mime,
                    width="stretch",
                    key=_widget_key(module, "download_button"),
                )
