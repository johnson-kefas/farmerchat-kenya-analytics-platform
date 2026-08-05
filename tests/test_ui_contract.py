"""Presentation-layer contract tests for the responsive dashboard redesign."""

from __future__ import annotations

import unittest
from unittest.mock import patch
from pathlib import Path

from src.charts import horizontal_bar
from src.components import metric_grid
from src.config import APP_VERSION, LIVESTOCK_MODULE, PROJECT_ROOT

import pandas as pd


class DashboardUIContractTests(unittest.TestCase):
    def test_responsive_css_contract(self) -> None:
        css = (PROJECT_ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns: repeat(", css)
        self.assertIn("auto-fit", css)
        self.assertIn("flex-wrap: wrap", css)
        self.assertIn('data-testid="stColumn"', css)
        self.assertIn("word-break: normal", css)
        self.assertIn("hyphens: none", css)

    def test_streamlit_material_icons_keep_their_native_font(self) -> None:
        css = (PROJECT_ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
        self.assertNotIn('[class*="st-"]', css)
        self.assertNotIn('[class*="css"]', css)
        self.assertIn('[data-testid="stIconMaterial"]', css)
        self.assertIn('font-family: "Material Symbols Rounded" !important', css)

    def test_metric_grid_uses_the_html_renderer_without_markdown_indentation(self) -> None:
        with patch("src.components.st.html") as html_renderer:
            metric_grid(
                [
                    {
                        "label": "Unique <approved> queries",
                        "value": 327000,
                        "note": "One retained row per query",
                        "accent": "teal",
                    },
                    {
                        "label": "Missing county",
                        "value": 1200,
                        "note": "Production records",
                        "accent": "pink",
                    },
                ]
            )

        html_renderer.assert_called_once()
        markup = html_renderer.call_args.args[0]
        self.assertNotIn("\n", markup)
        self.assertEqual(markup.count('<article class="metric-card'), 2)
        self.assertIn("Unique &lt;approved&gt; queries", markup)
        self.assertNotIn("unsafe_allow_html", markup)

    def test_custom_html_is_not_sent_through_markdown(self) -> None:
        component_source = (PROJECT_ROOT / "src" / "components.py").read_text(
            encoding="utf-8"
        )
        filter_source = (PROJECT_ROOT / "src" / "filters.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("unsafe_allow_html", component_source)
        self.assertNotIn("unsafe_allow_html", filter_source)

    def test_module_switch_and_livestock_filters_are_present(self) -> None:
        filter_source = (PROJECT_ROOT / "src" / "filters.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('key="analytics_module"', filter_source)
        self.assertIn('"Livestock Type"', filter_source)
        self.assertIn('"Confidence Level"', filter_source)
        self.assertIn("filter_intents", filter_source)
        self.assertEqual(
            LIVESTOCK_MODULE.asset_type_map["mixed_livestock"],
            "Mixed livestock",
        )

    def test_chart_uses_autosize_and_wrapped_title(self) -> None:
        frame = pd.DataFrame(
            {
                "Category": ["A long but readable category name", "Short label"],
                "Queries": [1200, 800],
            }
        )
        figure = horizontal_bar(
            frame,
            "Category",
            "Queries",
            "A deliberately long chart title that should wrap cleanly on laptops",
            "A deliberately long subtitle that should remain fully visible",
        )
        self.assertTrue(figure.layout.autosize)
        self.assertIn("<br>", figure.layout.title.text)
        self.assertIsNone(figure.layout.width)

    def test_version_is_updated(self) -> None:
        self.assertEqual(APP_VERSION, "4.0.0")


if __name__ == "__main__":
    unittest.main()
