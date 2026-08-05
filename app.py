"""FarmerChat Kenya unified Crop and Livestock Analytics entrypoint."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="FarmerChat Kenya Analytics",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.components import app_footer, load_css  # noqa: E402
from src.config import APP_TITLE, APP_VERSION, PROJECT_ROOT  # noqa: E402
from src.data import (  # noqa: E402
    apply_filters,
    load_approved_dataset,
    production_frame,
    resolve_data_path,
)
from src.filters import (  # noqa: E402
    render_export,
    render_module_selector,
    render_sidebar,
)
from src.pages import assets, data_quality, domains, geography, subdomains, time_trends  # noqa: E402


PAGE_RENDERERS = {
    "data_quality": data_quality.render,
    "value_chains": assets.render,
    "domains": domains.render,
    "subdomains": subdomains.render,
    "geography": geography.render,
    "time_trends": time_trends.render,
}


def main() -> None:
    """Load the active authoritative source and render one shared dashboard page."""
    load_css(PROJECT_ROOT / "assets" / "styles.css")
    module = render_module_selector()
    data_path = resolve_data_path(module)
    try:
        approved = load_approved_dataset(data_path, module)
    except (FileNotFoundError, ValueError, OSError) as exc:
        st.error(
            f"The approved {module.label.lower()} dashboard dataset could not be loaded.",
            icon="🚫",
        )
        st.code(str(exc))
        st.info(
            "Keep the packaged CSV in the data folder or set "
            f"{module.data_env_var} to its full path, then restart Streamlit."
        )
        st.stop()

    production = production_frame(approved)
    page_key, filters = render_sidebar(production, module)
    filtered = apply_filters(production, filters)

    renderer = PAGE_RENDERERS[page_key]
    renderer(filtered, module)
    render_export(filtered, module)
    app_footer(
        title=f"{APP_TITLE} · {module.label}",
        version=APP_VERSION,
        source_name=data_path.name,
    )


if __name__ == "__main__":
    main()
