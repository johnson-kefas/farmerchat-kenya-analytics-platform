"""Application-wide configuration and module-specific semantic definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


APP_TITLE = "FarmerChat Kenya Analytics"
APP_VERSION = "4.2.0"
PRODUCTION_YEARS = (2025, 2026)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

COMMON_SOURCE_PREFIX = (
    "asset_type",
    "asset_name",
    "query",
    "query_original",
    "user_country",
    "user_geo_level2",
    "query_year_month",
    "language",
    "value_chain",
    "clean_asset_type",
)

COMMON_SOURCE_SUFFIX = (
    "query_cleaning_changed",
    "query_is_garbled",
    "query_word_count",
    "query_duplicate_count",
    "is_duplicate_query",
    "classification_status",
    "primary_domain",
    "primary_subdomain",
    "primary_intent_id",
    "primary_farmer_intent",
    "primary_intent_score",
    "primary_match_evidence",
    "secondary_domain",
    "secondary_subdomain",
    "secondary_intent_id",
    "secondary_farmer_intent",
    "secondary_intent_score",
    "secondary_match_evidence",
    "matched_intent_count",
    "domain_confidence",
    "domain_review_flag",
    "domain_review_reason",
)


@dataclass(frozen=True)
class ModuleConfig:
    """Describe one analytics module without duplicating application logic."""

    key: str
    label: str
    sidebar_subtitle: str
    dataset_filename: str
    data_env_var: str
    component_column: str
    review_flag_column: str
    review_status_column: str
    asset_type_labels: tuple[tuple[str, str], ...]
    mixed_asset_label: str
    page_options: tuple[tuple[str, str], ...]
    time_signals: tuple[tuple[str, str], ...]

    @property
    def default_data_path(self) -> Path:
        """Return the packaged authoritative source path."""
        return PROJECT_ROOT / "data" / self.dataset_filename

    @property
    def source_columns(self) -> tuple[str, ...]:
        """Return the exact approved schema expected for this module."""
        return (
            *COMMON_SOURCE_PREFIX[:8],
            self.component_column,
            *COMMON_SOURCE_PREFIX[8:],
            *COMMON_SOURCE_SUFFIX[:5],
            self.review_flag_column,
            self.review_status_column,
            *COMMON_SOURCE_SUFFIX[5:],
        )

    @property
    def asset_type_map(self) -> dict[str, str]:
        """Return source-to-display labels for asset types."""
        return dict(self.asset_type_labels)


CROP_MODULE = ModuleConfig(
    key="crop",
    label="Crop",
    sidebar_subtitle="Crop query analytics",
    dataset_filename=(
        "farmerchat_kenya_crop_intent_labelled_deduplicated_"
        "asset_standardized_v_4.0.0.csv"
    ),
    data_env_var="FARMERCHAT_CROP_DATA_PATH",
    component_column="intercrop_components",
    review_flag_column="crop_review_flag",
    review_status_column="crop_review_status",
    asset_type_labels=(
        ("crop", "Single crop"),
        ("intercrop", "Intercrop"),
    ),
    mixed_asset_label="Intercrop",
    page_options=(
        ("data_quality", "1. Data quality"),
        ("value_chains", "2. Asset type analysis"),
        ("domains", "3. Agricultural domains"),
        ("subdomains", "4. Subdomain analysis"),
        ("geography", "5. Geographic analysis"),
        ("time_trends", "6. Time trends"),
    ),
    time_signals=(
        ("Crop planning", "Crop Planning"),
        ("Pest and disease", "Crop Pest and Disease"),
        ("Harvest and storage", "Harvest and Storage"),
    ),
)

LIVESTOCK_MODULE = ModuleConfig(
    key="livestock",
    label="Livestock",
    sidebar_subtitle="Livestock query analytics",
    dataset_filename=(
        "farmerchat_kenya_livestock_intent_labelled_deduplicated_"
        "asset_standardized_v_4.0.0.csv"
    ),
    data_env_var="FARMERCHAT_LIVESTOCK_DATA_PATH",
    component_column="mixed_livestock_components",
    review_flag_column="livestock_review_flag",
    review_status_column="livestock_review_status",
    asset_type_labels=(
        ("livestock", "Single livestock"),
        ("mixed_livestock", "Mixed livestock"),
    ),
    mixed_asset_label="Mixed livestock",
    page_options=(
        ("data_quality", "1. Data quality"),
        ("value_chains", "2. Livestock value chain"),
        ("domains", "3. Agricultural domains"),
        ("subdomains", "4. Subdomain analysis"),
        ("geography", "5. Geographic analysis"),
        ("time_trends", "6. Time trends"),
    ),
    time_signals=(
        ("Livestock planning", "Livestock Planning"),
        ("Livestock management", "Livestock Management"),
        ("Weather risk", "Climate and Weather Risk"),
    ),
)

MODULES = {
    CROP_MODULE.key: CROP_MODULE,
    LIVESTOCK_MODULE.key: LIVESTOCK_MODULE,
}
MODULE_OPTIONS = tuple(MODULES)
DEFAULT_MODULE_KEY = CROP_MODULE.key

# Backwards-compatible crop aliases retained for tests and external imports.
DEFAULT_DATA_PATH = CROP_MODULE.default_data_path
SOURCE_COLUMNS = list(CROP_MODULE.source_columns)
ASSET_TYPE_LABELS = CROP_MODULE.asset_type_map
PAGE_OPTIONS = [label for _, label in CROP_MODULE.page_options]

CORE_REQUIRED_FIELDS = [
    "query",
    "asset_type",
    "asset_name",
    "value_chain",
    "user_country",
    "query_year_month",
    "language",
]

METADATA_FIELDS = [
    "user_country",
    "user_geo_level2",
    "query_year_month",
    "language",
]

QUALITY_FIELDS = {
    "query": "Query text",
    "asset_type": "Asset type",
    "asset_name": "Asset name",
    "value_chain": "Value chain",
    "user_country": "Country",
    "user_geo_level2": "County",
    "query_year_month": "Year and month",
    "language": "Language",
    "primary_domain": "Primary domain",
    "primary_subdomain": "Primary subdomain",
    "primary_farmer_intent": "Primary farmer intent",
}

FIELD_INTERPRETATIONS = {
    "Query text": "Required core field",
    "Asset type": "Required core field",
    "Asset name": "Required core field",
    "Value chain": "Required core field",
    "Country": "Required metadata",
    "County": "Optional geographic metadata",
    "Year and month": "Required time metadata",
    "Language": "Required metadata",
    "Primary domain": "Classification coverage",
    "Primary subdomain": "Classification coverage",
    "Primary farmer intent": "Classification coverage",
}

CONFIDENCE_LABELS = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "no_match": "No match",
}

UNCLASSIFIED = "Unclassified"
MISSING_COUNTY = "Missing county"

MONTH_ORDER = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

SEASON_PHASES = {
    1: "Before MAM",
    2: "Before MAM",
    3: "MAM long rains",
    4: "MAM long rains",
    5: "MAM long rains",
    6: "Jun-Jul transition",
    7: "Jun-Jul transition",
    8: "Before OND",
    9: "Before OND",
    10: "OND short rains",
    11: "OND short rains",
    12: "OND short rains",
}

COLORS = {
    "ink": "#182230",
    "muted": "#667085",
    "grid": "#E7E9EE",
    "surface": "#FFFFFF",
    "blue": "#52658F",
    "blue_dark": "#34466B",
    "blue_light": "#E8ECF4",
    "teal": "#4F7C78",
    "teal_light": "#E6EFEE",
    "gold": "#96764F",
    "gold_light": "#F3ECE3",
    "olive": "#6C7958",
    "pink": "#896477",
    "grey": "#98A2B3",
    "grey_light": "#EEF0F3",
}

CATEGORY_PALETTE = [
    COLORS["blue"],
    COLORS["teal"],
    COLORS["gold"],
    COLORS["olive"],
    COLORS["pink"],
]

PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "farmerchat_dashboard_chart",
        "height": 900,
        "width": 1600,
        "scale": 2,
    },
}
